"""Facebook Page: a photo post, scheduled by Facebook itself for the post's day.

Official docs (checked 12 Nov 2026):
  https://developers.facebook.com/docs/pages-api/posts
  https://developers.facebook.com/docs/graph-api/reference/page/photos/
POST /{page-id}/photos with published=false and scheduled_publish_time (UNIX seconds).
"The publish date must be between 10 minutes and 30 days from the time of the API request."
PNG uploads are capped at 1 MB, so the image is sent as JPEG.
Needs a Page access token with pages_manage_posts, pages_read_engagement, pages_show_list.
"""
from __future__ import annotations

import datetime as dt

from .common import Context, Post, Skip, check, jpeg_bytes

NEEDS = ["FB_PAGE_ID", "FB_PAGE_TOKEN"]
MIN_LEAD = dt.timedelta(minutes=12)   # the API wants at least 10 minutes
MAX_LEAD = dt.timedelta(days=29)      # and at most 30 days


def plan(ctx: Context, post: Post) -> dt.datetime | None:
    """When to schedule for; None means publish immediately (the slot is today and too close)."""
    when = ctx.post_time(post.date)
    if when - ctx.now > MAX_LEAD:
        raise Skip(f"{post.date} is more than 29 days ahead; it will be scheduled by a later run")
    if when - ctx.now >= MIN_LEAD:
        return when
    if post.date == ctx.now.astimezone(ctx.tz).date():
        return None
    raise Skip(f"{post.date} is in the past; not back-posting")


def publish(ctx: Context, post: Post) -> dict:
    page, token = ctx.secret("FB_PAGE_ID"), ctx.secret("FB_PAGE_TOKEN")
    when = plan(ctx, post)
    data = {"caption": f"{post.text('facebook')}\n\n{post.url(ctx.cfg)}", "access_token": token}
    if when is not None:
        data.update(published="false", scheduled_publish_time=str(int(when.timestamp())))
    resp = check(ctx.http.post(
        f"https://graph.facebook.com/{ctx.cfg['facebook_graph_version']}/{page}/photos",
        data=data, files={"source": ("image.jpg", jpeg_bytes(post.image), "image/jpeg")}), "Facebook photo").json()
    post_id = resp.get("post_id") or resp["id"]
    return {"id": post_id, "photo_id": resp.get("id"), "url": f"https://www.facebook.com/{post_id}",
            "scheduled_for": when.isoformat() if when else None}


def describe(ctx: Context, post: Post) -> str:
    when = plan(ctx, post)
    return f"{'schedule for ' + when.isoformat() if when else 'publish now'}, image + caption with {post.url(ctx.cfg)}"
