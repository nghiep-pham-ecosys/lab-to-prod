"""metrics.collect: Facebook per-post numbers and the manual LinkedIn and X inbox. Synthetic ids, fake HTTP."""
import csv
import datetime as dt
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from metrics import collect  # noqa: E402
from test_publish import ENV, MONDAY, Resp, ctx_for, repo  # noqa: E402,F401

TOKEN = ENV["FB_PAGE_TOKEN"]
FB_ENV = {"FB_PAGE_ID": "42", "FB_PAGE_TOKEN": TOKEN}


def graph_error(code, message, status=400, subcode=None):
    err = {"message": message, "type": "OAuthException", "code": code}
    if subcode:
        err["error_subcode"] = subcode
    return Resp(status, {"error": err})


class GraphHTTP:
    """Answers by object path, like the Graph API. `routes` maps '<path>' or '<path>?<fields|metric>' to a Resp."""

    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get(self, url, params=None, **kw):
        params = params or {}
        self.calls.append((url, dict(params)))
        path = url.split("/v27.0/", 1)[1]
        what = params.get("fields") or params.get("metric") or ""
        for key in (f"{path}?{what}", path):
            if key in self.routes:
                answer = self.routes[key]
                if isinstance(answer, Exception):
                    raise answer
                return answer
        raise AssertionError(f"unexpected call {path} {what}")


POST_FIELDS = collect.FB_POST_FIELDS


def post_body(reactions=5, comments=1, shares=None):
    body = {"reactions": {"data": [], "summary": {"total_count": reactions}},
            "comments": {"data": [], "summary": {"total_count": comments}}}
    if shares is not None:
        body["shares"] = {"count": shares}
    return body


def views(n):
    return Resp(200, {"data": [{"name": "post_media_view", "period": "lifetime", "values": [{"value": n}]}]})


STATE = {
    # API record: the photo id of a scheduled photo, now public
    "2026-11-16": {"facebook": {"id": "9001", "photo_id": "9001", "url": "fb-a", "scheduled_for": "2026-11-16T08:30:00+07:00"}},
    # manual record: the number from the post link, read as {page}_{id}
    "notes:toy": {"facebook": {"id": "7007", "manual": True, "url": "fb-b"}},
    # API record that Facebook still holds as scheduled: skipped quietly
    "2026-11-20": {"facebook": {"id": "9005", "photo_id": "9005", "url": "fb-c", "scheduled_for": "2026-11-20T08:30:00+07:00"}},
    # a follow-up comment record is not a post
    "2026-11-16:followup1": {"facebook": {"id": "42_9001_1", "url": "fb-d"}},
}


def base_routes():
    return {
        "42": Resp(200, {"followers_count": 12}),
        "9001?page_story_id": Resp(200, {"page_story_id": "42_8001", "id": "9001"}),
        f"42_8001?{POST_FIELDS}": Resp(200, post_body(reactions=7, comments=2, shares=3)),
        "42_8001/insights?post_media_view": views(140),
        f"42_7007?{POST_FIELDS}": Resp(200, post_body(reactions=4, comments=0)),
        "42_7007/insights?post_media_view": views(60),
    }


def rows(repo):
    with (repo / "metrics" / "metrics.csv").open() as fh:
        return {(r["item"], r["channel"]): r for r in csv.DictReader(fh)}


@pytest.fixture
def frepo(repo):
    (repo / "metrics" / "inbox").mkdir(parents=True)
    (repo / "published.json").write_text(json.dumps(STATE))
    return repo


def run(repo, routes):
    http = GraphHTTP(routes)
    ctx = ctx_for(repo, MONDAY + dt.timedelta(days=1), http=http, env=FB_ENV)
    code = collect.collect(ctx)
    return code, ctx, http


def test_photo_id_is_read_through_its_post_id(frepo):
    code, ctx, http = run(frepo, base_routes())
    assert code == 0
    r = rows(frepo)
    a = r[("2026-11-16", "facebook")]
    assert (a["reactions"], a["comments"], a["shares"], a["views"], a["url"]) == ("7", "2", "3", "140", "fb-a")
    b = r[("notes:toy", "facebook")]
    assert (b["reactions"], b["comments"], b["shares"], b["views"]) == ("4", "0", "0", "60")
    assert ("2026-11-20", "facebook") not in r              # still scheduled
    assert ("2026-11-16:followup1", "facebook") not in r    # not a post
    assert r[("_account", "facebook")]["followers"] == "12"
    paths = [u.rsplit("/", 1)[-1] for u, _ in http.calls]
    assert "9001" in paths and "9005" not in paths
    # the photo itself is never asked for post fields (the Photo node has no shares field)
    assert not any(u.endswith("/9001") and p.get("fields") == POST_FIELDS for u, p in http.calls)
    assert all(p.get("access_token") == TOKEN for _, p in http.calls)


