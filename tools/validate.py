#!/usr/bin/env python3
"""Validate the calendar, the work ledger and every post folder under content/.

Usage:
    python tools/validate.py                # whole repo
    python tools/validate.py --check-links  # also require sources and work-ledger PRs to answer HTTP 200
    python tools/validate.py --week 2026-W47

Exit code 1 when there is at least one error. Warnings never fail the run.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
import struct
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_META = ["date", "series", "part", "title", "channels", "short_publish_at", "sources", "status", "image_alt"]
STATUSES = {"draft", "approved", "published"}
# channel name in front matter -> section heading in post.md
CHANNEL_SECTION = {
    "linkedin": "linkedin",
    "facebook": "facebook",
    "telegram": "telegram",
    "x_manual": "x",
    "youtube": "youtube",
}
X_LIMIT = 280
LINKEDIN_LIMIT = 3000
TELEGRAM_CAPTION_LIMIT = 1024  # Bot API sendPhoto caption
YOUTUBE_TITLE_LIMIT = 100
IMAGE_SIZE = (1200, 1200)
SHORT_SIZE = (1080, 1920)
SHORT_SECONDS = (30.0, 60.0)
TEXT_SUFFIXES = {".md", ".mdx", ".yaml", ".yml", ".json", ".srt", ".txt", ".csv", ".py", ".ts", ".tsx", ".js", ".mjs", ".astro", ".html", ".css", ".sh", ".java", ".expected", ".ipynb"}
URL_RE = re.compile(r"https?://\S+")
PRIVATE_LINK_RE = re.compile(r"(?i)claude\.ai/")  # links to private chat sessions
# From this ISO week on, every calendar item and post points to merged work in content/work.yaml.
WORK_FROM_WEEK = "2026-W48"
ORG = "nghiep-pham-ecosys"
WORK_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PRIVATE_REF_RE = re.compile(r"^private@[0-9a-f]{7,40}$")
LOCAL_TZ = dt.timezone(dt.timedelta(hours=7))  # Asia/Ho_Chi_Minh, no DST
SECRET_PATTERNS = [
    ("GitHub token", re.compile(r"\bgh[opsur]_[A-Za-z0-9]{30,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}")),
    ("Google OAuth refresh token", re.compile(r"\b1//[0-9A-Za-z_-]{40,}")),
    ("Meta access token", re.compile(r"\bEAA[A-Za-z0-9]{40,}")),
    ("Telegram bot token", re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b")),
    ("LinkedIn access token", re.compile(r"\bAQ[A-Za-z0-9_-]{120,}")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, where: Path | str, msg: str) -> None:
        self.errors.append(f"{_rel(where)}: {msg}")

    def warn(self, where: Path | str, msg: str) -> None:
        self.warnings.append(f"{_rel(where)}: {msg}")

    @property
    def ok(self) -> bool:
        return not self.errors


def _rel(p: Path | str) -> str:
    if isinstance(p, Path):
        for base in (ROOT, Path.cwd()):
            try:
                return str(p.resolve().relative_to(base.resolve()))
            except ValueError:
                continue
    return str(p)


# ---------------------------------------------------------------- parsing

def parse_post(path: Path) -> tuple[dict, dict[str, str]]:
    """Return (front matter, {section name: body}) for a post.md file."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("missing front matter (file must start with ---)")
    try:
        _, fm, body = text.split("---\n", 2)
    except ValueError as exc:
        raise ValueError("front matter is not closed with ---") from exc
    meta = yaml.safe_load(fm) or {}
    if not isinstance(meta, dict):
        raise ValueError("front matter is not a mapping")
    sections: dict[str, str] = {}
    current = None
    buf: list[str] = []
    for line in body.splitlines():
        m = re.match(r"^## +([a-z_]+)\s*$", line)
        if m:
            if current:
                sections[current] = "\n".join(buf).strip()
            current, buf = m.group(1), []
        elif current is not None:
            buf.append(line)
    if current:
        sections[current] = "\n".join(buf).strip()
    return meta, sections


