"""publish/youtube_release.py: a staged batch from a draft release goes to YouTube as private + publishAt.

Every HTTP call goes to a fake client; no network, no real token.
"""
import datetime as dt
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from publish import youtube_release as yr  # noqa: E402
from publish.common import Context, load_config  # noqa: E402

TZ = dt.timezone(dt.timedelta(hours=7))
NOW = dt.datetime(2026, 11, 26, 9, 0, tzinfo=TZ)
ENV = {"YT_CLIENT_ID": "cid", "YT_CLIENT_SECRET": "csecret", "YT_REFRESH_TOKEN": "refresh"}
TAG = "yt-example-en"


class Resp:
    def __init__(self, status=200, body=None, headers=None):
        self.status_code, self._body, self.headers = status, body or {}, headers or {}
        self.text = json.dumps(self._body)

    def json(self):
        return self._body


class FakeHTTP:
    """Answers like Google does; counts uploads so each video gets its own id."""

    def __init__(self, fail_upload_of=None, fail_captions=False):
        self.calls, self.uploads = [], 0
        self.fail_upload_of, self.fail_captions = fail_upload_of, fail_captions

    def _handle(self, method, url, **kw):
        self.calls.append((method, url, kw))
        if "oauth2.googleapis.com" in url:
            return Resp(200, {"access_token": "ya29.test"})
        if "uploadType=resumable" in url:
            body = json.loads(kw["data"])
            if self.fail_upload_of and body["snippet"]["title"] == self.fail_upload_of:
                return Resp(403, {"error": "quotaExceeded"})
            return Resp(200, {}, {"Location": "https://upload.youtube.test/session"})
        if "upload.youtube.test" in url:
            self.uploads += 1
            return Resp(201, {"id": f"VID{self.uploads:08d}"})
        if "/captions" in url:
            return Resp(500, {"error": "boom"}) if self.fail_captions else Resp(200, {"id": "cap1"})
        raise AssertionError(f"unexpected call {method} {url}")

    def post(self, url, **kw):
        return self._handle("POST", url, **kw)

    def put(self, url, **kw):
        return self._handle("PUT", url, **kw)

    def urls(self):
        return [u for _, u, _ in self.calls]

    def bodies(self):
        return [json.loads(kw["data"]) for _, u, kw in self.calls if "uploadType=resumable" in u]


def item(key, kind="video", publish_at="2026-12-01T19:00:00+07:00", captions=True, **extra):
    name = key.split("/")[-1]
    return {"key": key, "kind": kind, "path": ("shorts/" if kind == "short" else "") + f"{name}.mp4",
            "video": f"{name}.mp4", "captions": f"{name}.srt" if captions else None,
            "title": f"Title of {name}", "description": f"About {name}.\n\nMade with AI: synthetic voice.",
            "tags": ["rag", "toy example"], "language": "en", "publish_at": publish_at, "synthetic_media": True, **extra}


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "publish").mkdir()
    (tmp_path / "publish" / "config.yaml").write_text((ROOT / "publish" / "config.yaml").read_text())
    return tmp_path


def stage(tmp_path, items, tag=TAG, job="example"):
    assets = tmp_path / "batch"
    assets.mkdir(exist_ok=True)
    for it in items:
        (assets / it["video"]).write_bytes(b"\x00" * 1024)
        if it.get("captions"):
            (assets / it["captions"]).write_text("1\n00:00:00,000 --> 00:00:02,000\nHi\n")
    (assets / "manifest.json").write_text(json.dumps({"version": 1, "tag": tag, "job": job, "items": items}))
    return assets


def ctx_for(repo, live=True, http=None, now=NOW):
    return Context(repo, load_config(repo), dict(ENV), http or FakeHTTP(), now, live=live)


def batch():
    return [item("example.en"), item("example-1.en", kind="short", publish_at="2026-12-02T19:00:00+07:00")]


def test_dry_run_calls_nothing_and_writes_no_result(repo):
    assets = stage(repo, batch())
    ctx = ctx_for(repo, live=False)
    out = repo / "gh-output"
    assert yr.run(ctx, assets, TAG, github_output=out) == 0
    assert ctx.http.calls == []
    assert not (assets / "result.json").exists()
    assert out.read_text() == "complete=false\n"
    assert any("DRY RUN example.en" in line for line in ctx.log)


def test_live_uploads_private_with_publish_at_captions_and_logs_quota(repo):
    assets = stage(repo, batch())
    ctx = ctx_for(repo)
    out, summary = repo / "gh-output", repo / "summary.md"
    assert yr.run(ctx, assets, TAG, summary=summary, github_output=out) == 0
    bodies = ctx.http.bodies()
    assert [b["status"]["privacyStatus"] for b in bodies] == ["private", "private"]
    assert [b["status"]["publishAt"] for b in bodies] == ["2026-12-01T12:00:00.000Z", "2026-12-02T12:00:00.000Z"]
    assert bodies[0]["snippet"]["defaultLanguage"] == "en" and bodies[0]["snippet"]["categoryId"] == "28"
    assert bodies[0]["status"]["containsSyntheticMedia"] is True
    assert bodies[0]["snippet"]["tags"] == ["rag", "toy example"]
    assert sum("/captions" in u for u in ctx.http.urls()) == 2
    assert sum("oauth2" in u for u in ctx.http.urls()) == 1
    result = json.loads((assets / "result.json").read_text())
    assert result["complete"] is True and result["job"] == "example" and result["tag"] == TAG
    assert result["items"]["example.en"]["video_id"] == "VID00000001"
    assert result["items"]["example.en"]["url"] == "https://www.youtube.com/watch?v=VID00000001"
    assert result["items"]["example-1.en"]["url"] == "https://www.youtube.com/shorts/VID00000002"
    assert result["items"]["example-1.en"]["path"] == "shorts/example-1.en.mp4"
    assert result["quota"] == {"videos_insert": 2, "captions_insert": 2, "units": 800}
    assert out.read_text() == "complete=true\n"
    text = summary.read_text()
    assert "VID00000001" in text and "800 units" in text and "Complete: yes" in text
    assert any("quota: videos.insert" in line for line in ctx.log)
    assert not any("ya29" in line or "refresh" in line for line in ctx.log)


