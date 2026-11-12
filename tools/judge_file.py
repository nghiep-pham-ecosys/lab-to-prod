#!/usr/bin/env python3
"""Write content/<week>/judge.json from the scores a judging subagent returned.

    python tools/judge_file.py --week 2026-W47 --scores scores.json
    python tools/judge_file.py --week 2026-W47 --scores one.json --merge   # re-judged posts only

It adds the sha256 of each post.md, so the gate can tell if a post changed after judging.
It refuses scores that are not integers 1-5 on exactly the five rubric keys.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import automerge_gate as gate  # noqa: E402
import validate as v  # noqa: E402


def build(root: Path, week: str, scores: dict, merge: bool = False) -> dict:
    folders = {f.name: f for f in v.post_folders(root, week)}
    path = root / "content" / week / "judge.json"
    posts = json.loads(path.read_text(encoding="utf-8"))["posts"] if merge and path.exists() else {}
    for name, entry in scores.items():
        if name not in folders:
            raise ValueError(f"{name} is not a post folder of {week}")
        s = entry.get("scores") or {}
        if set(s) != set(gate.RUBRIC) or not all(isinstance(x, int) and not isinstance(x, bool) and 1 <= x <= 5 for x in s.values()):
            raise ValueError(f"{name}: scores must be integers 1-5 for exactly {gate.RUBRIC}")
        posts[name] = {"sha256": gate.post_hash(folders[name]), "scores": {k: s[k] for k in gate.RUBRIC},
                       "mean": round(sum(s.values()) / len(s), 2), "notes": str(entry.get("notes", "")).strip()}
    return {"week": week, "judged_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "judge": "subagent that did not see the drafting session", "rubric": gate.RUBRIC,
            "pass_rule": f"mean >= {gate.MIN_MEAN:.0f} and no score below {gate.MIN_SCORE}",
            "posts": dict(sorted(posts.items()))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--week", required=True)
    ap.add_argument("--scores", required=True, type=Path)
    ap.add_argument("--merge", action="store_true", help="keep existing entries, replace only the posts in --scores")
    ap.add_argument("--root", type=Path, default=v.ROOT)
    args = ap.parse_args(argv)
    try:
        data = build(args.root, args.week, json.loads(args.scores.read_text(encoding="utf-8")), args.merge)
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}")
        return 1
    out = args.root / "content" / args.week / "judge.json"
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for name, e in data["posts"].items():
        print(f"{e['mean']:.1f}  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
