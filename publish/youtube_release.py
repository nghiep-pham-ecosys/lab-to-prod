"""Upload a video batch staged on a draft GitHub release to YouTube, as private videos with publishAt.

nghiep-motion-studio stages each finished video (and its Shorts) as assets of a DRAFT release of this repository:
the mp4s, their SRTs and manifest.json. Draft releases and their assets are visible only to people with push access.
The youtube-upload workflow downloads the assets with GITHUB_TOKEN into one folder and runs:

    python -m publish.youtube_release --assets DIR --tag TAG [--publish-at ISO] [--live]

- Dry run unless --live: the manifest and the files are checked and the plan is printed; nothing is called.
- Live: each item not yet in result.json is uploaded as private with publishAt (YouTube makes it public then),
  then its SRT goes up as captions. result.json is written after every call that changes it, so a re-run skips
  what is already up. The exit code is 0 only when every item is uploaded (``complete: true``); the workflow
  deletes the draft release only then.
- --publish-at moves the whole batch so that its earliest item goes out at that time, keeping the spacing.
- A publish time in the past is refused for that item (no back-posting).
- An item with ``playlist`` lands in that playlist: found by exact title among the channel's own playlists
  (playlists.list, mine=true, every page), created when missing (playlists.insert), then the video is added
  (playlistItems.insert) unless playlistItems.list says it is already there. The playlist id is kept in
  result.json, so a re-run neither creates a second playlist nor adds the video twice. A failed playlist step
  leaves the batch incomplete; the re-run retries only that step. Items without ``playlist`` skip all of this.
- Quota is logged per call (see youtube.py) and totalled in result.json.
- The PAUSE file at the repository root stops the run before any call.

manifest.json (written by ``motion-studio stage-upload``)::

    {"version": 1, "tag": "yt-rag-en", "job": "rag",
     "items": [{"key": "rag.en", "kind": "video", "path": "rag.en.mp4", "video": "rag.en.mp4",
                "captions": "rag.en.srt", "title": "...", "description": "...", "tags": ["rag"],
                "language": "en", "publish_at": "2026-12-01T19:00:00+07:00", "synthetic_media": true,
                "playlist": {"title": "...", "description": "...", "privacy": "public"}}]}

``playlist`` is optional; ``description`` defaults to "" and ``privacy`` (public, unlisted or private) to public.

result.json (read by ``motion-studio finish-upload``)::

    {"version": 1, "tag": "yt-rag-en", "job": "rag", "complete": true,
     "items": {"rag.en": {"path": "rag.en.mp4", "video_id": "...", "url": "...", "publish_at": "...Z",
                          "captions": true, "uploaded_at": "...",
                          "playlist": {"id": "PL...", "title": "...", "added": true}}},
     "playlists": {"<title>": "PL..."},
     "quota": {"videos_insert": 1, "captions_insert": 1, "playlists_list": 1, "playlists_insert": 0,
               "playlist_items_list": 1, "playlist_items_insert": 1, "units": 452}}
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path, PurePosixPath

from .common import ROOT, Context, PublishError, default_env, load_config, paused
from .youtube import (CAPTIONS_UNITS, DAILY_UNITS, LIST_UNITS, PLAYLIST_INSERT_UNITS, UPLOADS_PER_DAY, access_token,
                      add_to_playlist, create_playlist, insert_captions, playlist_has_video, playlist_pages, upload_video)

VERSION = 1
NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
LANG_RE = re.compile(r"[a-z]{2,3}(-[A-Za-z0-9]{2,8})?")
KINDS = ("video", "short")
MAX_TITLE = 100            # characters (videos resource, snippet.title)
MAX_DESCRIPTION = 5000     # bytes (snippet.description)
MAX_TAGS = 500             # characters, counting quotes around tags with spaces and the commas between tags
AI_LABEL = "made with ai"  # lab-to-prod rule: videos made with AI tools say so on YouTube
LANG_NAMES = {"en": "English", "vi": "Tiếng Việt"}
MAX_PLAYLIST_TITLE = 150         # characters (verify: not stated on the playlists resource page, 26 Nov 2026)
MAX_PLAYLIST_DESCRIPTION = 5000  # bytes (verify, as above)
PLAYLIST_PRIVACY = ("public", "unlisted", "private")
QUOTA_KEYS = ("videos_insert", "captions_insert", "playlists_list", "playlists_insert", "playlist_items_list",
              "playlist_items_insert", "units")


class ManifestError(PublishError):
    """The staged batch is not uploadable as it is. Nothing was called."""


def parse_time(raw: object, what: str) -> dt.datetime:
    try:
        when = dt.datetime.fromisoformat(str(raw))
    except ValueError as exc:
        raise ManifestError(f"{what}: {raw!r} is not an ISO 8601 time") from exc
    if when.tzinfo is None:
        raise ManifestError(f"{what}: {raw!r} has no UTC offset")
    return when


def youtube_time(when: dt.datetime) -> str:
    return when.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def tags_length(tags: list[str]) -> int:
    return sum(len(t) + (2 if " " in t else 0) for t in tags) + max(len(tags) - 1, 0)


def _check_item(i: int, item: object, assets: Path, keys: set[str]) -> list[str]:
    if not isinstance(item, dict):
        return [f"items[{i}] must be an object"]
    problems = []
    key = item.get("key")
    where = f"items[{i}] ({key})"
    if not isinstance(key, str) or not NAME_RE.fullmatch(key):
        problems.append(f"items[{i}].key must match {NAME_RE.pattern}")
    elif key in keys:
        problems.append(f"{where}: key is used twice")
    else:
        keys.add(key)
    if item.get("kind") not in KINDS:
        problems.append(f"{where}: kind must be one of {', '.join(KINDS)}")
    rel = item.get("path")
    parts = PurePosixPath(rel).parts if isinstance(rel, str) else ()
    if not isinstance(rel, str) or not rel.endswith(".mp4") or rel.startswith("/") or ".." in parts or "\\" in rel:
        problems.append(f"{where}: path must be the video's relative path in its job folder")
    for field, suffix, required in (("video", ".mp4", True), ("captions", ".srt", False)):
        name = item.get(field)
        if name is None and not required:
            continue
        if not isinstance(name, str) or not NAME_RE.fullmatch(name) or not name.endswith(suffix):
            problems.append(f"{where}: {field} must be a {suffix} asset name")
        elif not (assets / name).is_file():
            problems.append(f"{where}: {name} is not among the release assets")
    title = item.get("title")
    if not isinstance(title, str) or not title.strip() or len(title) > MAX_TITLE or re.search(r"[<>]", title):
        problems.append(f"{where}: title must be 1-{MAX_TITLE} characters without < or >")
    desc = item.get("description")
    if not isinstance(desc, str) or len(desc.encode("utf-8")) > MAX_DESCRIPTION or re.search(r"[<>]", desc):
        problems.append(f"{where}: description must be text of at most {MAX_DESCRIPTION} bytes without < or >")
    elif AI_LABEL not in desc.lower():
        problems.append(f"{where}: description must say \"made with AI\"")
    tags = item.get("tags", [])
    if (not isinstance(tags, list) or not all(isinstance(t, str) and t.strip() and not re.search(r"[<>,]", t) for t in tags)
            or tags_length(tags) > MAX_TAGS):
        problems.append(f"{where}: tags must be a list of words or phrases, {MAX_TAGS} characters in all")
    if not isinstance(item.get("language"), str) or not LANG_RE.fullmatch(item["language"]):
        problems.append(f"{where}: language must be a language code such as en or vi")
    try:
        parse_time(item.get("publish_at"), f"{where} publish_at")
    except ManifestError as exc:
        problems.append(str(exc))
    if not isinstance(item.get("synthetic_media", True), bool):
        problems.append(f"{where}: synthetic_media must be true or false")
    if "playlist" in item:
        problems += _check_playlist(item["playlist"], where)
    return problems


def _check_playlist(pl: object, where: str) -> list[str]:
    if not isinstance(pl, dict):
        return [f"{where}: playlist must be an object with title, description and privacy"]
    problems = []
    unknown = sorted(set(pl) - {"title", "description", "privacy"})
    if unknown:
        problems.append(f"{where}: playlist has unknown field(s) {', '.join(unknown)}")
    title = pl.get("title")
    if not isinstance(title, str) or not title.strip() or title != title.strip() or len(title) > MAX_PLAYLIST_TITLE \
            or re.search(r"[<>]", title):
        problems.append(f"{where}: playlist.title must be 1-{MAX_PLAYLIST_TITLE} characters without < or > "
                        "or outer spaces")
    desc = pl.get("description", "")
    if not isinstance(desc, str) or len(desc.encode("utf-8")) > MAX_PLAYLIST_DESCRIPTION or re.search(r"[<>]", desc):
        problems.append(f"{where}: playlist.description must be text of at most {MAX_PLAYLIST_DESCRIPTION} bytes "
                        "without < or >")
    if pl.get("privacy", "public") not in PLAYLIST_PRIVACY:
        problems.append(f"{where}: playlist.privacy must be one of {', '.join(PLAYLIST_PRIVACY)}")
    return problems


def load_manifest(assets: Path, tag: str) -> dict:
    """Read and check ``manifest.json`` in the assets folder. Raises ManifestError listing every problem."""
    path = assets / "manifest.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ManifestError(f"cannot read {path.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestError("manifest.json must be a JSON object")
    problems = []
    if data.get("version") != VERSION:
        problems.append(f"version must be {VERSION}")
    if data.get("tag") != tag:
        problems.append(f"tag is {data.get('tag')!r}, but the release is {tag!r}")
    if not isinstance(data.get("job"), str) or not NAME_RE.fullmatch(data["job"]):
        problems.append(f"job must match {NAME_RE.pattern}")
    items = data.get("items")
    if not isinstance(items, list) or not items:
        problems.append("items must list at least one video")
        items = []
    keys: set[str] = set()
    for i, item in enumerate(items):
        problems += _check_item(i, item, assets, keys)
    if problems:
        raise ManifestError("manifest.json is refused, nothing uploaded:\n" + "\n".join(f"  - {p}" for p in problems))
    return data


def shift(items: list[dict], publish_at: str | None) -> list[dict]:
    """Move every item by the same amount so that the earliest goes public at ``publish_at``."""
    if not publish_at:
        return items
    target = parse_time(publish_at, "--publish-at")
    delta = target - min(parse_time(it["publish_at"], it["key"]) for it in items)
    return [{**it, "publish_at": (parse_time(it["publish_at"], it["key"]) + delta).isoformat()} for it in items]


def load_result(path: Path, manifest: dict) -> dict:
    """result.json of an earlier run of this batch (kept on the draft release), else a new one."""
    fresh = {"version": VERSION, "tag": manifest["tag"], "job": manifest["job"], "complete": False, "items": {},
             "playlists": {}, "quota": dict.fromkeys(QUOTA_KEYS, 0)}
    if not path.exists():
        return fresh
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ManifestError(f"cannot read {path.name}: {exc}") from exc
    if not isinstance(data, dict) or data.get("tag") != manifest["tag"] or data.get("job") != manifest["job"] \
            or not isinstance(data.get("items"), dict):
        raise ManifestError(f"{path.name} belongs to another batch; delete it from the release to start over")
    quota = data.setdefault("quota", {})
    for key in QUOTA_KEYS:
        quota.setdefault(key, 0)
    if not isinstance(data.get("playlists"), dict):
        data["playlists"] = {}
    return data


def save(path: Path, result: dict) -> None:
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def body_for(ctx: Context, item: dict) -> dict:
    lang = item["language"]
    snippet = {"title": item["title"], "description": item["description"], "categoryId": str(ctx.cfg["youtube_category_id"]),
               "defaultLanguage": lang, "defaultAudioLanguage": lang}
    if item.get("tags"):
        snippet["tags"] = item["tags"]
    return {"snippet": snippet,
            "status": {"privacyStatus": "private", "publishAt": youtube_time(parse_time(item["publish_at"], item["key"])),
                       "selfDeclaredMadeForKids": False, "containsSyntheticMedia": item.get("synthetic_media", True)}}


def watch_url(item: dict, video_id: str) -> str:
    return f"https://www.youtube.com/shorts/{video_id}" if item["kind"] == "short" else f"https://www.youtube.com/watch?v={video_id}"


def in_playlist(it: dict, done: dict | None) -> bool:
    """True when the item needs no playlist step: it has no ``playlist``, or result.json says it was added."""
    if not it.get("playlist"):
        return True
    got = (done or {}).get("playlist") or {}
    return got.get("added") is True and got.get("title") == it["playlist"]["title"]


def playlist_cell(it: dict, done: dict) -> str:
    if not it.get("playlist"):
        return "-"
    return f"{it['playlist']['title']} ({'added' if in_playlist(it, done) else 'not added'})"


def summary_table(result: dict, items: list[dict], live: bool) -> str:
    rows = ["| item | kind | publish at (UTC) | video | captions | playlist |", "| --- | --- | --- | --- | --- | --- |"]
    for it in items:
        done = result["items"].get(it["key"], {})
        when = youtube_time(parse_time(it["publish_at"], it["key"]))
        video = done.get("video_id") or ("not uploaded" if live else "dry run")
        rows.append(f"| {it['key']} | {it['kind']} | {when} | {video} | {'yes' if done.get('captions') else 'no'} "
                    f"| {playlist_cell(it, done)} |")
    q = result["quota"]
    rows.append("")
    playlist_calls = ""
    if any(q[k] for k in ("playlists_list", "playlists_insert", "playlist_items_list", "playlist_items_insert")):
        playlist_calls = (f", {q['playlists_list']} playlists.list, {q['playlists_insert']} playlists.insert, "
                          f"{q['playlist_items_list']} playlistItems.list, {q['playlist_items_insert']} "
                          "playlistItems.insert")
    rows.append(f"Quota this batch: {q['videos_insert']} videos.insert (of {UPLOADS_PER_DAY} uploads a day), "
                f"{q['captions_insert']} captions.insert{playlist_calls} = {q['units']} units (of {DAILY_UNITS:,} a day).")
    rows.append(f"Complete: {'yes' if result['complete'] else 'no'}.")
    return "\n".join(rows) + "\n"


def spend(ctx: Context, result: dict, key: str, method: str, units: int) -> None:
    """Count one Data API call in result.json and log it, before the call is made (a refused call costs too)."""
    result["quota"][key] += 1
    result["quota"]["units"] += units
    ctx.say(f"       quota: {method}, {units} unit{'s' if units != 1 else ''}")


def find_or_create_playlist(ctx: Context, it: dict, result: dict, auth: dict) -> tuple[str, bool]:
    """The id of the playlist named ``it['playlist']['title']`` (exact match), created when the channel has none.
    Returns ``(id, created)``. An id kept in result.json from an earlier call or run is used without a call."""
    pl = it["playlist"]
    title = pl["title"]
    known = result["playlists"].get(title)
    if known:
        return known, False
    found = []
    for page in playlist_pages(ctx, auth, lambda: spend(ctx, result, "playlists_list", "playlists.list", LIST_UNITS)):
        found += [p["id"] for p in page if isinstance(p, dict) and (p.get("snippet") or {}).get("title") == title]
        if found:
            break
    if found:
        ctx.say(f"       playlist {title!r} found: {found[0]}")
        return found[0], False
    spend(ctx, result, "playlists_insert", "playlists.insert", PLAYLIST_INSERT_UNITS)
    new_id = create_playlist(ctx, pl, it["language"], auth)
    ctx.say(f"       playlist {title!r} created as {pl.get('privacy', 'public')}: {new_id}")
    return new_id, True


def put_in_playlist(ctx: Context, it: dict, entry: dict, result: dict, auth: dict, save_result) -> None:
    """Make sure the uploaded video of ``it`` is in its playlist; record it in ``entry``. Raises on a refused call."""
    title = it["playlist"]["title"]
    playlist_id, created = find_or_create_playlist(ctx, it, result, auth)
    result["playlists"][title] = playlist_id
    save_result()  # the playlist exists now: a re-run must not create a second one
    video_id = entry["video_id"]
    there = False
    if not created:  # a playlist made a moment ago is empty: no need to ask
        spend(ctx, result, "playlist_items_list", "playlistItems.list", LIST_UNITS)
        try:
            there = playlist_has_video(ctx, playlist_id, video_id, auth)
        except PublishError as exc:
            if "HTTP 404" not in str(exc):
                raise
            # the kept id is gone (playlist deleted in Studio): forget it and look again, once
            ctx.say(f"       playlist {playlist_id} no longer exists; searching for {title!r} again")
            del result["playlists"][title]
            playlist_id, created = find_or_create_playlist(ctx, it, result, auth)
            result["playlists"][title] = playlist_id
            save_result()
            if not created:
                spend(ctx, result, "playlist_items_list", "playlistItems.list", LIST_UNITS)
                there = playlist_has_video(ctx, playlist_id, video_id, auth)
    if there:
        ctx.say(f"       {video_id} is already in playlist {title!r}")
    else:
        spend(ctx, result, "playlist_items_insert", "playlistItems.insert", PLAYLIST_INSERT_UNITS)
        add_to_playlist(ctx, playlist_id, video_id, auth)
        ctx.say(f"       {video_id} added to playlist {title!r}")
    entry["playlist"] = {"id": playlist_id, "title": title, "added": True}
    save_result()


def playlist_plan(it: dict) -> str:
    pl = it["playlist"]
    return (f"playlist {pl['title']!r}: find it by title among the channel's playlists, create it as "
            f"{pl.get('privacy', 'public')} if missing, add the video unless it is there")


def run(ctx: Context, assets: Path, tag: str, publish_at: str | None = None, result_path: Path | None = None,
        summary: Path | None = None, github_output: Path | None = None) -> int:
    """Upload the batch (live) or print its plan (dry run). Returns the exit code: 0 only if nothing failed and,
    when live, every item is uploaded."""
    result_path = result_path or assets / "result.json"

    def finish(code: int, complete: bool = False) -> int:
        if github_output:
            with open(github_output, "a", encoding="utf-8") as fh:
                fh.write(f"complete={'true' if complete else 'false'}\n")
        return code

    if paused(ctx.root):
        ctx.say("PAUSE file present: nothing is uploaded.")
        return finish(1)
    try:
        manifest = load_manifest(assets, tag)
        items = shift(manifest["items"], publish_at)
        result = load_result(result_path, manifest)
    except PublishError as exc:
        ctx.say(f"FAIL {exc}")
        return finish(1)
    ctx.say(f"{'LIVE' if ctx.live else 'DRY RUN'}: {len(items)} item(s) of job {manifest['job']} from release {tag}")
    failures, auth = 0, None

    def get_auth() -> dict:
        nonlocal auth
        auth = auth or {"Authorization": f"Bearer {access_token(ctx)}"}
        return auth

    def playlist_step(it: dict, entry: dict) -> None:
        nonlocal failures
        try:
            put_in_playlist(ctx, it, entry, result, get_auth(), lambda: save(result_path, result))
        except (PublishError, OSError, KeyError, ValueError) as exc:
            ctx.say(f"  FAIL {it['key']}: the video is up as {entry['video_id']}, but the playlist step failed "
                    f"({str(exc)[:200]}); run the workflow again to retry only that step")
            failures += 1

    for it in items:
        key, when = it["key"], parse_time(it["publish_at"], it["key"])
        done = result["items"].get(key)
        if done and done.get("video_id"):
            if in_playlist(it, done):
                ctx.say(f"  {key}: already uploaded as {done['video_id']}, skipped")
            elif not ctx.live:
                ctx.say(f"  DRY RUN {key}: already uploaded as {done['video_id']}; {playlist_plan(it)}")
            else:
                ctx.say(f"  {key}: already uploaded as {done['video_id']}; adding it to its playlist")
                playlist_step(it, done)
            continue
        if when <= ctx.now:
            ctx.say(f"  FAIL {key}: publish time {when.isoformat()} is in the past; not back-posting "
                    "(run again with publish_at to move the batch)")
            failures += 1
            continue
        line = f"{key}: {it['video']} as private, public at {youtube_time(when)}, title {it['title']!r}" \
               + (f", + {it['captions']}" if it.get("captions") else "")
        if not ctx.live:
            ctx.say(f"  DRY RUN {line}")
            if it.get("playlist"):
                ctx.say(f"          {playlist_plan(it)}")
            continue
        try:
            video_id = upload_video(ctx, assets / it["video"], body_for(ctx, it), get_auth())
        except (PublishError, OSError, KeyError, ValueError) as exc:
            ctx.say(f"  FAIL {key}: {str(exc)[:300]}")
            failures += 1
            continue
        result["quota"]["videos_insert"] += 1
        ctx.say(f"  OK   {line}: video {video_id}")
        ctx.say(f"       quota: videos.insert, 1 of {UPLOADS_PER_DAY} uploads a day")
        entry = {"path": it["path"], "kind": it["kind"], "video_id": video_id, "url": watch_url(it, video_id),
                 "publish_at": youtube_time(when), "captions": False,
                 "uploaded_at": ctx.now.astimezone(dt.timezone.utc).isoformat(timespec="seconds")}
        result["items"][key] = entry
        save(result_path, result)  # the video is up: never upload it again, whatever happens next
        if it.get("captions"):
            lang = it["language"]
            result["quota"]["captions_insert"] += 1
            result["quota"]["units"] += CAPTIONS_UNITS
            try:
                insert_captions(ctx, video_id, assets / it["captions"], lang, LANG_NAMES.get(lang, lang), auth)
                entry["captions"] = True
                ctx.say(f"       captions {it['captions']} added; quota: captions.insert, {CAPTIONS_UNITS} units")
            except Exception as exc:  # noqa: BLE001 - the video is up; captions can be added in Studio
                ctx.say(f"  WARN {key}: captions were refused ({str(exc)[:160]}); upload {it['captions']} in Studio "
                        f"(quota: captions.insert, {CAPTIONS_UNITS} units)")
            save(result_path, result)
        if it.get("playlist"):
            playlist_step(it, entry)
    complete = False
    if ctx.live:
        complete = all(result["items"].get(it["key"], {}).get("video_id") and in_playlist(it, result["items"][it["key"]])
                       for it in items)
        result["complete"] = complete
        save(result_path, result)
    table = summary_table(result, items, ctx.live)
    ctx.say(table)
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"## YouTube upload {tag} ({'live' if ctx.live else 'dry run'})\n\n{table}")
    if failures:
        return finish(1, complete)
    return finish(0 if complete or not ctx.live else 1, complete)


def main(argv: list[str] | None = None) -> int:
    import requests

    from .run import _with_timeout

    ap = argparse.ArgumentParser(description="Upload a staged video batch to YouTube as private (dry run unless --live)")
    ap.add_argument("--assets", type=Path, required=True, help="folder holding the downloaded release assets")
    ap.add_argument("--tag", required=True, help="tag of the draft release; must match manifest.json")
    ap.add_argument("--publish-at", help="move the batch so its earliest item goes public then (ISO 8601 with offset)")
    ap.add_argument("--live", action="store_true", help="really upload; without it nothing is called")
    ap.add_argument("--result", type=Path, help="result file (default: <assets>/result.json)")
    ap.add_argument("--summary", type=Path, help="append a markdown summary here (the job summary in Actions)")
    ap.add_argument("--github-output", type=Path, help="append complete=true|false here (step outputs in Actions)")
    args = ap.parse_args(argv)
    session = requests.Session()
    session.request = _with_timeout(session.request)
    ctx = Context(ROOT, load_config(ROOT), default_env(), session, dt.datetime.now(dt.timezone.utc), live=args.live)
    return run(ctx, args.assets, args.tag, args.publish_at, args.result, args.summary, args.github_output)


if __name__ == "__main__":
    sys.exit(main())
