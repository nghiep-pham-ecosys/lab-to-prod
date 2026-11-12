#!/usr/bin/env python3
"""Draw image.png (1200x1200) for a post folder from the `card:` block of its post.md.

    uv run --with pillow --with pyyaml python render/image/render.py content/2026-W47/2026-11-16-dsa-p2
    ... render.py --week 2026-W47        # every post folder of a week
    ... render.py <folder> --theme ink   # override the theme

card:
  layout: code | stat | table
  theme: light            # optional; a theme of the selected brand option (a name from another
                          # option maps to the same role: light, dark or the accent third theme)
  headline: "Same value, different object"
  code: ["Integer a = 127;", "> c == d   // false"]      # layout code; "> " marks the highlighted line
  stat: {value: "0.62", label: "recall", note: "8 of 13 bad answers caught"}   # layout stat
  rows: [["VPN", "hours to set up"], ["Direct Connect", "weeks"]]              # layout table
  lesson: "Use equals() for objects."
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "brand"))
import build as brand  # noqa: E402

W = H = 1200
M = 88
SS = brand.SS


def load_post(folder: Path) -> dict:
    text = (folder / "post.md").read_text(encoding="utf-8")
    return yaml.safe_load(text.split("---\n", 2)[1]) or {}


def series_names() -> dict:
    cal = yaml.safe_load((ROOT / "content" / "calendar.yaml").read_text(encoding="utf-8"))
    return {k: v["name"] for k, v in cal["series"].items()}


def wrap(c, text, fnt, max_w):
    lines, cur = [], ""
    for word in str(text).split():
        trial = f"{cur} {word}".strip()
        if cur and c.width(trial, fnt) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + [cur] if cur else lines


def fit(c, text, font_name, weight, sizes, max_w, max_lines):
    """Largest size from `sizes` at which the text wraps into max_lines."""
    for size in sizes:
        fnt = brand.font(font_name, size * SS, weight)
        lines = wrap(c, text, fnt, max_w)
        if len(lines) <= max_lines and all(c.width(ln, fnt) <= max_w for ln in lines):
            return fnt, size, lines
    raise ValueError(f"text does not fit in {max_lines} lines even at {sizes[-1]}px: {text!r}")


def theme_role(opt: dict, name: str) -> str:
    """'light' or 'dark' for the option's two main themes, 'third' for its accent theme."""
    if name not in (opt["primary"], opt["alt"]):
        return "third"
    return "dark" if brand.is_dark(opt["themes"][name]) else "light"


def resolve_theme(opt: dict, name: str) -> str:
    """A theme of the selected option. A name from another option (a card written before the
    brand changed) maps to the theme with the same role, so switching `selected` needs no edits."""
    if name in opt["themes"]:
        return name
    for other in brand.CFG["options"].values():
        if name in other["themes"]:
            role = theme_role(other, name)
            return next(t for t in opt["themes"] if theme_role(opt, t) == role)
    raise ValueError(f"theme {name!r} is not one of {list(opt['themes'])}")


