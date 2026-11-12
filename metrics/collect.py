#!/usr/bin/env python3
"""Collect daily numbers into metrics/metrics.csv: one row per item x channel x day measured.

    python -m metrics.collect            # collect for everything in published.json
    python -m metrics.collect --tokens   # only check token health; exit 1 when one needs attention

Sources (free official APIs only):
  facebook  Graph API: reactions, comments, shares per post; Page followers
  youtube   Data API videos.list(statistics), channels.list(statistics); Analytics API when the
            token has the yt-analytics.readonly scope (average view duration and percentage)
  telegram  getChatMemberCount (the Bot API has no view counts)
  devto     /api/articles/me/all: reactions, comments, page views
  linkedin  no self-serve analytics API: drop the weekly export as metrics/inbox/linkedin-*.csv
            with columns date,impressions,reactions,comments,shares,followers
  x         not collected (paid API)
A source that fails is reported and skipped; the others are still written.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from publish.common import ROOT, Context, PublishError, check, default_env, load_config  # noqa: E402
from publish.youtube import access_token  # noqa: E402

FIELDS = ["measured_on", "item", "channel", "url", "impressions", "views", "reactions", "comments", "shares",
          "followers", "avg_view_seconds", "avg_view_pct"]
ACCOUNT = "_account"   # item name for rows about the whole channel (followers)
LINKEDIN_TOKEN_DAYS = 60
WARN_DAYS = 7


def row(day: dt.date, item: str, channel: str, url: str = "", **values) -> dict:
    return {**dict.fromkeys(FIELDS, ""), "measured_on": day.isoformat(), "item": item, "channel": channel, "url": url,
            **{k: v for k, v in values.items() if v is not None}}


def facebook(ctx: Context, state: dict, day: dt.date) -> list[dict]:
    page, token = ctx.secret("FB_PAGE_ID"), ctx.secret("FB_PAGE_TOKEN")
    base = f"https://graph.facebook.com/{ctx.cfg['facebook_graph_version']}"
    out = []
    info = check(ctx.http.get(f"{base}/{page}", params={"fields": "followers_count,fan_count", "access_token": token}), "Facebook page").json()
    out.append(row(day, ACCOUNT, "facebook", followers=info.get("followers_count", info.get("fan_count"))))
    for item, channels in state.items():
        rec = channels.get("facebook")
        if not rec:
            continue
        resp = ctx.http.get(f"{base}/{rec['id']}", params={
            "fields": "shares,reactions.summary(total_count).limit(0),comments.summary(total_count).limit(0)", "access_token": token})
        if resp.status_code != 200:   # still scheduled, or deleted
            continue
        d = resp.json()
        out.append(row(day, item, "facebook", rec.get("url", ""),
                       reactions=d.get("reactions", {}).get("summary", {}).get("total_count"),
                       comments=d.get("comments", {}).get("summary", {}).get("total_count"),
                       shares=d.get("shares", {}).get("count", 0)))
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


def linkedin_inbox(root: Path) -> list[dict]:
    """Rows from the manual LinkedIn exports. The measuring day is the file's modification date."""
    out = []
    for path in sorted((root / "metrics" / "inbox").glob("linkedin-*.csv")):
        day = dt.date.fromtimestamp(path.stat().st_mtime)
        with path.open(newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                item = (r.get("date") or "").strip() or ACCOUNT
                out.append(row(day, item, "linkedin", **{k: r.get(k, "") for k in ("impressions", "reactions", "comments", "shares", "followers")}))
    return out


SOURCES = {"facebook": facebook, "youtube": youtube, "telegram": telegram, "devto": devto}


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
    day = ctx.now.astimezone(ctx.tz).date()
    rows, failed = linkedin_inbox(ctx.root), 0
    for name, source in SOURCES.items():
        if ctx.cfg["channels"].get(name) != "api":
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
