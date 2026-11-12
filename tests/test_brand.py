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


def test_lockup_is_a_style_flag_and_only_the_selected_honey_option_uses_it():
    flagged = {k for k, o in CFG["options"].items() if o["style"].get("lockup")}
    assert flagged == {"e"}
    assert CFG["selected"] == "e"


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


def test_lockup_mark_is_left_of_the_wordmark_and_sized_to_its_cap_height():
    build = _build()
    size = 120
    g = build.lockup_geometry("e", size)
    f = build.font("JetBrainsMono", 1000 * build.SS, 700)
    _, top, _, bottom = f.getbbox("H")
    cap = (bottom - top) / 1000 / build.SS * size
    x0, y0, x1, y1 = build._mark_ink("e", 1000)
    k = g["mark"] / 1000
    assert (y1 - y0) * k == pytest.approx(build.LOCKUP_MARK * cap, rel=1e-3)
    assert x1 * k - 1000 * k + g["cx"] < g["lead"]   # mark ink ends before the wordmark starts
    assert g["width"] == pytest.approx(g["lead"] + build.wordmark_width("e", size))


def test_lockup_logo_shows_the_mark_left_of_the_wordmark():
    logo = Image.open(BRAND / "option-e" / "logo.png").getchannel("A")
    cols = [x for x in range(logo.width) if logo.crop((x, 0, x + 1, logo.height)).getbbox()]
    gaps = [b - a for a, b in zip(cols, cols[1:]) if b - a > 1]
    assert max(gaps) >= 40   # a clear gap between ring and text, wider than letter spacing
    left, right = cols[0], cols[-1]
    assert abs((left + right) / 2 - logo.width / 2) < 8   # the whole lockup is centred
