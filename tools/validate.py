#!/usr/bin/env python3
"""Validate the calendar and every post folder under content/.

Usage:
    python tools/validate.py                # whole repo
    python tools/validate.py --check-links  # also require sources to answer HTTP 200
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
TEXT_SUFFIXES = {".md", ".mdx", ".yaml", ".yml", ".json", ".srt", ".txt", ".csv", ".py", ".ts", ".tsx", ".js", ".mjs", ".astro", ".html", ".css", ".sh"}
URL_RE = re.compile(r"https?://\S+")
PRIVATE_LINK_RE = re.compile(r"(?i)claude\.ai/")  # links to private chat sessions
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


def check_calendar(cal: dict, rep: Report, where: Path) -> dict[dt.date, dict]:
    """Validate calendar.yaml and return {date: item}."""
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
            by_date[d] = {**item, "week": name, "kind": kind,
                          "sources_required": bool(series[s].get("sources_required"))}
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


def check_repo_text(root: Path, rep: Report) -> None:
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


# ---------------------------------------------------------------- posts

def check_post(folder: Path, by_date: dict[dt.date, dict], rep: Report, check_links: bool = False) -> None:
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
    by_date = check_calendar(cal, rep, cal_path)
    for folder in post_folders(root, week):
        check_post(folder, by_date, rep, check_links)
    check_repo_text(root, rep)
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
