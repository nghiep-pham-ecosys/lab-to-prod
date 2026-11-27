"""publish/followup.py with a fake HTTP client and synthetic data only (Example Co, Acme)."""
import csv
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from metrics import collect  # noqa: E402
from publish import comments, followup  # noqa: E402
from publish.common import State, is_followup_key  # noqa: E402

TZ = dt.timezone(dt.timedelta(hours=7))
ENV = {"FB_PAGE_ID": "42", "FB_PAGE_TOKEN": "fb-token-SECRET", "YT_CLIENT_ID": "cid", "YT_CLIENT_SECRET": "csecret",
       "YT_REFRESH_TOKEN": "refresh", "LINKEDIN_ACCESS_TOKEN": "li-token-SECRET", "LINKEDIN_PERSON_URN": "abc123"}
FB = "https://graph.facebook.com/v27.0"
YT = "https://www.googleapis.com/youtube/v3"
LI = "https://api.linkedin.com/v2/socialActions/urn%3Ali%3Ashare%3A1/comments"
ME = "UC-our-channel"


class Resp:
    def __init__(self, status=200, body=None, headers=None):
        self.status_code, self._body = status, body if body is not None else {}
        self.text, self.headers = json.dumps(self._body), headers or {}

    def json(self):
        return self._body


class FakeHTTP:
    """Answers by (method, url); records every call. Any call not in routes fails the test."""

    def __init__(self, routes=None):
        self.routes, self.calls = routes or {}, []

    def _handle(self, method, url, **kw):
        self.calls.append((method, url, kw))
        if url == "https://oauth2.googleapis.com/token":
            return Resp(200, {"access_token": "yt-access"})
        answer = self.routes.get((method, url))
        if answer is None:
            raise AssertionError(f"unexpected call {method} {url}")
        return answer.pop(0) if isinstance(answer, list) else answer

    def get(self, url, **kw):
        return self._handle("GET", url, **kw)

    def post(self, url, **kw):
        return self._handle("POST", url, **kw)

    def posts(self):
        return [(m, u) for m, u, _ in self.calls if m == "POST" and "oauth2" not in u]


STATE = {
    # Example Co post, public 2026-11-20 (local) on four channels
    "2026-11-20": {
        "linkedin": {"id": "urn:li:share:1", "url": "https://www.linkedin.com/feed/update/urn:li:share:1/",
                     "at": "2026-11-20T01:30:00+00:00", "comment": True},
        "facebook": {"id": "42_777", "url": "https://www.facebook.com/42_777", "at": "2026-11-19T10:00:00+00:00",
                     "scheduled_for": "2026-11-20T08:30:00+07:00"},
        "youtube": {"id": "vid1", "url": "https://www.youtube.com/shorts/vid1", "at": "2026-11-19T10:00:00+00:00",
                    "scheduled_for": "2026-11-20T12:00:00.000Z"},
        "x": {"id": "9001", "url": "https://x.com/example/status/9001", "at": "2026-11-20T01:30:00+00:00",
              "manual": True, "via": "chrome"},
        "telegram": {"id": "5", "url": "https://t.me/example/5", "at": "2026-11-20T01:30:00+00:00"},
    },
    # Acme post, public 2026-11-13: follow-up 1 already done on facebook and linkedin
    "notes:acme-1": {
        "facebook": {"id": "888", "manual": True, "url": "https://www.facebook.com/42/posts/888",
                     "at": "2026-11-13T01:00:00+00:00"},
        "linkedin": {"id": "urn:li:share:2", "url": "https://www.linkedin.com/feed/update/urn:li:share:2/",
                     "at": "2026-11-13T01:30:00+00:00"},
        "x": {"url": "https://x.com/example/status/9002", "at": "2026-11-13T01:30:00+00:00", "manual": True},
    },
    "notes:acme-1:followup1": {
        "facebook": {"id": "888_c1", "url": "https://www.facebook.com/42/posts/888", "at": "2026-11-20T02:00:00+00:00"},
        "linkedin": {"id": "c2", "url": "https://www.linkedin.com/feed/update/urn:li:share:2/",
                     "at": "2026-11-20T02:00:00+00:00"},
        "x": {"url": "https://x.com/example/status/9003", "at": "2026-11-20T02:00:00+00:00", "manual": True},
    },
    # Example Co post with both follow-ups done
    "notes:example-2": {"facebook": {"id": "999", "url": "https://www.facebook.com/999",
                                     "at": "2026-11-13T01:00:00+00:00"}},
    "notes:example-2:followup1": {"facebook": {"id": "999_a", "at": "2026-11-20T01:00:00+00:00"}},
    "notes:example-2:followup2": {"facebook": {"id": "999_b", "at": "2026-11-26T01:00:00+00:00"}},
}