def split_x_posts(section: str) -> list[str]:
    """The x section holds one post, or several separated by a line of ---."""
    return [p.strip() for p in re.split(r"(?m)^---\s*$", section) if p.strip()]


def x_length(text: str) -> int:
    """Weighted length as X counts it: most CJK and emoji code points count as 2."""
    total = 0
    for ch in text:
        cp = ord(ch)
        light = cp <= 0x10FF or 0x2000 <= cp <= 0x200D or 0x2010 <= cp <= 0x201F or 0x2032 <= cp <= 0x2037
        total += 1 if light else 2
    return total


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'’-]+\b", text))


def mp4_info(path: Path) -> tuple[int, int, float] | None:
    """Return (width, height, seconds) read from the mp4 boxes, or None."""
    data = path.read_bytes()
    duration = None
    size = None

    def walk(start: int, end: int) -> None:
        nonlocal duration, size
        pos = start
        while pos + 8 <= end:
            length, kind = struct.unpack(">I4s", data[pos:pos + 8])
            header = 8
            if length == 1:
                length = struct.unpack(">Q", data[pos + 8:pos + 16])[0]
                header = 16
            elif length == 0:
                length = end - pos
            if length < header:
                return
            body = pos + header
            if kind in (b"moov", b"trak"):
                walk(body, pos + length)
            elif kind == b"mvhd":
                version = data[body]
                if version == 1:
                    timescale, dur = struct.unpack(">IQ", data[body + 20:body + 32])
                else:
                    timescale, dur = struct.unpack(">II", data[body + 12:body + 20])
                if timescale:
                    duration = dur / timescale
            elif kind == b"tkhd":
                w, h = struct.unpack(">II", data[pos + length - 8:pos + length])
                w, h = w >> 16, h >> 16
                if w and h:
                    size = (w, h)
            pos += length

    walk(0, len(data))
    if size is None or duration is None:
        return None
    return size[0], size[1], duration


# ---------------------------------------------------------------- calendar

def load_calendar(root: Path) -> dict:
    return yaml.safe_load((root / "content" / "calendar.yaml").read_text(encoding="utf-8"))


