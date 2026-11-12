"""Telegram channel: the image with a caption and the blog link.

Official docs (checked 12 Nov 2026): https://core.telegram.org/bots/api#sendphoto
sendPhoto, multipart upload (at most 10 MB), caption "0-1024 characters after entities parsing".
The bot must be an administrator of the channel. No parse mode is used, so nothing needs escaping.
"""
from __future__ import annotations

from .common import Context, Post, PublishError, check

NEEDS = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHANNEL"]
CAPTION_LIMIT = 1024


def caption(ctx: Context, post: Post) -> str:
    text = f"{post.text('telegram')}\n\n{post.url(ctx.cfg)}"
    if len(text) > CAPTION_LIMIT:
        raise PublishError(f"caption with link is {len(text)} characters, limit {CAPTION_LIMIT}")
    return text


def publish(ctx: Context, post: Post) -> dict:
    token, channel = ctx.secret("TELEGRAM_BOT_TOKEN"), ctx.secret("TELEGRAM_CHANNEL")
    chat = channel if channel.startswith(("@", "-")) else f"@{channel}"
    text = caption(ctx, post)
    try:
        resp = ctx.http.post(f"https://api.telegram.org/bot{token}/sendPhoto", data={"chat_id": chat, "caption": text},
                             files={"photo": ("image.png", post.image.read_bytes(), "image/png")})
    except Exception as exc:  # noqa: BLE001 - the URL holds the token: never let it reach a log
        raise PublishError(f"Telegram sendPhoto failed: {type(exc).__name__}") from None
    msg = check(resp, "Telegram sendPhoto").json()["result"]
    username = msg.get("chat", {}).get("username") or chat.lstrip("@")
    return {"id": msg["message_id"], "url": f"https://t.me/{username}/{msg['message_id']}"}


def describe(ctx: Context, post: Post) -> str:
    return f"send image.png with a {len(caption(ctx, post))}-character caption"