METRICS = [
    # day, item, channel, impressions, views, comments
    ("2026-11-26", "notes:acme-1", "facebook", "", "", "3"),        # 1 of 3 is our follow-up 1 -> 2 from others
    ("2026-11-26", "notes:acme-1", "linkedin", "900", "", "1"),     # only our follow-up; reach above median
    ("2026-11-26", "notes:example-2", "facebook", "", "", "5"),
    ("2026-11-26", "2026-11-20", "linkedin", "300", "", "1"),
    ("2026-11-26", "notes:other-3", "linkedin", "500", "", "0"),
    ("2026-11-26", "_account", "linkedin", "", "", ""),
]


def write_metrics(root, rows):
    path = root / "metrics" / "metrics.csv"
    path.parent.mkdir(exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, collect.FIELDS)
        w.writeheader()
        for day, item, channel, imp, views, com in rows:
            w.writerow({**dict.fromkeys(collect.FIELDS, ""), "measured_on": day, "item": item, "channel": channel,
                        "impressions": imp, "views": views, "comments": com})


@pytest.fixture
def root(tmp_path):
    (tmp_path / "publish").mkdir()
    shutil.copy(ROOT / "publish" / "config.yaml", tmp_path / "publish" / "config.yaml")
    (tmp_path / "published.json").write_text(json.dumps(STATE), encoding="utf-8")
    write_metrics(tmp_path, METRICS)
    return tmp_path


def run_due(root, day, capsys, notes=None):
    capsys.readouterr()
    assert followup.main(["due", "--date", day], env={}, http=FakeHTTP(), root=root) == 0
    captured = capsys.readouterr()
    if notes is not None:
        notes.append(captured.err)
    return json.loads(captured.out)


def keys(found):
    return sorted((f["channel"], f["key"]) for f in found)


# --- due rules -------------------------------------------------------------------------------------------------------

def test_nothing_due_before_day_7(root, capsys):
    found = run_due(root, "2026-11-26", capsys)
    assert all(f["post_key"] != "2026-11-20" for f in found)


def test_first_followup_due_on_day_7_for_each_followup_channel(root, capsys):
    found = [f for f in run_due(root, "2026-11-27", capsys) if f["post_key"] == "2026-11-20"]
    assert keys(found) == [(c, "2026-11-20:followup1") for c in ("facebook", "linkedin", "x", "youtube")]
    by = {f["channel"]: f for f in found}
    assert by["x"]["mode"] == "manual" and by["linkedin"]["mode"] == "api"
    assert by["linkedin"]["due_on"] == "2026-11-27" and by["linkedin"]["number"] == 1
    assert by["linkedin"]["metrics"] == {"measured_on": "2026-11-26", "impressions": 300, "comments": 1}
    assert by["linkedin"]["comments"] == 1 and by["youtube"]["comments"] is None
    assert by["facebook"]["post_url"] == "https://www.facebook.com/42_777"


def test_first_followup_stays_due_for_the_grace_days_then_drops(root, capsys):
    assert any(f["key"] == "2026-11-20:followup1" for f in run_due(root, "2026-11-29", capsys))
    assert not any(f["key"] == "2026-11-20:followup1" for f in run_due(root, "2026-11-30", capsys))


