#!/usr/bin/env python3
"""Keep bot-written state on the `publish-state` branch, because `main` only accepts pull requests.

    python tools/state_sync.py pull                      # before a run: merge the branch into the checkout
    python tools/state_sync.py push published.json ...   # after a run: commit these files to the branch

`pull` merges the branch's published.json into the working copy (union by item and channel; an entry
already in the branch wins, so a bot record is never replaced) and copies files that only the bot writes
(metrics/metrics.csv) from the branch. `push` commits the given files onto the branch (created as an
orphan the first time) and pushes; on a race it fetches, merges published.json again and retries.
Readers that want the full record (reports, routines) read published.json from this branch.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "publish-state"
BOT_FILES = ("metrics/metrics.csv",)


def merge_state(base: dict, branch: dict) -> dict:
    """Union of two published.json documents; on the same item and channel the branch entry wins."""
    out = json.loads(json.dumps(base))
    for key, channels in branch.items():
        out.setdefault(key, {}).update(channels)
    return out


def _git(*args: str, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd or ROOT, check=check, capture_output=True, text=True)


def _branch_file(path: str) -> str | None:
    proc = _git("show", f"origin/{BRANCH}:{path}", check=False)
    return proc.stdout if proc.returncode == 0 else None


def _fetch() -> bool:
    return _git("fetch", "--quiet", "origin", f"+refs/heads/{BRANCH}:refs/remotes/origin/{BRANCH}", check=False).returncode == 0


def pull(root: Path | None = None) -> None:
    root = root or ROOT
    if not _fetch():
        print(f"{BRANCH}: branch not found yet, nothing to merge")
        return
    state_path = root / "published.json"
    local = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    remote = json.loads(_branch_file("published.json") or "{}")
    state_path.write_text(json.dumps(merge_state(local, remote), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    for path in BOT_FILES:
        text = _branch_file(path)
        if text is not None:
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_text(text, encoding="utf-8")
    print(f"{BRANCH}: merged published.json ({len(remote)} item(s) from the branch)")


def push(files: list[str], root: Path | None = None, attempts: int = 3) -> None:
    root = root or ROOT
    for attempt in range(1, attempts + 1):
        exists = _fetch()
        with tempfile.TemporaryDirectory() as tmp:
            wt = Path(tmp) / "state"
            if exists:
                _git("worktree", "add", "--detach", str(wt), f"origin/{BRANCH}")
            else:
                _git("worktree", "add", "--detach", str(wt), "HEAD")
                _git("checkout", "--orphan", BRANCH, cwd=wt)
                _git("rm", "-rf", "--quiet", ".", cwd=wt)
            try:
                for name in files:
                    src, dst = root / name, wt / name
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if name == "published.json" and dst.exists():
                        merged = merge_state(json.loads(src.read_text(encoding="utf-8")),
                                             json.loads(dst.read_text(encoding="utf-8")))
                        dst.write_text(json.dumps(merged, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                                       encoding="utf-8")
                    else:
                        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
                    _git("add", name, cwd=wt)
                if not _git("status", "--porcelain", cwd=wt).stdout.strip():
                    print(f"{BRANCH}: nothing to commit")
                    return
                _git("-c", "user.name=github-actions[bot]",
                     "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
                     "commit", "--quiet", "-m", "chore: record publish state", cwd=wt)
                if _git("push", "--quiet", "origin", f"HEAD:refs/heads/{BRANCH}", cwd=wt, check=False).returncode == 0:
                    print(f"{BRANCH}: pushed {', '.join(files)}")
                    return
            finally:
                _git("worktree", "remove", "--force", str(wt), check=False)
        print(f"{BRANCH}: push rejected (attempt {attempt}), retrying")
    raise SystemExit(f"{BRANCH}: could not push after {attempts} attempts")


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("pull", "push"):
        print(__doc__)
        return 2
    if argv[0] == "pull":
        pull()
    else:
        if len(argv) < 2:
            print("push needs at least one file")
            return 2
        push(argv[1:])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
