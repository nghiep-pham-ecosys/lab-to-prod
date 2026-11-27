"""publish/comments.py with a fake HTTP client and synthetic data only (Example Co, Acme)."""
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from publish import comments  # noqa: E402

NOW = dt.datetime(2026, 11, 27, 3, 0, tzinfo=dt.timezone.utc)
ENV = {"FB_PAGE_ID": "42", "FB_PAGE_TOKEN": "fb-token-SECRET", "YT_CLIENT_ID": "cid", "YT_CLIENT_SECRET": "csecret",
       "YT_REFRESH_TOKEN": "refresh"}
ME = "UC-our-channel"
FB = "https://graph.facebook.com/v27.0"
YT = "https://www.googleapis.com/youtube/v3"


class Resp:
    def __init__(self, status=200, body=None):
        self.status_code, self._body = status, body if body is not None else {}
        self.text = json.dumps(self._body)

    def json(self):
        return self._body


class FakeHTTP:
    """Answers by (method, url); a value is a Resp or a list of Resps served in order. Records every call."""

    def __init__(self, routes):
        self.routes, self.calls = routes, []

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


def yt_comment(cid, author, text, at, channel="UC-acme"):
    return {"id": cid, "snippet": {"authorDisplayName": author, "authorChannelId": {"value": channel},
                                   "textDisplay": text, "publishedAt": at}}


def yt_thread(top, replies=(), total=None):
    return {"snippet": {"topLevelComment": top, "totalReplyCount": len(replies) if total is None else total},
            "replies": {"comments": list(replies)}}


def fb_comment(cid, name, who, text, at, parent=None, nested=()):
    c = {"id": cid, "from": {"id": who, "name": name}, "message": text, "created_time": at}
    if parent:
        c["parent"] = {"id": parent}
    if nested:
        c["comments"] = {"data": [{"from": {"id": n}} for n in nested]}
    return c


@pytest.fixture
def root(tmp_path):
    (tmp_path / "publish").mkdir()
    shutil.copy(ROOT / "publish" / "config.yaml", tmp_path / "publish" / "config.yaml")
    state = {
        "2026-11-20": {"youtube": {"id": "vid1", "url": "https://www.youtube.com/shorts/vid1", "at": "2026-11-19T10:00:00+00:00",
                                   "scheduled_for": "2026-11-20T12:00:00.000Z"},
                       "facebook": {"id": "777", "url": "https://www.facebook.com/777", "at": "2026-11-19T10:00:00+00:00",
                                    "scheduled_for": "2026-11-20T08:30:00+07:00"},
                       "linkedin": {"id": "urn:li:activity:1", "url": "https://example.com/li"}},
        "notes:acme-1": {"facebook": {"id": "888", "manual": True, "url": "https://www.facebook.com/42/posts/888",
                                      "at": "2026-11-21T01:00:00+00:00"}},
        "2026-12-04": {"youtube": {"id": "future", "url": "https://www.youtube.com/shorts/future",
                                   "at": "2026-11-26T10:00:00+00:00", "scheduled_for": "2026-12-04T12:00:00.000Z"}},
        "2026-08-01": {"facebook": {"id": "old", "url": "https://www.facebook.com/old", "at": "2026-08-01T01:00:00+00:00"}},
    }
    (tmp_path / "published.json").write_text(json.dumps(state), encoding="utf-8")
    return tmp_path


