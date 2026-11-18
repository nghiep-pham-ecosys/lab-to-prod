"""LinkedIn: a member post with one image or one PDF document, then the blog link as the first comment.

Two paths. The post folder decides which one runs:

* Image (default): no `linkedin.pdf` in the folder. Unchanged since 12 Nov 2026.
  Share on LinkedIn (self-serve product, scope w_member_social), checked 12 Nov 2026:
  https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin
  Flow: POST /v2/assets?action=registerUpload -> upload the binary to uploadUrl -> POST /v2/ugcPosts.
* Document: the folder has `linkedin.pdf` (format: docs/post-format.md). Checked 18 Nov 2026:
  Documents API https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/documents-api
  Posts API     https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api
  Flow: POST /rest/documents?action=initializeUpload (owner = person URN) -> PUT the bytes to uploadUrl
  -> POST /rest/posts with content.media.id = the document URN. PDF at most 100 MB and 300 pages.
  Both rest calls need LinkedIn-Version (LINKEDIN_VERSION below) and X-Restli-Protocol-Version 2.0.0.
  NOT VERIFIED LIVE: the docs allow a person as document owner ("the caller must match the document
  owner") but have no official example of a person-authored document post. If LinkedIn refuses it,
  remove linkedin.pdf and the image path runs again. This is a document post, not a carousel:
  organic carousels are not supported by the API.

Both paths: the post id comes back in the X-RestLi-Id header. Tokens last 60 days and cannot be
refreshed with this product, so the author signs in again when the expiry warning fires.

The first comment is best effort: the comments documentation lists a different scope than the
self-serve one, so a refusal is recorded (comment: false) and the author adds the link by hand.
"""
from __future__ import annotations

from urllib.parse import quote

from .common import Context, Post, PublishError, check

API = "https://api.linkedin.com/v2"
REST = "https://api.linkedin.com/rest"
LINKEDIN_VERSION = "202610"           # YYYYMM; the one place to bump the rest API version
DOCUMENT = "linkedin.pdf"             # present in a post folder -> document post instead of image post
DOCUMENT_MAX_BYTES = 100 * 1024 * 1024
NEEDS = ["LINKEDIN_ACCESS_TOKEN", "LINKEDIN_PERSON_URN"]


def document(post: Post):
    """The PDF for a document post, or None for the default image post."""
    path = post.folder / DOCUMENT
    return path if path.is_file() else None


def _author(ctx: Context) -> str:
    author = ctx.secret("LINKEDIN_PERSON_URN")
    return author if author.startswith("urn:li:person:") else f"urn:li:person:{author}"


def _image_post(ctx: Context, post: Post, token: str, author: str, headers: dict) -> str:
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
    return created.headers.get("X-RestLi-Id") or created.json().get("id")


def _document_post(ctx: Context, post: Post, pdf, token: str, author: str) -> str:
    data = pdf.read_bytes()
    if len(data) > DOCUMENT_MAX_BYTES:
        raise PublishError(f"{DOCUMENT} is {len(data)} bytes, LinkedIn limit {DOCUMENT_MAX_BYTES}")
    headers = {"Authorization": f"Bearer {token}", "X-Restli-Protocol-Version": "2.0.0",
               "LinkedIn-Version": LINKEDIN_VERSION}

    init = check(ctx.http.post(f"{REST}/documents?action=initializeUpload", headers=headers, json={
        "initializeUploadRequest": {"owner": author}}), "LinkedIn document initializeUpload").json()["value"]
    check(ctx.http.put(init["uploadUrl"], headers={"Authorization": f"Bearer {token}"}, data=data),
          "LinkedIn document upload")

    created = check(ctx.http.post(f"{REST}/posts", headers=headers, json={
        "author": author,
        "commentary": post.text("linkedin"),
        "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
        "content": {"media": {"title": str(post.meta.get("document_title") or post.meta["title"])[:200],
                              "id": init["document"]}},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }), "LinkedIn post")
    return created.headers.get("x-restli-id") or created.headers.get("X-RestLi-Id") or created.json().get("id")


def publish(ctx: Context, post: Post) -> dict:
    token, author = ctx.secret("LINKEDIN_ACCESS_TOKEN"), _author(ctx)
    headers = {"Authorization": f"Bearer {token}", "X-Restli-Protocol-Version": "2.0.0"}
    pdf = document(post)
    if pdf:
        urn = _document_post(ctx, post, pdf, token, author)
    else:
        urn = _image_post(ctx, post, token, author, headers)
    if not urn:
        raise PublishError("LinkedIn post: no post id in the response")
    result = {"id": urn, "url": f"https://www.linkedin.com/feed/update/{urn}/", "comment": False}
    if pdf:
        result["media"] = "document"

    try:
        check(ctx.http.post(f"{API}/socialActions/{quote(urn, safe='')}/comments", headers=headers, json={
            "actor": author, "object": urn, "message": {"text": f"Full note with code: {post.url(ctx.cfg)}"},
        }), "LinkedIn first comment")
        result["comment"] = True
    except Exception as exc:  # noqa: BLE001 - the post itself is live; never fail the channel for the comment
        ctx.say(f"  linkedin: post is live, first comment was refused ({str(exc)[:120]}); add the blog link by hand")
    return result


def describe(ctx: Context, post: Post) -> str:
    pdf = document(post)
    media = (f"{DOCUMENT} as a document post (rest/documents + rest/posts, LinkedIn-Version {LINKEDIN_VERSION})"
             if pdf else "image.png (v2/ugcPosts)")
    return f"post now, {len(post.text('linkedin'))} characters + {media}, then first comment with {post.url(ctx.cfg)}"
