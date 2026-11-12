#!/usr/bin/env python3
"""Publish approved content. Dry run by default: nothing is posted without --live.

    python -m publish.run --event merge              # what the merge trigger would do
    python -m publish.run --event daily --live       # what the weekday cron does
    python -m publish.run --event daily --date 2026-11-16 --only telegram
    python -m publish.run export --week 2026-W47     # write x.md, x-schedule.md, hashnode-*.md

Rules:
- Only posts with status "approved" are published. Articles are published on or after their date.
- published.json records every success; a second run skips what is already there (idempotent).
- A file named PAUSE at the repository root stops everything.
- A failing channel does not stop the others. The exit code is 1 if any channel failed.
- --dry-run is accepted for clarity; it is the default. --live is the only way to post.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "publish"

from . import devto, facebook, hashnode, linkedin, telegram, x, youtube  # noqa: E402
from .common import ROOT, Context, PublishError, Skip, State, default_env, load_articles, load_config, load_posts, paused  # noqa: E402

POST_CHANNELS = {"linkedin": linkedin, "facebook": facebook, "telegram": telegram, "youtube": youtube}
ARTICLE_CHANNELS = {"devto": devto}


def due_items(ctx: Context, event: str, channel: str, date: dt.date | None):
    """Items a channel should handle on this run."""
    today = date or ctx.now.astimezone(ctx.tz).date()
    if channel in ARTICLE_CHANNELS:
        # Articles go out on their own day; a missed day is caught up within a week.
        return [a for a in load_articles(ctx.root) if a.date <= today <= a.date + dt.timedelta(days=7)]
    posts = [p for p in load_posts(ctx.root) if p.meta.get("status") == "approved" and channel in (p.meta.get("channels") or [])]
    if event == "merge":   # the platform schedules by itself: hand over everything still ahead
        return [p for p in posts if p.date >= today or channel == "youtube"]
    return [p for p in posts if p.date == today]


def run(ctx: Context, event: str, only: list[str] | None = None, date: dt.date | None = None) -> int:
    if paused(ctx.root):
        ctx.say("PAUSE file present: nothing is published.")
        return 0
    state = State(ctx.root)
    failures = 0
    channels = [c for c in ctx.cfg["events"][event] if not only or c in only]
    for channel in channels:
        mode = ctx.cfg["channels"].get(channel, "off")
        if mode != "api":
            ctx.say(f"{channel}: {mode}, skipped")
            continue
        module = {**POST_CHANNELS, **ARTICLE_CHANNELS}[channel]
        for item in due_items(ctx, event, channel, date):
            label = f"{channel} {item.key}"
            if state.done(item.key, channel):
                ctx.say(f"{label}: already published, skipped")
                continue
            try:
                if not ctx.live:
                    ctx.say(f"{label}: DRY RUN would {module.describe(ctx, item)}")
                    continue
                result = module.publish(ctx, item)
                state.record(item.key, channel, result, ctx.now)
                state.save()   # save after every success so a crash never causes a double post
                ctx.say(f"{label}: ok {result.get('url', '')}")
            except Skip as exc:
                ctx.say(f"{label}: skipped ({exc})")
            except PublishError as exc:
                failures += 1
                ctx.say(f"{label}: FAILED {exc}")
            except Exception as exc:  # noqa: BLE001 - keep the other channels going; never print the exception body
                failures += 1
                ctx.say(f"{label}: FAILED unexpected {type(exc).__name__}")
    return 1 if failures else 0


def export(ctx: Context, week: str) -> list[Path]:
    """Write the files for the channels that are posted by hand."""
    week_dir = ctx.root / "content" / week
    written = []
    if ctx.cfg["channels"].get("x") == "manual":
        posts = [p for p in load_posts(ctx.root) if p.folder.parent.name == week]
        written += x.export(ctx, posts, week_dir)
    if ctx.cfg["channels"].get("hashnode") == "manual":
        for art in load_articles(ctx.root):
            y, w, _ = art.date.isocalendar()
            if f"{y}-W{w:02d}" == week:
                week_dir.mkdir(parents=True, exist_ok=True)
                written.append(hashnode.export(ctx, art, week_dir))
    return written


def main(argv: list[str] | None = None) -> int:
    import requests

    ap = argparse.ArgumentParser(description="Publish approved content (dry run unless --live)")
    ap.add_argument("command", nargs="?", choices=["publish", "export"], default="publish")
    ap.add_argument("--event", choices=["merge", "daily"], help="which trigger to act as")
    ap.add_argument("--live", action="store_true", help="really post; without it nothing leaves this machine")
    ap.add_argument("--dry-run", action="store_true", help="the default; wins over --live")
    ap.add_argument("--only", action="append", help="limit to one channel (repeatable)")
    ap.add_argument("--date", type=dt.date.fromisoformat, help="act as if today were this date")
    ap.add_argument("--week", help="for export: ISO week, e.g. 2026-W47")
    args = ap.parse_args(argv)
    cfg = load_config(ROOT)
    now = dt.datetime.now(dt.timezone.utc)
    if args.date and args.command == "publish":
        offset = dt.datetime.strptime(cfg["timezone_offset"].replace(":", ""), "%z").tzinfo
        now = dt.datetime.combine(args.date, dt.time(8, 15), tzinfo=offset)
    session = requests.Session()
    session.request = _with_timeout(session.request)
    ctx = Context(ROOT, cfg, default_env(), session, now, live=args.live and not args.dry_run)
    if args.command == "export":
        if not args.week:
            ap.error("export needs --week")
        for path in export(ctx, args.week):
            print(path.relative_to(ROOT))
        return 0
    if not args.event:
        ap.error("publish needs --event merge or --event daily")
    if not ctx.live:
        print("DRY RUN: nothing will be posted. Add --live to post.")
    return run(ctx, args.event, args.only, args.date)


def _with_timeout(request):
    def wrapped(method, url, **kwargs):
        kwargs.setdefault("timeout", 120)
        return request(method, url, **kwargs)
    return wrapped


if __name__ == "__main__":
    sys.exit(main())
