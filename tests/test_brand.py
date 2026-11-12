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
            assert set(theme) == {"bg", "fg", "muted", "accent", "line", "panel", "panel_fg"}