def iso_week(d: dt.date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def needs_work(d: dt.date) -> bool:
    return iso_week(d) >= WORK_FROM_WEEK


def work_ids(value) -> list[str] | None:
    """`work:` holds one ledger id or a list of ids. None when absent or malformed."""
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if isinstance(value, list) and value and all(isinstance(v, str) and v.strip() for v in value):
        return [v.strip() for v in value]
    return None


def check_work_refs(value, d: dt.date, ledger: dict[str, dict], rep: Report, where: Path | str,
                    what: str) -> list[str]:
    """Check the `work:` of one calendar item or post and return its ids."""
    ids = work_ids(value)
    if ids is None:
        if value is not None:
            rep.error(where, f"{what}: work must be a ledger id or a list of ids")
        elif needs_work(d):
            rep.error(where, f"{what}: from {WORK_FROM_WEEK} every item needs work: <id> from content/work.yaml")
        return []
    for wid in ids:
        entry = ledger.get(wid)
        if entry is None:
            rep.error(where, f"{what}: work {wid!r} is not in content/work.yaml")
        elif isinstance(entry.get("merged"), dt.date) and entry["merged"] > d:
            rep.error(where, f"{what}: work {wid!r} was merged on {entry['merged']}, after {d}")
    return ids


def check_calendar(cal: dict, rep: Report, where: Path,
                   ledger: dict[str, dict] | None = None) -> dict[dt.date, dict]:
    """Validate calendar.yaml (with the work ledger {id: entry}) and return {date: item}."""
    ledger = ledger or {}
    series = cal.get("series") or {}
    pillars = cal.get("pillars") or {}
    by_date: dict[dt.date, dict] = {}
    seen_parts: set[tuple[str, int]] = set()
    counts: dict[str, int] = {p: 0 for p in pillars}
    for week in cal.get("weeks") or []:
        name = week.get("week")
        for item in week.get("items") or []:
            d = item.get("date")
            if not isinstance(d, dt.date):
                rep.error(where, f"{name}: item date {d!r} is not a date")
                continue
            if iso_week(d) != name:
                rep.error(where, f"{d} is listed under {name} but belongs to {iso_week(d)}")
            if d in by_date:
                rep.error(where, f"{d} appears twice")
            s = item.get("series")
            if s not in series:
                rep.error(where, f"{d}: unknown series {s!r}")
                continue
            part = item.get("part")
            if not isinstance(part, int) or part < 1:
                rep.error(where, f"{d}: part must be a positive integer")
            if (s, part) in seen_parts:
                rep.error(where, f"{d}: {s} part {part} appears twice")
            seen_parts.add((s, part))
            if not item.get("slug") or not item.get("topic"):
                rep.error(where, f"{d}: slug and topic are required")
            kind = series[s].get("kind")
            if kind == "post" and d.weekday() > 4:
                rep.error(where, f"{d}: a {s} post must fall on a weekday")
            if kind == "blog" and d.weekday() != 5:
                rep.error(where, f"{d}: a blog article must fall on a Saturday")
            pillar = item.get("pillar") or series[s].get("pillar")
            if pillar not in pillars:
                rep.error(where, f"{d}: unknown pillar {pillar!r}")
            else:
                counts[pillar] += 1
            short = item.get("short")
            if short:
                try:
                    at = dt.datetime.fromisoformat(str(short.get("publish_at")))
                    if at.tzinfo is None:
                        raise ValueError("no UTC offset")
                    if at.date() < d:
                        rep.error(where, f"{d}: short publish_at is before the post date")
                except ValueError as exc:
                    rep.error(where, f"{d}: short.publish_at is not an ISO datetime with offset ({exc})")
            ids = check_work_refs(item.get("work"), d, ledger, rep, where, str(d))
            by_date[d] = {**item, "week": name, "kind": kind, "work": ids,
                          "sources_required": bool(series[s].get("sources_required"))}
    for i, item in enumerate(cal.get("parked") or [], 1):
        if not isinstance(item, dict) or item.get("series") not in series or not item.get("topic"):
            rep.error(where, f"parked item {i}: needs a known series and a topic")
        elif "date" in item:
            rep.error(where, f"parked item {i}: a parked item has no date; move it into a week to plan it")
    total = sum(counts.values())
    if total:
        for p, n in counts.items():
            share, target = n / total, float(pillars[p].get("target", 0))
            if abs(share - target) > 0.10:
                rep.warn(where, f"pillar {p} is {share:.0%} of the calendar, target {target:.0%}")
    return by_date


def pillar_shares(cal: dict) -> dict[str, float]:
    series = cal.get("series") or {}
    counts: dict[str, int] = {}
    for week in cal.get("weeks") or []:
        for item in week.get("items") or []:
            p = item.get("pillar") or series.get(item.get("series"), {}).get("pillar")
            counts[p] = counts.get(p, 0) + 1
    total = sum(counts.values()) or 1
    return {p: n / total for p, n in counts.items()}


# ---------------------------------------------------------------- work ledger

def load_work(root: Path) -> dict:
    path = root / "content" / "work.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def check_work(work: dict, rep: Report, where: Path, today: dt.date | None = None) -> dict[str, dict]:
    """Validate content/work.yaml and return {id: entry}.

    Error messages never echo a repo name that is not listed: an unlisted repo must stay unnamed,
    and CI logs of this repository are public.
    """
    today = today or dt.datetime.now(LOCAL_TZ).date()
    repos = work.get("repos") or {}
    public, private = set(repos.get("public") or []), set(repos.get("private") or [])
    if public & private:
        rep.error(where, "a repo is listed as both public and private")
    out: dict[str, dict] = {}
    for i, entry in enumerate(work.get("entries") or [], 1):
        if not isinstance(entry, dict):
            rep.error(where, f"entry {i} is not a mapping")
            continue
        wid = entry.get("id")
        label = f"entry {wid!r}" if isinstance(wid, str) else f"entry {i}"
        if not isinstance(wid, str) or not WORK_ID_RE.match(wid):
            rep.error(where, f"{label}: id must be lowercase words joined by hyphens")
            continue
        if wid in out:
            rep.error(where, f"{label}: id appears twice")
        out[wid] = entry
        repo, ref = entry.get("repo"), str(entry.get("ref") or "")
        if repo in public:
            # A commit URL is for changes with no pull request in the repo, such as work merged
            # before a private repo went public with rewritten history.
            base = rf"https://github\.com/{ORG}/{re.escape(repo)}"
            if not re.fullmatch(rf"{base}/(?:pull/\d+|commit/[0-9a-f]{{7,40}})", ref):
                rep.error(where, f"{label}: ref must be the merged pull request URL "
                                 f"(or a commit URL when there is no pull request) in {ORG}/{repo}")
        elif repo in private:
            if not PRIVATE_REF_RE.match(ref):
                rep.error(where, f"{label}: ref of a private repo must be private@<commit sha>")
            if URL_RE.search(yaml.safe_dump(entry)):
                rep.error(where, f"{label}: a private repo is named, never linked")
        else:
            rep.error(where, f"{label}: repo is not listed under repos; an unlisted repo is never a post source")
        merged = entry.get("merged")
        if not isinstance(merged, dt.date):
            rep.error(where, f"{label}: merged must be a date YYYY-MM-DD")
        elif merged > today:
            rep.error(where, f"{label}: merged {merged} is in the future")
        if not str(entry.get("what") or "").strip():
            rep.error(where, f"{label}: what is empty")
    return out


def private_link_re(work: dict) -> re.Pattern | None:
    """Links to the private repos of the ledger: they are named in posts, never linked."""
    names = (work.get("repos") or {}).get("private") or []
    if not names:
        return None
    alt = "|".join(re.escape(n) for n in names)
    return re.compile(rf"(?i)github\.com/{ORG}/(?:{alt})(?![\w.-])")


# ---------------------------------------------------------------- banned terms and secrets

def load_banned(root: Path) -> tuple[list[re.Pattern], set[str]]:
    """Public hashed terms, plus plain-text patterns from the git-ignored local file if present."""
    patterns: list[re.Pattern] = [PRIVATE_LINK_RE]
    hashes: set[str] = set()
    for name in ("banned_terms.yaml", "banned_terms.local.yaml"):
        path = root / "tools" / name
        if not path.exists():
            continue
        cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        patterns += [re.compile(p) for p in cfg.get("patterns") or []]
        hashes |= set(cfg.get("token_sha256") or [])
    return patterns, hashes


def find_banned(text: str, patterns: list[re.Pattern], hashes: set[str]) -> list[str]:
    hits = [m.group(0) for p in patterns for m in p.finditer(text)]
    if hashes:
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        candidates = set(tokens) | {f"{a} {b}" for a, b in zip(tokens, tokens[1:])}
        for cand in candidates:
            if hashlib.sha256(cand.encode()).hexdigest() in hashes:
                hits.append(cand)
    return hits


def find_secrets(text: str) -> list[str]:
    return [name for name, pat in SECRET_PATTERNS if pat.search(text)]


def published_dirs(root: Path) -> list[Path]:
    """Folders whose text ends up in public posts."""
    return [p for p in (root / "content", root / "blog" / "src" / "content", root / "reports") if p.exists()]


def tracked_files(root: Path) -> list[Path]:
    try:
        out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=root,
                             capture_output=True, text=True, check=True).stdout
        return [root / line for line in out.splitlines() if line]
    except (OSError, subprocess.CalledProcessError):
        return [p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts and "node_modules" not in p.parts]


