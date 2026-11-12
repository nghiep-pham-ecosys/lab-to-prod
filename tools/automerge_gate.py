#!/usr/bin/env python3
"""Silent-approval gate for the weekly pull request. Reads judge.json; never calls a model.

    python tools/automerge_gate.py --week 2026-W47 [--apply] [--check-links]

For every post folder of the week:
  1. judge.json has scores for it, made on exactly the current post.md (sha256 must match)
  2. the mean of the five rubric scores is at least 4 and no score is below 3
  3. with --check-links: every source link answers HTTP 200
A post that fails is held: with --apply its status goes back to "draft", so the publishers skip
it and it waits for a manual review, while the other posts go out.

Exit code: 0 when the week may merge (possibly with held posts), 1 when it must not merge
(judge.json missing or unreadable, or no post passed).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate as v  # noqa: E402

RUBRIC = ["technical_accuracy", "sources", "one_clear_idea", "voice", "no_banned_info"]
MIN_MEAN, MIN_SCORE = 4.0, 3


def post_hash(folder: Path) -> str:
    return hashlib.sha256((folder / "post.md").read_bytes()).hexdigest()


def judge_post(folder: Path, verdicts: dict, check_links: bool) -> list[str]:
    """Reasons this post is held; empty when it passes."""
    entry = verdicts.get(folder.name)
    if not entry:
        return ["not judged"]
    if entry.get("sha256") != post_hash(folder):
        return ["post.md changed after it was judged"]
    scores = entry.get("scores") or {}
    if set(scores) != set(RUBRIC) or not all(isinstance(s, int) and 1 <= s <= 5 for s in scores.values()):
        return [f"scores must be integers 1-5 for exactly: {', '.join(RUBRIC)}"]
    reasons = []
    mean = sum(scores.values()) / len(RUBRIC)
    if mean < MIN_MEAN:
        reasons.append(f"mean score {mean:.1f} is below {MIN_MEAN:.0f}")
    low = [k for k, s in scores.items() if s < MIN_SCORE]
    if low:
        reasons.append("below 3 on " + ", ".join(sorted(low)))
    if check_links:
        meta, _ = v.parse_post(folder / "post.md")
        for url in meta.get("sources") or []:
            code = v.http_status(url)
            if code != 200:
                reasons.append(f"source {url} answered {code}")
    return reasons


def hold(folder: Path) -> None:
    path = folder / "post.md"
    text = path.read_text(encoding="utf-8")
    path.write_text(re.sub(r"(?m)^status:\s*approved\b", "status: draft", text, count=1), encoding="utf-8")


def gate(root: Path, week: str, apply: bool = False, check_links: bool = False) -> tuple[int, dict[str, list[str]]]:
    folders = v.post_folders(root, week)
    judge_path = root / "content" / week / "judge.json"
    try:
        data = json.loads(judge_path.read_text(encoding="utf-8"))
        verdicts = data["posts"]
        if data.get("week") != week or not isinstance(verdicts, dict):
            raise ValueError("wrong week or shape")
    except (OSError, ValueError, KeyError) as exc:
        return 1, {"judge.json": [f"missing or unreadable ({type(exc).__name__})"]}
    results = {f.name: judge_post(f, verdicts, check_links) for f in folders}
    held = [f for f in folders if results[f.name]]
    if apply:
        for f in held:
            hold(f)
    return (0 if folders and len(held) < len(folders) else 1), results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--week", required=True)
    ap.add_argument("--apply", action="store_true", help="set held posts back to status: draft")
    ap.add_argument("--check-links", action="store_true")
    ap.add_argument("--root", type=Path, default=v.ROOT)
    args = ap.parse_args(argv)
    code, results = gate(args.root, args.week, args.apply, args.check_links)
    for name, reasons in results.items():
        print(f"{'HOLD' if reasons else 'PASS'} {name}" + (": " + "; ".join(reasons) if reasons else ""))
    print("gate: " + ("may merge" if code == 0 else "must not merge"))
    return code


if __name__ == "__main__":
    sys.exit(main())
