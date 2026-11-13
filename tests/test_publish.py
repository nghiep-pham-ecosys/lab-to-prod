import datetime as dt
import json
import sys
from pathlib import Path

import pytest
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from publish import devto, facebook, run as runner, telegram, youtube  # noqa: E402
from publish.common import Context, State, load_articles, load_config, load_posts  # noqa: E402

TZ = dt.timezone(dt.timedelta(hours=7))
ENV = {"LINKEDIN_ACCESS_TOKEN": "li-token", "LINKEDIN_PERSON_URN": "abc123", "FB_PAGE_ID": "42", "FB_PAGE_TOKEN": "fb-token",
       "YT_CLIENT_ID": "cid", "YT_CLIENT_SECRET": "csecret", "YT_REFRESH_TOKEN": "refresh",
       "TELEGRAM_BOT_TOKEN": "111:tg-token", "TELEGRAM_CHANNEL": "@labtoprod_test", "DEVTO_API_KEY": "dev-key"}


class Resp:
    def __init__(self, status=200, body=None, headers=None):
        self.status_code, self._body, self.headers = status, body or {}, headers or {}
        self.text = json.dumps(self._body)

    def json(self):
        return self._body


class FakeHTTP:
    """Records every call and answers like the real platforms do."""

    def __init__(self, fail=()):
        self.calls, self.fail = [], fail

    def _handle(self, method, url, **kw):
        self.calls.append((method, url, kw))
        if any(f in url for f in self.fail):
            return Resp(500, {"error": "boom"})
        if "registerUpload" in url:
            return Resp(200, {"value": {"asset": "urn:li:digitalmediaAsset:A1", "uploadMechanism": {
                "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest": {"uploadUrl": "https://upload.linkedin.test/u"}}}})
        if "upload.linkedin.test" in url:
            return Resp(201)
        if url.endswith("/ugcPosts"):
            return Resp(201, {}, {"X-RestLi-Id": "urn:li:share:999"})
        if "/comments" in url:
            return Resp(201, {})
        if "graph.facebook.com" in url:
            return Resp(200, {"id": "photo1", "post_id": "42_777"})
        if "oauth2.googleapis.com" in url:
            return Resp(200, {"access_token": "ya29.test"})
        if "uploadType=resumable" in url:
            return Resp(200, {}, {"Location": "https://upload.youtube.test/session"})
        if "upload.youtube.test" in url:
            return Resp(201, {"id": "VIDEO123"})
        if "/captions" in url:
            return Resp(200, {"id": "cap1"})
        if "api.telegram.org" in url:
            return Resp(200, {"ok": True, "result": {"message_id": 5, "chat": {"username": "labtoprod_test"}}})
        if "articles/me/all" in url:
            return Resp(200, [])
        if url.endswith("/api/articles"):
            return Resp(201, {"id": 77, "url": "https://dev.to/x/why"})
        raise AssertionError(f"unexpected call {method} {url}")

    def post(self, url, **kw):
        return self._handle("POST", url, **kw)

    def put(self, url, **kw):
        return self._handle("PUT", url, **kw)

    def get(self, url, **kw):
        return self._handle("GET", url, **kw)

    def urls(self):
        return [u for _, u, _ in self.calls]


