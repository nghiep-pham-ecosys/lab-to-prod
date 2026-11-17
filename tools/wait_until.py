#!/usr/bin/env python3
"""Hold a scheduled run until a wall-clock time, because GitHub starts `schedule` runs hours late.

    python tools/wait_until.py --at 08:15 --workflow publish.yml

Only acts on `schedule` events (GITHUB_EVENT_NAME); any other event goes at once. A scheduled run:
- skips when another scheduled run of the same workflow is already in progress (one waiter is enough);
- skips when it would wait longer than --max-wait-min (a GitHub job may run at most 6 h; a later cron covers it);
- otherwise sleeps until --at today in --tz, then goes. A run that starts after --at goes at once.
Writes `go=true|false` to $GITHUB_OUTPUT and a line to $GITHUB_STEP_SUMMARY. Measured delays: lab-to-prod#32.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from zoneinfo import ZoneInfo


def decide(now: dt.datetime, at: dt.time, tz: ZoneInfo, max_wait: dt.timedelta) -> tuple[bool, float, str]:
    """Return (go, seconds to wait, reason) for a run that started at `now` (timezone-aware)."""
    local = now.astimezone(tz)
    target = dt.datetime.combine(local.date(), at, tzinfo=tz)
    wait = target - local
    if wait <= dt.timedelta(0):
        return True, 0.0, f"started {local:%H:%M} after {at:%H:%M}: go now"
    if wait > max_wait:
        return False, 0.0, f"started {local:%H:%M}, {at:%H:%M} is {wait} away (> {max_wait}): skip, a later run covers it"
    return True, wait.total_seconds(), f"started {local:%H:%M}: wait {wait} until {at:%H:%M}"


def other_waiters(runs: list[dict], self_id: str) -> list[int]:
    """Ids of in-progress scheduled runs other than this one."""
    return [r["databaseId"] for r in runs if str(r.get("databaseId")) != str(self_id)]


def in_progress_schedule_runs(workflow: str) -> list[dict]:
    out = subprocess.run(
        ["gh", "run", "list", "--workflow", workflow, "--event", "schedule", "--status", "in_progress",
         "--json", "databaseId", "--limit", "20"],
        check=True, capture_output=True, text=True,
    ).stdout
    return json.loads(out or "[]")


def emit(go: bool, reason: str) -> None:
    print(f"go={str(go).lower()} · {reason}", flush=True)
    for var, line in (("GITHUB_OUTPUT", f"go={str(go).lower()}"), ("GITHUB_STEP_SUMMARY", f"wait_until: {reason}")):
        path = os.environ.get(var)
        if path:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--at", required=True, type=dt.time.fromisoformat, help="local time HH:MM to start the work")
    ap.add_argument("--tz", default="Asia/Ho_Chi_Minh")
    ap.add_argument("--max-wait-min", type=int, default=330)
    ap.add_argument("--workflow", required=True, help="workflow file name, e.g. publish.yml")
    args = ap.parse_args(argv)

    if os.environ.get("GITHUB_EVENT_NAME") != "schedule":
        emit(True, f"event {os.environ.get('GITHUB_EVENT_NAME') or 'local'}: no wait")
        return 0

    others = other_waiters(in_progress_schedule_runs(args.workflow), os.environ.get("GITHUB_RUN_ID", ""))
    if others:
        emit(False, f"scheduled run(s) {others} already in progress: skip")
        return 0

    go, seconds, reason = decide(dt.datetime.now(dt.timezone.utc), args.at, ZoneInfo(args.tz),
                                 dt.timedelta(minutes=args.max_wait_min))
    print(reason, flush=True)
    end = time.monotonic() + seconds
    while (left := end - time.monotonic()) > 0:
        time.sleep(min(left, 1800))
        print(f"still waiting, {max(0, end - time.monotonic()) / 60:.0f} min left", flush=True)
    emit(go, reason)
    return 0


if __name__ == "__main__":
    sys.exit(main())
