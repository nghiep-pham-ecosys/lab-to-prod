#!/usr/bin/env python3
"""Build every brand asset from brand.yaml.

    uv run --with pillow --with pyyaml python brand/build.py          # every option
    uv run --with pillow --with pyyaml python brand/build.py c d e    # only these

Writes brand/option-<key>/: logo, avatar, channel banners, one sample card per image theme and
a preview sheet. Nothing here is drawn by hand, so a palette change is one edit.

An option's `style` picks the mark, the wordmark and the background texture. With `gloss: true`
backgrounds get a gradient and soft light, accents are drawn as metallic foil (the theme's
`foil` colours), and panels get a shadow and a sheen. With `lockup: true` the logo and the
banners set the mark to the left of the wordmark (avatars stay mark only).
"""
from __future__ import annotations

import math
import sys
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
CFG = yaml.safe_load((HERE / "brand.yaml").read_text(encoding="utf-8"))
SS = 2  # supersampling factor: draw big, downscale for smooth edges

NAME = CFG["name"]
TAGLINE = CFG["tagline"]


def font(name: str, size: float, weight: int = 400, ligatures: bool = True) -> ImageFont.FreeTypeFont:
    """A brand font at `size` (supersampled pixels). `ligatures=False` uses Pillow's basic layout,
    which applies no OpenType substitutions, so JetBrains Mono draws `==` as two characters."""
    engine = None if ligatures else ImageFont.Layout.BASIC
    f = ImageFont.truetype(str(HERE / "fonts" / f"{name}.ttf"), int(size), layout_engine=engine)
    values = []
    for a in f.get_variation_axes():
        label = a["name"].decode() if isinstance(a["name"], bytes) else a["name"]
        if label.lower().startswith("weight"):
            values.append(max(a["minimum"], min(a["maximum"], weight)))
        elif label.lower().startswith("optical"):
            values.append(max(a["minimum"], min(a["maximum"], size / SS)))
        else:
            values.append(a["default"] if "default" in a else a["minimum"])
    f.set_variation_by_axes(values)
    return f


def _rgb(hex_color: str) -> tuple[int, int, int]:
    return tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5))


def is_dark(t: dict) -> bool:
    return sum(_rgb(t["bg"])) < 384