def write_post(root, date, slug, series, part, status="approved", channels=None, short_at=None):
    y, w, _ = date.isocalendar()
    folder = root / "content" / f"{y}-W{w:02d}" / f"{date}-{slug}"
    folder.mkdir(parents=True)
    meta = {"date": date, "series": series, "part": part, "title": f"Title {slug}", "status": status, "sources": [],
            "channels": channels or ["linkedin", "facebook", "telegram", "x_manual"], "short_publish_at": short_at, "image_alt": "alt text"}
    body = {"linkedin": "5 things about it.\n\n#a #b #c", "x": "An X post.", "facebook": "A Facebook post.",
            "telegram": "A Telegram post.", "youtube": "Keyword Title #Shorts\nWhat the video shows."}
    (folder / "post.md").write_text("---\n" + yaml.safe_dump(meta) + "---\n" + "".join(f"\n## {k}\n\n{t}\n" for k, t in body.items()))
    Image.new("RGB", (1200, 1200), "#F6F1E7").save(folder / "image.png")
    if short_at:
        (folder / "short.mp4").write_bytes(b"\x00" * 2048)
        (folder / "short.srt").write_text("1\n00:00:00,000 --> 00:00:02,000\nHi\n")
    return folder


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "publish").mkdir()
    (tmp_path / "publish" / "config.yaml").write_text((ROOT / "publish" / "config.yaml").read_text())
    posts = tmp_path / "blog" / "src" / "content" / "posts"
    posts.mkdir(parents=True)
    (posts / "why.md").write_text("---\ntitle: Why\ndescription: Because.\ndate: 2026-11-21\nseries: build-log\ntags: [build-in-public, llmops]\n---\n\nSee the [feed](/lab-to-prod/rss.xml).\n")
    write_post(tmp_path, dt.date(2026, 11, 16), "dsa-p2", "dsa-in-java", 2,
               channels=["linkedin", "facebook", "telegram", "x_manual", "youtube"], short_at="2026-11-17T19:00:00+07:00")
    write_post(tmp_path, dt.date(2026, 11, 17), "ml-p1", "ml-foundations", 1)
    write_post(tmp_path, dt.date(2026, 11, 18), "ai-eng-p2", "ai-engineering", 2, status="draft")
    return tmp_path


def ctx_for(repo, now, live=True, http=None, env=ENV):
    return Context(repo, load_config(repo), dict(env), http or FakeHTTP(), now, live=live)


SUNDAY = dt.datetime(2026, 11, 15, 22, 30, tzinfo=TZ)
MONDAY = dt.datetime(2026, 11, 16, 8, 15, tzinfo=TZ)


def test_dry_run_makes_no_calls_and_writes_no_state(repo):
    ctx = ctx_for(repo, SUNDAY, live=False)
    assert runner.run(ctx, "merge") == 0 and runner.run(ctx, "daily", date=dt.date(2026, 11, 16)) == 0
    assert ctx.http.calls == [] and not (repo / "published.json").exists()
    assert any("DRY RUN would schedule for 2026-11-16T08:30:00+07:00" in line for line in ctx.log)


def test_merge_schedules_facebook_and_uploads_short_for_approved_posts_only(repo):
    ctx = ctx_for(repo, SUNDAY)
    assert runner.run(ctx, "merge") == 0
    state = json.loads((repo / "published.json").read_text())
    assert set(state) == {"2026-11-16", "2026-11-17"}          # the draft of 18 Nov is untouched
    assert set(state["2026-11-16"]) == {"facebook", "youtube"} and set(state["2026-11-17"]) == {"facebook"}
    fb = [kw for _, u, kw in ctx.http.calls if "graph.facebook.com/v27.0/42/photos" in u]
    assert fb[0]["data"]["published"] == "false"
    assert fb[0]["data"]["scheduled_publish_time"] == str(int(dt.datetime(2026, 11, 16, 8, 30, tzinfo=TZ).timestamp()))
    assert fb[0]["files"]["source"][2] == "image/jpeg"
    start = next(kw for _, u, kw in ctx.http.calls if "uploadType=resumable" in u)
    status = json.loads(start["data"])["status"]
    assert status == {"privacyStatus": "private", "publishAt": "2026-11-17T12:00:00.000Z",
                      "selfDeclaredMadeForKids": False, "containsSyntheticMedia": False}
    assert state["2026-11-16"]["youtube"]["captions"] is True
    assert not any("linkedin" in u or "telegram" in u for u in ctx.http.urls())


