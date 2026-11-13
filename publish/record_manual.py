"""Record a post made by hand (Chrome, Typefully, a phone) in published.json, and check before posting.

published.json is the one record of what is live. run.py writes API posts; this tool writes manual ones,
so the file is never edited by hand and a manual post can never be posted twice by mistake.

Usage:
  python -m publish.record_manual check  --key KEY --channel CHANNEL
  python -m publish.record_manual record --key KEY --channel CHANNEL --url URL [--id ID] [--via chrome] [--at ISO]

KEY is the post date for repo posts (2026-11-16), `article:<slug>` for articles, or a stable slug for posts
made outside the weekly folders (for example `notes:en-4-agent-loop`).
Exit codes: check → 0 not posted yet, 1 already posted (prints where); record → 0 written, 1 already
recorded (nothing changed), 2 bad arguments.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

from publish.common import ROOT, State

CHANNELS = ("x", "linkedin", "facebook", "telegram", "youtube", "devto", "hashnode", "threads", "bluesky")
_KEY = re.compile(r"^[a-z0-9][a-z0-9:._-]{2,80}$")


def _parse(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m publish.record_manual", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("check", "record"):
        s = sub.add_parser(name)
        s.add_argument("--key", required=True)
        s.add_argument("--channel", required=True, choices=CHANNELS)
        s.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
        if name == "record":
            s.add_argument("--url", required=True)
            s.add_argument("--id", default="")
            s.add_argument("--via", default="manual", help="chrome, typefully, phone, ...")
            s.add_argument("--at", default="", help="ISO time of the post; default now")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parse(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    if not _KEY.match(args.key):
        print(f"bad --key {args.key!r}: lower case letters, digits and : . _ - only", file=sys.stderr)
        return 2
    state = State(args.root)
    existing = state.data.get(args.key, {}).get(args.channel)

    if args.cmd == "check":
        if existing:
            print(f"ALREADY POSTED {args.key} on {args.channel}: {existing.get('url', '?')} at {existing.get('at', '?')}")
            return 1
        print(f"not posted yet: {args.key} on {args.channel}")
        return 0

    if not args.url.startswith("https://"):
        print("--url must be the https link of the live post", file=sys.stderr)
        return 2
    if existing:
        print(f"already recorded {args.key} on {args.channel}: {existing.get('url', '?')} (nothing changed)")
        return 1
    try:
        when = dt.datetime.fromisoformat(args.at) if args.at else dt.datetime.now(dt.timezone.utc)
    except ValueError:
        print(f"bad --at {args.at!r}: use ISO 8601, for example 2026-11-13T08:40+07:00", file=sys.stderr)
        return 2
    if when.tzinfo is None:
        print("--at needs a UTC offset, for example +07:00", file=sys.stderr)
        return 2
    result = {"url": args.url, "manual": True, "via": args.via}
    if args.id:
        result["id"] = args.id
    state.record(args.key, args.channel, result, when)
    state.save()
    print(f"recorded {args.key} on {args.channel}: {args.url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