def test_second_followup_on_day_14_needs_comments_or_reach(root, capsys):
    notes = []
    found = run_due(root, "2026-11-27", capsys, notes)
    second = [f for f in found if f["post_key"] == "notes:acme-1"]
    # facebook: 2 comments from others; linkedin: only our own comment but 900 > median 500; x: no metrics
    assert keys(second) == [("facebook", "notes:acme-1:followup2"), ("linkedin", "notes:acme-1:followup2")]
    assert all(f["number"] == 2 and f["due_on"] == "2026-11-27" for f in second)
    assert "x notes:acme-1: follow-up 2 not due (no metrics for this post)" in notes[0]


def test_second_followup_held_back_without_comments_or_reach(root, capsys):
    write_metrics(root, [("2026-11-26", "notes:acme-1", "facebook", "", "", "1"),
                         ("2026-11-26", "notes:acme-1", "linkedin", "100", "", "1"),
                         ("2026-11-26", "notes:other-3", "linkedin", "500", "", "0")])
    notes = []
    assert [f for f in run_due(root, "2026-11-27", capsys, notes) if f["post_key"] == "notes:acme-1"] == []
    err = notes[0]
    assert "facebook notes:acme-1: follow-up 2 not due (no comments from others, reach not above median)" in err


def test_second_followup_needs_the_first(root, capsys):
    data = json.loads((root / "published.json").read_text())
    del data["notes:acme-1:followup1"]["facebook"]
    (root / "published.json").write_text(json.dumps(data))
    found = run_due(root, "2026-11-27", capsys)
    assert not any(f["channel"] == "facebook" and f["post_key"] == "notes:acme-1" for f in found)


def test_cap_of_two_per_post_and_channel(root, capsys):
    for day in ("2026-11-20", "2026-11-27", "2026-11-28"):
        assert not any(f["post_key"] == "notes:example-2" for f in run_due(root, day, capsys))


def test_due_output_has_no_personal_fields(root, capsys):
    for f in run_due(root, "2026-11-27", capsys):
        assert set(f) == {"channel", "post_key", "post_url", "number", "key", "due_on", "mode", "metrics", "comments"}


def test_due_writes_summary_and_out(root, capsys, tmp_path):
    out, summary = tmp_path / "due.json", tmp_path / "summary.md"
    assert followup.main(["due", "--date", "2026-11-27", "--out", str(out), "--summary", str(summary)],
                         env={}, http=FakeHTTP(), root=root) == 0
    assert len(json.loads(out.read_text())) == 6
    assert summary.read_text().startswith("## Follow-ups due on 2026-11-27: 6")


def test_bad_date(root, capsys):
    assert followup.main(["due", "--date", "27/11"], env={}, http=FakeHTTP(), root=root) == 2


# --- post ------------------------------------------------------------------------------------------------------------

NOW = dt.datetime(2026, 11, 27, 3, 0, tzinfo=dt.timezone.utc)   # 10:00 local, day 7 of the 2026-11-20 post


def approved(root, items):
    path = root / "approved.json"
    path.write_text(json.dumps(items), encoding="utf-8")
    return ["post", "--file", str(path)]


def post_routes():
    return {
        ("POST", LI): Resp(201, {"id": "li-c1", "commentUrn": "urn:li:comment:(urn:li:share:1,li-c1)"},
                           headers={"x-restli-id": "li-c1"}),
        ("POST", f"{FB}/42_777/comments"): Resp(200, {"id": "42_777_c1"}),
        ("GET", f"{YT}/channels"): Resp(200, {"items": [{"id": ME}]}),
        ("POST", f"{YT}/commentThreads"): Resp(200, {"id": "yt-thread-1"}),
    }


ITEMS = [{"channel": c, "post_key": "2026-11-20", "number": 1, "text": f"Update a week later ({c})"}
         for c in ("linkedin", "facebook", "youtube")]


def test_post_dry_run_calls_nothing(root, capsys):
    http = FakeHTTP()
    assert followup.main(approved(root, ITEMS), env=ENV, http=http, root=root, now=NOW) == 0
    assert http.calls == []
    assert "planned" in capsys.readouterr().out
    assert "2026-11-20:followup1" not in json.loads((root / "published.json").read_text())


