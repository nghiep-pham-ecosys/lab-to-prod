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
Scopes: youtube.upload and youtube.force-ssl (captions, playlists).
The long videos from nghiep-motion-studio reuse upload_video and insert_captions (publish/youtube_release.py).

Playlists (docs checked 26 Nov 2026):
  https://developers.google.com/youtube/v3/docs/playlists/list
  https://developers.google.com/youtube/v3/docs/playlists/insert
  https://developers.google.com/youtube/v3/docs/playlistItems/list
  https://developers.google.com/youtube/v3/docs/playlistItems/insert
- playlists.list and playlistItems.list cost 1 unit each; playlists.insert and playlistItems.insert cost 50 units.
- playlists.list with mine=true returns the channel's own playlists, at most 50 a page (maxResults 0-50, default 5);
  nextPageToken goes back as pageToken for the next page.
- playlistItems.list takes playlistId and an optional videoId, so one call answers "is this video in it?".
- playlists.insert and playlistItems.insert accept the youtube.force-ssl scope that captions already need.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from .common import Context, Post, PublishError, Skip, check

NEEDS = ["YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"]
UPLOAD = "https://www.googleapis.com/upload/youtube/v3"
API = "https://www.googleapis.com/youtube/v3"
AI_NOTE = "Animation rendered from code; script drafted with AI assistance and reviewed by me."
# Quota (docs checked 12 Nov 2026, see above): every videos.insert takes one of the 100 uploads a day in its own
# bucket; every captions.insert costs 400 of the 10,000 daily units. The token refresh is OAuth, not the Data API.
UPLOADS_PER_DAY = 100
CAPTIONS_UNITS = 400
DAILY_UNITS = 10_000
LIST_UNITS = 1             # playlists.list, playlistItems.list
PLAYLIST_INSERT_UNITS = 50  # playlists.insert, playlistItems.insert
MAX_PLAYLIST_PAGES = 40     # 50 playlists a page: 2,000 playlists before the search gives up


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


def upload_video(ctx: Context, video: Path, body: dict, auth: dict) -> str:
    """Resumable upload of one mp4 with its snippet and status; returns the new video id (one videos.insert)."""
    size = video.stat().st_size
    start = check(ctx.http.post(f"{UPLOAD}/videos?uploadType=resumable&part=snippet,status", headers={
        **auth, "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Length": str(size), "X-Upload-Content-Type": "video/mp4"}, data=json.dumps(body)),
        "YouTube upload start", ok=(200,))
    with video.open("rb") as fh:
        done = check(ctx.http.put(start.headers["Location"], headers={**auth, "Content-Length": str(size), "Content-Type": "video/mp4"},
                                  data=fh), "YouTube upload")
    return done.json()["id"]


def insert_captions(ctx: Context, video_id: str, srt: Path, language: str, name: str, auth: dict) -> None:
    """Add an SRT as a caption track (one captions.insert, 400 units). Raises PublishError when refused."""
    meta = {"snippet": {"videoId": video_id, "language": language, "name": name}}
    check(ctx.http.post(f"{UPLOAD}/captions?uploadType=multipart&part=snippet", headers=auth, files={
        "snippet": (None, json.dumps(meta), "application/json; charset=UTF-8"),
        "file": (srt.name, srt.read_bytes(), "application/octet-stream")}), "YouTube captions")


def playlist_pages(ctx: Context, auth: dict, before_call=lambda: None):
    """Yield the channel's own playlists page by page (one playlists.list call, 1 unit, per page).
    ``before_call`` runs before every call, so the caller can count the quota."""
    token = None
    for _ in range(MAX_PLAYLIST_PAGES):
        params = {"part": "snippet", "mine": "true", "maxResults": 50}
        if token:
            params["pageToken"] = token
        before_call()
        page = check(ctx.http.get(f"{API}/playlists", params=params, headers=auth), "YouTube playlists.list").json()
        yield page.get("items") or []
        token = page.get("nextPageToken")
        if not token:
            return
    raise PublishError(f"playlists.list gave more than {MAX_PLAYLIST_PAGES} pages; refusing to guess")


def create_playlist(ctx: Context, playlist: dict, language: str, auth: dict) -> str:
    """Create a playlist on the channel (one playlists.insert, 50 units); returns its id."""
    body = {"snippet": {"title": playlist["title"], "description": playlist.get("description", ""),
                        "defaultLanguage": language},
            "status": {"privacyStatus": playlist.get("privacy", "public")}}
    resp = check(ctx.http.post(f"{API}/playlists", params={"part": "snippet,status"},
                               headers={**auth, "Content-Type": "application/json; charset=UTF-8"},
                               data=json.dumps(body)), "YouTube playlists.insert")
    return resp.json()["id"]


def playlist_has_video(ctx: Context, playlist_id: str, video_id: str, auth: dict) -> bool:
    """Is the video already in the playlist? (one playlistItems.list, 1 unit)"""
    params = {"part": "id", "playlistId": playlist_id, "videoId": video_id, "maxResults": 1}
    page = check(ctx.http.get(f"{API}/playlistItems", params=params, headers=auth), "YouTube playlistItems.list").json()
    return bool(page.get("items"))


def add_to_playlist(ctx: Context, playlist_id: str, video_id: str, auth: dict) -> str:
    """Append the video to the playlist (one playlistItems.insert, 50 units); returns the playlist item id."""
    body = {"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": video_id}}}
    resp = check(ctx.http.post(f"{API}/playlistItems", params={"part": "snippet"},
                               headers={**auth, "Content-Type": "application/json; charset=UTF-8"},
                               data=json.dumps(body)), "YouTube playlistItems.insert")
    return resp.json().get("id", "")


def publish(ctx: Context, post: Post) -> dict:
    video, srt = post.folder / "short.mp4", post.folder / "short.srt"
    if not video.exists():
        raise PublishError("short.mp4 is missing")
    body = metadata(ctx, post)
    auth = {"Authorization": f"Bearer {access_token(ctx)}"}
    video_id = upload_video(ctx, video, body, auth)
    result = {"id": video_id, "url": f"https://www.youtube.com/shorts/{video_id}",
              "scheduled_for": body["status"]["publishAt"], "captions": False}
    if srt.exists():
        try:
            insert_captions(ctx, video_id, srt, "en", "English", auth)
            result["captions"] = True
        except Exception as exc:  # noqa: BLE001 - the video is uploaded; captions can be added in Studio
            ctx.say(f"  youtube: video uploaded, captions were refused ({str(exc)[:120]}); upload short.srt in Studio")
    return result


def describe(ctx: Context, post: Post) -> str:
    body = metadata(ctx, post)
    return f"upload short.mp4 as private, public at {body['status']['publishAt']}, title {body['snippet']['title']!r}, + short.srt"