def test_post_error_is_logged_with_status_code_and_message_and_the_others_continue(frepo):
    routes = base_routes()
    routes[f"42_8001?{POST_FIELDS}"] = graph_error(
        100, f"(#100) Tried accessing nonexisting field (shares) access_token={TOKEN} {TOKEN}", subcode=33)
    code, ctx, _ = run(frepo, routes)
    assert code == 0
    text = "\n".join(ctx.log)
    assert "facebook 2026-11-16: no numbers, post 42_8001: HTTP 400 code 100/33: (#100) Tried accessing" in text
    assert TOKEN not in text and "access_token=***" in text
    assert "facebook: 1 post(s) without numbers" in text
    r = rows(frepo)
    assert ("2026-11-16", "facebook") not in r and r[("notes:toy", "facebook")]["reactions"] == "4"


def test_photo_without_page_story_and_photo_errors_are_logged(frepo):
    routes = base_routes()
    routes["9001?page_story_id"] = Resp(200, {"id": "9001"})
    _, ctx, _ = run(frepo, routes)
    assert any("photo 9001: the photo has no page_story_id" in line for line in ctx.log)
    routes["9001?page_story_id"] = graph_error(10, "(#10) Permission denied", status=403)
    _, ctx, _ = run(frepo, routes)
    assert any("photo 9001: HTTP 403 code 10: (#10) Permission denied" in line for line in ctx.log)


def test_network_error_is_scrubbed_and_does_not_stop_the_run(frepo):
    routes = base_routes()
    routes["9001?page_story_id"] = ConnectionError(f"https://graph.facebook.com/x?access_token={TOKEN}")
    code, ctx, _ = run(frepo, routes)
    text = "\n".join(ctx.log)
    assert code == 0 and "ConnectionError" in text and TOKEN not in text
    assert rows(frepo)[("notes:toy", "facebook")]["views"] == "60"


def test_insights_error_keeps_the_counts_and_leaves_views_empty(frepo):
    routes = base_routes()
    routes["42_8001/insights?post_media_view"] = graph_error(200, "(#200) Requires read_insights permission", status=403)
    _, ctx, _ = run(frepo, routes)
    a = rows(frepo)[("2026-11-16", "facebook")]
    assert a["reactions"] == "7" and a["views"] == ""
    assert any("no views, insights 42_8001: HTTP 403 code 200" in line for line in ctx.log)


def test_error_reply_without_json_body_is_still_logged(frepo):
    class Broken(Resp):
        def json(self):
            raise ValueError("not json")

    bad = Broken(502)
    bad.text = "Bad gateway"
    routes = base_routes()
    routes[f"42_7007?{POST_FIELDS}"] = bad
    _, ctx, _ = run(frepo, routes)
    assert any("post 42_7007: HTTP 502 code ?: Bad gateway" in line for line in ctx.log)


def test_manual_inbox_reads_linkedin_and_x_with_item_and_measured_on(frepo):
    inbox = frepo / "metrics" / "inbox"
    (inbox / "linkedin-2026-11.csv").write_text(
        "item,date,measured_on,impressions,reactions,comments,shares,followers\n"
        "notes:toy,,2026-11-28,300,12,2,1,\n"
        ",2026-11-16,2026-11-28,412,18,3,1,\n"
        ",,2026-11-28,,,,,1530\n"
        ",,,,,,,\n")
    (inbox / "x-2026-11.csv").write_text("date,impressions,reactions,comments,shares,followers\n2026-11-16,90,2,,0,\n")
    old = dt.datetime(2026, 11, 20, 12, 0).timestamp()
    os.utime(inbox / "x-2026-11.csv", (old, old))
    got = {(r["item"], r["channel"]): r for r in collect.manual_inbox(frepo)}
    assert got[("notes:toy", "linkedin")]["impressions"] == "300"
    assert got[("notes:toy", "linkedin")]["measured_on"] == "2026-11-28"
    assert got[("2026-11-16", "linkedin")]["reactions"] == "18"
    assert got[("_account", "linkedin")]["followers"] == "1530"
    x = got[("2026-11-16", "x")]
    assert x["measured_on"] == "2026-11-20" and x["impressions"] == "90" and x["comments"] == ""
    assert len(got) == 4
