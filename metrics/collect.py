#!/usr/bin/env python3
"""Collect daily numbers into metrics/metrics.csv: one row per item x channel x day measured.

    python -m metrics.collect            # collect for everything in published.json
    python -m metrics.collect --tokens   # only check token health; exit 1 when one needs attention

Sources (free official APIs only):
  facebook  Graph API: Page followers; per post reactions, comments, shares and views (post_media_view),
            read on the post id (a scheduled photo's id is turned into its post id; docs in facebook())
  youtube   Data API videos.list(statistics), channels.list(statistics); Analytics API when the
            token has the yt-analytics.readonly scope (average view duration and percentage)
  telegram  getChatMemberCount (the Bot API has no view counts)
  devto     /api/articles/me/all: reactions, comments, page views
  linkedin  no self-serve analytics API: the main session copies the post analytics into
            metrics/inbox/linkedin-*.csv (metrics/inbox/README.md)
  x         no free API: the same manual path, metrics/inbox/x-*.csv; without a file X is "no data"
A source that fails is reported and skipped; the others are still written.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from publish.common import ROOT, Context, PublishError, check, default_env, is_followup_key, load_config  # noqa: E402
from publish.youtube import access_token  # noqa: E402

FIELDS = ["measured_on", "item", "channel", "url", "impressions", "views", "reactions", "comments", "shares",
          "followers", "avg_view_seconds", "avg_view_pct"]
ACCOUNT = "_account"   # item name for rows about the whole channel (followers)
LINKEDIN_TOKEN_DAYS = 60
WARN_DAYS = 7


def row(day: dt.date, item: str, channel: str, url: str = "", **values) -> dict:
    return {**dict.fromkeys(FIELDS, ""), "measured_on": day.isoformat(), "item": item, "channel": channel, "url": url,
            **{k: v for k, v in values.items() if v is not None}}


FB_POST_FIELDS = "shares,reactions.summary(total_count).limit(0),comments.summary(total_count).limit(0)"
FB_VIEWS_METRIC = "post_media_view"
_TOKEN_IN_URL = re.compile(r"access_token=[^&\s\"']+")


def _scrub(text: str, token: str) -> str:
    text = _TOKEN_IN_URL.sub("access_token=***", str(text))
    return text.replace(token, "***") if token else text


def _fb_error(resp, token: str) -> str:
    """'HTTP 400 code 100/33: message' from a Graph error reply, token scrubbed."""
    try:
        err = (resp.json() or {}).get("error") or {}
    except (ValueError, AttributeError):
        err = {}
    if not isinstance(err, dict):
        err = {"message": str(err)}
    code = err.get("code", "?")
    if err.get("error_subcode"):
        code = f"{code}/{err['error_subcode']}"
    message = err.get("message") or (resp.text or "")[:200]
    return _scrub(f"HTTP {resp.status_code} code {code}: {' '.join(str(message).split())[:300]}", token)


def _fb_get(ctx: Context, url: str, params: dict, token: str) -> tuple[dict | None, str]:
    """(json, "") on 200, else (None, reason). Never raises: one bad post must not stop the others."""
    try:
        resp = ctx.http.get(url, params={**params, "access_token": token}, timeout=30)
    except Exception as exc:  # noqa: BLE001 - a network error's message can hold the full URL, token included
        return None, _scrub(f"{type(exc).__name__}: {exc}", token)
    if resp.status_code != 200:
        return None, _fb_error(resp, token)
    return resp.json(), ""


def _fb_scheduled(rec: dict, now: dt.datetime) -> bool:
    when = rec.get("scheduled_for")
    try:
        return bool(when) and dt.datetime.fromisoformat(when) > now
    except ValueError:
        return False


def facebook(ctx: Context, state: dict, day: dt.date) -> list[dict]:
    """Page followers, then one row per published Page post.

    Graph API docs (checked 27 Nov 2026, version from publish/config.yaml, v27.0 when checked):
      https://developers.facebook.com/docs/graph-api/reference/photo/
      https://developers.facebook.com/docs/graph-api/reference/post/
      https://developers.facebook.com/docs/graph-api/reference/insights/
      https://developers.facebook.com/docs/graph-api/reference/insights-result/
      https://developers.facebook.com/blog/post/2026/02/18/introducing-graph-api-v25-and-marketing-api-v25/
    - Which object. The API publisher schedules photos (POST /{page}/photos), so published.json keeps the photo id.
      The Photo node lists no `shares` field and no `reactions` or `comments` edge, so the old read of those fields
      on a photo id was refused (the likely cause of the missing rows, lab-to-prod#68). The Photo node has
      `page_story_id`: "ID of the page story this corresponds to. May not be on all photos. Applies only to
      published photos". So a photo id is turned into its post id first. A manual record whose id has no "_" is
      {page-id}_{id} (publish.comments.Facebook.object_id, reused here).
    - Post fields. The Post node lists `shares` ("Number of times the post has been shared", a struct with
      `count`) and the edges `comments`, `reactions` and `insights` ("Insights for this post (only for Pages)").
    - Views. GET /{post-id}/insights?metric=post_media_view: "The number of times your content was played or
      displayed. Content includes videos, posts, stories and ads.", period lifetime, not marked deprecated. It goes
      to the `views` column. `post_impressions` and `post_impressions_unique` are marked "Deprecated above Graph
      API v25" and are not read. The v25 blog names post_total_media_view_unique and post_media_view as the
      replacements. The InsightsResult page lists name, period and values (a list of InsightsValue); the
      `value` field of an InsightsValue is read from the last item and was not checked on its own page.
    - Permissions: insights need `read_insights` and `pages_read_engagement` and "a Page access token requested by
      a person who can perform the ANALYZE task on the Page".
    A post that cannot be read is logged with the HTTP status, the Graph error code and message (token scrubbed)
    and skipped; the other posts are still read. A post scheduled for later is skipped quietly.
    """
    from publish.comments import Facebook as FacebookComments   # one place that knows how ids are stored

    page, token = ctx.secret("FB_PAGE_ID"), ctx.secret("FB_PAGE_TOKEN")
    base = f"https://graph.facebook.com/{ctx.cfg['facebook_graph_version']}"
    ids = FacebookComments(ctx)
    out = []
    info = check(ctx.http.get(f"{base}/{page}", params={"fields": "followers_count,fan_count", "access_token": token}), "Facebook page").json()
    out.append(row(day, ACCOUNT, "facebook", followers=info.get("followers_count", info.get("fan_count"))))
    skipped = 0
    for item, channels in sorted(state.items()):
        rec = channels.get("facebook")
        if not rec or not rec.get("id") or _fb_scheduled(rec, ctx.now):
            continue
        post_id = ids.object_id(rec)
        if "_" not in post_id:   # a photo id from the API publisher
            d, why = _fb_get(ctx, f"{base}/{post_id}", {"fields": "page_story_id"}, token)
            if d is not None and not d.get("page_story_id"):
                why = "the photo has no page_story_id (not published yet, or not a Page photo)"
            if why:
                skipped += 1
                ctx.say(f"facebook {item}: no numbers, photo {post_id}: {why}")
                continue
            post_id = str(d["page_story_id"])
        d, why = _fb_get(ctx, f"{base}/{post_id}", {"fields": FB_POST_FIELDS}, token)
        if why:
            skipped += 1
            ctx.say(f"facebook {item}: no numbers, post {post_id}: {why}")
            continue
        views = None
        ins, why = _fb_get(ctx, f"{base}/{post_id}/insights", {"metric": FB_VIEWS_METRIC}, token)
        if why:
            ctx.say(f"facebook {item}: no views, insights {post_id}: {why}")
        else:
            for metric in ins.get("data") or []:
                if metric.get("name") == FB_VIEWS_METRIC and metric.get("values"):
                    value = metric["values"][-1].get("value")
                    views = value if isinstance(value, (int, float)) else None
        out.append(row(day, item, "facebook", rec.get("url", ""), views=views,
                       reactions=d.get("reactions", {}).get("summary", {}).get("total_count"),
                       comments=d.get("comments", {}).get("summary", {}).get("total_count"),
                       shares=(d.get("shares") or {}).get("count", 0)))
    if skipped:
        ctx.say(f"facebook: {skipped} post(s) without numbers, reasons above")
    return out


def youtube(ctx: Context, state: dict, day: dt.date) -> list[dict]:
    auth = {"Authorization": f"Bearer {access_token(ctx)}"}
    api = "https://www.googleapis.com/youtube/v3"
    out = []
    ch = check(ctx.http.get(f"{api}/channels", params={"part": "statistics", "mine": "true"}, headers=auth), "YouTube channel").json()
    if ch.get("items"):
        out.append(row(day, ACCOUNT, "youtube", followers=ch["items"][0]["statistics"].get("subscriberCount")))
    ids = {rec["youtube"]["id"]: (item, rec["youtube"]) for item, rec in state.items() if "youtube" in rec}
    if not ids:
        return out
    stats = check(ctx.http.get(f"{api}/videos", params={"part": "statistics", "id": ",".join(ids)}, headers=auth), "YouTube videos").json()
    extra = {}
    try:   # needs the yt-analytics.readonly scope; without it the two columns stay empty
        rep = ctx.http.get("https://youtubeanalytics.googleapis.com/v2/reports", headers=auth, params={
            "ids": "channel==MINE", "startDate": "2026-11-01", "endDate": day.isoformat(), "dimensions": "video",
            "metrics": "averageViewDuration,averageViewPercentage", "filters": "video==" + ",".join(ids)})
        if rep.status_code == 200:
            extra = {r[0]: (r[1], r[2]) for r in rep.json().get("rows", [])}
    except Exception:  # noqa: BLE001
        pass
    for v in stats.get("items", []):
        item, rec = ids[v["id"]]
        s = v["statistics"]
        avg = extra.get(v["id"], (None, None))
        out.append(row(day, item, "youtube", rec.get("url", ""), views=s.get("viewCount"), reactions=s.get("likeCount"),
                       comments=s.get("commentCount"), avg_view_seconds=avg[0], avg_view_pct=avg[1]))
    return out


def telegram(ctx: Context, state: dict, day: dt.date) -> list[dict]:
    token, channel = ctx.secret("TELEGRAM_BOT_TOKEN"), ctx.secret("TELEGRAM_CHANNEL")
    chat = channel if channel.startswith(("@", "-")) else f"@{channel}"
    try:
        resp = ctx.http.get(f"https://api.telegram.org/bot{token}/getChatMemberCount", params={"chat_id": chat})
    except Exception as exc:  # noqa: BLE001 - the URL holds the token
        raise PublishError(f"Telegram getChatMemberCount failed: {type(exc).__name__}") from None
    return [row(day, ACCOUNT, "telegram", followers=check(resp, "Telegram member count").json()["result"])]


def devto(ctx: Context, state: dict, day: dt.date) -> list[dict]:
    headers = {"api-key": ctx.secret("DEVTO_API_KEY"), "Accept": "application/vnd.forem.api-v1+json"}
    mine = check(ctx.http.get("https://dev.to/api/articles/me/all?per_page=200", headers=headers), "DEV articles").json()
    by_id = {a["id"]: a for a in mine}
    out = []
    for item, channels in state.items():
        a = by_id.get(channels.get("devto", {}).get("id"))
        if a:
            out.append(row(day, item, "devto", a.get("url", ""), views=a.get("page_views_count"),
                           reactions=a.get("public_reactions_count"), comments=a.get("comments_count")))
    return out


MANUAL_CHANNELS = ("linkedin", "x")   # no free read API: numbers come from files in metrics/inbox
MANUAL_COLUMNS = ("impressions", "views", "reactions", "comments", "shares", "followers")


def manual_inbox(root: Path) -> list[dict]:
    """Rows from the hand-made exports metrics/inbox/linkedin-*.csv and x-*.csv (metrics/inbox/README.md).

    Columns: `item` (the published.json key) or `date` (the post's date, the key of a daily post); both empty means
    the account row with `followers`. `measured_on` (YYYY-MM-DD) is the day the numbers were read; without it the
    file's modification date is used. A missing number stays empty ("no data"), never 0.
    """
    out = []
    for channel in MANUAL_CHANNELS:
        for path in sorted((root / "metrics" / "inbox").glob(f"{channel}-*.csv")):
            file_day = dt.date.fromtimestamp(path.stat().st_mtime)
            with path.open(newline="", encoding="utf-8-sig") as fh:
                for r in csv.DictReader(fh):
                    r = {k.strip(): (v or "").strip() for k, v in r.items() if k}
                    if not any(r.values()):
                        continue
                    day = dt.date.fromisoformat(r["measured_on"]) if r.get("measured_on") else file_day
                    item = r.get("item") or r.get("date") or ACCOUNT
                    out.append(row(day, item, channel, r.get("url", ""), **{k: r.get(k, "") for k in MANUAL_COLUMNS}))
    return out


SOURCES = {"facebook": facebook, "youtube": youtube, "telegram": telegram, "devto": devto}
# A channel with none of its secrets set is not connected yet: skip it instead of failing every night.
# A channel with only some of them set is a broken setup and still fails.
SECRETS = {"facebook": ("FB_PAGE_ID", "FB_PAGE_TOKEN"),
           "youtube": ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"),
           "telegram": ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHANNEL"),
           "devto": ("DEVTO_API_KEY",)}


def merge_rows(path: Path, new: list[dict]) -> int:
    """Upsert on (measured_on, item, channel) so a second run on the same day does not duplicate."""
    rows = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                rows[(r["measured_on"], r["item"], r["channel"])] = r
    for r in new:
        rows[(r["measured_on"], r["item"], r["channel"])] = r
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        for key in sorted(rows):
            w.writerow({k: rows[key].get(k, "") for k in FIELDS})
    return len(rows)


def collect(ctx: Context) -> int:
    state_path = ctx.root / "published.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    state = {k: v for k, v in state.items() if not is_followup_key(k)}  # follow-up comments are not posts
    day = ctx.now.astimezone(ctx.tz).date()
    rows, failed = manual_inbox(ctx.root), 0
    for name, source in SOURCES.items():
        if ctx.cfg["channels"].get(name) != "api":
            continue
        if not any(ctx.env.get(s, "").strip() for s in SECRETS.get(name, ())):
            ctx.say(f"{name}: not connected (no secrets), skipped")
            continue
        try:
            got = source(ctx, state, day)
            rows += got
            ctx.say(f"{name}: {len(got)} row(s)")
        except PublishError as exc:
            failed += 1
            ctx.say(f"{name}: FAILED {exc}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            ctx.say(f"{name}: FAILED unexpected {type(exc).__name__}")
    total = merge_rows(ctx.root / "metrics" / "metrics.csv", rows)
    ctx.say(f"metrics.csv: {total} row(s)")
    return 1 if failed else 0


def check_tokens(ctx: Context) -> int:
    """Warn 7 days before a token stops working. Returns 1 if anything needs the author."""
    problems = []
    today = ctx.now.astimezone(ctx.tz).date()
    issued = ctx.env.get("LINKEDIN_TOKEN_ISSUED", "").strip()
    if ctx.env.get("LINKEDIN_ACCESS_TOKEN"):
        if not issued:
            problems.append("LinkedIn: set the repository variable LINKEDIN_TOKEN_ISSUED (YYYY-MM-DD) so expiry can be tracked")
        else:
            left = (dt.date.fromisoformat(issued) + dt.timedelta(days=LINKEDIN_TOKEN_DAYS) - today).days
            ctx.say(f"linkedin: token has {left} day(s) left")
            if left <= WARN_DAYS:
                problems.append(f"LinkedIn: token expires in {left} day(s); run scripts/tokens/linkedin_token.py and update the secret")
    if ctx.env.get("FB_PAGE_TOKEN"):
        try:
            tok = ctx.env["FB_PAGE_TOKEN"]
            d = check(ctx.http.get(f"https://graph.facebook.com/{ctx.cfg['facebook_graph_version']}/debug_token",
                                   params={"input_token": tok, "access_token": tok}), "Facebook debug_token").json()["data"]
            if not d.get("is_valid"):
                problems.append("Facebook: the Page token is no longer valid")
            for key, label in (("expires_at", "token"), ("data_access_expires_at", "data access")):
                if d.get(key):
                    left = (dt.datetime.fromtimestamp(d[key], dt.timezone.utc).date() - today).days
                    ctx.say(f"facebook: {label} has {left} day(s) left")
                    if left <= WARN_DAYS:
                        problems.append(f"Facebook: {label} expires in {left} day(s); run scripts/tokens/facebook_token.py")
        except PublishError as exc:
            problems.append(f"Facebook: {exc}")
    if ctx.env.get("YT_REFRESH_TOKEN"):
        try:
            access_token(ctx)
            ctx.say("youtube: refresh token works")
        except PublishError:
            problems.append("YouTube: the refresh token was refused; run scripts/tokens/youtube_token.py "
                            "(a consent screen left in Testing expires tokens after 7 days)")
    for p in problems:
        ctx.say(f"ATTENTION {p}")
    return 1 if problems else 0


def main(argv=None) -> int:
    import requests

    ap = argparse.ArgumentParser(description="Collect metrics into metrics/metrics.csv")
    ap.add_argument("--tokens", action="store_true", help="only check token health")
    args = ap.parse_args(argv)
    session = requests.Session()
    ctx = Context(ROOT, load_config(ROOT), default_env(), session, dt.datetime.now(dt.timezone.utc), live=True)
    return check_tokens(ctx) if args.tokens else collect(ctx)


if __name__ == "__main__":
    sys.exit(main())