def render(folder: Path, theme_name: str | None = None) -> Path:
    meta = load_post(folder)
    card = meta.get("card")
    if not card:
        raise ValueError(f"{folder}/post.md has no card: block")
    key = brand.CFG["selected"]
    opt = brand.CFG["options"][key]
    theme_name = resolve_theme(opt, theme_name or card.get("theme") or opt["primary"])
    t, o = opt["themes"][theme_name], brand.OPT[key]
    inner = W - 2 * M

    c = brand.Canvas(W, H, t["bg"])
    brand.texture(c, key, t)
    c.rect([M - 24, M - 24, W - M + 24, H - M + 24], fill=t["bg"])

    kicker = f"{series_names().get(meta['series'], meta['series'])} · Part {meta['part']}".upper()
    c.text((M, M + 14), kicker, brand.font(o["mono"], 30 * SS, 600), t["accent"], anchor="lm", spacing=3)
    c.line([(M, M + 56), (W - M, M + 56)], t["line"], 2)

    footer_top = H - M - 70
    c.line([(M, footer_top), (W - M, footer_top)], t["line"], 2)
    c.text((M, H - M - 22), brand.NAME, brand.font(o["body"], 30 * SS, 500), t["muted"], anchor="lm")
    o["mark"](c, W - M - 44, H - M - 22, 110, t["fg"], t["accent"])

    lesson_lines, lesson_f, lesson_h = [], None, 0
    if card.get("lesson"):
        lesson_f, lsize, lesson_lines = fit(c, card["lesson"], o["body"], 500, [44, 40, 36], inner, 2)
        lesson_h = len(lesson_lines) * lsize * 1.3 + 30

    layout = card.get("layout", "code")
    weight = 600 if key == "a" else 700
    y = M + 96
    body_bottom = footer_top - 30 - lesson_h

    def headline(max_lines, sizes):
        nonlocal y
        fnt, size, lines = fit(c, card["headline"], o["display"], weight, sizes, inner, max_lines)
        y += size * 0.55
        for ln in lines:
            c.text((M, y), ln, fnt, t["fg"], anchor="lm")
            y += size * 1.16
        y += 26 - size * 0.55

    if layout == "code":
        lines = [str(x) for x in card["code"]]
        headline(3, [92, 80, 68, 58])
        plain = [ln[2:] if ln.startswith("> ") else ln for ln in lines]
        avail_h = body_bottom - y
        for size in (46, 42, 38, 34, 30, 27, 24):
            fnt = brand.font(o["mono"], size * SS, 500)
            lh = size * 1.52
            if max(c.width(ln, fnt) for ln in plain) <= inner - 80 and 72 + lh * len(lines) <= avail_h:
                break
        else:
            raise ValueError("code block does not fit; shorten lines or remove some")
        bh = 72 + lh * len(lines)
        c.rect([M, y, W - M, y + bh], fill=t["panel"], radius=18)
        cy = y + 36 + lh / 2
        for raw, ln in zip(lines, plain):
            c.text((M + 40, cy), ln, fnt, t["panel_accent"] if raw.startswith("> ") else t["panel_fg"], anchor="lm")
            cy += lh
        y += bh
    elif layout == "stat":
        stat = card["stat"]
        headline(2, [72, 64, 56])
        box_h = min(430, body_bottom - y)
        c.rect([M, y, W - M, y + box_h], fill=t["panel"], radius=18)
        vf, vsize, _ = fit(c, stat["value"], o["display"], weight, [230, 200, 170, 140, 110], inner - 100, 1)
        c.text((M + 50, y + box_h * 0.42), str(stat["value"]), vf, t["panel_accent"], anchor="lm")
        c.text((M + 54, y + box_h * 0.80), str(stat.get("label", "")).upper(), brand.font(o["mono"], 32 * SS, 600),
               t["panel_fg"], anchor="lm", spacing=3)
        y += box_h
        if stat.get("note"):
            nf, _, nl = fit(c, stat["note"], o["body"], 400, [36, 32], inner, 2)
            for ln in nl:
                y += 46
                c.text((M, y), ln, nf, t["muted"], anchor="lm")
    elif layout == "table":
        rows = card["rows"]
        headline(2, [80, 68, 58])
        label_f = brand.font(o["mono"], 30 * SS, 600)
        row_h = min(120, (body_bottom - y) / len(rows))
        if row_h < 70:
            raise ValueError("too many rows for the table layout")
        col = M + max(c.width(str(r[0]).upper(), label_f, 2) for r in rows) + 50
        for i, (label, value) in enumerate(rows):
            cy = y + row_h * (i + 0.5)
            if i:
                c.line([(M, y + row_h * i), (W - M, y + row_h * i)], t["line"], 2)
            c.text((M, cy), str(label).upper(), label_f, t["accent"], anchor="lm", spacing=2)
            vf, _, vl = fit(c, value, o["body"], 500, [40, 36, 32, 28], W - M - col, 2)
            off = -22 if len(vl) == 2 else 0
            for ln in vl:
                c.text((col, cy + off), ln, vf, t["fg"], anchor="lm")
                off += 46
        y += row_h * len(rows)
    else:
        raise ValueError(f"unknown card layout {layout!r}")

    if lesson_lines:
        ly = footer_top - lesson_h + 20
        for ln in lesson_lines:
            c.text((M, ly), ln, lesson_f, t["fg"], anchor="lm")
            ly += lesson_h / len(lesson_lines) - 6
    out = folder / "image.png"
    c.save(out)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Render image.png for post folders")
    ap.add_argument("folders", nargs="*", type=Path)
    ap.add_argument("--week", help="render every post folder of content/<week>/")
    ap.add_argument("--theme")
    args = ap.parse_args(argv)
    folders = list(args.folders)
    if args.week:
        folders += sorted(p for p in (ROOT / "content" / args.week).iterdir() if p.is_dir())
    if not folders:
        ap.error("give at least one post folder or --week")
    for folder in folders:
        print(render(folder.resolve(), args.theme).relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
