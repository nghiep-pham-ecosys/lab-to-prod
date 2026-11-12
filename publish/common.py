"""Shared pieces for the publishers: posts, state, configuration, HTTP."""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import validate as v  # noqa: E402

CHANNEL_SECTION = v.CHANNEL_SECTION


class PublishError(Exception):
    """A channel failed. The message is safe to print: it never contains a token."""


class Skip(Exception):
    """Nothing to do for this item on this channel right now (not a failure)."""


@dataclass
class Post:
    folder: Path
    meta: dict
    sections: dict

    @property
    def date(self) -> dt.date:
        return self.meta["date"]

    @property
    def key(self) -> str:
        return self.date.isoformat()

    @property
    def image(self) -> Path:
        return self.folder / "image.png"

    def text(self, channel: str) -> str:
        return self.sections.get(CHANNEL_SECTION.get(channel, channel), "").strip()

    def url(self, cfg: dict) -> str:
        return f"{cfg['site_url']}/notes/{self.folder.name}/"


@dataclass
class Article:
    path: Path
    meta: dict
    body: str

    @property
    def date(self) -> dt.date:
        return self.meta["date"]

    @property
    def key(self) -> str:
        return f"article:{self.path.stem}"

    def url(self, cfg: dict) -> str:
        return f"{cfg['site_url']}/posts/{self.path.stem}/"


@dataclass
class Context:
    root: Path
    cfg: dict
    env: dict
    http: object
    now: dt.datetime
    live: bool = False
    log: list = field(default_factory=list)

    def secret(self, name: str) -> str:
        value = self.env.get(name, "").strip()
        if not value:
            raise PublishError(f"secret {name} is not set")
        return value

    def say(self, msg: str) -> None:
        self.log.append(msg)
        print(msg)

    @property
    def tz(self) -> dt.timezone:
        sign = 1 if self.cfg["timezone_offset"][0] == "+" else -1
        hh, mm = self.cfg["timezone_offset"][1:].split(":")
        return dt.timezone(sign * dt.timedelta(hours=int(hh), minutes=int(mm)))

    def post_time(self, day: dt.date) -> dt.datetime:
        hh, mm = self.cfg["post_time"].split(":")
        return dt.datetime(day.year, day.month, day.day, int(hh), int(mm), tzinfo=self.tz)


def load_config(root: Path = ROOT) -> dict:
    return yaml.safe_load((root / "publish" / "config.yaml").read_text(encoding="utf-8"))


def load_posts(root: Path = ROOT) -> list[Post]:
    posts = []
    for folder in v.post_folders(root):
        if (folder / "post.md").exists():
            meta, sections = v.parse_post(folder / "post.md")
            posts.append(Post(folder, meta, sections))
    return posts


def load_articles(root: Path = ROOT) -> list[Article]:
    out = []
    for path in sorted((root / "blog" / "src" / "content" / "posts").glob("*.md")):
        _, fm, body = path.read_text(encoding="utf-8").split("---\n", 2)
        meta = yaml.safe_load(fm) or {}
        if not meta.get("draft"):
            out.append(Article(path, meta, body.strip()))
    return out


def paused(root: Path = ROOT) -> bool:
    return (root / "PAUSE").exists()


class State:
    """published.json: {item key: {channel: {id, url, at, ...}}}. The idempotency record."""

    def __init__(self, root: Path = ROOT):
        self.path = root / "published.json"
        self.data: dict = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.dirty = False

    def done(self, key: str, channel: str) -> bool:
        return channel in self.data.get(key, {})

    def record(self, key: str, channel: str, result: dict, now: dt.datetime) -> None:
        self.data.setdefault(key, {})[channel] = {**result, "at": now.astimezone(dt.timezone.utc).isoformat(timespec="seconds")}
        self.dirty = True

    def save(self) -> None:
        if self.dirty:
            self.path.write_text(json.dumps(self.data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
            self.dirty = False


def check(resp, what: str, ok=(200, 201)):
    """Raise PublishError with the platform's own message when a call fails."""
    if resp.status_code not in ok:
        body = (resp.text or "")[:300].replace("\n", " ")
        raise PublishError(f"{what} failed: HTTP {resp.status_code} {body}")
    return resp


def jpeg_bytes(image: Path, max_bytes: int = 4_000_000) -> bytes:
    """Post images as JPEG: Facebook caps PNG uploads at 1 MB and other formats at 4 MB."""
    from PIL import Image
    with Image.open(image) as im:
        rgb = im.convert("RGB")
        for quality in (92, 85, 75):
            buf = io.BytesIO()
            rgb.save(buf, "JPEG", quality=quality, optimize=True)
            if buf.tell() <= max_bytes:
                return buf.getvalue()
    raise PublishError(f"{image.name} cannot be compressed under {max_bytes} bytes")


def default_env() -> dict:
    return dict(os.environ)