class Canvas:
    """A supersampled RGBA canvas with a few drawing helpers. Coordinates are final pixels."""

    def __init__(self, w: int, h: int, bg: str | None, theme: dict | None = None):
        self.w, self.h = w, h
        self.theme = theme
        self.im = Image.new("RGBA", (w * SS, h * SS), bg or (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    # ---- layers: gloss effects are drawn on a transparent layer, then composited

    @contextmanager
    def layer(self, blur: float = 0, tint: str | None = None):
        """Draw on a transparent layer; on exit blur it and composite it onto the canvas.

        `tint` is the colour of the transparent pixels: blurring mixes them in, so it must match
        what is drawn, or a light glow gets a grey fringe.
        """
        base_im = self.im
        self.im = Image.new("RGBA", base_im.size, (*_rgb(tint), 0) if tint else (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)
        try:
            yield
        finally:
            top = self.im
            if blur:
                top = top.filter(ImageFilter.GaussianBlur(blur * SS))
            self.im = Image.alpha_composite(base_im, top)
            self.d = ImageDraw.Draw(self.im)

    @contextmanager
    def accent(self):
        """Whatever is drawn inside becomes metallic foil when the theme has `foil` colours."""
        foil = (self.theme or {}).get("foil")
        if not foil:
            yield
            return
        base_im = self.im
        self.im = Image.new("RGBA", base_im.size, (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)
        try:
            yield
        finally:
            mask = self.im.getchannel("A")
            box = mask.getbbox()
            if box:
                w, h = box[2] - box[0], box[3] - box[1]
                side = int(math.hypot(w, h)) + 2
                ramp = Image.linear_gradient("L").resize((side, side)).rotate(-35, resample=Image.BICUBIC)
                left, top = (side - w) // 2, (side - h) // 2
                ramp = ramp.crop((left, top, left + w, top + h))
                grad = ImageOps.colorize(ramp, black=foil[0], mid=foil[1], white=foil[2], midpoint=118).convert("RGBA")
                base_im.paste(grad, box[:2], mask.crop(box))
            self.im = base_im
            self.d = ImageDraw.Draw(self.im)

    def gradient(self, top: str, bottom: str):
        ramp = Image.linear_gradient("L").resize(self.im.size)
        self.im = ImageOps.colorize(ramp, black=top, white=bottom).convert("RGBA")
        self.d = ImageDraw.Draw(self.im)

    def glow(self, c, r, color, alpha):
        """A soft blob of light."""
        with self.layer(blur=r * 0.45, tint=color):
            self.circle(c, r, (*_rgb(color), alpha))

    def shadow(self, box, radius=0, blur=24, alpha=70, dy=14):
        with self.layer(blur=blur):
            x0, y0, x1, y1 = box
            self.rect([x0, y0 + dy, x1, y1 + dy], fill=(0, 0, 0, alpha), radius=radius)

    def sheen(self, box, radius=0, alpha=34):
        """A highlight that fades from the top edge of a panel to nothing at its middle, as on glass."""
        x0, y0, x1, y1 = (int(v * SS) for v in box)
        w, h = x1 - x0, y1 - y0
        fade = Image.linear_gradient("L").resize((w, h)).point(lambda v: max(0, int(alpha * (1 - v / 255 * 2))))
        shape = Image.new("L", (w, h), 0)
        ImageDraw.Draw(shape).rounded_rectangle([0, 0, w - 1, h - 1], radius=int(radius * SS), fill=255)
        mask = Image.composite(fade, Image.new("L", (w, h), 0), shape)
        top = Image.new("RGBA", self.im.size, (255, 255, 255, 0))
        top.paste(Image.new("RGBA", (w, h), (255, 255, 255, 255)), (x0, y0), mask)
        self.im = Image.alpha_composite(self.im, top)
        self.d = ImageDraw.Draw(self.im)
        with self.layer(tint="#FFFFFF"):
            self.line([(box[0] + radius, box[1] + 1.5), (box[2] - radius, box[1] + 1.5)], (255, 255, 255, 90), 1.5)

    # ---- primitives

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
        self.d.line([(x * SS, y * SS) for x, y in pts], fill=fill, width=max(1, int(width * SS)), joint="curve")

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


def style(key: str) -> dict:
    return CFG["options"][key].get("style", {})


def code_font(name: str, size: float, weight: int = 500) -> ImageFont.FreeTypeFont:
    """The font for code panels: no programming ligatures, so code reads as typed."""
    return font(name, size, weight, ligatures=False)


def display_weight(key: str) -> int:
    """Headline weight: the serif is lighter, and a little heavier on glossy backgrounds."""
    if OPT[key]["display"] == "Fraunces":
        return 650 if style(key).get("gloss") else 600
    return 700


def _foil(c: Canvas) -> bool:
    return bool((c.theme or {}).get("foil"))


# ---------------------------------------------------------------- marks

def mark_arrow(c: Canvas, cx, cy, size, fg, accent, weight=1.0):
    """L, a reaction arrow, P. Reads as 'Lab yields Prod'."""
    f = font("Fraunces", size * 0.62 * SS, 600)
    gap = size * 0.34
    c.text((cx - gap, cy), "L", f, fg, anchor="rm")
    c.text((cx + gap, cy), "P", f, fg, anchor="lm")
    with c.accent():
        c.arrow(cx - gap * 0.72, cx + gap * 0.72, cy + size * 0.03, accent, size * (0.045 if _foil(c) else 0.035))


def mark_hexagon(c: Canvas, cx, cy, size, fg, accent, weight=1.0):
    """A benzene-like hexagon whose vertices are nodes, one lit: lab ring, prod graph.

    `weight` thickens strokes and nodes, so the ring holds its own next to a bold wordmark.
    """
    r = size * 0.36
    pts = hexagon(cx, cy, r)
    c.polygon(pts, outline=fg, width=size * 0.035 * weight)
    inner = hexagon(cx, cy, r * (0.62 - 0.03 * (weight - 1)))
    for i in (0, 2, 4):
        c.line([inner[i], inner[(i + 1) % 6]], fg, size * 0.03 * weight)
    for i, p in enumerate(pts):
        if i != 5:
            c.circle(p, size * 0.045 * (1 + (weight - 1) * 0.6), fg)
    t = c.theme or {}
    if t and not _foil(c) and accent.lower() == fg.lower():
        # The accent is the ink colour (an amber card): a filled node would not read as lit, so
        # draw a light node with an ink outline, the size of the foil node.
        r = size * 0.075 * (1 + (weight - 1) * 0.4)
        c.circle(pts[5], r, fg)
        c.circle(pts[5], r - size * 0.03 * weight, t.get("panel_fg", "#FFFFFF"))
        return
    with c.accent():
        c.circle(pts[5], size * (0.075 if _foil(c) else 0.06) * (1 + (weight - 1) * 0.4), accent)


def mark_badge(c: Canvas, cx, cy, size, fg, accent, weight=1.0):
    """A glossy yellow rounded square holding L, an arrow and P in black."""
    t = c.theme or {}
    ink = "#0B0B0A"
    half, rad = size * 0.40, size * 0.17
    box = [cx - half, cy - half, cx + half, cy + half]
    if _foil(c) and size > 200:
        c.shadow(box, radius=rad, blur=size * 0.04, alpha=80, dy=size * 0.025)
    with c.accent():
        c.rect(box, fill=t.get("panel_accent", accent), radius=rad)
    if _foil(c):
        c.sheen(box, radius=rad, alpha=60)
    f = font("SpaceGrotesk", size * 0.34 * SS, 700)
    gap = size * 0.12
    c.text((cx - gap, cy), "L", f, ink, anchor="rm")
    c.text((cx + gap, cy), "P", f, ink, anchor="lm")
    c.arrow(cx - gap * 0.72, cx + gap * 0.72, cy + size * 0.012, ink, size * 0.03)


# ---------------------------------------------------------------- wordmarks (y is the vertical centre)

def _place(x, total, anchor):
    return x - total / 2 if anchor == "m" else x - total if anchor == "r" else x


def wordmark_arrow(c: Canvas, x, y, size, fg, accent, anchor="l"):
    """'Lab ⟶ Prod' set in a serif, with a drawn reaction arrow."""
    f = font("Fraunces", size * SS, 600)
    w_lab, w_prod = c.width("Lab", f), c.width("Prod", f)
    arrow, pad = size * 1.15, size * 0.28
    total = w_lab + pad + arrow + pad + w_prod
    x = _place(x, total, anchor)
    c.text((x, y), "Lab", f, fg, anchor="lm")
    ax = x + w_lab + pad
    with c.accent():
        c.arrow(ax, ax + arrow, y + size * 0.06, accent, size * (0.085 if _foil(c) else 0.07))
    c.text((ax + arrow + pad, y), "Prod", f, fg, anchor="lm")
    return total


def wordmark_mono(c: Canvas, x, y, size, fg, accent, anchor="l"):
    """'lab-to-prod' in mono, with the 'to' in the accent colour and a block cursor."""
    f = font("JetBrainsMono", size * SS, 700)
    w_lab, w_to, w_prod = (c.width(s, f) for s in ("lab", "-to-", "prod"))
    total = w_lab + w_to + w_prod + size * 0.55
    x = _place(x, total, anchor)
    c.text((x, y), "lab", f, fg, anchor="lm")
    c.text((x + w_lab + w_to, y), "prod", f, fg, anchor="lm")
    end = x + w_lab + w_to + w_prod
    with c.accent():
        c.text((x + w_lab, y), "-to-", f, accent, anchor="lm")
        c.rect([end + size * 0.1, y - size * 0.42, end + size * 0.5, y + size * 0.42], fill=accent)
    return total


def wordmark_pill(c: Canvas, x, y, size, fg, accent, anchor="l"):
    """'Lab' and 'Prod' in a heavy grotesk around a glossy yellow pill that carries the arrow."""
    t = c.theme or {}
    f = font("SpaceGrotesk", size * SS, 700)
    w_lab, w_prod = c.width("Lab", f), c.width("Prod", f)
    pill_w, pill_h, pad = size * 1.25, size * 0.66, size * 0.22
    total = w_lab + pad + pill_w + pad + w_prod
    x = _place(x, total, anchor)
    c.text((x, y), "Lab", f, fg, anchor="lm")
    px = x + w_lab + pad
    box = [px, y - pill_h / 2 + size * 0.03, px + pill_w, y + pill_h / 2 + size * 0.03]
    with c.accent():
        c.rect(box, fill=t.get("panel_accent", accent), radius=pill_h / 2)
    if _foil(c):
        c.sheen(box, radius=pill_h / 2, alpha=70)
    c.arrow(px + pill_w * 0.22, px + pill_w * 0.78, y + size * 0.03, "#0B0B0A", size * 0.075)
    c.text((px + pill_w + pad, y), "Prod", f, fg, anchor="lm")
    return total


MARKS = {"arrow": mark_arrow, "hexagon": mark_hexagon, "badge": mark_badge}
WORDMARKS = {"arrow": wordmark_arrow, "mono": wordmark_mono, "pill": wordmark_pill}
WORDMARK_FONT = {"arrow": ("Fraunces", 600), "mono": ("JetBrainsMono", 700), "pill": ("SpaceGrotesk", 700)}
OPT = {key: {"mark": MARKS[opt["style"]["mark"]], "wordmark": WORDMARKS[opt["style"]["wordmark"]], **opt["fonts"]}
       for key, opt in CFG["options"].items()}


# ---------------------------------------------------------------- lockup: mark left of the wordmark

LOCKUP_MARK = 1.6   # mark ink height / wordmark cap height
LOCKUP_GAP = 0.42   # space between the mark ink and the wordmark, in wordmark font sizes
LOCKUP_WEIGHT = 1.7  # mark stroke weight next to the bold wordmark (hexagon only; other marks ignore it)


def _ink_box(draw, w: int, h: int) -> tuple[float, float, float, float]:
    """Bounding box (final pixels) of what `draw(canvas)` puts on an empty canvas."""
    c = Canvas(w, h, None)
    draw(c)
    box = c.im.getchannel("A").getbbox()
    return tuple(v / SS for v in box)


@lru_cache(maxsize=None)
def _mark_ink(key: str, ref: int) -> tuple[float, float, float, float]:
    """Ink box of the option's mark drawn at size `ref`, centred at (ref, ref)."""
    return _ink_box(lambda c: OPT[key]["mark"](c, ref, ref, ref, "#000000", "#000000", LOCKUP_WEIGHT), 2 * ref, 2 * ref)


def wordmark_width(key: str, size: float) -> float:
    return OPT[key]["wordmark"](Canvas(1, 1, None), 0, 0, size, "#000000", "#000000")


def lockup_geometry(key: str, size: float) -> dict:
    """Where the mark goes for a wordmark of font size `size` whose left edge is at x = 0.

    mark: the size argument for the mark function; cx, dy: its centre (dy from the wordmark's
    vertical centre); lead: where the wordmark starts; width: the whole lockup.
    """
    fname, weight = WORDMARK_FONT[style(key)["wordmark"]]
    l, t, r, b = font(fname, 1000 * SS, weight).getbbox("H")
    cap = (b - t) / 1000 / SS * size
    ref = 1000
    x0, y0, x1, y1 = _mark_ink(key, ref)
    mark = LOCKUP_MARK * cap / ((y1 - y0) / ref)
    k = mark / ref
    lead = (x1 - x0) * k + LOCKUP_GAP * size
    return {"mark": mark, "cx": (ref - x0) * k, "dy": (ref - (y0 + y1) / 2) * k, "lead": lead,
            "width": lead + wordmark_width(key, size)}


def lockup(c: Canvas, key: str, x, y, size, fg, accent, anchor="l") -> dict:
    """Draw the mark and the wordmark side by side, vertically centred on y."""
    g = lockup_geometry(key, size)
    x = _place(x, g["width"], anchor)
    OPT[key]["mark"](c, x + g["cx"], y + g["dy"], g["mark"], fg, accent, LOCKUP_WEIGHT)
    OPT[key]["wordmark"](c, x + g["lead"], y, size, fg, accent, anchor="l")
    return {**g, "x": x}


def texture(c: Canvas, key: str, t: dict):
    kind = style(key).get("texture")
    if kind == "grid":
        c.grid(48, t["line"], 1)   # lab notebook squares
    elif kind == "dots":
        c.dots(40, t["line"], 1.6)  # terminal dot grid


def new_canvas(w: int, h: int, t: dict, key: str) -> Canvas:
    """A canvas with the option's background: flat, or gradient plus soft light when glossy."""
    c = Canvas(w, h, t["bg"], t)
    if style(key).get("gloss"):
        c.gradient(t["bg"], t.get("bg2", t["bg"]))
        texture(c, key, t)
        big = max(w, h)
        if is_dark(t):
            c.glow((w * 0.86, h * 0.02), big * 0.34, t["panel_accent"], 62)
            c.glow((w * 0.04, h * 1.0), big * 0.26, t["panel_accent"], 30)
        else:
            c.glow((w * 0.12, h * 0.0), big * 0.36, "#FFFFFF", 150)
            c.glow((w * 0.95, h * 1.0), big * 0.30, t["panel_accent"], 70)
    else:
        texture(c, key, t)
    return c


def panel(c: Canvas, box, t: dict, key: str, radius=18):
    """A dark block for code or a number; glossy options add a shadow, a sheen and a gold edge."""
    if style(key).get("gloss"):
        c.shadow(box, radius=radius, blur=26, alpha=120 if is_dark(t) else 64)
        c.rect(box, fill=t["panel"], radius=radius)
        c.sheen(box, radius=radius, alpha=16)
        with c.accent():
            c.rect(box, outline=t["panel_accent"], width=2.5, radius=radius)
    else:
        c.rect(box, fill=t["panel"], radius=radius)


def rule(c: Canvas, x0, x1, y, t: dict, key: str):
    if style(key).get("gloss"):
        with c.accent():
            c.line([(x0, y), (x1, y)], t["panel_accent"], 3)
    else:
        c.line([(x0, y), (x1, y)], t["line"], 2)


# ---------------------------------------------------------------- assets

def build_logo(key, t, out, suffix=""):
    c = Canvas(1600, 400, None, t)
    size = {"arrow": 170, "mono": 150, "pill": 160}[style(key)["wordmark"]]
    if style(key).get("lockup"):
        lockup(c, key, 800, 200, size * 0.86, t["fg"], t["accent"], anchor="m")
    else:
        OPT[key]["wordmark"](c, 800, 200, size, t["fg"], t["accent"], anchor="m")
    c.save(out / f"logo{suffix}.png")


def build_avatar(key, t, out, name="avatar.png"):
    c = new_canvas(800, 800, t, key)
    size = {"arrow": 430, "hexagon": 600, "badge": 640}[style(key)["mark"]]
    OPT[key]["mark"](c, 400, 400, size, t["fg"], t["accent"])
    im = c.save(out / name)
    if name == "avatar.png":
        im.resize((640, 640), Image.LANCZOS).save(out / "avatar-telegram.png", optimize=True)


def banner_layout(key, box, align="l") -> dict:
    """Positions of the banner text. box = (x0, y0, x1, y1): the area safe from cropping and overlays.

    Without a lockup the kicker, wordmark and tagline share one x (left edge or centre). With a
    lockup the mark sits left of the wordmark and the kicker and tagline start where the wordmark
    starts; when centred, the whole group (mark + text column) is centred in the box.
    """
    o = OPT[key]
    x0, y0, x1, y1 = box
    bh = y1 - y0
    wm = bh * {"arrow": 0.30, "mono": 0.25, "pill": 0.27}[style(key)["wordmark"]]
    tag_f = font(o["body"], bh * 0.088 * SS, 400)
    small = bh * 0.085
    lead = lockup_geometry(key, wm)["lead"] if style(key).get("lockup") else 0
    one_line = Canvas(1, 1, None).width(TAGLINE, tag_f) <= (x1 - x0) - lead
    tagline = [(TAGLINE, 0.78, "muted")] if one_line else list(zip(TAGLINE.split(" — "), (0.74, 0.88), ("fg", "muted")))
    lay = {"wm": wm, "small": small, "tag_f": tag_f, "lead": lead, "anchor": "l" if align == "l" or lead else "m",
           "y_kicker": y0 + bh * 0.13, "y_wm": y0 + bh * 0.44,
           "tagline": [(s, y0 + bh * f, role) for s, f, role in tagline]}
    if not lead:
        lay["x_group"] = lay["x_text"] = x0 if align == "l" else (x0 + x1) / 2
        return lay
    m = Canvas(1, 1, None)
    column = max([wordmark_width(key, wm)] + [m.width(s, tag_f) for s, _, _ in lay["tagline"]])
    gx = x0 if align == "l" else (x0 + x1) / 2 - (lead + column) / 2
    lay.update(x_group=gx, x_text=gx + lead, right=gx + lead + column)
    if gx < x0 - 0.5 or lay["right"] > x1 + 0.5:
        raise ValueError(f"option {key}: banner lockup ({gx:.0f}..{lay['right']:.0f}) leaves the safe box {box}")
    return lay


def banner(key, t, out, name, w, h, box, align="l"):
    """box = (x0, y0, x1, y1): the area that is safe from cropping and overlays."""
    o = OPT[key]
    gloss = style(key).get("gloss")
    c = new_canvas(w, h, t, key)
    x0, y0, x1, y1 = box
    bh = y1 - y0
    if not gloss:
        c.rect([x0 - bh * 0.12, y0, x1 + bh * 0.12, y1], fill=t["bg"])  # quiet patch behind the text
    lay = banner_layout(key, box, align)
    x, anchor, small = lay["x_text"], lay["anchor"], lay["small"]
    c.text((x, lay["y_kicker"]), "NGHIEP PHAM", font(o["mono"], small * SS, 600), t["accent"] if gloss else t["muted"],
           anchor=anchor + "m", spacing=0 if anchor == "m" else small * 0.18)
    if lay["lead"]:
        lockup(c, key, lay["x_group"], lay["y_wm"], lay["wm"], t["fg"], t["accent"])
    else:
        o["wordmark"](c, x, lay["y_wm"], lay["wm"], t["fg"], t["accent"], anchor=anchor)
    for s, y, role in lay["tagline"]:
        c.text((x, y), s, lay["tag_f"], t[role], anchor=anchor + "m")
    c.save(out / f"banner-{name}.png")


def sample_card(key, t, out, name, sample):
    """A 1200x1200 post image in one theme. render/image draws the real ones the same way."""
    o = OPT[key]
    gloss = style(key).get("gloss")
    c = new_canvas(1200, 1200, t, key)
    m = 88
    if not gloss:
        c.rect([m - 24, m - 24, 1200 - m + 24, 1200 - m + 24], fill=t["bg"])
    c.text((m, m + 14), sample["series"].upper(), font(o["mono"], 30 * SS, 700 if gloss else 600), t["accent"], anchor="lm", spacing=3)
    rule(c, m, 1200 - m, m + 56, t, key)
    y = m + 130
    title_f = font(o["display"], 92 * SS, display_weight(key))
    for ln in sample["title"]:
        c.text((m, y), ln, title_f, t["fg"], anchor="lm")
        y += 108
    y += 40
    code_f = code_font(o["mono"], 38 * SS)
    bh = 76 + 58 * len(sample["code"])
    panel(c, [m, y, 1200 - m, y + bh], t, key)
    cy = y + 38 + 29
    for ln, hot in sample["code"]:
        c.text((m + 40, cy), ln, code_f, t["panel_accent"] if hot else t["panel_fg"], anchor="lm")
        cy += 58
    y += bh + 46
    c.text((m, y), sample["lesson"], font(o["body"], 44 * SS, 600 if gloss else 500), t["fg"], anchor="lm")
    c.line([(m, 1200 - m - 70), (1200 - m, 1200 - m - 70)], t["line"], 2)
    c.text((m, 1200 - m - 22), NAME, font(o["body"], 30 * SS, 500), t["muted"], anchor="lm")
    o["mark"](c, 1200 - m - 44, 1200 - m - 22, 110, t["fg"], t["accent"])
    c.save(out / f"theme-{name}.png")


def preview(key, opt, out):
    """One sheet with everything, for choosing between the options."""
    W, pad = 2400, 60
    themes = opt["themes"]
    sheet = Image.new("RGB", (W, 5200), "#D9D9D9")
    d = ImageDraw.Draw(sheet)
    inter = str(HERE / "fonts" / "Inter.ttf")
    lab = ImageFont.truetype(inter, 34)
    d.text((pad, 30), f"Option {key.upper()} — {opt['title']}", font=ImageFont.truetype(inter, 52), fill="#111")
    y = 130
    x = pad
    for fname, caption in (("avatar.png", "avatar"), ("avatar-alt.png", "avatar, dark")):
        if not (out / fname).exists():
            continue
        av = Image.open(out / fname).convert("RGB").resize((420, 420), Image.LANCZOS)
        mask = Image.new("L", av.size, 0)
        ImageDraw.Draw(mask).ellipse([0, 0, 419, 419], fill=255)
        sheet.paste(av, (x, y), mask)
        d.text((x, y + 432), caption, font=lab, fill="#333")
        x += 470
    lx = x + 30
    lw = W - pad - lx
    lh = min(lw // 4, 210)
    for i, (fname, theme) in enumerate([("logo.png", themes[opt["primary"]]), ("logo-alt.png", themes[opt["alt"]])]):
        lg = Image.open(out / fname).resize((lh * 4, lh), Image.LANCZOS)
        tile = Image.new("RGB", (lw, lh), theme["bg"])
        tile.paste(lg, ((lw - lh * 4) // 2, 0), lg)
        sheet.paste(tile, (lx, y + i * (lh + 16)))
    y += 510
    for fname in ("banner-linkedin.png", "banner-linkedin-alt.png", "banner-facebook.png"):
        if not (out / fname).exists():
            continue
        im = Image.open(out / fname).convert("RGB")
        w = W - 2 * pad
        im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
        sheet.paste(im, (pad, y))
        d.text((pad, y + im.height + 8), fname, font=lab, fill="#333")
        y += im.height + 70
    tw = (W - 4 * pad) // 3
    for i, name in enumerate(themes):
        im = Image.open(out / f"theme-{name}.png").convert("RGB").resize((tw, tw), Image.LANCZOS)
        sheet.paste(im, (pad + i * (tw + pad), y))
        d.text((pad + i * (tw + pad), y + tw + 8), f"post image, theme: {name}", font=lab, fill="#333")
    sheet.crop((0, 0, W, y + tw + 70)).save(out / "preview.png", optimize=True)


def main(keys: list[str] | None = None):
    for key, opt in CFG["options"].items():
        if keys and key not in keys:
            continue
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
        if style(key).get("gloss"):   # dark variants for platforms shown in dark mode
            build_avatar(key, alt, out, "avatar-alt.png")
            banner(key, alt, out, "linkedin-alt", 1584, 396, (560, 70, 1500, 330))
        for name, th in themes.items():
            sample_card(key, th, out, name, CFG["sample"])
        preview(key, opt, out)
        print(f"option {key}: {len(list(out.glob('*.png')))} files in {out.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