def test_rerun_skips_items_already_uploaded(repo):
    assets = stage(repo, batch())
    first = FakeHTTP(fail_upload_of="Title of example-1.en")
    assert yr.run(ctx_for(repo, http=first), assets, TAG) == 1
    result = json.loads((assets / "result.json").read_text())
    assert result["complete"] is False and set(result["items"]) == {"example.en"}
    second = FakeHTTP()
    out = repo / "gh-output"
    assert yr.run(ctx_for(repo, http=second), assets, TAG, github_output=out) == 0
    assert [b["snippet"]["title"] for b in second.bodies()] == ["Title of example-1.en"]
    result = json.loads((assets / "result.json").read_text())
    assert result["complete"] is True and result["items"]["example.en"]["video_id"] == "VID00000001"
    assert result["quota"]["videos_insert"] == 2
    assert out.read_text() == "complete=true\n"


def test_refused_captions_keep_the_video_and_count_the_quota(repo):
    assets = stage(repo, [item("example.en")])
    ctx = ctx_for(repo, http=FakeHTTP(fail_captions=True))
    assert yr.run(ctx, assets, TAG) == 0
    result = json.loads((assets / "result.json").read_text())
    assert result["items"]["example.en"]["captions"] is False and result["complete"] is True
    assert result["quota"]["units"] == 400
    assert any("WARN example.en: captions were refused" in line for line in ctx.log)


def test_past_publish_time_is_refused_and_publish_at_moves_the_batch(repo):
    assets = stage(repo, batch())
    late = ctx_for(repo, now=dt.datetime(2026, 12, 1, 20, 0, tzinfo=TZ))
    assert yr.run(late, assets, TAG) == 1
    assert [b["snippet"]["title"] for b in late.http.bodies()] == ["Title of example-1.en"]
    assert any("FAIL example.en: publish time" in line for line in late.log)
    (assets / "result.json").unlink(missing_ok=True)
    moved = ctx_for(repo, now=dt.datetime(2026, 12, 1, 20, 0, tzinfo=TZ))
    assert yr.run(moved, assets, TAG, publish_at="2026-12-08T19:00:00+07:00") == 0
    assert [b["status"]["publishAt"] for b in moved.http.bodies()] == ["2026-12-08T12:00:00.000Z", "2026-12-09T12:00:00.000Z"]


@pytest.mark.parametrize("change, message", [
    ({"title": "x" * 101}, "title must be"),
    ({"title": "a <b>"}, "title must be"),
    ({"description": "No label here."}, "made with AI"),
    ({"description": "made with AI " + "x" * 5000}, "description must be"),
    ({"publish_at": "2026-12-01T19:00:00"}, "no UTC offset"),
    ({"video": "../x.mp4"}, "video must be"),
    ({"captions": "missing.srt"}, "missing.srt is not among the release assets"),
    ({"tags": ["a,b"]}, "tags must be"),
    ({"language": "English"}, "language must be"),
    ({"path": "/abs/x.mp4"}, "path must be"),
    ({"kind": "live"}, "kind must be"),
])
def test_manifest_problems_stop_before_any_call(repo, change, message):
    it = item("example.en")
    assets = stage(repo, [it])
    data = json.loads((assets / "manifest.json").read_text())
    data["items"][0].update(change)
    (assets / "manifest.json").write_text(json.dumps(data))
    ctx = ctx_for(repo)
    assert yr.run(ctx, assets, TAG) == 1
    assert ctx.http.calls == []
    assert any(message in line for line in ctx.log), ctx.log


def test_tag_mismatch_and_foreign_result_are_refused(repo):
    assets = stage(repo, [item("example.en")])
    ctx = ctx_for(repo)
    assert yr.run(ctx, assets, "yt-other-en") == 1 and ctx.http.calls == []
    (assets / "result.json").write_text(json.dumps({"tag": "yt-other-en", "job": "example", "items": {}}))
    ctx = ctx_for(repo)
    assert yr.run(ctx, assets, TAG) == 1 and ctx.http.calls == []
    assert any("another batch" in line for line in ctx.log)


def test_pause_file_stops_before_any_call(repo):
    assets = stage(repo, [item("example.en")])
    (repo / "PAUSE").write_text("")
    ctx = ctx_for(repo)
    out = repo / "gh-output"
    assert yr.run(ctx, assets, TAG, github_output=out) == 1
    assert ctx.http.calls == [] and out.read_text() == "complete=false\n"


def test_missing_secret_fails_without_upload_or_leak(repo):
    assets = stage(repo, [item("example.en")])
    ctx = Context(repo, load_config(repo), {}, FakeHTTP(), NOW, live=True)
    assert yr.run(ctx, assets, TAG) == 1
    assert ctx.http.calls == []
    assert any("secret YT_CLIENT_ID is not set" in line for line in ctx.log)


def test_tags_length_counts_quotes_and_commas():
    assert yr.tags_length(["a", "b c"]) == 1 + 5 + 1