def check_repo_text(root: Path, rep: Report, private_links: re.Pattern | None = None) -> None:
    patterns, hashes = load_banned(root)
    pub = published_dirs(root)
    for path in tracked_files(root):
        if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if path.name != "validate.py" and "tests" not in path.parts:
            for name in find_secrets(text):
                rep.error(path, f"looks like a committed secret ({name})")
        if any(base in path.parents for base in pub):
            hits = find_banned(text, patterns, hashes)
            if hits:
                rep.error(path, "banned term: " + ", ".join(sorted(set(hits))))
            if private_links and private_links.search(text):
                rep.error(path, "links a private repo; private repos are named, never linked")


# ---------------------------------------------------------------- posts

def check_post(folder: Path, by_date: dict[dt.date, dict], rep: Report, check_links: bool = False,
               ledger: dict[str, dict] | None = None) -> None:
    post = folder / "post.md"
    if not post.exists():
        rep.error(folder, "post.md is missing")
        return
    try:
        meta, sections = parse_post(post)
    except (ValueError, yaml.YAMLError) as exc:
        rep.error(post, str(exc))
        return

    for key in REQUIRED_META:
        if key not in meta:
            rep.error(post, f"front matter key {key!r} is missing")
    status = meta.get("status")
    if status not in STATUSES:
        rep.error(post, f"status must be one of {sorted(STATUSES)}")
    final = status in {"approved", "published"}
    need = rep.error if final else rep.warn

    d = meta.get("date")
    if not isinstance(d, dt.date):
        rep.error(post, "date must be YYYY-MM-DD")
        return
    item = by_date.get(d)
    ids = check_work_refs(meta.get("work"), d, ledger or {}, rep, post, "post")
    if item is not None and (ids or item.get("work")) and set(ids) != set(item.get("work") or []):
        rep.error(post, f"work is {ids} but the calendar says {item.get('work')}")
    if item is None:
        rep.error(post, f"{d} is not in content/calendar.yaml")
    else:
        if item["kind"] != "post":
            rep.error(post, f"{d} is a blog day in the calendar; long articles live in blog/")
        for key in ("series", "part"):
            if meta.get(key) != item.get(key):
                rep.error(post, f"{key} is {meta.get(key)!r} but the calendar says {item.get(key)!r}")
        expected = f"{d.isoformat()}-{item['slug']}"
        if folder.name != expected:
            rep.error(folder, f"folder should be named {expected}")
        if folder.parent.name != item["week"]:
            rep.error(folder, f"folder should be under content/{item['week']}/")
        cal_short = (item.get("short") or {}).get("publish_at")
        if cal_short and final and "youtube" not in (meta.get("channels") or []):
            rep.error(post, "the calendar plans a Short for this post but youtube is not in channels")

    channels = meta.get("channels") or []
    if not isinstance(channels, list) or not channels:
        rep.error(post, "channels must be a non-empty list")
        channels = []
    for ch in channels:
        if ch not in CHANNEL_SECTION:
            rep.error(post, f"unknown channel {ch!r}")
        elif not sections.get(CHANNEL_SECTION[ch]):
            rep.error(post, f"section '## {CHANNEL_SECTION[ch]}' is missing or empty")

    part = meta.get("part")
    if "linkedin" in sections:
        text = sections["linkedin"]
        if len(text) > LINKEDIN_LIMIT:
            rep.error(post, f"linkedin is {len(text)} characters, limit {LINKEDIN_LIMIT}")
        if URL_RE.search(text):
            rep.error(post, "linkedin body contains a link; links go in the first comment")
        n = word_count(text)
        if not 180 <= n <= 280:
            rep.warn(post, f"linkedin is {n} words, target 180-280")
        tags = len(re.findall(r"(?<!\w)#\w+", text))
        if not 3 <= tags <= 5:
            rep.warn(post, f"linkedin has {tags} hashtags, target 3-5")
        if not re.search(rf"Part {part} of my .+ notes", text):
            rep.warn(post, f"linkedin does not end with 'Part {part} of my ... notes'")
    if "x" in sections:
        posts = split_x_posts(sections["x"])
        if len(posts) > 1:
            rep.warn(post, f"x has {len(posts)} posts; x.com can only schedule single posts")
        for i, p in enumerate(posts, 1):
            if x_length(p) > X_LIMIT:
                rep.error(post, f"x post {i} is {x_length(p)} characters, limit {X_LIMIT}")
            if URL_RE.search(p):
                rep.error(post, f"x post {i} contains a link; links go in the first reply")
    if "facebook" in sections:
        n = word_count(sections["facebook"])
        if not 80 <= n <= 120:
            rep.warn(post, f"facebook is {n} words, target 80-120")
    if "telegram" in sections and len(sections["telegram"]) > TELEGRAM_CAPTION_LIMIT:
        rep.error(post, f"telegram is {len(sections['telegram'])} characters, photo caption limit {TELEGRAM_CAPTION_LIMIT}")

    if not str(meta.get("image_alt") or "").strip():
        need(post, "image_alt is empty; every image needs alt text")
    image = folder / "image.png"
    if not image.exists():
        need(folder, "image.png is missing")
    else:
        from PIL import Image
        with Image.open(image) as im:
            if im.size != IMAGE_SIZE:
                rep.error(image, f"image is {im.size[0]}x{im.size[1]}, expected {IMAGE_SIZE[0]}x{IMAGE_SIZE[1]}")

    if "youtube" in channels:
        lines = [ln for ln in sections.get("youtube", "").splitlines() if ln.strip()]
        title = lines[0].strip() if lines else ""
        if title:
            if "#Shorts" not in title:
                rep.error(post, "youtube title (first line of the section) must contain #Shorts")
            if len(title) > YOUTUBE_TITLE_LIMIT:
                rep.error(post, f"youtube title is {len(title)} characters, limit {YOUTUBE_TITLE_LIMIT}")
        at = meta.get("short_publish_at")
        try:
            parsed = at if isinstance(at, dt.datetime) else dt.datetime.fromisoformat(str(at))
            if parsed.tzinfo is None:
                raise ValueError
            cal_short = ((item or {}).get("short") or {}).get("publish_at")
            if cal_short and parsed != dt.datetime.fromisoformat(cal_short):
                rep.error(post, f"short_publish_at is {at} but the calendar says {cal_short}")
        except (TypeError, ValueError):
            rep.error(post, "short_publish_at must be an ISO datetime with UTC offset when youtube is a channel")
        video, srt = folder / "short.mp4", folder / "short.srt"
        if not srt.exists():
            need(folder, "short.srt is missing; every video needs subtitles")
        if not video.exists():
            need(folder, "short.mp4 is missing")
        else:
            info = mp4_info(video)
            if info is None:
                rep.error(video, "cannot read size and duration from the mp4")
            else:
                w, h, secs = info
                if (w, h) != SHORT_SIZE:
                    rep.error(video, f"video is {w}x{h}, expected {SHORT_SIZE[0]}x{SHORT_SIZE[1]}")
                if not SHORT_SECONDS[0] <= secs <= SHORT_SECONDS[1]:
                    rep.error(video, f"video is {secs:.1f}s, expected {SHORT_SECONDS[0]:.0f}-{SHORT_SECONDS[1]:.0f}s")
    elif meta.get("short_publish_at"):
        rep.error(post, "short_publish_at is set but youtube is not in channels")

    sources = meta.get("sources") or []
    if not isinstance(sources, list) or any(not re.match(r"https?://", str(s)) for s in sources):
        rep.error(post, "sources must be a list of http(s) links")
        sources = []
    if item and item["sources_required"] and not sources:
        need(post, f"series {meta.get('series')} needs at least one source link")
    if check_links:
        for url in sources:
            code = http_status(url)
            if code != 200:
                rep.error(post, f"source {url} answered {code}, expected 200")