def test_daily_posts_only_today_to_linkedin_and_telegram(repo):
    ctx = ctx_for(repo, MONDAY)
    assert runner.run(ctx, "daily") == 0
    state = json.loads((repo / "published.json").read_text())
    assert set(state) == {"2026-11-16"} and set(state["2026-11-16"]) == {"linkedin", "telegram"}
    assert state["2026-11-16"]["linkedin"] == {**state["2026-11-16"]["linkedin"], "id": "urn:li:share:999", "comment": True}
    assert state["2026-11-16"]["telegram"]["url"] == "https://t.me/labtoprod_test/5"
    ugc = next(kw for _, u, kw in ctx.http.calls if u.endswith("/ugcPosts"))
    assert ugc["json"]["author"] == "urn:li:person:abc123"
    assert "http" not in ugc["json"]["specificContent"]["com.linkedin.ugc.ShareContent"]["shareCommentary"]["text"]


def test_live_channels_limit_posting_to_listed_channels(repo):
    env = {"FB_PAGE_ID": "42", "FB_PAGE_TOKEN": "fb-token"}       # only the Facebook secrets exist
    merge = ctx_for(repo, SUNDAY, env=env)
    assert runner.run(merge, "merge", live_channels={"facebook"}) == 0
    state = json.loads((repo / "published.json").read_text())
    assert {ch for rec in state.values() for ch in rec} == {"facebook"}
    assert not any("youtube" in u or "googleapis" in u for u in merge.http.urls())
    assert any("youtube 2026-11-16: DRY RUN" in line for line in merge.log)
    daily = ctx_for(repo, MONDAY, env=env)
    assert runner.run(daily, "daily", live_channels={"facebook"}) == 0   # no FAILED for missing secrets
    assert daily.http.calls == []


def test_second_run_is_idempotent(repo):
    runner.run(ctx_for(repo, MONDAY), "daily")
    again = ctx_for(repo, MONDAY)
    assert runner.run(again, "daily") == 0 and again.http.calls == []
    assert any("already published" in line for line in again.log)


def test_one_failing_channel_does_not_block_the_other_and_exit_code_is_1(repo):
    ctx = ctx_for(repo, MONDAY, http=FakeHTTP(fail=("registerUpload",)))
    assert runner.run(ctx, "daily") == 1
    state = json.loads((repo / "published.json").read_text())
    assert set(state["2026-11-16"]) == {"telegram"}
    retry = ctx_for(repo, MONDAY)                              # next run only redoes the failed channel
    assert runner.run(retry, "daily") == 0
    assert not any("telegram" in u for u in retry.http.urls())


def test_linkedin_comment_refusal_keeps_the_post(repo):
    ctx = ctx_for(repo, MONDAY, http=FakeHTTP(fail=("/comments",)))
    assert runner.run(ctx, "daily", only=["linkedin"]) == 0
    assert json.loads((repo / "published.json").read_text())["2026-11-16"]["linkedin"]["comment"] is False


def test_pause_file_stops_everything(repo):
    (repo / "PAUSE").write_text("")
    ctx = ctx_for(repo, MONDAY)
    assert runner.run(ctx, "daily") == 0 and ctx.http.calls == []


def test_missing_secret_fails_that_channel_without_leaking(repo):
    env = {k: val for k, val in ENV.items() if k != "TELEGRAM_BOT_TOKEN"}
    ctx = ctx_for(repo, MONDAY, env=env)
    assert runner.run(ctx, "daily") == 1
    assert any("secret TELEGRAM_BOT_TOKEN is not set" in line for line in ctx.log)
    assert not any(token in line for line in ctx.log for token in ENV.values() if "token" in token)


def test_channel_set_to_manual_in_config_is_skipped(repo):
    cfg = repo / "publish" / "config.yaml"
    cfg.write_text(cfg.read_text().replace("linkedin: api", "linkedin: manual"))
    ctx = ctx_for(repo, MONDAY)
    runner.run(ctx, "daily")
    assert not any("linkedin" in u for u in ctx.http.urls())


