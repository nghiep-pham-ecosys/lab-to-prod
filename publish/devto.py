"""DEV (dev.to): republish the Saturday article with canonical_url pointing at the blog.

Official docs (checked 12 Nov 2026): https://developers.forem.com/api/v1
POST https://dev.to/api/articles, header "api-key", body {"article": {...}}; tags is a
comma-separated string of at most 4 tags. GET /api/articles/me/all lists own articles with
canonical_url, which is used to avoid a duplicate if published.json was lost.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from .common import Article, Context, check

NEEDS = ["DEVTO_API_KEY"]
API = "https://dev.to/api"


def payload(ctx: Context, art: Article) -> dict:
    site = ctx.cfg["site_url"]
    parts = urlparse(site)
    origin, base = f"{parts.scheme}://{parts.netloc}", parts.path.rstrip("/")
    body = art.body
    if base:  # make site-relative links absolute
        body = body.replace(f"]({base}/", f"]({origin}{base}/")
    tags = [re.sub(r"[^a-z0-9]", "", str(t).lower()) for t in art.meta.get("tags", [])]
    footer = f"\n\n---\n\n*Originally published on [Lab to Prod]({art.url(ctx.cfg)}).*"
    return {"article": {
        "title": art.meta["title"], "body_markdown": body + footer, "published": True,
        "canonical_url": art.url(ctx.cfg), "description": art.meta.get("description", ""),
        "tags": ",".join([t for t in tags if t][:4]),
        "main_image": f"{site}/og/posts/{art.path.stem}.png",
    }}


def publish(ctx: Context, art: Article) -> dict:
    headers = {"api-key": ctx.secret("DEVTO_API_KEY"), "Accept": "application/vnd.forem.api-v1+json"}
    mine = check(ctx.http.get(f"{API}/articles/me/all?per_page=200", headers=headers), "DEV list articles").json()
    for existing in mine:
        if existing.get("canonical_url") == art.url(ctx.cfg):
            return {"id": existing["id"], "url": existing["url"], "found_existing": True}
    created = check(ctx.http.post(f"{API}/articles", headers=headers, json=payload(ctx, art)), "DEV create article").json()
    return {"id": created["id"], "url": created["url"]}


def describe(ctx: Context, art: Article) -> str:
    p = payload(ctx, art)["article"]
    return f"publish {p['title']!r}, tags {p['tags']}, canonical {p['canonical_url']}"
