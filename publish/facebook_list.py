"""List the newest Facebook Page posts with their permalinks, for recording manual posts.

    python -m publish.facebook_list [--limit 10]

Reads FB_PAGE_ID and FB_PAGE_TOKEN from the environment (GitHub Secrets in the
`facebook-list` workflow) and prints one line per post: created time, post id, permalink and the first
words of the text. It never prints the token and never writes anything. Record a post with
`python -m publish.record_manual record --channel facebook --url <permalink> --id <post id> ...`.
"""
from __future__ import annotations

import argparse
import os
import sys

import requests

from publish.common import ROOT, load_config


def list_posts(page: str, token: str, version: str, limit: int, http=requests) -> list[dict]:
    resp = http.get(f"https://graph.facebook.com/{version}/{page}/posts",
                    params={"fields": "id,created_time,permalink_url,message", "limit": limit, "access_token": token},
                    timeout=30)
    if resp.status_code != 200:
        body = (resp.text or "")[:300].replace(token, "***")
        raise SystemExit(f"Facebook answered HTTP {resp.status_code}: {body}")
    return resp.json().get("data", [])


def line(post: dict) -> str:
    text = " ".join((post.get("message") or "").split())[:60]
    return f"{post.get('created_time', '?')}  {post.get('id', '?')}  {post.get('permalink_url', '?')}  {text}"


def main(argv: list[str] | None = None, env=os.environ, http=requests) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args(argv)
    page, token = env.get("FB_PAGE_ID", "").strip(), env.get("FB_PAGE_TOKEN", "").strip()
    if not page or not token:
        print("FB_PAGE_ID or FB_PAGE_TOKEN is not set", file=sys.stderr)
        return 1
    version = load_config(ROOT)["facebook_graph_version"]
    for post in list_posts(page, token, version, args.limit, http=http):
        print(line(post))
    return 0


if __name__ == "__main__":
    sys.exit(main())
