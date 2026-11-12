#!/usr/bin/env python3
"""Build every brand asset from brand.yaml.

    uv run --with pillow --with pyyaml python brand/build.py

Writes brand/option-a/ and brand/option-b/: logo, avatar, channel banners, one sample card per
image theme and a preview sheet. Nothing here is drawn by hand, so a palette change is one edit.
"""
from __future__ import annotations

import math
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
CFG = yaml.safe_load((HERE / "brand.yaml").read_text(encoding="utf-8"))
SS = 2  # supersampling factor: draw big, downscale for smooth edges

NAME = CFG["name"]
TAGLINE = CFG["tagline"]


def font(name: str, size: float, weight: int = 400) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(HERE / "fonts" / f"{name}.ttf"), int(size))
    axes = f.get_variation_axes()
    values = []
    for a in axes:
        label = a["name"].decode() if isinstance(a["name"], bytes) else a["name"]
        if label.lower().startswith("weight"):
            values.append(max(a["minimum"], min(a["maximum"], weight)))
        elif label.lower().startswith("optical"):
            values.append(max(a["minimum"], min(a["maximum"], size / SS)))
        else:
            values.append(a["default"] if "default" in a else a["minimum"])
    f.set_variation_by_axes(values)
    return f


class Canvas:
    """A supersampled RGBA canvas with a few drawing helpers. Coordinates are final pixels."""

    def __init__(self, w: int, h: int, bg: str | None):
        self.w, self.h = w, h
        self.im = Image.new("RGBA", (w * SS, h * SS), bg or (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def text(self, xy, s, fnt, fill, anchor="la", spacing=0.0):
        x, y = xy
        if spacing:
            for ch in s:
                self.d.text((x * SS, y * SS), ch, font=fnt, fill=fill, anchor=anchor)
                x += fnt.getlength(ch) / SS + spacing
            return x
        self.d.text((x * SS, y * SS), s, font=fnt, fill=fill, anchor=anchor)
        return x + fnt.getlength(s) / SS

    def width(self, s, fnt, spacing=0.0):
        return fnt.getlength(s) / SS + spacing * len(s)

    def line(self, pts, fill, width):
        self.d.line([(x * SS, y * SS) for x, y in pts], fill=fill, width=int(width * SS), joint="curve")

    def rect(self, box, fill=None, outline=None, width=1, radius=0):
        b = [v * SS for v in box]
        self.d.rounded_rectangle(b, radius=radius * SS, fill=fill, outline=outline, width=int(width * SS))

    def polygon(self, pts, fill=None, outline=None, width=1):
        p = [(x * SS, y * SS) for x, y in pts]
        if fill:
            self.d.polygon(p, fill=fill)
        if outline:
            self.d.line(p + [p[0], p[1]], fill=outline, width=int(width * SS), joint="curve")

    def circle(self, c, r, fill):
        x, y = c
        self.d.ellipse([(x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r) * SS], fill=fill)

    def arrow(self, x0, x1, y, fill, width, head=None):
        """A reaction arrow: straight shaft with an open head."""
        head = head or width * 3.2
        self.line([(x0, y), (x1, y)], fill, width)
        self.line([(x1 - head, y - head * 0.8), (x1, y), (x1 - head, y + head * 0.8)], fill, width)

    def grid(self, step, fill, width=1):
        for x in range(0, self.w + 1, step):
            self.line([(x, 0), (x, self.h)], fill, width)
        for y in range(0, self.h + 1, step):
            self.line([(0, y), (self.w, y)], fill, width)

    def dots(self, step, fill, r=1.5):
        for x in range(step, self.w, step):
            for y in range(step, self.h, step):
                self.circle((x, y), r, fill)

    def save(self, path: Path) -> Image.Image:
        out = self.im.resize((self.w, self.h), Image.LANCZOS)
        path.parent.mkdir(parents=True, exist_ok=True)
        out.save(path, optimize=True)
        return out


def hexagon(cx, cy, r, rot=30):
    return [(cx + r * math.cos(math.radians(rot + 60 * i)), cy + r * math.sin(math.radians(rot + 60 * i)))
            for i in range(6)]


# ---------------------------------------------------------------- marks

def mark_a(c: Canvas, cx, cy, size, fg, accent):
    """Option A mark: L, a reaction arrow, P. Reads as 'Lab yields Prod'."""
    f = font("Fraunces", size * 0.62 * SS, 600)
    gap = size * 0.34
    c.text((cx - gap, cy), "L", f, fg, anchor="rm")
    c.text((cx + gap, cy), "P", f, fg, anchor="lm")
    c.arrow(cx - gap * 0.72, cx + gap * 0.72, cy + size * 0.03, accent, size * 0.035)


def wordmark_a(c: Canvas, x, y, size, fg, accent, anchor="l"):
    """'Lab ⟶ Prod' set in a serif, with a drawn reaction arrow. y is the vertical centre."""
    f = font("Fraunces", size * SS, 600)
    w_lab, w_prod = c.width("Lab", f), c.width("Prod", f)
    arrow = size * 1.15
    pad = size * 0.28
    total = w_lab + pad + arrow + pad + w_prod
    if anchor == "m":
        x -= total / 2
    elif anchor == "r":
        x -= total
    c.text((x, y), "Lab", f, fg, anchor="lm")
    ax = x + w_lab + pad
    c.arrow(ax, ax + arrow, y + size * 0.06, accent, size * 0.07)
    c.text((ax + arrow + pad, y), "Prod", f, fg, anchor="lm")
    return total


def mark_b(c: Canvas, cx, cy, size, fg, accent):
    """Option B mark: a benzene-like hexagon whose vertices are nodes, one lit: lab ring, prod graph."""
    r = size * 0.36
    pts = hexagon(cx, cy, r)
    c.polygon(pts, outline=fg, width=size * 0.035)
    inner = hexagon(cx, cy, r * 0.62)
    for i in (0, 2, 4):
        c.line([inner[i], inner[(i + 1) % 6]], fg, size * 0.03)
    for i, p in enumerate(pts):
        c.circle(p, size * (0.06 if i == 5 else 0.045), accent if i == 5 else fg)


def wordmark_b(c: Canvas, x, y, size, fg, accent, anchor="l"):
    """'lab-to-prod' in mono, with the 'to' in the accent colour and a block cursor."""
    f = font("JetBrainsMono", size * SS, 700)
    parts = [("lab", fg), ("-to-", accent), ("prod", fg)]
    total = sum(c.width(t, f) for t, _ in parts) + size * 0.55
    if anchor == "m":
        x -= total / 2
    elif anchor == "r":
        x -= total
    for t, col in parts:
        x = c.text((x, y), t, f, col, anchor="lm")
    c.rect([x + size * 0.1, y - size * 0.42, x + size * 0.5, y + size * 0.42], fill=accent)
    return total


OPT = {
    "a": {"mark": mark_a, "wordmark": wordmark_a, "display": "Fraunces", "body": "Inter", "mono": "JetBrainsMono"},
    "b": {"mark": mark_b, "wordmark": wordmark_b, "display": "SpaceGrotesk", "body": "SpaceGrotesk", "mono": "JetBrainsMono"},
}


def texture(c: Canvas, key: str, t: dict):
    if key == "a":
        c.grid(48, t["line"], 1)  # lab notebook squares
    else:
        c.dots(40, t["line"], 1.6)  # terminal dot grid


# ---------------------------------------------------------------- assets

def build_logo(key, t, out, suffix=""):
    c = Canvas(1600, 400, None)
    OPT[key]["wordmark"](c, 800, 200, 170 if key == "a" else 150, t["fg"], t["accent"], anchor="m")
    c.save(out / f"logo{suffix}.png")


def build_avatar(key, t, out):
    c = Canvas(800, 800, t["bg"])
    texture(c, key, t)
    OPT[key]["mark"](c, 400, 400, 430 if key == "a" else 600, t["fg"], t["accent"])
    im = c.save(out / "avatar.png")
    im.resize((640, 640), Image.LANCZOS).save(out / "avatar-telegram.png", optimize=True)


def banner(key, t, out, name, w, h, box, align="l"):
    """box = (x0, y0, x1, y1): the area that is safe from cropping and overlays."""
    o = OPT[key]
    c = Canvas(w, h, t["bg"])
    texture(c, key, t)
    x0, y0, x1, y1 = box
    bh = y1 - y0
    c.rect([x0 - bh * 0.12, y0, x1 + bh * 0.12, y1], fill=t["bg"])  # quiet patch behind the text
    wm = bh * (0.30 if key == "a" else 0.25)
    small = bh * 0.085
    x = x0 if align == "l" else (x0 + x1) / 2
    anchor = "l" if align == "l" else "m"
    tag_f = font(o["body"], bh * 0.088 * SS, 400)
    tag = TAGLINE
    if c.width(tag, tag_f) > (x1 - x0):
        head, tail = tag.split(" — ")
        tag = None
    c.text((x, y0 + bh * 0.13), "NGHIEP PHAM", font(o["mono"], small * SS, 600), t["muted"],
           anchor=anchor + "m", spacing=0 if anchor == "m" else small * 0.18)
    o["wordmark"](c, x, y0 + bh * 0.44, wm, t["fg"], t["accent"], anchor=anchor)
    if tag:
        c.text((x, y0 + bh * 0.78), tag, tag_f, t["muted"], anchor=anchor + "m")
    else:
        c.text((x, y0 + bh * 0.74), head, tag_f, t["fg"], anchor=anchor + "m")
        c.text((x, y0 + bh * 0.88), tail, tag_f, t["muted"], anchor=anchor + "m")
    c.save(out / f"banner-{name}.png")


def sample_card(key, t, out, name, sample):
    """A 1200x1200 post image in one theme. render/image draws the real ones the same way."""
    o = OPT[key]
    c = Canvas(1200, 1200, t["bg"])
    texture(c, key, t)
    m = 88
    c.rect([m - 24, m - 24, 1200 - m + 24, 1200 - m + 24], fill=t["bg"])
    c.text((m, m + 14), sample["series"].upper(), font(o["mono"], 30 * SS, 600), t["accent"], anchor="lm", spacing=3)
    c.line([(m, m + 56), (1200 - m, m + 56)], t["line"], 2)
    y = m + 130
    title_f = font(o["display"], 92 * SS, 600 if key == "a" else 700)
    for ln in sample["title"]:
        c.text((m, y), ln, title_f, t["fg"], anchor="lm")
        y += 108
    y += 40
    code_f = font(o["mono"], 38 * SS, 500)
    bh = 76 + 58 * len(sample["code"])
    c.rect([m, y, 1200 - m, y + bh], fill=t["panel"], radius=18)
    cy = y + 38 + 29
    for ln, hot in sample["code"]:
        c.text((m + 40, cy), ln, code_f, t["panel_accent"] if hot else t["panel_fg"], anchor="lm")
        cy += 58
    y += bh + 46
    c.text((m, y), sample["lesson"], font(o["body"], 44 * SS, 500), t["fg"], anchor="lm")
    c.line([(m, 1200 - m - 70), (1200 - m, 1200 - m - 70)], t["line"], 2)
    c.text((m, 1200 - m - 22), NAME, font(o["body"], 30 * SS, 500), t["muted"], anchor="lm")
    o["mark"](c, 1200 - m - 44, 1200 - m - 22, 110, t["fg"], t["accent"])
    c.save(out / f"theme-{name}.png")


def preview(key, opt, out):
    """One sheet with everything, for choosing between the options."""
    W, pad = 2400, 60
    files = ["banner-linkedin.png", "banner-facebook.png"]
    sheet = Image.new("RGB", (W, 4200), "#D9D9D9")
    d = ImageDraw.Draw(sheet)
    lab = ImageFont.truetype(str(HERE / "fonts" / "Inter.ttf"), 34)
    d.text((pad, 30), f"Option {key.upper()} — {opt['title']}", font=ImageFont.truetype(str(HERE / "fonts" / "Inter.ttf"), 52), fill="#111")
    y = 130
    av = Image.open(out / "avatar.png").resize((520, 520), Image.LANCZOS)
    mask = Image.new("L", av.size, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, 519, 519], fill=255)
    sheet.paste(av, (pad, y), mask)
    d.text((pad, y + 535), "avatar (shown round)", font=lab, fill="#333")
    lx = pad + 600
    for i, (fname, bgc) in enumerate([("logo.png", opt["themes"][opt["primary"]]["bg"]), ("logo-alt.png", opt["themes"][opt["alt"]]["bg"])]):
        lg = Image.open(out / fname).resize((1000, 250), Image.LANCZOS)
        tile = Image.new("RGB", (1000, 250), bgc)
        tile.paste(lg, (0, 0), lg)
        sheet.paste(tile, (lx, y + i * 275))
    yt = Image.open(out / "banner-youtube.png").resize((640, 360), Image.LANCZOS)
    sheet.paste(yt, (lx + 1060, y))
    d.text((lx + 1060, y + 370), "YouTube 2560x1440", font=lab, fill="#333")
    y += 620
    for fname in files:
        im = Image.open(out / fname)
        w = W - 2 * pad
        im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
        sheet.paste(im, (pad, y))
        d.text((pad, y + im.height + 8), fname, font=lab, fill="#333")
        y += im.height + 70
    tw = (W - 4 * pad) // 3
    for i, name in enumerate(opt["themes"]):
        im = Image.open(out / f"theme-{name}.png").resize((tw, tw), Image.LANCZOS)
        sheet.paste(im, (pad + i * (tw + pad), y))
        d.text((pad + i * (tw + pad), y + tw + 8), f"theme: {name}", font=lab, fill="#333")
    sheet = sheet.crop((0, 0, W, y + tw + 70))
    sheet.save(out / "preview.png", optimize=True)


def main():
    for key, opt in CFG["options"].items():
        out = HERE / f"option-{key}"
        themes = opt["themes"]
        t, alt = themes[opt["primary"]], themes[opt["alt"]]
        build_logo(key, t, out)
        build_logo(key, alt, out, "-alt")
        build_avatar(key, t, out)
        # LinkedIn: the profile photo covers the bottom-left, so text sits right of it.
        banner(key, t, out, "linkedin", 1584, 396, (560, 70, 1500, 330))
        # YouTube: only the central 1546x423 is visible on every device.
        banner(key, t, out, "youtube", 2560, 1440, (507, 509, 2053, 931), align="m")
        # Facebook Page cover: phones crop the sides, so keep to the centre.
        banner(key, t, out, "facebook", 1640, 624, (300, 150, 1340, 474), align="m")
        for name, th in themes.items():
            sample_card(key, th, out, name, CFG["sample"])
        preview(key, opt, out)
        print(f"option {key}: {len(list(out.glob('*.png')))} files in {out.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
