"""YouTube: upload the Short as private with publishAt, then upload its subtitles.

Official docs (checked 12 Nov 2026):
  https://developers.google.com/youtube/v3/docs/videos/insert
  https://developers.google.com/youtube/v3/guides/using_resumable_upload_protocol
  https://developers.google.com/youtube/v3/docs/captions/insert
  https://developers.google.com/youtube/v3/determine_quota_cost
- status.publishAt only works with privacyStatus "private"; YouTube makes the video public then.
- Quota: videos.insert has its own bucket of 100 calls a day; captions.insert costs 400 of the
  10,000 daily units. Two Shorts a week is far below both.
- The revision history (2 Nov 2026) says uploads from unverified API projects are no longer
  locked to private. If a video still stays private after publishAt, set it public in Studio.
- There is no "Short" flag: YouTube decides from the vertical format and the length.
Scopes: youtube.upload and youtube.force-ssl (captions).
"""
from __future__ import annotations

import datetime as dt
import json

from .common import Context, Post, PublishError, Skip, check

NEEDS = ["YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"]
UPLOAD = "https://www.googleapis.com/upload/youtube/v3"
AI_NOTE = "Animation rendered from code; script drafted with AI assistance and reviewed by me."


def access_token(ctx: Context) -> str:
    resp = check(ctx.http.post("https://oauth2.googleapis.com/token", data={
        "client_id": ctx.secret("YT_CLIENT_ID"), "client_secret": ctx.secret("YT_CLIENT_SECRET"),
        "refresh_token": ctx.secret("YT_REFRESH_TOKEN"), "grant_type": "refresh_token"}), "Google token refresh")
    return resp.json()["access_token"]


def publish_at(ctx: Context, post: Post) -> dt.datetime:
    raw = post.meta.get("short_publish_at")
    when = raw if isinstance(raw, dt.datetime) else dt.datetime.fromisoformat(str(raw))
    if when <= ctx.now:
        raise Skip(f"short_publish_at {when.isoformat()} is in the past; not back-posting")
    return when


def metadata(ctx: Context, post: Post) -> dict:
    lines = [ln for ln in post.text("youtube").splitlines() if ln.strip()]
    title, body = lines[0].strip(), "\n".join(lines[1:])
    when = publish_at(ctx, post).astimezone(dt.timezone.utc)
    return {
        "snippet": {"title": title, "categoryId": str(ctx.cfg["youtube_category_id"]), "defaultLanguage": "en",
                    "description": f"{body}\n\nFull note: {post.url(ctx.cfg)}\n\n{AI_NOTE}"},
        "status": {"privacyStatus": "private", "publishAt": when.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                   "selfDeclaredMadeForKids": False, "containsSyntheticMedia": False},
    }


def publish(ctx: Context, post: Post) -> dict:
    video, srt = post.folder / "short.mp4", post.folder / "short.srt"
    if not video.exists():
        raise PublishError("short.mp4 is missing")
    body = metadata(ctx, post)
    auth = {"Authorization": f"Bearer {access_token(ctx)}"}
    size = video.stat().st_size
    start = check(ctx.http.post(f"{UPLOAD}/videos?uploadType=resumable&part=snippet,status", headers={
        **auth, "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Length": str(size), "X-Upload-Content-Type": "video/mp4"}, data=json.dumps(body)),
        "YouTube upload start", ok=(200,))
    with video.open("rb") as fh:
        done = check(ctx.http.put(start.headers["Location"], headers={**auth, "Content-Length": str(size), "Content-Type": "video/mp4"},
                                  data=fh), "YouTube upload")
    video_id = done.json()["id"]
    result = {"id": video_id, "url": f"https://www.youtube.com/shorts/{video_id}",
              "scheduled_for": body["status"]["publishAt"], "captions": False}
    if srt.exists():
        try:
            meta = {"snippet": {"videoId": video_id, "language": "en", "name": "English"}}
            check(ctx.http.post(f"{UPLOAD}/captions?uploadType=multipart&part=snippet", headers=auth, files={
                "snippet": (None, json.dumps(meta), "application/json; charset=UTF-8"),
                "file": ("short.srt", srt.read_bytes(), "application/octet-stream")}), "YouTube captions")
            result["captions"] = True
        except Exception as exc:  # noqa: BLE001 - the video is uploaded; captions can be added in Studio
            ctx.say(f"  youtube: video uploaded, captions were refused ({str(exc)[:120]}); upload short.srt in Studio")
    return result


def describe(ctx: Context, post: Post) -> str:
    body = metadata(ctx, post)
    return f"upload short.mp4 as private, public at {body['status']['publishAt']}, title {body['snippet']['title']!r}, + short.srt"
