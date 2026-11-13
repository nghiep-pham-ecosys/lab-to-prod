import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import state_sync as ss  # noqa: E402


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def make_repo(tmp_path):
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "--quiet", "--bare", str(remote))
    work = tmp_path / "work"
    git(tmp_path, "init", "--quiet", "-b", "main", str(work))
    git(work, "config", "user.email", "t@example.com")
    git(work, "config", "user.name", "t")
    (work / "published.json").write_text(json.dumps({"notes:a": {"x": {"url": "https://x/1"}}}))
    git(work, "add", ".")
    git(work, "commit", "--quiet", "-m", "init")
    git(work, "remote", "add", "origin", str(remote))
    git(work, "push", "--quiet", "origin", "main")
    return work


def test_merge_state_union_branch_wins():
    base = {"a": {"x": {"url": "1"}}, "b": {"x": {"url": "2"}}}
    branch = {"a": {"x": {"url": "bot"}, "facebook": {"url": "fb"}}, "c": {"x": {"url": "3"}}}
    out = ss.merge_state(base, branch)
    assert out == {"a": {"x": {"url": "bot"}, "facebook": {"url": "fb"}}, "b": {"x": {"url": "2"}}, "c": {"x": {"url": "3"}}}
    assert base == {"a": {"x": {"url": "1"}}, "b": {"x": {"url": "2"}}}


def test_push_creates_branch_then_pull_merges(tmp_path, monkeypatch):
    work = make_repo(tmp_path)
    monkeypatch.setattr(ss, "ROOT", work)
    ss.pull()   # no branch yet: no change, no error
    state = json.loads((work / "published.json").read_text())
    state["2026-11-16"] = {"facebook": {"id": "1", "url": "https://fb/1"}}
    (work / "published.json").write_text(json.dumps(state))
    (work / "metrics").mkdir()
    (work / "metrics" / "metrics.csv").write_text("measured_on,item\n2026-11-16,x\n")
    ss.push(["published.json", "metrics/metrics.csv"])
    assert git(work, "branch", "--show-current").strip() == "main"
    # a fresh checkout of main sees the bot record after pull
    git(work, "checkout", "--quiet", "--", "published.json")
    (work / "metrics" / "metrics.csv").unlink()
    ss.pull()
    merged = json.loads((work / "published.json").read_text())
    assert merged["2026-11-16"]["facebook"]["url"] == "https://fb/1"
    assert merged["notes:a"]["x"]["url"] == "https://x/1"
    assert (work / "metrics" / "metrics.csv").read_text().startswith("measured_on")


def test_push_again_merges_and_never_drops_records(tmp_path, monkeypatch):
    work = make_repo(tmp_path)
    monkeypatch.setattr(ss, "ROOT", work)
    (work / "published.json").write_text(json.dumps({"k1": {"facebook": {"url": "1"}}}))
    ss.push(["published.json"])
    (work / "published.json").write_text(json.dumps({"k2": {"facebook": {"url": "2"}}}))
    ss.push(["published.json"])
    ss.pull()
    merged = json.loads((work / "published.json").read_text())
    assert set(merged) == {"k1", "k2"}
