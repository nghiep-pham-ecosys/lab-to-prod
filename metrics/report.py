#!/usr/bin/env python3
"""Print the tables of the weekly report as markdown, from published.json and metrics.csv.

    python -m metrics.report --week 2026-W47
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import statistics
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from publish.common import ROOT, load_articles, load_config, load_posts  # noqa: E402

NUMBERS = ["impressions", "views", "reactions", "comments", "shares"]


def iso_week(d: dt.date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def latest_rows(root: Path) -> dict:
    """{(item, channel): the most recent metrics row}"""
    path, out = root / "metrics" / "metrics.csv", {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as fh:
            for r in sorted(csv.DictReader(fh), key=lambda r: r["measured_on"]):
                out[(r["item"], r["channel"])] = r
    return out


def followers(root: Path, week: str) -> dict:
    """{channel: (first, last)} follower counts measured inside the week."""
    path, out = root / "metrics" / "metrics.csv", {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as fh:
            for r in sorted(csv.DictReader(fh), key=lambda r: r["measured_on"]):
                if r["item"] == "_account" and r["followers"] and iso_week(dt.date.fromisoformat(r["measured_on"])) == week:
                    first, _ = out.get(r["channel"], (r["followers"], None))
                    out[r["channel"]] = (first, r["followers"])
    return out


def report(root: Path, week: str) -> str:
    cfg = load_config(root)
    state_path = root / "published.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    rows = latest_rows(root)
    items = [(p.key, p.date, p.meta["title"], [c for c in p.meta.get("channels", []) if c != "x_manual"])
             for p in load_posts(root) if p.folder.parent.name == week]
    items += [(a.key, a.date, a.meta["title"], ["devto"]) for a in load_articles(root) if iso_week(a.date) == week]
    out = [f"## Published, {week}", "", "| Date | Title | Channel | Status | Link |", "| --- | --- | --- | --- | --- |"]
    planned = done = 0
    for key, date, title, channels in sorted(items, key=lambda i: i[1]):
        for ch in channels:
            if cfg["channels"].get(ch) != "api":
                continue
            planned += 1
            rec = state.get(key, {}).get(ch)
            done += bool(rec)
            out.append(f"| {date} | {title} | {ch} | {'published ' + rec.get('at', '')[:16] if rec else 'not published'} | {rec.get('url', '') if rec else ''} |")
    out += ["", f"On schedule: {done} of {planned} planned channel posts" + (f" ({done / planned:.0%})." if planned else "."), "",
            "## Numbers (latest measurement)", "", "| Date | Channel | " + " | ".join(NUMBERS) + " |", "| --- | --- |" + " --- |" * len(NUMBERS)]
    week_keys = {i[0] for i in items}
    for (item, ch), r in sorted(rows.items()):
        if item in week_keys:
            out.append(f"| {item} | {ch} | " + " | ".join(r[n] or "-" for n in NUMBERS) + " |")
    earlier: dict = {}
    for (item, ch), r in rows.items():
        if item not in week_keys and item != "_account":
            for n in NUMBERS:
                if r[n]:
                    earlier.setdefault((ch, n), []).append(float(r[n]))
    if earlier:
        out += ["", "Median of earlier items: " + ", ".join(f"{ch} {n} {statistics.median(vals):g}" for (ch, n), vals in sorted(earlier.items())) + "."]
    else:
        out += ["", "No earlier items to compare with yet."]
    out += ["", "## Followers during the week", "", "| Channel | First | Last | Change |", "| --- | --- | --- | --- |"]
    for ch, (first, last) in sorted(followers(root, week).items()):
        out.append(f"| {ch} | {first} | {last} | {int(float(last)) - int(float(first)):+d} |")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--week", required=True)
    args = ap.parse_args(argv)
    print(report(ROOT, args.week))
    return 0


if __name__ == "__main__":
    sys.exit(main())
