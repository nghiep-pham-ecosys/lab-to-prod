"""List unanswered YouTube and Facebook Page comments, and post replies the author approved.

    python -m publish.comments list [--days 7] [--post-days 60] [--channel youtube] [--out FILE] [--summary FILE]
    python -m publish.comments reply --file replies.json [--live] [--out FILE] [--summary FILE]

`list` reads the posts from published.json (the `youtube` and `facebook` entries with an id), asks each platform for
the top-level comments of the last `--days` days, drops those already answered by our own channel or Page, and
prints a JSON list: {channel, post_key, post_url, comment_id, author, text, at}. It never posts.

`reply` reads a JSON list of {channel, comment_id, text}. For every item it first checks that our channel or Page has
not answered that comment yet (so a second run never posts twice), then posts the reply. Without `--live` it only
prints the plan and calls nothing. A `PAUSE` file at the repository root stops it before any call. The author approves
each reply text; nothing here writes a reply by itself (CLAUDE.md rule 6).

Secrets: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN (YouTube) and FB_PAGE_ID, FB_PAGE_TOKEN (Facebook). A
channel whose secrets are missing is skipped with a warning. Errors print the platform's message, never a token.

YouTube Data API v3 (docs checked 27 Nov 2026):
  https://developers.google.com/youtube/v3/docs/commentThreads/list
  https://developers.google.com/youtube/v3/docs/commentThreads
  https://developers.google.com/youtube/v3/docs/comments
  https://developers.google.com/youtube/v3/docs/comments/list
  https://developers.google.com/youtube/v3/docs/comments/insert
  https://developers.google.com/youtube/v3/docs/channels/list
- commentThreads.list (1 unit): part `snippet,replies`, filter `videoId`, maxResults 1-100, `order=time` (the
  default), `textFormat=plainText`, `pageToken`/`nextPageToken`.
- `replies.comments` "contains a limited number of replies": when it is shorter than `snippet.totalReplyCount`,
  comments.list with `parentId` (1 unit a page, maxResults 1-100) gives them all.
- Comment fields used: `id`, `snippet.authorDisplayName`, `snippet.authorChannelId.value`, `snippet.textDisplay`
  (`textOriginal` is returned only to the comment's author), `snippet.publishedAt`.
- comments.insert (50 units) "creates a reply to an existing comment": part `snippet`, body `snippet.parentId` and
  `snippet.textOriginal`, scope `youtube.force-ssl` (already in scripts/tokens/youtube_token.py). "YouTube currently
  supports replies only for top-level comments", so only top-level comments are listed.
- channels.list with `mine=true` and `part=id` (1 unit) gives our own channel id.
- The two list pages have no Authorization section; the OAuth token the publisher already uses is sent.

Facebook Graph API (docs checked 27 Nov 2026, version from publish/config.yaml):
  https://developers.facebook.com/docs/graph-api/reference/object/comments/
  https://developers.facebook.com/docs/graph-api/reference/comment/
  https://developers.facebook.com/docs/pages-api/comments-mentions/
  https://developers.facebook.com/docs/permissions/reference/pages_manage_engagement
  https://developers.facebook.com/docs/permissions/reference/pages_read_engagement
- GET /{object-id}/comments: `filter=stream` returns comments of every level in chronological order (`toplevel`, the
  default, only the first level). The Pages guide reads `fields=from,message` and shows `id`, `from {name, id}`,
  `message` and `created_time` (like 2020-02-19T23:05:53+0000) in each item, with `paging.cursors`. The Comment node
  page lists `parent` ("for comment replies, the comment this is a reply to") and the `comments` edge, but its field
  table does not list `from`, `message` or `created_time`; those three come from the Pages guide only.
- "The `id` field of /PAGEPOST-ID/comments is no longer returned unless the caller can perform MODERATE on the Page"
  (the edge page). A comment without an id cannot be answered; `list` counts and reports it.
- POST /{object-id}/comments with `message` returns `{"id": ...}`. Comments have their own comments edge ("replies
  to comments"), so a reply is POST /{comment-id}/comments. It needs a Page token of someone with the MODERATE task
  and `pages_manage_engagement` ("create, edit and delete comments posted on the Page"; it depends on
  `pages_read_user_content` and `pages_show_list`). The Pages guide lists `pages_manage_engagement`,
  `pages_read_engagement` and `pages_read_user_engagement` for comments. Until the author renews FB_PAGE_TOKEN with
  `pages_manage_engagement` (scripts/tokens/facebook_token.py), Facebook refuses the reply and this tool says so.
- Ids in published.json: the API publisher keeps the photo id (POST /{page}/photos), a manual record keeps the
  number from the post link. A manual id without "_" is read as {page-id}_{id}. Not yet checked against a live Page.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import requests

from .common import ROOT, Context, PublishError, State, is_followup_key, load_config, paused
from .youtube import API as YT_API, access_token

CHANNELS = ("youtube", "facebook")
NEEDS = {"youtube": ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"), "facebook": ("FB_PAGE_ID", "FB_PAGE_TOKEN")}
MAX_PAGES = 20            # 100 comments a page: 2,000 comments a post before the tool gives up
YT_LIST_UNITS = 1         # commentThreads.list, comments.list, channels.list
YT_INSERT_UNITS = 50      # comments.insert
FB_FIELDS = "id,from,message,created_time,parent,comments{from}"


class ScopeRefused(PublishError):
    """The token cannot write comments. The author must renew it; the run stops for that channel."""


def _when(raw: str) -> dt.datetime:
    return dt.datetime.fromisoformat(raw).astimezone(dt.timezone.utc)


def _iso(when: dt.datetime) -> str:
    return when.astimezone(dt.timezone.utc).isoformat(timespec="seconds")


def _fail(resp, what: str, secret: str = "") -> PublishError:
    body = (resp.text or "")[:300].replace("\n", " ")
    if secret:
        body = body.replace(secret, "***")
    return PublishError(f"{what} failed: HTTP {resp.status_code} {body}")


def targets(state: dict, channel: str, now: dt.datetime, post_days: int) -> list[tuple[str, dict]]:
    """(post key, published.json entry) for every post of the channel that is public and not older than post_days."""
    out = []
    for key, channels in sorted(state.items()):
        if is_followup_key(key):  # our own follow-up comment, not a post
            continue
        entry = channels.get(channel) or {}
        if not entry.get("id"):
            continue
        public = _when(entry.get("scheduled_for") or entry.get("at") or _iso(now))
        if public > now or public < now - dt.timedelta(days=post_days):
            continue
        out.append((key, entry))
    return out


class YouTube:
    def __init__(self, ctx: Context):
        self.ctx, self.http = ctx, ctx.http
        self.auth = {"Authorization": f"Bearer {access_token(ctx)}"}
        self.units = 0
        self._me: str | None = None

    def _get(self, path: str, params: dict, what: str) -> dict:
        self.units += YT_LIST_UNITS
        resp = self.http.get(f"{YT_API}/{path}", params=params, headers=self.auth)
        if resp.status_code != 200:
            raise _fail(resp, what)
        return resp.json()

    def me(self) -> str:
        if self._me is None:
            items = self._get("channels", {"part": "id", "mine": "true"}, "YouTube channels.list").get("items") or []
            if not items:
                raise PublishError("YouTube channels.list returned no channel for this token")
            self._me = items[0]["id"]
        return self._me

    def threads(self, video_id: str, since: dt.datetime):
        """Top-level comment threads of the video, newest first, until one is older than `since`."""
        token = None
        for _ in range(MAX_PAGES):
            params = {"part": "snippet,replies", "videoId": video_id, "maxResults": 100, "order": "time",
                      "textFormat": "plainText"}
            if token:
                params["pageToken"] = token
            page = self._get("commentThreads", params, "YouTube commentThreads.list")
            for item in page.get("items") or []:
                top = item["snippet"]["topLevelComment"]
                if _when(top["snippet"]["publishedAt"]) < since:
                    return
                yield item
            token = page.get("nextPageToken")
            if not token:
                return
        raise PublishError(f"commentThreads.list gave more than {MAX_PAGES} pages for {video_id}; refusing to guess")

    def replies(self, parent_id: str) -> list[dict]:
        out, token = [], None
        for _ in range(MAX_PAGES):
            params = {"part": "snippet", "parentId": parent_id, "maxResults": 100, "textFormat": "plainText"}
            if token:
                params["pageToken"] = token
            page = self._get("comments", params, "YouTube comments.list")
            out.extend(page.get("items") or [])
            token = page.get("nextPageToken")
            if not token:
                return out
        raise PublishError(f"comments.list gave more than {MAX_PAGES} pages for {parent_id}; refusing to guess")

    def _author(self, comment: dict) -> str:
        return ((comment.get("snippet") or {}).get("authorChannelId") or {}).get("value", "")

    def answered(self, thread: dict) -> bool:
        top = thread["snippet"]["topLevelComment"]
        shown = (thread.get("replies") or {}).get("comments") or []
        total = thread["snippet"].get("totalReplyCount", len(shown))
        replies = shown if len(shown) >= total else self.replies(top["id"])
        return any(self._author(r) == self.me() for r in replies)

    def unanswered(self, key: str, entry: dict, since: dt.datetime) -> list[dict]:
        out = []
        for thread in self.threads(entry["id"], since):
            top = thread["snippet"]["topLevelComment"]
            if self._author(top) == self.me() or self.answered(thread):
                continue
            snip = top["snippet"]
            out.append({"channel": "youtube", "post_key": key, "post_url": entry.get("url", ""), "comment_id": top["id"],
                        "author": snip.get("authorDisplayName", ""), "text": snip.get("textDisplay", ""),
                        "at": _iso(_when(snip["publishedAt"]))})
        return out

    def already_replied(self, comment_id: str) -> bool:
        return any(self._author(r) == self.me() for r in self.replies(comment_id))

    def reply(self, comment_id: str, text: str) -> str:
        self.units += YT_INSERT_UNITS
        body = {"snippet": {"parentId": comment_id, "textOriginal": text}}
        resp = self.http.post(f"{YT_API}/comments", params={"part": "snippet"},
                              headers={**self.auth, "Content-Type": "application/json; charset=UTF-8"}, data=json.dumps(body))
        if resp.status_code == 403 and "insufficientPermissions" in (resp.text or ""):
            raise ScopeRefused("YouTube refused the reply: the token lacks the youtube.force-ssl scope; "
                               "renew it with scripts/tokens/youtube_token.py (docs/setup.md, section 5)")
        if resp.status_code not in (200, 201):
            raise _fail(resp, "YouTube comments.insert")
        return resp.json().get("id", "")


class Facebook:
    def __init__(self, ctx: Context):
        self.http = ctx.http
        self.page, self.token = ctx.secret("FB_PAGE_ID"), ctx.secret("FB_PAGE_TOKEN")
        self.base = f"https://graph.facebook.com/{ctx.cfg['facebook_graph_version']}"

    def object_id(self, entry: dict) -> str:
        raw = str(entry["id"])
        if "_" not in raw and entry.get("manual"):
            return f"{self.page}_{raw}"
        return raw

    def _get(self, path: str, params: dict, what: str) -> dict:
        try:
            resp = self.http.get(f"{self.base}/{path}", params={**params, "access_token": self.token}, timeout=30)
        except Exception as exc:  # a network error's message can hold the full URL, token included
            raise PublishError(f"{what} failed: {type(exc).__name__}: {str(exc).replace(self.token, '***')}") from None
        if resp.status_code != 200:
            raise _fail(resp, what, self.token)
        return resp.json()

    def comments(self, object_id: str) -> list[dict]:
        out, after = [], None
        for _ in range(MAX_PAGES):
            params = {"filter": "stream", "fields": FB_FIELDS, "limit": 100}
            if after:
                params["after"] = after
            page = self._get(f"{object_id}/comments", params, "Facebook comments")
            out.extend(page.get("data") or [])
            paging = page.get("paging") or {}
            after = (paging.get("cursors") or {}).get("after")
            if not paging.get("next") or not after:
                return out
        raise PublishError(f"Facebook comments gave more than {MAX_PAGES} pages for {object_id}; refusing to guess")

    def _ours(self, comment: dict) -> bool:
        return str((comment.get("from") or {}).get("id", "")) == self.page

    def unanswered(self, key: str, entry: dict, since: dt.datetime, notes: list) -> list[dict]:
        everything = self.comments(self.object_id(entry))
        answered = {str((c.get("parent") or {}).get("id")) for c in everything if self._ours(c) and c.get("parent")}
        out, hidden = [], 0
        for c in everything:
            if c.get("parent") or self._ours(c) or _when(c["created_time"]) < since:
                continue
            nested = (c.get("comments") or {}).get("data") or []
            if str(c.get("id")) in answered or any(self._ours(r) for r in nested):
                continue
            if not c.get("id"):
                hidden += 1
                continue
            out.append({"channel": "facebook", "post_key": key, "post_url": entry.get("url", ""), "comment_id": c["id"],
                        "author": (c.get("from") or {}).get("name", ""), "text": c.get("message", ""),
                        "at": _iso(_when(c["created_time"]))})
        if hidden:
            notes.append(f"facebook {key}: {hidden} comment(s) came without an id (the token lacks the MODERATE task)")
        return out

    def already_replied(self, comment_id: str) -> bool:
        page = self._get(f"{comment_id}/comments", {"filter": "stream", "fields": "from", "limit": 100}, "Facebook replies")
        return any(self._ours(c) for c in page.get("data") or [])

    def reply(self, comment_id: str, text: str) -> str:
        resp = self.http.post(f"{self.base}/{comment_id}/comments", data={"message": text, "access_token": self.token},
                              timeout=30)
        if resp.status_code != 200:
            try:
                error = resp.json().get("error") or {}
            except ValueError:
                error = {}
            if error.get("code") in (10, 200) or resp.status_code == 403 or "permission" in str(error.get("message", "")).lower():
                raise ScopeRefused("Facebook refused the reply: the Page token lacks pages_manage_engagement; renew it "
                                   "with scripts/tokens/facebook_token.py (docs/setup.md, section 4, steps 3 and 6)")
            raise _fail(resp, "Facebook reply", self.token)
        return resp.json().get("id", "")


CLIENTS = {"youtube": YouTube, "facebook": Facebook}


def _client(ctx: Context, channel: str, notes: list):
    missing = [n for n in NEEDS[channel] if not ctx.env.get(n, "").strip()]
    if missing:
        notes.append(f"{channel}: skipped, secrets not set: {', '.join(missing)}")
        return None
    try:
        return CLIENTS[channel](ctx)
    except PublishError as exc:
        notes.append(f"{channel}: {exc}")
        return None


def list_comments(ctx: Context, state: dict, days: int, post_days: int, channels=CHANNELS) -> tuple[list[dict], list[str], bool]:
    """Returns (unanswered comments, notes, ok). ok is False when a channel or a post could not be read."""
    since = ctx.now - dt.timedelta(days=days)
    found, notes, ok = [], [], True
    for channel in channels:
        posts = targets(state, channel, ctx.now, post_days)
        if not posts:
            notes.append(f"{channel}: no post in published.json within {post_days} days")
            continue
        client = _client(ctx, channel, notes)
        if client is None:
            ok = False
            continue
        for key, entry in posts:
            try:
                if channel == "facebook":
                    found.extend(client.unanswered(key, entry, since, notes))
                else:
                    found.extend(client.unanswered(key, entry, since))
            except PublishError as exc:
                ok = False
                notes.append(f"{channel} {key}: {exc}")
        if channel == "youtube":
            notes.append(f"youtube: {client.units} quota units used")
    found.sort(key=lambda c: c["at"], reverse=True)
    return found, notes, ok


def load_replies(path: Path) -> list[dict]:
    """Read and check the replies file before anything is called."""
    try:
        items = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PublishError(f"replies file {path} is not valid JSON: {exc}") from exc
    if not isinstance(items, list):
        raise PublishError("replies must be a JSON list of {channel, comment_id, text}")
    for i, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise PublishError(f"reply {i} is not an object")
        if item.get("channel") not in CHANNELS:
            raise PublishError(f"reply {i}: channel must be one of {', '.join(CHANNELS)}")
        if not str(item.get("comment_id", "")).strip() or not str(item.get("text", "")).strip():
            raise PublishError(f"reply {i}: comment_id and text are required")
    return items


def post_replies(ctx: Context, items: list[dict]) -> tuple[list[dict], bool]:
    """Post each approved reply once. Returns (one result per item, ok)."""
    results, clients, refused, done, ok = [], {}, {}, set(), True
    for item in items:
        channel, comment_id, text = item["channel"], str(item["comment_id"]).strip(), str(item["text"]).strip()
        row = {"channel": channel, "comment_id": comment_id, "text": text, "status": "", "reply_id": "", "detail": ""}
        results.append(row)
        if (channel, comment_id) in done:
            row.update(status="skipped", detail="listed twice in this file")
            continue
        done.add((channel, comment_id))
        if not ctx.live:
            row.update(status="planned", detail="dry run: nothing called")
            continue
        if channel in refused:
            row.update(status="refused", detail=refused[channel])
            ok = False
            continue
        if channel not in clients:
            notes: list = []
            clients[channel] = _client(ctx, channel, notes)
            if clients[channel] is None:
                refused[channel] = "; ".join(notes)
                row.update(status="refused", detail=refused[channel])
                ok = False
                continue
        client = clients[channel]
        try:
            if client.already_replied(comment_id):
                row.update(status="skipped", detail="already answered by our channel or Page")
                continue
            row.update(status="posted", reply_id=client.reply(comment_id, text))
        except ScopeRefused as exc:
            refused[channel] = str(exc)
            row.update(status="refused", detail=str(exc))
            ok = False
        except PublishError as exc:
            row.update(status="failed", detail=str(exc))
            ok = False
    yt = clients.get("youtube")
    if yt:
        ctx.say(f"youtube: {yt.units} quota units used")
    return results, ok


def _cell(text: str, width: int = 80) -> str:
    flat = " ".join(str(text).split()).replace("|", "\\|")
    return flat if len(flat) <= width else flat[: width - 1] + "…"


PERSONAL = ("author", "text")


def redact(found: list[dict]) -> list[dict]:
    """Drop the commenter's name and words. The repository is public, so job summaries, logs and artifacts are too."""
    return [{k: v for k, v in item.items() if k not in PERSONAL} for item in found]