def list_routes():
    threads = {"items": [
        yt_thread(yt_comment("yt-new", "Acme Reader", "Does this work on CPU?", "2026-11-26T09:00:00Z")),
        yt_thread(yt_comment("yt-done", "Example Co", "Nice one", "2026-11-25T09:00:00Z"),
                  [yt_comment("yt-r1", "Us", "Thanks!", "2026-11-25T10:00:00Z", channel=ME)]),
        yt_thread(yt_comment("yt-hidden-reply", "Acme Two", "Source?", "2026-11-24T09:00:00Z"),
                  [yt_comment("yt-r2", "Someone", "+1", "2026-11-24T10:00:00Z")], total=2),
        yt_thread(yt_comment("yt-ours", "Us", "Pinned: blog link", "2026-11-23T09:00:00Z", channel=ME)),
        yt_thread(yt_comment("yt-old", "Acme Old", "Too old", "2026-11-10T09:00:00Z")),
    ]}
    return {
        ("GET", f"{YT}/channels"): Resp(200, {"items": [{"id": ME}]}),
        ("GET", f"{YT}/commentThreads"): Resp(200, threads),
        ("GET", f"{YT}/comments"): Resp(200, {"items": [yt_comment("yt-r2", "Someone", "+1", "2026-11-24T10:00:00Z"),
                                                       yt_comment("yt-r3", "Us", "Here", "2026-11-24T11:00:00Z", channel=ME)]}),
        ("GET", f"{FB}/777/comments"): [
            Resp(200, {"data": [fb_comment("777_a", "Acme Reader", "9001", "Which dataset?", "2026-11-26T01:00:00+0000"),
                                fb_comment("777_b", "Example Co", "9002", "Great", "2026-11-25T01:00:00+0000")],
                       "paging": {"cursors": {"after": "CUR"}, "next": "https://graph.facebook.com/next"}}),
            Resp(200, {"data": [fb_comment("777_c", "Lab to Prod", "42", "Thank you", "2026-11-25T02:00:00+0000", parent="777_b"),
                                fb_comment("777_d", "Acme Fan", "9003", "Agreed", "2026-11-24T01:00:00+0000", nested=("42",)),
                                fb_comment("777_e", "Acme Old", "9004", "Old one", "2026-11-01T01:00:00+0000")],
                       "paging": {"cursors": {"after": "CUR2"}}})],
        ("GET", f"{FB}/42_888/comments"): Resp(200, {"data": [
            fb_comment("888_a", "Example Co", "9005", "Link please", "2026-11-22T01:00:00+0000"),
            fb_comment("888_b", "Acme Reply", "9006", "me too", "2026-11-22T02:00:00+0000", parent="888_a")]}),
    }


def test_list_redact_drops_names_and_text(root, capsys):
    out = root / "found.json"
    assert comments.main(["list", "--redact", "--out", str(out)], env=ENV, http=FakeHTTP(list_routes()), root=root,
                         now=NOW) == 0
    found = json.loads(out.read_text())
    assert found and all("author" not in c and "text" not in c for c in found)
    assert found[0]["comment_id"] == "yt-new"
    printed = capsys.readouterr().out
    assert "Acme Reader" not in printed and "Does this work on CPU?" not in printed


def test_list_filters_answered_and_the_date_window(root, capsys):
    http = FakeHTTP(list_routes())
    out = root / "found.json"
    summary = root / "summary.md"
    assert comments.main(["list", "--out", str(out), "--summary", str(summary)], env=ENV, http=http, root=root, now=NOW) == 0
    found = json.loads(out.read_text())
    assert [(c["channel"], c["comment_id"]) for c in found] == [
        ("youtube", "yt-new"), ("facebook", "777_a"), ("facebook", "888_a")]
    first = found[0]
    assert first == {"channel": "youtube", "post_key": "2026-11-20", "post_url": "https://www.youtube.com/shorts/vid1",
                     "comment_id": "yt-new", "author": "Acme Reader", "text": "Does this work on CPU?",
                     "at": "2026-11-26T09:00:00+00:00"}
    assert found[2]["post_key"] == "notes:acme-1" and found[2]["at"] == "2026-11-22T01:00:00+00:00"
    printed = capsys.readouterr()
    assert json.loads(printed.out) == found
    assert "fb-token-SECRET" not in printed.out + printed.err + summary.read_text()
    assert "yt-new" in summary.read_text()
    assert "Acme Reader" not in summary.read_text() and "Does this work on CPU?" not in summary.read_text(), \
        "the job summary of a public repository never shows names or comment text"
    # nothing is ever posted by list; only the Google token refresh uses POST
    assert http.posts() == []
    urls = [u for _, u, _ in http.calls]
    assert not any("future" in str(kw) for _, _, kw in http.calls), "a post that is not public yet is not read"
    assert f"{FB}/old/comments" not in urls, "posts older than --post-days are not read"
    # the replies of a thread with hidden replies are fetched with parentId, the others are not
    comment_calls = [kw["params"] for m, u, kw in http.calls if u == f"{YT}/comments"]
    assert comment_calls == [{"part": "snippet", "parentId": "yt-hidden-reply", "maxResults": 100, "textFormat": "plainText"}]
    fb_params = [kw["params"] for m, u, kw in http.calls if u == f"{FB}/777/comments"]
    assert fb_params[0]["filter"] == "stream" and "after" not in fb_params[0] and fb_params[1]["after"] == "CUR"


def test_list_days_option_widens_the_window(root):
    http = FakeHTTP(list_routes())
    found, notes, ok = comments.list_comments(
        comments.Context(root=root, cfg=comments.load_config(root), env=ENV, http=http, now=NOW),
        json.loads((root / "published.json").read_text()), days=30, post_days=60, channels=("facebook",))
    assert ok
    assert [c["comment_id"] for c in found] == ["777_a", "888_a", "777_e"]


