from pathlib import Path

import pytest
import yaml
from PIL import Image

BRAND = Path(__file__).resolve().parents[1] / "brand"
CFG = yaml.safe_load((BRAND / "brand.yaml").read_text())
SIZES = {"logo.png": (1600, 400), "logo-alt.png": (1600, 400), "avatar.png": (800, 800),
         "avatar-telegram.png": (640, 640), "banner-linkedin.png": (1584, 396),
         "banner-youtube.png": (2560, 1440), "banner-facebook.png": (1640, 624)}


@pytest.mark.parametrize("key", sorted(CFG["options"]))
def test_option_assets_exist_with_platform_sizes(key):
    out = BRAND / f"option-{key}"
    for name, size in SIZES.items():
        assert Image.open(out / name).size == size, name
    themes = CFG["options"][key]["themes"]
    assert len(themes) == 3
    for theme in themes:
        assert Image.open(out / f"theme-{theme}.png").size == (1200, 1200)
    assert (out / "preview.png").exists()


def test_selected_option_and_theme_keys():
    assert CFG["selected"] in CFG["options"]
    for opt in CFG["options"].values():
        assert opt["primary"] in opt["themes"] and opt["alt"] in opt["themes"]
        for theme in opt["themes"].values():
            required = {"bg", "fg", "muted", "accent", "line", "panel", "panel_fg", "panel_accent"}
            optional = {"bg2", "foil"}  # gradient end and metallic highlight (glossy options C/D/E)
            assert required <= set(theme), required - set(theme)
            assert set(theme) <= required | optional, set(theme) - required - optional


def _build():
    import importlib
    import sys
    sys.path.insert(0, str(BRAND))
    return importlib.import_module("build")


# The safe boxes main() passes to banner(): LinkedIn right of the photo, YouTube's 1546x423
# centre visible on every device, Facebook's centre that phones do not crop.
BANNER_BOXES = {"linkedin": ((560, 70, 1500, 330), "l"), "youtube": ((507, 509, 2053, 931), "m"),
                "facebook": ((300, 150, 1340, 474), "m")}


def test_lockup_is_a_style_flag_used_by_the_signal_and_honey_options():
    flagged = {k for k, o in CFG["options"].items() if o["style"].get("lockup")}
    assert flagged == {"d", "e"}
    assert CFG["selected"] == "d"


def test_only_the_selected_signal_option_uses_the_honeycomb_texture():
    textured = {k for k, o in CFG["options"].items() if o["style"].get("texture") == "honeycomb"}
    assert textured == {"d"}


@pytest.mark.parametrize("name", sorted(BANNER_BOXES))
def test_lockup_banners_stay_inside_the_safe_area(name):
    build = _build()
    box, align = BANNER_BOXES[name]
    for key, opt in CFG["options"].items():
        lay = build.banner_layout(key, box, align)
        if not opt["style"].get("lockup"):
            assert lay["lead"] == 0
            continue
        assert lay["lead"] > 0
        assert box[0] <= lay["x_group"] and lay["right"] <= box[2]
        assert lay["x_text"] == pytest.approx(lay["x_group"] + lay["lead"])
        if align == "m":   # the group is centred in the box
            assert (lay["x_group"] + lay["right"]) / 2 == pytest.approx((box[0] + box[2]) / 2)


@pytest.mark.parametrize("key", ["d", "e"])
def test_lockup_mark_is_left_of_the_wordmark_and_sized_to_its_cap_height(key):
    build = _build()
    size = 120
    g = build.lockup_geometry(key, size)
    fname, weight = build.WORDMARK_FONT[CFG["options"][key]["style"]["wordmark"]]
    f = build.font(fname, 1000 * build.SS, weight)
    _, top, _, bottom = f.getbbox("H")
    cap = (bottom - top) / 1000 / build.SS * size
    x0, y0, x1, y1 = build._mark_ink(key, 1000)
    k = g["mark"] / 1000
    ratio = build.LOCKUP_MARK[CFG["options"][key]["style"]["mark"]]
    assert ratio == {"d": 1.8, "e": 1.6}[key]   # the badge is a filled square, so it sits a little taller
    assert (y1 - y0) * k == pytest.approx(ratio * cap, rel=1e-3)
    assert x1 * k - 1000 * k + g["cx"] < g["lead"]   # mark ink ends before the wordmark starts
    assert g["width"] == pytest.approx(g["lead"] + build.wordmark_width(key, size))