def list_summary(found: list[dict], notes: list[str], days: int) -> str:
    lines = [f"## Unanswered comments, last {days} days: {len(found)}", "",
             "Names and comment text are left out (public repository). Read them on the post itself.", "",
             "| Channel | Post | Comment id | At |", "| --- | --- | --- | --- |"]
    lines += [f"| {c.get('channel', '')} | {c.get('post_url', '')} | {c.get('comment_id', '')} | {c.get('at', '')} |"
              for c in found]
    lines.append("")
    lines += [f"- {n}" for n in notes]
    return "\n".join(lines) + "\n"


def reply_summary(results: list[dict], live: bool) -> str:
    lines = [f"## Replies ({'live' if live else 'dry run'})", "", "| Channel | Comment | Status | Reply id | Text | Detail |",
             "| --- | --- | --- | --- | --- | --- |"]
    for r in results:
        lines.append(f"| {r['channel']} | {r['comment_id']} | {r['status']} | {r['reply_id']} | {_cell(r['text'])} | "
                     f"{_cell(r['detail'], 120)} |")
    return "\n".join(lines) + "\n"


def _write(path: str | None, text: str, append: bool = False) -> None:
    if path:
        with open(path, "a" if append else "w", encoding="utf-8") as fh:
            fh.write(text)


