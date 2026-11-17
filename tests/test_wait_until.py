import datetime as dt
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import wait_until as wu  # noqa: E402

TZ = ZoneInfo("Asia/Ho_Chi_Minh")
AT = dt.time(8, 15)
MAX = dt.timedelta(minutes=330)


def utc(y, mo, d, h, mi):
    return dt.datetime(y, mo, d, h, mi, tzinfo=dt.timezone.utc)


def test_delayed_early_run_waits_until_target():
    # cron 17:30Z (00:30 local) started 4.5 h late: 22:00Z = 05:00 local -> wait 3 h 15 min
    go, seconds, _ = wu.decide(utc(2026, 11, 17, 22, 0), AT, TZ, MAX)
    assert go and seconds == 3 * 3600 + 15 * 60


def test_run_after_target_goes_at_once():
    # the 01:15Z cron started 8 h late, as on 2026-11-17
    go, seconds, _ = wu.decide(utc(2026, 11, 17, 9, 9), AT, TZ, MAX)
    assert go and seconds == 0


def test_on_time_early_run_skips_when_wait_exceeds_job_limit():
    # cron 17:30Z on time = 00:30 local -> 7 h 45 min to wait, more than 5.5 h
    go, seconds, reason = wu.decide(utc(2026, 11, 17, 17, 30), AT, TZ, MAX)
    assert not go and seconds == 0 and "skip" in reason


def test_wait_exactly_at_limit_goes():
    # 02:45 local -> exactly 5 h 30 min
    go, seconds, _ = wu.decide(utc(2026, 11, 17, 19, 45), AT, TZ, MAX)
    assert go and seconds == 330 * 60


def test_target_uses_local_date_not_utc_date():
    # 23:30Z on the 17th is 06:30 local on the 18th: target is 08:15 on the 18th
    go, seconds, _ = wu.decide(utc(2026, 11, 17, 23, 30), AT, TZ, MAX)
    assert go and seconds == 105 * 60


def test_other_waiters_excludes_self():
    runs = [{"databaseId": 11}, {"databaseId": 12}]
    assert wu.other_waiters(runs, "11") == [12]
    assert wu.other_waiters([{"databaseId": 11}], "11") == []


def test_non_schedule_event_goes_without_gh(monkeypatch, tmp_path):
    out = tmp_path / "out"
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(wu, "in_progress_schedule_runs", lambda wf: (_ for _ in ()).throw(AssertionError("no gh")))
    assert wu.main(["--at", "08:15", "--workflow", "publish.yml"]) == 0
    assert out.read_text() == "go=true\n"


def test_schedule_skips_when_another_waiter_runs(monkeypatch, tmp_path):
    out = tmp_path / "out"
    monkeypatch.setenv("GITHUB_EVENT_NAME", "schedule")
    monkeypatch.setenv("GITHUB_RUN_ID", "5")
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(wu, "in_progress_schedule_runs", lambda wf: [{"databaseId": 5}, {"databaseId": 4}])
    assert wu.main(["--at", "08:15", "--workflow", "publish.yml"]) == 0
    assert out.read_text() == "go=false\n"
