#!/usr/bin/env python3
"""Telegram and DEV: check the keys you paste, then store them in GitHub Secrets.

    python3 scripts/tokens/simple_secrets.py telegram
    python3 scripts/tokens/simple_secrets.py devto

What you paste is hidden while typing and is never printed back.
"""
import sys

from _common import DEFAULT_REPO, TokenError, ask, http_json, main_guard, store_secret


def telegram(repo: str = DEFAULT_REPO, ask=ask, http_json=http_json, store=store_secret) -> None:
    token = ask("Telegram bot token from @BotFather (hidden)", secret=True)
    channel = ask("Channel username, for example @labtoprod_nghiep")
    channel = channel if channel.startswith(("@", "-")) else f"@{channel}"
    api = f"https://api.telegram.org/bot{token}"
    try:
        bot = http_json(f"{api}/getMe")["result"]
        admins = http_json(f"{api}/getChatAdministrators", {"chat_id": channel})["result"]
    except TokenError as exc:
        # the request address holds the token: report only the status part
        raise TokenError("Telegram refused: " + str(exc).split(" answered ")[-1]) from None
    mine = [a for a in admins if a["user"]["id"] == bot["id"]]
    if not mine:
        raise TokenError(f"@{bot['username']} is not an administrator of {channel}; add it in the channel settings")
    if mine[0].get("can_post_messages") is False:
        raise TokenError(f"@{bot['username']} is an administrator but may not post; enable 'Post messages'")
    store("TELEGRAM_BOT_TOKEN", token, repo)
    store("TELEGRAM_CHANNEL", channel, repo)
    print(f"Done. Bot @{bot['username']} can post to {channel}.")


def devto(repo: str = DEFAULT_REPO, ask=ask, http_json=http_json, store=store_secret) -> None:
    key = ask("DEV API key (hidden)", secret=True)
    me = http_json("https://dev.to/api/users/me", headers={"api-key": key, "Accept": "application/vnd.forem.api-v1+json"})
    store("DEVTO_API_KEY", key, repo)
    print(f"Done. DEV account: {me.get('username', 'unknown')}.")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else ""
    if which not in ("telegram", "devto"):
        sys.exit("usage: simple_secrets.py telegram | devto")
    main_guard({"telegram": telegram, "devto": devto}[which])