def test_list_skips_a_channel_without_secrets(root, capsys):
    env = {k: v for k, v in ENV.items() if not k.startswith("YT_")}
    http = FakeHTTP(list_routes())
    assert comments.main(["list", "--channel", "youtube"], env=env, http=http, root=root, now=NOW) == 1
    assert "secrets not set" in capsys.readouterr().err
    assert http.calls == []


def test_list_keeps_going_when_one_post_fails(root, capsys):
    routes = list_routes()
    routes[("GET", f"{FB}/42_888/comments")] = Resp(400, {"error": {"message": "Unsupported get request", "code": 100}})
    found, notes, ok = comments.list_comments(
        comments.Context(root=root, cfg=comments.load_config(root), env=ENV, http=FakeHTTP(routes), now=NOW),
        json.loads((root / "published.json").read_text()), days=7, post_days=60, channels=("facebook",))
    assert not ok
    assert [c["comment_id"] for c in found] == ["777_a"]
    assert any("notes:acme-1" in n and "HTTP 400" in n for n in notes)


def write_replies(root, items):
    path = root / "replies.json"
    path.write_text(json.dumps(items), encoding="utf-8")
    return path


REPLIES = [{"channel": "youtube", "comment_id": "yt-new", "text": "Yes, it runs on CPU in about 2 s."},
           {"channel": "facebook", "comment_id": "777_a", "text": "A synthetic one, built in the notebook."}]


def reply_routes(yt_replies=(), fb_replies=()):
    return {
        ("GET", f"{YT}/channels"): Resp(200, {"items": [{"id": ME}]}),
        ("GET", f"{YT}/comments"): Resp(200, {"items": list(yt_replies)}),
        ("POST", f"{YT}/comments"): Resp(200, {"id": "yt-reply-1"}),
        ("GET", f"{FB}/777_a/comments"): Resp(200, {"data": [{"from": {"id": w}} for w in fb_replies]}),
        ("POST", f"{FB}/777_a/comments"): Resp(200, {"id": "777_a_reply"}),
    }


def test_reply_posts_on_both_channels(root):
    http = FakeHTTP(reply_routes())
    out, summary = root / "result.json", root / "summary.md"
    path = write_replies(root, REPLIES)
    assert comments.main(["reply", "--file", str(path), "--live", "--out", str(out), "--summary", str(summary)],
                         env=ENV, http=http, root=root, now=NOW) == 0
    results = json.loads(out.read_text())
    assert [(r["channel"], r["status"], r["reply_id"]) for r in results] == [
        ("youtube", "posted", "yt-reply-1"), ("facebook", "posted", "777_a_reply")]
    yt_post = next(kw for m, u, kw in http.calls if (m, u) == ("POST", f"{YT}/comments"))
    assert json.loads(yt_post["data"]) == {"snippet": {"parentId": "yt-new", "textOriginal": REPLIES[0]["text"]}}
    assert yt_post["params"] == {"part": "snippet"}
    fb_post = next(kw for m, u, kw in http.calls if (m, u) == ("POST", f"{FB}/777_a/comments"))
    assert fb_post["data"]["message"] == REPLIES[1]["text"]
    text = summary.read_text()
    assert "posted" in text and "yt-reply-1" in text and "fb-token-SECRET" not in text


def test_reply_skips_comments_we_already_answered(root):
    http = FakeHTTP(reply_routes(yt_replies=[yt_comment("r", "Us", "done", "2026-11-26T10:00:00Z", channel=ME)],
                                 fb_replies=["9001", "42"]))
    path = write_replies(root, REPLIES + [REPLIES[0]])
    out = root / "result.json"
    assert comments.main(["reply", "--file", str(path), "--live", "--out", str(out)], env=ENV, http=http, root=root, now=NOW) == 0
    assert [r["status"] for r in json.loads(out.read_text())] == ["skipped", "skipped", "skipped"]
    assert http.posts() == []


def test_reply_run_twice_posts_once(root):
    routes = reply_routes()
    routes[("GET", f"{YT}/comments")] = [Resp(200, {"items": []}),
                                        Resp(200, {"items": [yt_comment("yt-reply-1", "Us", "x", "2026-11-27T03:00:00Z", channel=ME)]})]
    routes[("GET", f"{FB}/777_a/comments")] = [Resp(200, {"data": []}), Resp(200, {"data": [{"from": {"id": "42"}}]})]
    http = FakeHTTP(routes)
    path = write_replies(root, REPLIES)
    for _ in range(2):
        assert comments.main(["reply", "--file", str(path), "--live"], env=ENV, http=http, root=root, now=NOW) == 0
    assert http.posts() == [("POST", f"{YT}/comments"), ("POST", f"{FB}/777_a/comments")]