def main(argv: list[str] | None = None, env=None, http=requests, root: Path = ROOT, now: dt.datetime | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    lp = sub.add_parser("list", help="print unanswered comments as JSON")
    lp.add_argument("--days", type=int, default=7, help="comments from the last N days (default 7)")
    lp.add_argument("--post-days", type=int, default=60, help="look at posts public in the last N days (default 60)")
    lp.add_argument("--channel", choices=CHANNELS, action="append", help="limit to a channel (repeatable)")
    lp.add_argument("--redact", action="store_true",
                    help="leave names and comment text out of stdout and --out (always on in the workflow)")
    rp = sub.add_parser("reply", help="post approved replies from a JSON file")
    rp.add_argument("--file", required=True, type=Path)
    rp.add_argument("--live", action="store_true", help="really post (otherwise print the plan and call nothing)")
    for p in (lp, rp):
        p.add_argument("--out", help="also write the JSON result to this file")
        p.add_argument("--summary", help="append a Markdown summary to this file (GITHUB_STEP_SUMMARY)")
    args = ap.parse_args(argv)

    env = dict(os.environ) if env is None else env
    ctx = Context(root=root, cfg=load_config(root), env=env, http=http,
                  now=now or dt.datetime.now(dt.timezone.utc), live=getattr(args, "live", False))

    if args.cmd == "list":
        if args.days < 1 or args.post_days < 1:
            print("--days and --post-days must be at least 1", file=sys.stderr)
            return 2
        found, notes, ok = list_comments(ctx, State(root).data, args.days, args.post_days, tuple(args.channel or CHANNELS))
        if args.redact:
            found = redact(found)
        print(json.dumps(found, indent=2, ensure_ascii=False))
        for note in notes:
            print(note, file=sys.stderr)
        _write(args.out, json.dumps(found, indent=2, ensure_ascii=False) + "\n")
        _write(args.summary, list_summary(found, notes, args.days), append=True)
        return 0 if ok else 1

    if ctx.live and paused(root):
        print("PAUSE file present: no reply is posted.")
        _write(args.summary, "PAUSE file present: no reply is posted.\n", append=True)
        return 0
    try:
        items = load_replies(args.file)
    except PublishError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    results, ok = post_replies(ctx, items)
    for r in results:
        print(f"{r['channel']} {r['comment_id']}: {r['status']} {r['reply_id']} {r['detail']}".rstrip())
    _write(args.out, json.dumps(results, indent=2, ensure_ascii=False) + "\n")
    _write(args.summary, reply_summary(results, ctx.live), append=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
