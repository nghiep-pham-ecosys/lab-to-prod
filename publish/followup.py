"""Follow-up comments: one from the author 7 days after a post, a second at 14 days only when the post earned it.

    python -m publish.followup due  [--date YYYY-MM-DD] [--out FILE] [--summary FILE]
    python -m publish.followup post --file approved.json [--live] [--out FILE] [--summary FILE]

`due` reads published.json and metrics/metrics.csv and calls nothing. It prints a JSON list of the follow-ups that
are due on `--date` (default: today, local time from publish/config.yaml):

- number 1: 7 to 9 days after the post went public (GRACE_DAYS covers a missed day or a weekend);
- number 2: 14 to 16 days after the post, only when follow-up 1 is recorded and the post has comments from other
  people or above-median impressions on that channel in metrics/metrics.csv;
- never more than 2 per post and channel. They are recorded in published.json under `<post key>:followup1` and
  `<post key>:followup2`, so other readers (comments.py, metrics/collect.py) skip them (common.is_followup_key).

Each item: {channel, post_key, post_url, number, key, due_on, mode, metrics, comments}. `metrics` is the latest row
for that post and channel (counts only), `comments` its comment count. Nothing personal is read or written: no
names, no comment text, so the output is safe for a public run log.

`post` reads a JSON list of {channel, post_key, number, text} that the author approved. For each item it checks the
rules again (post known, number 1 or 2, follow-up 1 before 2, not before its day, not recorded yet), then posts one
top-level comment and records it in published.json at once, so a second run never posts twice. Without `--live` it
prints the plan and calls nothing. A `PAUSE` file at the repository root stops a live run before any call. X (and any
channel set to `manual` in config.yaml) is never called: the item comes back as `manual` with the record_manual
commands. A follow-up never names or quotes a commenter; its text is public in the run log.

Secrets: LINKEDIN_ACCESS_TOKEN, LINKEDIN_PERSON_URN (LinkedIn), FB_PAGE_ID, FB_PAGE_TOKEN (Facebook) and
YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN (YouTube). A channel whose secrets are missing is refused with a
note. Errors print the platform's message, never a token.

LinkedIn Comments API (docs checked 27 Nov 2026, version li-lms-2026-11):
  https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/comments-api
- "Create a Comment": POST https://api.linkedin.com/rest/socialActions/{shareUrn|ugcPostUrn|commentUrn}/comments with
  the headers Linkedin-Version (YYYYMM), X-Restli-Protocol-Version 2.0.0 and Content-Type application/json.
  Body: `actor` (person URN, required), `message.text` (required), `object` (the share or ugcPost, as in the URL).
  `parentComment` is only for nested comments, so a follow-up leaves it out.
- The new comment id comes back in the `x-restli-id` header; the body also has `id` and `commentUrn`.
- Permission: the page lists `w_member_social_feed` ("Post, comment, and react on posts on behalf of an
  authenticated member"). The self-serve token has `w_member_social`. The first comment in publish/linkedin.py uses
  the same call on the v2 path and works live with that token (published.json: comment true), so a follow-up uses
  that path too. A 401 or 403 is still reported as `refused`, and the author posts that comment by hand and records it
  with record_manual. 429 means the one-minute comment rate limit.

Facebook Graph API (docs checked 27 Nov 2026, version from publish/config.yaml):
  https://developers.facebook.com/docs/graph-api/reference/object/comments/
- POST /{object-id}/comments with `message` "publishes a new comment on any object" (Page posts, photos, posts,
  videos) and returns {"id": "{comment-id}"}. It needs a Page token of someone with the MODERATE task and
  `pages_manage_engagement`. publish/comments.py already does this call (Facebook.reply) and maps a refusal to
  ScopeRefused; this module reuses it with the post id instead of a comment id.

YouTube Data API v3 (docs checked 27 Nov 2026):
  https://developers.google.com/youtube/v3/docs/commentThreads/insert
  https://developers.google.com/youtube/v3/docs/channels/list
- commentThreads.insert: POST https://www.googleapis.com/youtube/v3/commentThreads?part=snippet, 50 units, scope
  youtube.force-ssl (already in the token). The body must set `snippet.channelId`, `snippet.videoId` and
  `snippet.topLevelComment.snippet.textOriginal`; it returns a commentThread resource (its `id` is kept).
- `snippet.channelId` is our own channel (the video is ours): channels.list mine=true, part=id (1 unit), through
  publish/comments.py (YouTube.me).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import statistics
import sys
from pathlib import Path
from urllib.parse import quote

import requests

from . import comments
from .common import FOLLOWUP, ROOT, Context, PublishError, State, is_followup_key, load_config, paused
from .linkedin import API, _author as linkedin_author
from .youtube import API as YT_API

CHANNELS = ("linkedin", "facebook", "youtube", "x")   # where a follow-up makes sense; x is always by hand
API_CHANNELS = ("linkedin", "facebook", "youtube")
NEEDS = {"linkedin": ("LINKEDIN_ACCESS_TOKEN", "LINKEDIN_PERSON_URN"), **comments.NEEDS}
DAYS = {1: 7, 2: 14}    # follow-up number -> days after the post
GRACE_DAYS = 2          # a follow-up stays due this many days after its day, then it is skipped
MAX_FOLLOWUPS = 2
YT_INSERT_UNITS = 50    # commentThreads.insert
COUNTS = ("impressions", "views", "reactions", "comments", "shares")


def followup_key(post_key: str, number: int) -> str:
    return f"{post_key}{FOLLOWUP}{number}"


def public_day(entry: dict, tz: dt.timezone) -> dt.date | None:
    """The local day the post went public: its scheduled time if it had one, else when it was recorded."""
    raw = entry.get("scheduled_for") or entry.get("at")
    if not raw:
        return None
    try:
        return comments._when(str(raw)).astimezone(tz).date()
    except ValueError:
        return None


def channel_mode(cfg: dict, channel: str) -> str:
    return "manual" if channel == "x" else ("api" if cfg.get("channels", {}).get(channel) == "api" else "manual")


# --- metrics -------------------------------------------------------------------------------------------------------

def _num(raw) -> float | None:
    try:
        return float(raw) if str(raw).strip() != "" else None
    except ValueError:
        return None


def load_metrics(root: Path) -> list[dict]:
    path = root / "metrics" / "metrics.csv"
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def latest(rows: list[dict], day: dt.date) -> dict[tuple[str, str], dict]:
    """(item, channel) -> the newest row measured on or before `day`."""
    out: dict[tuple[str, str], dict] = {}
    for r in rows:
        if (r.get("measured_on") or "") > day.isoformat() or is_followup_key(r.get("item", "")):
            continue
        k = (r.get("item", ""), r.get("channel", ""))
        if k not in out or r["measured_on"] >= out[k]["measured_on"]:
            out[k] = r
    return out


def reach(row: dict | None) -> float | None:
    """Impressions; YouTube has no impressions column, so its views stand in."""
    if not row:
        return None
    value = _num(row.get("impressions"))
    return value if value is not None else _num(row.get("views"))


def median_reach(newest: dict[tuple[str, str], dict], channel: str) -> float | None:
    values = [v for (item, ch), r in newest.items() if ch == channel and item != "_account"
              for v in [reach(r)] if v is not None]
    return statistics.median(values) if values else None


def summary_of(row: dict | None) -> dict:
    if not row:
        return {}
    out = {"measured_on": row.get("measured_on", "")}
    for name in COUNTS:
        value = _num(row.get(name))
        if value is not None:
            out[name] = int(value)
    return out


def ours(state: dict, post_key: str, channel: str, measured_on: str) -> int:
    """Comments counted in a metrics row that are ours: the LinkedIn first comment, and follow-up 1 when it was
    posted on or before the day the row was measured."""
    count = 1 if channel == "linkedin" and (state.get(post_key, {}).get("linkedin") or {}).get("comment") else 0
    first = (state.get(followup_key(post_key, 1)) or {}).get(channel) or {}
    if first and str(first.get("at", ""))[:10] <= measured_on:
        count += 1
    return count


# --- due -----------------------------------------------------------------------------------------------------------

def due(state: dict, rows: list[dict], day: dt.date, tz: dt.timezone, cfg: dict) -> tuple[list[dict], list[str]]:
    """The follow-ups due on `day`, and notes on the ones held back (no personal data in either)."""
    newest = latest(rows, day)
    found, notes = [], []
    for post_key in sorted(state):
        if is_followup_key(post_key):
            continue
        for channel in CHANNELS:
            entry = state[post_key].get(channel) or {}
            posted = public_day(entry, tz) if entry.get("url") else None
            if posted is None:
                continue
            age = (day - posted).days
            done = [n for n in DAYS if (state.get(followup_key(post_key, n)) or {}).get(channel)]
            if len(done) >= MAX_FOLLOWUPS:
                continue
            number = 1 if 1 not in done else 2
            if not DAYS[number] <= age <= DAYS[number] + GRACE_DAYS:
                continue
            row = newest.get((post_key, channel))
            if number == 2:
                others = None
                if row and _num(row.get("comments")) is not None:
                    others = int(_num(row["comments"])) - ours(state, post_key, channel, row["measured_on"])
                median, mine = median_reach(newest, channel), reach(row)
                above = median is not None and mine is not None and mine > median
                if not (others and others > 0) and not above:
                    why = "no metrics for this post" if row is None else "no comments from others, reach not above median"
                    notes.append(f"{channel} {post_key}: follow-up 2 not due ({why})")
                    continue
            found.append({
                "channel": channel, "post_key": post_key, "post_url": entry.get("url", ""), "number": number,
                "key": followup_key(post_key, number),
                "due_on": (posted + dt.timedelta(days=DAYS[number])).isoformat(),
                "mode": channel_mode(cfg, channel), "metrics": summary_of(row),
                "comments": int(_num(row["comments"])) if row and _num(row.get("comments")) is not None else None,
            })
    return found, notes


# --- post ----------------------------------------------------------------------------------------------------------

class LinkedIn:
    def __init__(self, ctx: Context):
        self.http, self.token, self.author = ctx.http, ctx.secret("LINKEDIN_ACCESS_TOKEN"), linkedin_author(ctx)

    def comment(self, entry: dict, text: str) -> str:
        urn = str(entry["id"])
        # Same v2 endpoint and headers as the first comment in publish/linkedin.py, which works live with the
        # self-serve w_member_social token (published.json records comment: true from 2026-11).
        resp = self.http.post(f"{API}/socialActions/{quote(urn, safe='')}/comments", timeout=30, headers={
            "Authorization": f"Bearer {self.token}", "X-Restli-Protocol-Version": "2.0.0"},
            json={"actor": self.author, "object": urn, "message": {"text": text}})
        if resp.status_code in (401, 403):
            raise comments.ScopeRefused(f"LinkedIn refused the comment (HTTP {resp.status_code}): the comments API "
                                        "refused the token; post it by hand and record it with record_manual")
        if resp.status_code not in (200, 201):
            raise comments._fail(resp, "LinkedIn comment", self.token)
        headers = {k.lower(): v for k, v in (getattr(resp, "headers", None) or {}).items()}
        try:
            body = resp.json()
        except ValueError:
            body = {}
        return headers.get("x-restli-id") or body.get("commentUrn") or body.get("id") or ""


class Facebook(comments.Facebook):
    def comment(self, entry: dict, text: str) -> str:
        return self.reply(self.object_id(entry), text)   # POST /{object-id}/comments works on posts and comments


class YouTube(comments.YouTube):
    def comment(self, entry: dict, text: str) -> str:
        body = {"snippet": {"channelId": self.me(), "videoId": str(entry["id"]),
                            "topLevelComment": {"snippet": {"textOriginal": text}}}}
        self.units += YT_INSERT_UNITS
        resp = self.http.post(f"{YT_API}/commentThreads", params={"part": "snippet"},
                              headers={**self.auth, "Content-Type": "application/json; charset=UTF-8"},
                              data=json.dumps(body))
        if resp.status_code == 403 and "insufficientPermissions" in (resp.text or ""):
            raise comments.ScopeRefused("YouTube refused the comment: the token lacks the youtube.force-ssl scope; "
                                        "renew it with scripts/tokens/youtube_token.py (docs/setup.md, section 5)")
        if resp.status_code not in (200, 201):
            raise comments._fail(resp, "YouTube commentThreads.insert")
        return resp.json().get("id", "")


CLIENTS = {"linkedin": LinkedIn, "facebook": Facebook, "youtube": YouTube}


def _client(ctx: Context, channel: str):
    """(client, None) or (None, why)."""
    missing = [n for n in NEEDS[channel] if not ctx.env.get(n, "").strip()]
    if missing:
        return None, f"secrets not set: {', '.join(missing)}"
    try:
        return CLIENTS[channel](ctx), None
    except PublishError as exc:
        return None, str(exc)


def load_approved(path: Path) -> list[dict]:
    """Read and check the approved file before anything is called."""
    try:
        items = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PublishError(f"approved file {path} is not valid JSON: {exc}") from exc
    if not isinstance(items, list):
        raise PublishError("approved must be a JSON list of {channel, post_key, number, text}")
    for i, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise PublishError(f"item {i} is not an object")
        if item.get("channel") not in CHANNELS:
            raise PublishError(f"item {i}: channel must be one of {', '.join(CHANNELS)}")
        if item.get("number") not in DAYS or isinstance(item.get("number"), bool):
            raise PublishError(f"item {i}: number must be 1 or 2")
        if not str(item.get("post_key", "")).strip() or not str(item.get("text", "")).strip():
            raise PublishError(f"item {i}: post_key and text are required")
        if is_followup_key(str(item["post_key"])):
            raise PublishError(f"item {i}: post_key must be the post, not a follow-up")
    return items


def _manual_detail(fkey: str, channel: str) -> str:
    return (f"post by hand, then: python -m publish.record_manual check --key {fkey} --channel {channel}; "
            f"python -m publish.record_manual record --key {fkey} --channel {channel} --url <comment link>")


def post_followups(ctx: Context, state: State, items: list[dict]) -> tuple[list[dict], bool]:
    """Post each approved follow-up once and record it at once. Returns (one result per item, ok)."""
    results, clients, refused, seen, ok = [], {}, {}, set(), True
    today = ctx.now.astimezone(ctx.tz).date()
    for item in items:
        channel, post_key, number = item["channel"], str(item["post_key"]).strip(), item["number"]
        text, fkey = str(item["text"]).strip(), followup_key(str(item["post_key"]).strip(), item["number"])
        row = {"channel": channel, "post_key": post_key, "number": number, "key": fkey, "status": "",
               "comment_id": "", "text": text, "detail": ""}
        results.append(row)
        if (fkey, channel) in seen:
            row.update(status="skipped", detail="listed twice in this file")
            continue
        seen.add((fkey, channel))
        if state.done(fkey, channel):
            row.update(status="skipped", detail="already recorded in published.json")
            continue
        entry = state.data.get(post_key, {}).get(channel) or {}
        posted = public_day(entry, ctx.tz)
        if not entry or posted is None:
            row.update(status="failed", detail=f"no {channel} post {post_key} in published.json")
            ok = False
            continue
        if number == 2 and not state.done(followup_key(post_key, 1), channel):
            row.update(status="refused", detail="follow-up 1 is not recorded yet")
            ok = False
            continue
        if today < posted + dt.timedelta(days=DAYS[number]):
            row.update(status="refused", detail=f"too early: due on {(posted + dt.timedelta(days=DAYS[number])).isoformat()}")
            ok = False
            continue
        if channel_mode(ctx.cfg, channel) == "manual":
            row.update(status="manual", detail=_manual_detail(fkey, channel))
            continue
        if not entry.get("id"):
            row.update(status="failed", detail=f"the {channel} record of {post_key} has no id")
            ok = False
            continue
        if not ctx.live:
            row.update(status="planned", detail="dry run: nothing called")
            continue
        if channel in refused:
            row.update(status="refused", detail=refused[channel])
            ok = False
            continue
        if channel not in clients:
            clients[channel], why = _client(ctx, channel)
            if clients[channel] is None:
                refused[channel] = why
                row.update(status="refused", detail=why)
                ok = False
                continue
        try:
            comment_id = clients[channel].comment(entry, text)
        except comments.ScopeRefused as exc:
            refused[channel] = str(exc)
            row.update(status="refused", detail=str(exc))
            ok = False
            continue
        except PublishError as exc:
            row.update(status="failed", detail=str(exc))
            ok = False
            continue
        state.record(fkey, channel, {"id": comment_id, "url": entry.get("url", ""), "post_id": str(entry["id"]),
                                     "via": "api"}, ctx.now)
        state.save()   # at once: a crash later in the run must not post this one again
        row.update(status="posted", comment_id=comment_id)
    yt = clients.get("youtube")
    if yt:
        ctx.say(f"youtube: {yt.units} quota units used")
    return results, ok


# --- output --------------------------------------------------------------------------------------------------------

def due_summary(found: list[dict], notes: list[str], day: dt.date) -> str:
    lines = [f"## Follow-ups due on {day.isoformat()}: {len(found)}", "",
             "| Channel | Post | No. | Due on | Mode | Comments | Reach |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for f in found:
        m = f["metrics"]
        reach_text = m.get("impressions", m.get("views", ""))
        comments_text = "" if f["comments"] is None else f["comments"]
        lines.append(f"| {f['channel']} | {f['post_url']} | {f['number']} | {f['due_on']} | {f['mode']} | "
                     f"{comments_text} | {reach_text} |")
    lines.append("")
    lines += [f"- {n}" for n in notes]
    return "\n".join(lines) + "\n"


def post_summary(results: list[dict], live: bool) -> str:
    lines = [f"## Follow-ups ({'live' if live else 'dry run'})", "",
             "| Channel | Key | Status | Comment id | Text | Detail |", "| --- | --- | --- | --- | --- | --- |"]
    for r in results:
        lines.append(f"| {r['channel']} | {r['key']} | {r['status']} | {r['comment_id']} | {comments._cell(r['text'])} | "
                     f"{comments._cell(r['detail'], 160)} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None, env=None, http=requests, root: Path = ROOT, now: dt.datetime | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m publish.followup", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    dp = sub.add_parser("due", help="print the follow-ups due on a day as JSON (calls nothing)")
    dp.add_argument("--date", help="YYYY-MM-DD, default today (local time)")
    pp = sub.add_parser("post", help="post approved follow-ups from a JSON file")
    pp.add_argument("--file", required=True, type=Path)
    pp.add_argument("--live", action="store_true", help="really post (otherwise print the plan and call nothing)")
    for p in (dp, pp):
        p.add_argument("--out", help="also write the JSON result to this file")
        p.add_argument("--summary", help="append a Markdown summary to this file (GITHUB_STEP_SUMMARY)")
    args = ap.parse_args(argv)

    env = dict(os.environ) if env is None else env
    ctx = Context(root=root, cfg=load_config(root), env=env, http=http,
                  now=now or dt.datetime.now(dt.timezone.utc), live=getattr(args, "live", False))
    state = State(root)

    if args.cmd == "due":
        try:
            day = dt.date.fromisoformat(args.date) if args.date else ctx.now.astimezone(ctx.tz).date()
        except ValueError:
            print(f"bad --date {args.date!r}: use YYYY-MM-DD", file=sys.stderr)
            return 2
        found, notes = due(state.data, load_metrics(root), day, ctx.tz, ctx.cfg)
        text = json.dumps(found, indent=2, ensure_ascii=False)
        print(text)
        for note in notes:
            print(note, file=sys.stderr)
        comments._write(args.out, text + "\n")
        comments._write(args.summary, due_summary(found, notes, day), append=True)
        return 0

    if ctx.live and paused(root):
        print("PAUSE file present: no follow-up is posted.")
        comments._write(args.summary, "PAUSE file present: no follow-up is posted.\n", append=True)
        return 0
    try:
        items = load_approved(args.file)
    except PublishError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    results, ok = post_followups(ctx, state, items)
    for r in results:
        print(f"{r['channel']} {r['key']}: {r['status']} {r['comment_id']} {r['detail']}".rstrip())
    comments._write(args.out, json.dumps(results, indent=2, ensure_ascii=False) + "\n")
    comments._write(args.summary, post_summary(results, ctx.live), append=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