def test_reply_without_live_calls_nothing(root):
    http = FakeHTTP({})
    out = root / "result.json"
    assert comments.main(["reply", "--file", str(write_replies(root, REPLIES)), "--out", str(out)],
                         env=ENV, http=http, root=root, now=NOW) == 0
    assert http.calls == []
    assert {r["status"] for r in json.loads(out.read_text())} == {"planned"}


def test_reply_stops_on_pause(root):
    (root / "PAUSE").write_text("")
    http = FakeHTTP({})
    assert comments.main(["reply", "--file", str(write_replies(root, REPLIES)), "--live"], env=ENV, http=http, root=root,
                         now=NOW) == 0
    assert http.calls == []


def test_facebook_reply_refused_without_engagement_scope(root, capsys):
    routes = reply_routes()
    refusal = Resp(403, {"error": {"message": "(#200) The user hasn't authorized the application to perform this action",
                                   "type": "OAuthException", "code": 200}})
    routes[("POST", f"{FB}/777_a/comments")] = refusal
    routes[("GET", f"{FB}/777_b/comments")] = Resp(200, {"data": []})
    http = FakeHTTP(routes)
    items = REPLIES + [{"channel": "facebook", "comment_id": "777_b", "text": "Thanks"}]
    out = root / "result.json"
    assert comments.main(["reply", "--file", str(write_replies(root, items)), "--live", "--out", str(out)],
                         env=ENV, http=http, root=root, now=NOW) == 1
    results = json.loads(out.read_text())
    assert [r["status"] for r in results] == ["posted", "refused", "refused"]
    assert "pages_manage_engagement" in results[1]["detail"] and "facebook_token.py" in results[1]["detail"]
    # after the first refusal no further Facebook reply is tried
    assert http.posts() == [("POST", f"{YT}/comments"), ("POST", f"{FB}/777_a/comments")]
    assert "fb-token-SECRET" not in capsys.readouterr().out


def test_youtube_reply_refused_without_force_ssl(root):
    routes = reply_routes()
    routes[("POST", f"{YT}/comments")] = Resp(403, {"error": {"errors": [{"reason": "insufficientPermissions"}]}})
    out = root / "result.json"
    assert comments.main(["reply", "--file", str(write_replies(root, REPLIES[:1])), "--live", "--out", str(out)],
                         env=ENV, http=FakeHTTP(routes), root=root, now=NOW) == 1
    row = json.loads(out.read_text())[0]
    assert row["status"] == "refused" and "youtube.force-ssl" in row["detail"]


def test_other_reply_errors_fail_without_the_token(root):
    routes = reply_routes()
    routes[("POST", f"{FB}/777_a/comments")] = Resp(500, {"error": {"message": "boom fb-token-SECRET", "code": 1}})
    out = root / "result.json"
    assert comments.main(["reply", "--file", str(write_replies(root, REPLIES[1:])), "--live", "--out", str(out)],
                         env=ENV, http=FakeHTTP(routes), root=root, now=NOW) == 1
    row = json.loads(out.read_text())[0]
    assert row["status"] == "failed" and "HTTP 500" in row["detail"] and "fb-token-SECRET" not in row["detail"]


@pytest.mark.parametrize("items", [{"channel": "youtube"}, [{"channel": "linkedin", "comment_id": "1", "text": "x"}],
                                   [{"channel": "youtube", "comment_id": "", "text": "x"}],
                                   [{"channel": "facebook", "comment_id": "1", "text": "  "}]])
def test_reply_file_is_checked_before_any_call(root, items, capsys):
    http = FakeHTTP({})
    assert comments.main(["reply", "--file", str(write_replies(root, items)), "--live"], env=ENV, http=http, root=root,
                         now=NOW) == 2
    assert http.calls == []


def test_facebook_token_asks_for_the_engagement_scopes():
    sys.path.insert(0, str(ROOT / "scripts" / "tokens"))
    import facebook_token
    scopes = facebook_token.SCOPES.split(",")
    assert "pages_manage_engagement" in scopes and "pages_read_user_content" in scopes
    assert "pages_manage_posts" in scopes, "posting keeps working"
