"""Hashnode: manual. No API call is made.

Hashnode retired free API access on 13 May 2026: "Every API request, queries and mutations,
now requires a Pro plan on your publication." (https://hashnode.com/announcements/graphql-api)
This project uses no paid API, so the article is written to a file that the author pastes
into the Hashnode editor, the same way X posts are handled. If that ever changes, replace
export() with an API publisher and set `hashnode: api` in config.yaml.
"""
from __future__ import annotations

from pathlib import Path

from .common import Article, Context

NEEDS: list[str] = []


def export(ctx: Context, art: Article, out_dir: Path) -> Path:
    out = out_dir / f"hashnode-{art.path.stem}.md"
    tags = ", ".join(str(t) for t in art.meta.get("tags", [])[:5])
    out.write_text(
        f"<!-- Paste into the Hashnode editor (hashnode.com/draft). Not committed to a schedule.\n"
        f"     Title:            {art.meta['title']}\n"
        f"     Subtitle:         {art.meta.get('description', '')}\n"
        f"     Tags:             {tags}\n"
        f"     Cover image:      {ctx.cfg['site_url']}/og/posts/{art.path.stem}.png\n"
        f"     Article settings: \"Are you republishing?\" -> original URL = {art.url(ctx.cfg)}\n"
        f"-->\n\n{art.body}\n\n---\n\n*Originally published on [Lab to Prod]({art.url(ctx.cfg)}).*\n",
        encoding="utf-8")
    return out
