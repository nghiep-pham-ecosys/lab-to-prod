import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from publish import record_manual as rm  # noqa: E402

URL = "https://x.com/example/status/1"


def run(tmp_path, *args):
    return rm.main([*args, "--root", str(tmp_path)])


def test_check_then_record_then_check_again(tmp_path, capsys):
    assert run(tmp_path, "check", "--key", "notes:en-4-agent-loop", "--channel", "x") == 0
    assert run(tmp_path, "record", "--key", "notes:en-4-agent-loop", "--channel", "x", "--url", URL,
               "--via", "chrome", "--at", "2026-11-12T09:00+07:00") == 0
    data = json.loads((tmp_path / "published.json").read_text())
    entry = data["notes:en-4-agent-loop"]["x"]
    assert entry == {"url": URL, "manual": True, "via": "chrome", "at": "2026-11-12T02:00:00+00:00"}
    assert run(tmp_path, "check", "--key", "notes:en-4-agent-loop", "--channel", "x") == 1
    assert "ALREADY POSTED" in capsys.readouterr().out


def test_record_twice_changes_nothing(tmp_path):
    assert run(tmp_path, "record", "--key", "2026-11-16", "--channel", "linkedin", "--url", URL) == 0
    before = (tmp_path / "published.json").read_text()
    assert run(tmp_path, "record", "--key", "2026-11-16", "--channel", "linkedin",
               "--url", "https://www.linkedin.com/feed/update/other") == 1
    assert (tmp_path / "published.json").read_text() == before


def test_other_channel_same_key_is_separate(tmp_path):
    assert run(tmp_path, "record", "--key", "2026-11-16", "--channel", "x", "--url", URL) == 0
    assert run(tmp_path, "check", "--key", "2026-11-16", "--channel", "linkedin") == 0


def test_keeps_existing_api_records(tmp_path):
    (tmp_path / "published.json").write_text(json.dumps({"2026-11-16": {"telegram": {"id": 5, "url": "https://t.me/c/5", "at": "x"}}}))
    assert run(tmp_path, "record", "--key", "2026-11-16", "--channel", "x", "--url", URL) == 0
    data = json.loads((tmp_path / "published.json").read_text())
    assert set(data["2026-11-16"]) == {"telegram", "x"}


def test_bad_arguments(tmp_path):
    assert run(tmp_path, "record", "--key", "Bad Key", "--channel", "x", "--url", URL) == 2
    assert run(tmp_path, "record", "--key", "2026-11-16", "--channel", "x", "--url", "http://insecure") == 2
    assert run(tmp_path, "record", "--key", "2026-11-16", "--channel", "x", "--url", URL, "--at", "2026-11-12T09:00") == 2
    assert run(tmp_path, "record", "--key", "2026-11-16", "--channel", "myspace", "--url", URL) == 2
    assert not (tmp_path / "published.json").exists()
