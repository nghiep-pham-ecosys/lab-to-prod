"""X: manual. No API call is made (the X API is pay-per-use).

export() writes x.md next to each post and one schedule sheet per week, so the author can
schedule the five posts on x.com in a few minutes on Sunday.
"""
from __future__ import annotations

from pathlib import Path

from .common import Context, Post

NEEDS: list[str] = []


def export(ctx: Context, posts: list[Post], week_dir: Path) -> list[Path]:
    written, rows = [], []
    for post in posts:
        text = post.text("x_manual")
        if not text:
            continue
        when = ctx.post_time(post.date)
        out = post.folder / "x.md"
        out.write_text(
            f"<!-- X post for {post.date}. Schedule on x.com for {when:%a %d %b %H:%M} (UTC{ctx.cfg['timezone_offset']}).\n"
            f"     Attach: image.png   Alt text: {post.meta.get('image_alt', '')}\n"
            f"     First reply after it is live: {post.url(ctx.cfg)}\n-->\n\n{text}\n", encoding="utf-8")
        written.append(out)
        rows.append(f"## {when:%a %d %b, %H:%M}\n\nImage: `{post.folder.name}/image.png`  \nAlt text: {post.meta.get('image_alt', '')}  \n"
                    f"First reply: {post.url(ctx.cfg)}\n\n```text\n{text}\n```\n")
    if rows:
        sheet = week_dir / "x-schedule.md"
        sheet.write_text(f"# X posts to schedule by hand: {week_dir.name}\n\nOn x.com: compose, attach the image, add the alt text, "
                         f"choose Schedule. After each post goes live, reply with its blog link.\n\n" + "\n".join(rows), encoding="utf-8")
        written.append(sheet)
    return written
