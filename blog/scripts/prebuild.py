#!/usr/bin/env python3
"""Generate what the Astro build needs but git does not hold.

    uv run --with pillow --with pyyaml python blog/scripts/prebuild.py

- public/og/default.png and public/og/posts/<id>.png: 1200x630 Open Graph images in the brand theme
- public/notes/<id>.png: the image of each post folder, so notes can show it
- public/favicon.png: the brand avatar, small
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import yaml
from PIL import Image

BLOG = Path(__file__).resolve().parents[1]
ROOT = BLOG.parent
sys.path.insert(0, str(ROOT / "brand"))
import build as brand  # noqa: E402

CFG = brand.CFG
KEY = CFG["selected"]
OPT = CFG["options"][KEY]
THEME = OPT["themes"][OPT["primary"]]
SERIES = yaml.safe_load((ROOT / "content" / "calendar.yaml").read_text(encoding="utf-8"))["series"]


def wrap(c: brand.Canvas, text: str, fnt, max_w: float) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and c.width(trial, fnt) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + [cur] if cur else lines


def og_image(path: Path, kicker: str, title: str) -> None:
    o, t = brand.OPT[KEY], THEME
    c = brand.Canvas(1200, 630, t["bg"])
    brand.texture(c, KEY, t)
    m = 72
    c.rect([m - 24, m - 24, 1200 - m + 24, 630 - m + 24], fill=t["bg"])
    c.text((m, m + 10), kicker.upper(), brand.font(o["mono"], 26 * brand.SS, 600), t["accent"], anchor="lm", spacing=3)
    size = 76
    while True:
        fnt = brand.font(o["display"], size * brand.SS, 620)
        lines = wrap(c, title, fnt, 1200 - 2 * m)
        if len(lines) <= 4 or size <= 44:
            break
        size -= 6
    y = m + 100 + size * 0.4
    for line in lines[:4]:
        c.text((m, y), line, fnt, t["fg"], anchor="lm")
        y += size * 1.14
    c.line([(m, 630 - m - 62), (1200 - m, 630 - m - 62)], t["line"], 2)
    c.text((m, 630 - m - 18), CFG["name"], brand.font(o["body"], 28 * brand.SS, 500), t["muted"], anchor="lm")
    o["mark"](c, 1200 - m - 44, 630 - m - 18, 104, t["fg"], t["accent"])
    c.save(path)


def front_matter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text.split("---\n", 2)[1]) or {}


def main() -> None:
    pub = BLOG / "public"
    og_image(pub / "og" / "default.png", "Notes from a chemist turned AI engineer", "AI engineering, ML and climate")
    n_posts = 0
    for md in sorted((BLOG / "src" / "content" / "posts").glob("*.md")):
        meta = front_matter(md)
        kicker = SERIES.get(meta.get("series"), {}).get("name", "Article")
        og_image(pub / "og" / "posts" / f"{md.stem}.png", kicker, meta["title"])
        n_posts += 1
    n_notes = 0
    (pub / "notes").mkdir(parents=True, exist_ok=True)
    for image in sorted((ROOT / "content").glob("[0-9]*-W[0-9]*/*/image.png")):
        shutil.copyfile(image, pub / "notes" / f"{image.parent.name}.png")
        n_notes += 1
    Image.open(ROOT / "brand" / f"option-{KEY}" / "avatar.png").resize((96, 96), Image.LANCZOS).save(pub / "favicon.png")
    print(f"prebuild: {n_posts} article image(s), {n_notes} note image(s), default image and favicon")


if __name__ == "__main__":
    main()