def test_post_live_posts_each_once_and_records(root, capsys):
    http = FakeHTTP(post_routes())
    assert followup.main(approved(root, ITEMS) + ["--live"], env=ENV, http=http, root=root, now=NOW) == 0
    assert sorted(http.posts()) == sorted([("POST", LI), ("POST", f"{FB}/42_777/comments"),
                                           ("POST", f"{YT}/commentThreads")])
    li = next(kw for m, u, kw in http.calls if u == LI)
    assert li["json"] == {"actor": "urn:li:person:abc123", "object": "urn:li:share:1",
                          "message": {"text": "Update a week later (linkedin)"}}
    assert "LinkedIn-Version" not in li["headers"] and li["headers"]["X-Restli-Protocol-Version"] == "2.0.0"
    fb = next(kw for m, u, kw in http.calls if u == f"{FB}/42_777/comments")
    assert fb["data"]["message"] == "Update a week later (facebook)"
    yt = json.loads(next(kw for m, u, kw in http.calls if u == f"{YT}/commentThreads")["data"])
    assert yt == {"snippet": {"channelId": ME, "videoId": "vid1",
                              "topLevelComment": {"snippet": {"textOriginal": "Update a week later (youtube)"}}}}
    record = json.loads((root / "published.json").read_text())["2026-11-20:followup1"]
    assert record["linkedin"]["id"] == "li-c1" and record["facebook"]["id"] == "42_777_c1"
    assert record["youtube"]["id"] == "yt-thread-1" and record["youtube"]["post_id"] == "vid1"
    out = capsys.readouterr().out
    assert "youtube: 51 quota units used" in out and "SECRET" not in out

    # second run: idempotent through published.json, no call at all
    http2 = FakeHTTP(post_routes())
    assert followup.main(approved(root, ITEMS) + ["--live"], env=ENV, http=http2, root=root, now=NOW) == 0
    assert http2.posts() == []
    assert capsys.readouterr().out.count("already recorded in published.json") == 3


def test_post_listed_twice_posts_once(root, capsys):
    http = FakeHTTP(post_routes())
    assert followup.main(approved(root, ITEMS[1:2] * 2) + ["--live"], env=ENV, http=http, root=root, now=NOW) == 0
    assert http.posts() == [("POST", f"{FB}/42_777/comments")]
    assert "listed twice in this file" in capsys.readouterr().out


def test_post_x_is_manual_and_never_called(root, capsys, tmp_path):
    http = FakeHTTP()
    out = tmp_path / "r.json"
    item = {"channel": "x", "post_key": "2026-11-20", "number": 1, "text": "Update a week later"}
    assert followup.main(approved(root, [item]) + ["--live", "--out", str(out)], env=ENV, http=http, root=root,
                         now=NOW) == 0
    assert http.calls == []
    row = json.loads(out.read_text())[0]
    assert row["status"] == "manual"
    assert "record_manual record --key 2026-11-20:followup1 --channel x" in row["detail"]
    assert "2026-11-20:followup1" not in json.loads((root / "published.json").read_text())


def test_x_manual_record_closes_the_followup(root, capsys):
    from publish import record_manual
    assert record_manual.main(["record", "--key", "2026-11-20:followup1", "--channel", "x", "--url",
                               "https://x.com/example/status/9100", "--at", "2026-11-27T09:00+07:00",
                               "--root", str(root)]) == 0
    found = run_due(root, "2026-11-27", capsys)
    assert not any(f["channel"] == "x" and f["post_key"] == "2026-11-20" for f in found)
    item = {"channel": "x", "post_key": "2026-11-20", "number": 1, "text": "again"}
    assert followup.main(approved(root, [item]), env=ENV, http=FakeHTTP(), root=root, now=NOW) == 0
    assert "already recorded in published.json" in capsys.readouterr().out