def check_article(path: Path, by_date: dict[dt.date, dict], rep: Report, ledger: dict[str, dict]) -> None:
    """A Saturday article from WORK_FROM_WEEK on carries the work of its calendar item."""
    try:
        meta, _ = parse_post(path)
    except (ValueError, yaml.YAMLError) as exc:
        rep.error(path, str(exc))
        return
    d = meta.get("date")
    if isinstance(d, dt.datetime):
        d = d.date()
    if not isinstance(d, dt.date):
        return  # the blog build checks its own front matter
    ids = check_work_refs(meta.get("work"), d, ledger, rep, path, "article")
    item = by_date.get(d)
    if item is not None and item.get("kind") == "blog" and (ids or item.get("work")) \
            and set(ids) != set(item.get("work") or []):
        rep.error(path, f"work is {ids} but the calendar says {item.get('work')}")


def article_files(root: Path, week: str | None = None) -> list[Path]:
    out = []
    for path in sorted((root / "blog" / "src" / "content" / "posts").glob("*.md")):
        if week:
            m = re.search(r"(?m)^date:\s*(\d{4}-\d{2}-\d{2})", path.read_text(encoding="utf-8"))
            if not m or iso_week(dt.date.fromisoformat(m.group(1))) != week:
                continue
        out.append(path)
    return out


