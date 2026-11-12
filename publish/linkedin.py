"""LinkedIn: a member post with one image, then the blog link as the first comment.

Official docs (checked 12 Nov 2026):
  Share on LinkedIn (self-serve product, scope w_member_social)
  https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin
Flow: POST /v2/assets?action=registerUpload -> upload the binary to uploadUrl -> POST /v2/ugcPosts.
The post id comes back in the X-RestLi-Id header. Tokens last 60 days and cannot be refreshed
with this product, so the author signs in again when the expiry warning fires.

The first comment is best effort: the comments documentation lists a different scope than the
self-serve one, so a refusal is recorded (comment: false) and the author adds the link by hand.
"""
from __future__ import annotations

from urllib.parse import quote

from .common import Context, Post, check

API = "https://api.linkedin.com/v2"
NEEDS = ["LINKEDIN_ACCESS_TOKEN", "LINKEDIN_PERSON_URN"]


def publish(ctx: Context, post: Post) -> dict:
    token, author = ctx.secret("LINKEDIN_ACCESS_TOKEN"), ctx.secret("LINKEDIN_PERSON_URN")
    if not author.startswith("urn:li:person:"):
        author = f"urn:li:person:{author}"
    headers = {"Authorization": f"Bearer {token}", "X-Restli-Protocol-Version": "2.0.0"}

    reg = check(ctx.http.post(f"{API}/assets?action=registerUpload", headers=headers, json={
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": author,
            "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}],
        }}), "LinkedIn registerUpload").json()["value"]
    upload_url = reg["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    check(ctx.http.put(upload_url, headers={"Authorization": f"Bearer {token}"}, data=post.image.read_bytes()),
          "LinkedIn image upload")

    created = check(ctx.http.post(f"{API}/ugcPosts", headers=headers, json={
        "author": author,
        "lifecycleState": "PUBLISHED",
        "specificContent": {"com.linkedin.ugc.ShareContent": {
            "shareCommentary": {"text": post.text("linkedin")},
            "shareMediaCategory": "IMAGE",
            "media": [{"status": "READY", "media": reg["asset"],
                       "description": {"text": str(post.meta.get("image_alt", ""))[:200]},
                       "title": {"text": str(post.meta["title"])[:200]}}],
        }},
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }), "LinkedIn post")
    urn = created.headers.get("X-RestLi-Id") or created.json().get("id")
    result = {"id": urn, "url": f"https://www.linkedin.com/feed/update/{urn}/", "comment": False}

    try:
        check(ctx.http.post(f"{API}/socialActions/{quote(urn, safe='')}/comments", headers=headers, json={
            "actor": author, "object": urn, "message": {"text": f"Full note with code: {post.url(ctx.cfg)}"},
        }), "LinkedIn first comment")
        result["comment"] = True
    except Exception as exc:  # noqa: BLE001 - the post itself is live; never fail the channel for the comment
        ctx.say(f"  linkedin: post is live, first comment was refused ({str(exc)[:120]}); add the blog link by hand")
    return result


def describe(ctx: Context, post: Post) -> str:
    return f"post now, {len(post.text('linkedin'))} characters + image.png, then first comment with {post.url(ctx.cfg)}"