def test_post_refuses_too_early_second_without_first_and_third(root, capsys, tmp_path):
    items = [{"channel": "facebook", "post_key": "2026-11-20", "number": 1, "text": "early"},
             {"channel": "youtube", "post_key": "2026-11-20", "number": 2, "text": "no first yet"}]
    out = tmp_path / "r.json"
    http = FakeHTTP()
    early = dt.datetime(2026, 11, 26, 3, 0, tzinfo=dt.timezone.utc)
    assert followup.main(approved(root, items) + ["--live", "--out", str(out)], env=ENV, http=http, root=root,
                         now=early) == 1
    rows = json.loads(out.read_text())
    assert [r["status"] for r in rows] == ["refused", "refused"]
    assert rows[0]["detail"] == "too early: due on 2026-11-27"
    assert rows[1]["detail"] == "follow-up 1 is not recorded yet"
    assert http.calls == []
    bad = approved(root, [{"channel": "facebook", "post_key": "2026-11-20", "number": 3, "text": "third"}])
    assert followup.main(bad, env=ENV, http=http, root=root, now=NOW) == 2
    assert "number must be 1 or 2" in capsys.readouterr().err


def test_post_refused_scope_stops_the_channel(root, capsys, tmp_path):
    http = FakeHTTP({("POST", f"{FB}/42_777/comments"): Resp(403, {"error": {"code": 200, "message": "Permissions error"}})})
    items = [ITEMS[1], {**ITEMS[1], "post_key": "notes:acme-1", "number": 2}]
    data = json.loads((root / "published.json").read_text())
    out = tmp_path / "r.json"
    assert followup.main(approved(root, items) + ["--live", "--out", str(out)], env=ENV, http=http, root=root,
                         now=NOW) == 1
    rows = json.loads(out.read_text())
    assert [r["status"] for r in rows] == ["refused", "refused"]
    assert len(http.posts()) == 1
    assert json.loads((root / "published.json").read_text()) == data
    assert "SECRET" not in capsys.readouterr().out + out.read_text()


def test_post_linkedin_refusal_points_to_the_manual_path(root, capsys, tmp_path):
    http = FakeHTTP({("POST", LI): Resp(403, {"message": "Not enough permissions"})})
    out = tmp_path / "r.json"
    assert followup.main(approved(root, ITEMS[:1]) + ["--live", "--out", str(out)], env=ENV, http=http, root=root,
                         now=NOW) == 1
    assert "record_manual" in json.loads(out.read_text())[0]["detail"]


def test_post_missing_secrets_refused(root, capsys, tmp_path):
    out = tmp_path / "r.json"
    assert followup.main(approved(root, ITEMS[:1]) + ["--live", "--out", str(out)], env={}, http=FakeHTTP(),
                         root=root, now=NOW) == 1
    assert json.loads(out.read_text())[0]["detail"] == "secrets not set: LINKEDIN_ACCESS_TOKEN, LINKEDIN_PERSON_URN"


def test_pause_stops_a_live_run(root, capsys):
    (root / "PAUSE").write_text("")
    http = FakeHTTP(post_routes())
    assert followup.main(approved(root, ITEMS) + ["--live"], env=ENV, http=http, root=root, now=NOW) == 0
    assert http.calls == []
    assert "PAUSE" in capsys.readouterr().out


def test_unknown_post_fails(root, capsys, tmp_path):
    out = tmp_path / "r.json"
    item = {"channel": "facebook", "post_key": "notes:acme-404", "number": 1, "text": "x"}
    assert followup.main(approved(root, [item]) + ["--out", str(out)], env=ENV, http=FakeHTTP(), root=root,
                         now=NOW) == 1
    assert json.loads(out.read_text())[0]["status"] == "failed"


# --- other readers skip follow-up records -------------------------------------------------------------------------

def test_followup_keys_are_not_posts_for_other_readers(root):
    assert is_followup_key("2026-11-20:followup1") and not is_followup_key("notes:acme-1")
    state = State(root).data
    posts = comments.targets(state, "facebook", NOW, 60)
    assert all(not is_followup_key(k) for k, _ in posts)
    assert {k for k, _ in posts} == {"2026-11-20", "notes:acme-1", "notes:example-2"}
