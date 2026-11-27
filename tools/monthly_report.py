#!/usr/bin/env python3
"""Write the monthly post performance report reports/YYYY-MM.md.

    python tools/monthly_report.py --month 2026-11                 # reads the publish-state branch
    python tools/monthly_report.py --month 2026-11 --metrics m.csv --state p.json --out /tmp/r.md

Inputs. `metrics/metrics.csv` and `published.json` are read from the `publish-state` branch with
`git show` after a `git fetch` of that one branch (tools/state_sync.py writes it; this tool never
writes it). `--metrics` and `--state` read local files instead. Titles, series, hook lines and formats
come from the post folders, the blog articles and `content/calendar.yaml` on the checkout.

This tool calls no platform API. Every number comes from metrics/metrics.csv, whose columns are
filled by metrics/collect.py (the API fields and their documentation are listed there). The column
meanings used here: `impressions` (LinkedIn export), `views` (YouTube viewCount, DEV page_views_count),
`reactions`, `comments`, `shares`, and `followers` on the `_account` rows.

Rules:
- A post is one item on one channel. Its month is the local date (config timezone_offset) of
  `scheduled_for`, or of `at` when the record has no schedule. Sub-records such as `<date>:reply`
  are not posts; `<date>:followup1` and `<date>:followup2` are the follow-up comments (lab-to-prod#62).
- Each post uses its last measurement in metrics.csv.
- Reach = impressions, or views when the row has no impressions.
  Engagement rate = (reactions + comments + shares) / reach. A reach of 0 has no rate.
- A post or channel with no metrics row is "no data", never 0. An empty column is "no data" too.
- Proposals are generated from the numbers in the report. They are proposals only; the author decides.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import re
import statistics
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

BRANCH = "publish-state"
ACCOUNT = "_account"
NO_DATA = "no data"
COUNTS = ("reactions", "comments", "shares")
FORMAT_ORDER = ("image", "PDF document", "Short", "article", "unknown")
_SUB = re.compile(r"^(\d{4}-\d{2}-\d{2}):(.+)$")
_FOLLOWUP = re.compile(r"^followup([12])$")
_MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


# ---------------------------------------------------------------- inputs

@dataclass
class Meta:
    """What the checkout knows about one item key."""
    title: str
    series: str = ""
    week: str = ""
    hooks: dict = field(default_factory=dict)   # {channel: first sentence}
    pdf: bool = False                           # linkedin.pdf in the post folder
    article: bool = False


def first_sentence(text: str, limit: int = 140, wrapped: bool = False) -> str:
    """The hook: the first sentence of the first line, for a table cell.

    `wrapped` joins the first paragraph first, for article bodies whose lines wrap mid-sentence.
    """
    para = next((p for p in re.split(r"\n\s*\n", (text or "").strip()) if p.strip()), "")
    lines = [s.strip() for s in para.splitlines() if s.strip()]
    line = " ".join(lines) if wrapped else (lines[0] if lines else "")
    line = re.split(r"(?<=[.!?])\s+", line, maxsplit=1)[0]
    return line if len(line) <= limit else line[: limit - 3].rstrip() + "..."


def iso_week(day: dt.date) -> str:
    y, w, _ = day.isocalendar()
    return f"{y}-W{w:02d}"


def load_meta(root: Path) -> dict[str, Meta]:
    """{item key: Meta} from the post folders and the blog articles."""
    from publish.common import load_articles, load_posts
    from publish.linkedin import DOCUMENT

    out: dict[str, Meta] = {}
    for p in load_posts(root):
        hooks = {}
        for ch in ("linkedin", "facebook", "telegram", "x", "youtube"):
            text = p.sections.get(ch, "")
            if text.strip():
                hooks[ch] = first_sentence(text)
        out[p.key] = Meta(str(p.meta.get("title", p.key)), str(p.meta.get("series", "")), p.folder.parent.name,
                          hooks, (p.folder / DOCUMENT).is_file())
    for a in load_articles(root):
        hook = first_sentence(a.body, wrapped=True)
        out[a.key] = Meta(str(a.meta.get("title", a.key)), str(a.meta.get("series", "")), iso_week(a.date),
                          {"devto": hook}, article=True)
    return out


def load_experiments(root: Path) -> dict[str, str]:
    """{week: experiment} from content/calendar.yaml."""
    cal = yaml.safe_load((root / "content" / "calendar.yaml").read_text(encoding="utf-8")) or {}
    return {str(w["week"]): str(w.get("experiment", "")) for w in cal.get("weeks", []) if w.get("experiment")}


def local_tz(root: Path) -> dt.timezone:
    cfg = yaml.safe_load((root / "publish" / "config.yaml").read_text(encoding="utf-8")) or {}
    off = str(cfg.get("timezone_offset", "+00:00"))
    sign = -1 if off.startswith("-") else 1
    hh, mm = off.lstrip("+-").split(":")
    return dt.timezone(sign * dt.timedelta(hours=int(hh), minutes=int(mm)))


def read_branch(root: Path, path: str, fetch: bool = True) -> str:
    """A file from origin/publish-state. Fetch updates only the remote-tracking ref."""
    if fetch:
        subprocess.run(["git", "fetch", "--quiet", "origin", f"+refs/heads/{BRANCH}:refs/remotes/origin/{BRANCH}"],
                       cwd=root, check=False, capture_output=True, text=True)
    proc = subprocess.run(["git", "show", f"origin/{BRANCH}:{path}"], cwd=root, check=False,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"cannot read {path} from origin/{BRANCH}: {proc.stderr.strip()}")
    return proc.stdout


# ---------------------------------------------------------------- model

def _num(value) -> float | None:
    value = (value or "").strip() if isinstance(value, str) else value
    if value in ("", None):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _when(rec: dict) -> dt.datetime | None:
    raw = rec.get("scheduled_for") or rec.get("at")
    if not raw:
        return None
    try:
        when = dt.datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    return when if when.tzinfo else when.replace(tzinfo=dt.timezone.utc)


@dataclass
class Post:
    key: str
    channel: str
    posted: dt.date
    meta: Meta
    row: dict | None = None      # last metrics row, or None

    @property
    def fmt(self) -> str:
        if self.meta.article or self.key.startswith("article:"):
            return "article"
        if self.channel == "youtube":
            return "Short"
        if not self.meta.week or self.key.startswith("notes:"):
            return "unknown"
        if self.channel == "linkedin" and self.meta.pdf:
            return "PDF document"
        return "image"

    @property
    def week(self) -> str:
        return self.meta.week or iso_week(self.posted)

    @property
    def hook(self) -> str:
        return self.meta.hooks.get(self.channel) or self.meta.hooks.get("linkedin") or ""

    @property
    def reach(self) -> float | None:
        if self.row is None:
            return None
        imp = _num(self.row.get("impressions"))
        return imp if imp is not None else _num(self.row.get("views"))

    def count(self, name: str) -> float | None:
        return None if self.row is None else _num(self.row.get(name))

    @property
    def engaged(self) -> float | None:
        vals = [self.count(n) for n in COUNTS]
        return None if all(v is None for v in vals) else sum(v or 0 for v in vals)

    @property
    def rate(self) -> float | None:
        reach, engaged = self.reach, self.engaged
        if not reach or engaged is None:
            return None
        return engaged / reach


def engagement_rate(reactions, comments, shares, reach) -> float | None:
    """(reactions + comments + shares) / reach; None without a positive reach or any count."""
    p = Post("x", "x", dt.date.min, Meta("x"), {"views": reach, "reactions": reactions, "comments": comments,
                                                "shares": shares})
    return p.rate


def parse_metrics(text: str) -> list[dict]:
    return sorted(csv.DictReader(io.StringIO(text)), key=lambda r: r.get("measured_on", ""))


def last_rows(rows: list[dict], until: dt.date | None = None) -> dict:
    """{(item, channel): last row measured on or before `until`}."""
    out = {}
    for r in rows:
        if until is None or dt.date.fromisoformat(r["measured_on"]) <= until:
            out[(r["item"], r["channel"])] = r
    return out


def build_posts(state: dict, rows: list[dict], meta: dict[str, Meta], tz: dt.tzinfo) -> list[Post]:
    """Every post in published.json (all months), each with its last metrics row."""
    latest = last_rows(rows)
    out = []
    for key, channels in state.items():
        if _SUB.match(key):
            continue
        m = meta.get(key) or Meta(key)
        for ch, rec in channels.items():
            when = _when(rec) if isinstance(rec, dict) else None
            if when is None:
                continue
            out.append(Post(key, ch, when.astimezone(tz).date(), m, latest.get((key, ch))))
    return sorted(out, key=lambda p: (p.posted, p.key, p.channel))


def in_month(day: dt.date, month: str) -> bool:
    return day.strftime("%Y-%m") == month


def pick_top_bottom(posts: list[Post], n: int = 3) -> tuple[list[Post], list[Post]]:
    """Top n and bottom n posts by engagement rate. Posts without a rate are left out.

    Ties: the top prefers more reach, the bottom prefers more reach too (a 0 % rate on 30 views says
    more than on 3). With fewer than 2n rated posts the bottom list skips posts already in the top.
    """
    rated = [p for p in posts if p.rate is not None]
    top = sorted(rated, key=lambda p: (-p.rate, -(p.reach or 0), p.key, p.channel))[:n]
    rest = [p for p in rated if p not in top]
    bottom = sorted(rest, key=lambda p: (p.rate, -(p.reach or 0), p.key, p.channel))[:n]
    return top, bottom


# ---------------------------------------------------------------- formatting

def pct(x: float | None) -> str:
    return NO_DATA if x is None else f"{x * 100:.1f} %"


def num(x: float | None) -> str:
    return NO_DATA if x is None else f"{x:,.0f}"


def cell(text: str) -> str:
    return (text or "-").replace("|", "\\|").replace("\n", " ")


def _stats(values: list[float]) -> tuple[float | None, float | None]:
    return (statistics.mean(values), statistics.median(values)) if values else (None, None)


def _sum(values: list[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return sum(vals) if vals else None


def followers(rows: list[dict], month: str) -> dict[str, tuple[float, float]]:
    """{channel: (first, last)} follower counts measured inside the month."""
    out: dict[str, tuple[float, float]] = {}
    for r in rows:
        f = _num(r.get("followers"))
        if r.get("item") == ACCOUNT and f is not None and r["measured_on"].startswith(month):
            first = out.get(r["channel"], (f, f))[0]
            out[r["channel"]] = (first, f)
    return out


# ---------------------------------------------------------------- report

def build_report(month: str, metrics_text: str, state: dict, meta: dict[str, Meta], experiments: dict[str, str],
                 tz: dt.tzinfo, source: str = "") -> str:
    rows = parse_metrics(metrics_text)
    every = build_posts(state, rows, meta, tz)
    posts = [p for p in every if in_month(p.posted, month)]
    measured = [r["measured_on"] for r in rows]
    out = [f"# Post performance, {month}", ""]
    if source:
        out.append(f"Source: {source}.")
    out.append(f"Posts in the month: {len(posts)} on {len({p.channel for p in posts})} channel(s). "
               + (f"Measurements from {min(measured)} to {max(measured)}; each post uses its last one."
                  if measured else "metrics.csv has no rows."))
    out += ["", "Engagement rate = (reactions + comments + shares) / reach. Reach = impressions, or views when a channel "
            "has no impressions. \"no data\" means nothing was measured, which is not 0.", ""]

    # per channel
    out += ["## Per channel", "",
            "| Channel | Posts | Measured | Reach | Reactions | Comments | Shares | Follower change | Engagement rate |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    fol = followers(rows, month)
    no_data_channels = []
    for ch in sorted({p.channel for p in posts} | set(fol)):
        mine = [p for p in posts if p.channel == ch]
        got = [p for p in mine if p.row is not None]
        if ch in fol:
            first, last = fol[ch]
            change = f"{int(last - first):+d}"
        else:
            change = NO_DATA
        if not got:
            if mine:
                no_data_channels.append((ch, len(mine)))
            out.append(f"| {ch} | {len(mine)} | 0 | {NO_DATA} | {NO_DATA} | {NO_DATA} | {NO_DATA} | {change} | {NO_DATA} |")
            continue
        with_reach = [p for p in got if p.reach]
        reach_sum = _sum([p.reach for p in got])
        engaged_sum = _sum([p.engaged for p in with_reach])
        rate = engaged_sum / sum(p.reach for p in with_reach) if with_reach and engaged_sum is not None else None
        out.append(f"| {ch} | {len(mine)} | {len(got)} | {num(reach_sum)} | "
                   + " | ".join(num(_sum([p.count(n) for p in got])) for n in COUNTS)
                   + f" | {change} | {pct(rate)} |")

    # top and bottom
    top, bottom = pick_top_bottom(posts)
    rated = [p for p in posts if p.rate is not None]
    out += ["", "## Top and bottom posts", "",
            f"{len(rated)} of {len(posts)} posts have a rate (a measurement with reach above 0)."
            + (" Fewer than 6, so the bottom list leaves out posts already in the top list." if 0 < len(rated) < 6 else ""),
            ""]
    for label, group in (("Top 3", top), ("Bottom 3", bottom)):
        out += [f"### {label}", ""]
        if not group:
            out += ["No post with a rate.", ""]
            continue
        out += ["| Rate | Reach | Channel | Date | Title | Series | Hook |", "| --- | --- | --- | --- | --- | --- | --- |"]
        for p in group:
            out.append(f"| {pct(p.rate)} | {num(p.reach)} | {p.channel} | {p.posted} | {cell(p.meta.title)} | "
                       f"{cell(p.meta.series)} | {cell(p.hook)} |")
        out.append("")

    # per series and per format
    for title, attr, order in (("Per series", "series", None), ("Per format", "fmt", FORMAT_ORDER)):
        groups: dict[str, list[Post]] = {}
        for p in posts:
            name = (p.meta.series or "unknown") if attr == "series" else p.fmt
            groups.setdefault(name, []).append(p)
        names = [n for n in (order or sorted(groups)) if n in groups]
        out += [f"## {title}", "", "| Name | Posts | Measured | Reach mean | Reach median | Rate mean | Rate median |",
                "| --- | --- | --- | --- | --- | --- | --- |"]
        for name in names:
            g = groups[name]
            reach = [p.reach for p in g if p.reach is not None]
            rates = [p.rate for p in g if p.rate is not None]
            rm, rmed = _stats(reach)
            em, emed = _stats(rates)
            out.append(f"| {cell(name)} | {len(g)} | {sum(p.row is not None for p in g)} | {num(rm)} | {num(rmed)} | "
                       f"{pct(em)} | {pct(emed)} |")
        out.append("")
    out.append("Reach mixes impressions and views across channels; compare a series or format within one channel "
               "before acting on it.")

    # experiments
    weeks = sorted({p.week for p in posts})
    exp_rows, verdicts = [], []
    for wk in weeks:
        text = experiments.get(wk, "")
        for ch in sorted({p.channel for p in posts if p.week == wk}):
            now = [p for p in every if p.week == wk and p.channel == ch and p.rate is not None]
            before = [p for p in every if p.week < wk and p.channel == ch and p.rate is not None]
            if not now:
                continue
            nm, bm = statistics.median(p.rate for p in now), (statistics.median(p.rate for p in before) if before else None)
            nr = statistics.median(p.reach for p in now)
            br = statistics.median(p.reach for p in before) if before else None
            exp_rows.append(f"| {wk} | {cell(text)} | {ch} | {len(now)} | {num(nr)} | {pct(nm)} | {len(before)} | "
                            f"{num(br)} | {pct(bm)} |")
            verdicts.append((wk, text, ch, len(now), nm, nr, len(before), bm, br))
    out += ["", "## Experiments", "",
            "Each week's posts against all earlier weeks on the same channel (medians, posts with a rate only).", ""]
    if exp_rows:
        out += ["| Week | Experiment | Channel | Posts | Reach median | Rate median | Earlier posts | Earlier reach median "
                "| Earlier rate median |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |", *exp_rows]
    else:
        out.append("No measured post in the month, so no experiment can be compared.")
    untested = [wk for wk in weeks if experiments.get(wk) and wk not in {v[0] for v in verdicts}]
    if untested:
        out += ["", "Weeks with an experiment and no measured post: "
                + "; ".join(f"{wk} ({experiments[wk]})" for wk in untested) + "."]

    # follow-ups
    out += ["", "## Follow-up comments", ""]
    fu = []
    for key, channels in state.items():
        m = _SUB.match(key)
        if not m or not _FOLLOWUP.match(m.group(2)):
            continue
        for ch, rec in channels.items():
            when = _when(rec) if isinstance(rec, dict) else None
            if when is None or not in_month(when.astimezone(tz).date(), month):
                continue
            day = when.astimezone(tz).date()
            mine = [r for r in rows if r["item"] == m.group(1) and r["channel"] == ch]
            before = next((r for r in reversed(mine) if dt.date.fromisoformat(r["measured_on"]) <= day), None)
            after = mine[-1] if mine and mine[-1] is not before else None
            fu.append((m.group(1), ch, _FOLLOWUP.match(m.group(2)).group(1), day, before, after))
    if not fu:
        out.append(f"No follow-up comment recorded in {month} (keys `<date>:followup1` and `<date>:followup2`).")
    else:
        out += ["| Post | Channel | No. | Commented on | Reach before | Reach now | Engaged before | Engaged now |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        for key, ch, n, day, before, after in sorted(fu):
            def vals(r):
                if r is None:
                    return NO_DATA, NO_DATA
                p = Post(key, ch, day, Meta(key), r)
                return num(p.reach), num(p.engaged)
            rb, eb = vals(before)
            ra, ea = vals(after)
            title = (meta.get(key) or Meta(key)).title
            out.append(f"| {cell(title)} | {ch} | {n} | {day} | {rb} | {ra} | {eb} | {ea} |")
        out += ["", f"{len(fu)} follow-up comment(s). \"now\" is the last measurement after the comment; "
                "no data means none was taken after it yet."]

    # proposals
    out += ["", "## Proposals for next month", "",
            "Proposals only, each tied to a number above. The author decides.", ""]
    props = proposals(posts, no_data_channels, verdicts, top)
    out += [f"{i}. {p}" for i, p in enumerate(props, 1)]
    return "\n".join(out) + "\n"


_HOW = {"linkedin": "drop the LinkedIn export in metrics/inbox/ each week",
        "facebook": "check why metrics.yml stores no per-post Facebook rows",
        "x": "note impressions by hand from the post analytics (the API is paid)",
        "telegram": "the Bot API has no view counts; decide if member count is enough"}


def proposals(posts: list[Post], no_data: list[tuple[str, int]], verdicts: list, top: list[Post]) -> list[str]:
    out = []
    if no_data:
        detail = ", ".join(f"{ch} ({n} posts: {_HOW.get(ch, 'add a source')})" for ch, n in no_data)
        out.append(f"Measure the channels with no data before judging them: {detail}.")
    groups: dict[str, list[float]] = {}
    for p in posts:
        if p.rate is not None:
            groups.setdefault(f"{p.channel} {p.fmt}" if p.fmt != "article" else "devto article", []).append(p.rate)
        if p.rate is not None and p.meta.series:
            groups.setdefault(f"series {p.meta.series}", []).append(p.rate)
    ranked = sorted(((statistics.median(v), len(v), k) for k, v in groups.items() if len(v) >= 2), reverse=True)
    if len(ranked) >= 2 and ranked[0][0] > ranked[-1][0]:
        hi, lo = ranked[0], ranked[-1]
        out.append(f"Give more slots to {hi[2]}: median rate {pct(hi[0])} over {hi[1]} posts, against {pct(lo[0])} "
                   f"for {lo[2]} over {lo[1]} posts. Small samples: treat it as a hint.")
    else:
        rated = sum(p.rate is not None for p in posts)
        out.append(f"Keep the mix of series and formats: only {rated} posts have a rate and no group with 2 or more "
                   "posts stands out yet.")
    tested = [v for v in verdicts if v[1]]
    if tested:
        wk, text, ch, n, nm, nr, nb, bm, br = tested[-1]
        if bm is None or nm == bm:
            why = "no earlier week to compare with" if bm is None else f"the same median rate as {nb} earlier posts ({pct(bm)})"
            out.append(f"Run the {wk} experiment (\"{text}\") again before deciding: {ch} has {n} measured posts that "
                       f"week, median rate {pct(nm)}, and {why}.")
        elif nm > bm:
            out.append(f"Keep the {wk} experiment (\"{text}\"): {ch} median rate {pct(nm)} over {n} posts against "
                       f"{pct(bm)} over {nb} earlier posts.")
        else:
            out.append(f"Drop or change the {wk} experiment (\"{text}\"): {ch} median rate {pct(nm)} over {n} posts, "
                       f"not above {pct(bm)} over {nb} earlier posts.")
    if len(out) < 3 and top:
        p = top[0]
        out.append(f"Reuse the hook pattern of \"{p.meta.title}\" ({p.channel}, rate {pct(p.rate)} on "
                   f"{num(p.reach)} reach): {p.hook or 'see the post'}")
    if len(out) < 3:
        out.append(f"Keep posting and measuring: {len(posts)} posts this month is too few for a stronger proposal.")
    return out[:3]


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--month", required=True, help="YYYY-MM")
    ap.add_argument("--metrics", type=Path, help="local metrics.csv instead of the publish-state branch")
    ap.add_argument("--state", type=Path, help="local published.json instead of the publish-state branch")
    ap.add_argument("--out", type=Path, help="default reports/YYYY-MM.md")
    ap.add_argument("--no-fetch", action="store_true", help="read origin/publish-state as it is")
    args = ap.parse_args(argv)
    if not _MONTH.match(args.month):
        print(f"bad --month {args.month!r}: use YYYY-MM", file=sys.stderr)
        return 2
    fetch = not args.no_fetch
    sources = []
    if args.metrics:
        metrics_text = args.metrics.read_text(encoding="utf-8")
        sources.append(f"metrics from {args.metrics.name}")
    else:
        metrics_text = read_branch(root, "metrics/metrics.csv", fetch)
        fetch = False
        sources.append(f"metrics/metrics.csv on {BRANCH}")
    if args.state:
        state = json.loads(args.state.read_text(encoding="utf-8"))
        sources.append(f"state from {args.state.name}")
    else:
        state = json.loads(read_branch(root, "published.json", fetch))
        sources.append(f"published.json on {BRANCH}")
    text = build_report(args.month, metrics_text, state, load_meta(root), load_experiments(root), local_tz(root),
                        ", ".join(sources))
    out = args.out or root / "reports" / f"{args.month}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