def http_status(url: str, timeout: float = 20.0) -> int | str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (link check)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception as exc:  # noqa: BLE001 - any network failure is a failed check
        return type(exc).__name__


def post_folders(root: Path, week: str | None = None) -> list[Path]:
    out = []
    for wk in sorted((root / "content").glob("[0-9][0-9][0-9][0-9]-W[0-9][0-9]")):
        if week and wk.name != week:
            continue
        out += [p for p in sorted(wk.iterdir()) if p.is_dir()]
    return out


def validate(root: Path = ROOT, week: str | None = None, check_links: bool = False) -> Report:
    rep = Report()
    cal_path = root / "content" / "calendar.yaml"
    try:
        cal = load_calendar(root)
    except (OSError, yaml.YAMLError) as exc:
        rep.error(cal_path, f"cannot read calendar: {exc}")
        return rep
    work_path = root / "content" / "work.yaml"
    try:
        work = load_work(root)
    except (OSError, yaml.YAMLError) as exc:
        rep.error(work_path, f"cannot read the work ledger: {exc}")
        work = {}
    ledger = check_work(work, rep, work_path)
    if check_links:
        for wid, entry in ledger.items():
            ref = str(entry.get("ref") or "")
            if ref.startswith("https://"):
                code = http_status(ref)
                if code != 200:
                    rep.error(work_path, f"entry {wid!r}: {ref} answered {code}, expected 200")
    by_date = check_calendar(cal, rep, cal_path, ledger)
    for folder in post_folders(root, week):
        check_post(folder, by_date, rep, check_links, ledger)
    for article in article_files(root, week):
        check_article(article, by_date, rep, ledger)
    check_repo_text(root, rep, private_link_re(work))
    return rep


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--week", help="only check post folders of this ISO week, e.g. 2026-W47")
    ap.add_argument("--check-links", action="store_true", help="require every source link to answer HTTP 200")
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args(argv)
    rep = validate(args.root, args.week, args.check_links)
    for w in rep.warnings:
        print(f"warning: {w}")
    for e in rep.errors:
        print(f"ERROR: {e}")
    n = len(post_folders(args.root, args.week))
    print(f"{n} post folder(s) checked, {len(rep.errors)} error(s), {len(rep.warnings)} warning(s)")
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())