@pytest.mark.parametrize("key", ["d", "e"])
def test_lockup_logo_shows_the_mark_left_of_the_wordmark(key):
    logo = Image.open(BRAND / f"option-{key}" / "logo.png").getchannel("A").point(lambda v: 255 if v > 40 else 0)
    cols = [x for x in range(logo.width) if logo.crop((x, 0, x + 1, logo.height)).getbbox()]
    gaps = [b - a for a, b in zip(cols, cols[1:]) if b - a > 1]
    assert max(gaps) >= 40   # a clear gap between mark and text, wider than letter spacing
    left, right = cols[0], cols[-1]
    assert abs((left + right) / 2 - logo.width / 2) < 12   # the whole lockup is centred


@pytest.mark.parametrize("name", sorted(BANNER_BOXES))
def test_banner_accent_ring_is_inside_the_safe_box_and_clear_of_the_text(name):
    build = _build()
    box, align = BANNER_BOXES[name]
    lay = build.banner_layout("d", box, align)
    cx, cy, r = build.banner_accent("d", box, lay)
    half_w = 3 ** 0.5 / 2 * r
    assert box[0] <= cx - half_w and cx + half_w <= box[2] + 0.5
    assert box[1] <= cy - r and cy + r <= box[3]
    # the kicker ends well before the ring, and the ring ends above the badge and wordmark
    kicker = build.Canvas(1, 1, None).width("NGHIEP PHAM", build.font("JetBrainsMono", lay["small"] * build.SS, 600), lay["small"] * 0.18)
    assert lay["x_text"] + kicker + 20 < cx - half_w
    g = build.lockup_geometry("d", lay["wm"])
    assert cy + r < lay["y_wm"] - g["mark"] * 0.4 or cx - half_w > lay["right"]
    assert build.banner_accent("e", box, build.banner_layout("e", box, align)) is None


def test_card_rule_stops_before_the_accent_ring():
    build = _build()
    ring = build.card_accent("d", 1200, 88, 88 + 400, 102)
    assert ring is not None
    cx, cy, r = ring
    assert cx + 3 ** 0.5 / 2 * r == pytest.approx(1200 - 88)
    assert build.rule_end(1200, 88, ring) < cx - 3 ** 0.5 / 2 * r
    assert build.card_accent("d", 1200, 88, 1050, 102) is None   # a kicker that long gets no ring
    assert build.card_accent("e", 1200, 88, 400, 102) is None
    assert build.rule_end(1200, 88, None) == 1200 - 88


def test_honeycomb_keeps_clear_of_what_is_drawn_on_top(monkeypatch, tmp_path):
    build = _build()
    t = CFG["options"]["d"]["themes"]["light"]

    def card(name, near, far):
        monkeypatch.setitem(build.HONEY, "near", near)
        monkeypatch.setitem(build.HONEY, "far", far)
        c = build.new_canvas(400, 400, t, "d", accent=(340, 60, 24))
        c.rect([120, 160, 280, 240], fill=t["fg"])
        return c.save(tmp_path / name).convert("RGB")

    plain, textured = card("plain.png", 0, 0), card("textured.png", 0.3, 0.3)
    near_shape = [(x, y) for x in range(112, 288, 4) for y in (152, 156, 244, 248)]
    assert all(plain.getpixel(p) == textured.getpixel(p) for p in near_shape)   # a clear halo
    far_away = [(x, y) for x in range(0, 400, 3) for y in (330, 360, 390)]
    assert any(plain.getpixel(p) != textured.getpixel(p) for p in far_away)     # the lattice is there


def test_badge_ring_is_pressed_in_and_left_out_of_the_favicon(tmp_path):
    build = _build()
    av = Image.open(BRAND / "option-d" / "avatar.png").convert("RGB")
    # the left side of the ring passes just above the L: groove darker than the gold around it
    groove = av.getpixel((234, 300))
    gold = av.getpixel((200, 300))
    assert sum(groove) < sum(gold) - 60
    build.build_favicon("d", tmp_path / "favicon.png")
    fav = Image.open(tmp_path / "favicon.png")
    assert fav.size == (96, 96) and fav.mode == "RGBA"
    assert fav.getpixel((0, 0))[3] == 0          # transparent corners
    assert fav.getpixel((48, 10))[3] == 255      # the badge fills the square