def test_facebook_window(repo):
    post = load_posts(repo)[0]
    assert facebook.plan(ctx_for(repo, SUNDAY), post) == dt.datetime(2026, 11, 16, 8, 30, tzinfo=TZ)
    assert facebook.plan(ctx_for(repo, dt.datetime(2026, 11, 16, 8, 25, tzinfo=TZ)), post) is None   # too close: publish now
    with pytest.raises(facebook.Skip):
        facebook.plan(ctx_for(repo, dt.datetime(2026, 10, 1, tzinfo=TZ)), post)                         # more than 29 days ahead
    with pytest.raises(facebook.Skip):
        facebook.plan(ctx_for(repo, dt.datetime(2026, 11, 20, tzinfo=TZ)), post)                        # in the past


def test_youtube_does_not_back_post_and_telegram_enforces_caption_limit(repo):
    post = load_posts(repo)[0]
    with pytest.raises(youtube.Skip):
        youtube.publish_at(ctx_for(repo, dt.datetime(2026, 11, 18, tzinfo=TZ)), post)
    post.sections["telegram"] = "x" * 1000
    with pytest.raises(telegram.PublishError):
        telegram.caption(ctx_for(repo, MONDAY), post)


def test_devto_publishes_article_on_its_day_with_canonical_and_absolute_links(repo):
    ctx = ctx_for(repo, dt.datetime(2026, 11, 21, 8, 15, tzinfo=TZ))
    assert runner.run(ctx, "daily", only=["devto"]) == 0
    sent = next(kw for m, u, kw in ctx.http.calls if m == "POST" and u.endswith("/api/articles"))["json"]["article"]
    assert sent["canonical_url"] == "https://nghiep-pham-ecosys.github.io/lab-to-prod/posts/why/"
    assert sent["tags"] == "buildinpublic,llmops" and sent["published"] is True
    assert "](https://nghiep-pham-ecosys.github.io/lab-to-prod/rss.xml)" in sent["body_markdown"]
    assert json.loads((repo / "published.json").read_text())["article:why"]["devto"]["id"] == 77
    early = ctx_for(repo, dt.datetime(2026, 11, 20, 8, 15, tzinfo=TZ))
    (repo / "published.json").unlink()
    runner.run(early, "daily", only=["devto"])
    assert early.http.calls == []                                # not before its date


def test_devto_finds_an_existing_article_instead_of_duplicating(repo):
    class Existing(FakeHTTP):
        def _handle(self, method, url, **kw):
            if "articles/me/all" in url:
                self.calls.append((method, url, kw))
                return Resp(200, [{"id": 9, "url": "https://dev.to/x/old", "canonical_url": "https://nghiep-pham-ecosys.github.io/lab-to-prod/posts/why/"}])
            return super()._handle(method, url, **kw)
    ctx = ctx_for(repo, MONDAY, http=Existing())
    assert devto.publish(ctx, load_articles(repo)[0]) == {"id": 9, "url": "https://dev.to/x/old", "found_existing": True}
    assert not any(m == "POST" for m, _, _ in ctx.http.calls)


def test_export_writes_x_and_hashnode_files_without_any_call(repo):
    ctx = ctx_for(repo, SUNDAY, live=False)
    names = sorted(p.name for p in runner.export(ctx, "2026-W47"))
    assert names == ["hashnode-why.md", "x-schedule.md", "x.md", "x.md", "x.md"] and ctx.http.calls == []
    sheet = (repo / "content/2026-W47/x-schedule.md").read_text()
    assert "Mon 16 Nov, 08:30" in sheet and "An X post." in sheet
    assert "original URL = https://nghiep-pham-ecosys.github.io/lab-to-prod/posts/why/" in (repo / "content/2026-W47/hashnode-why.md").read_text()


def test_state_survives_reload(repo):
    s = State(repo)
    s.record("2026-11-16", "telegram", {"id": 1, "url": "u"}, MONDAY)
    s.save()
    assert State(repo).done("2026-11-16", "telegram") and not State(repo).done("2026-11-16", "linkedin")
