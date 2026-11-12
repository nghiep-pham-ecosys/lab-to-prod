import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "render" / "image"))
sys.path.insert(0, str(ROOT / "sim"))
import render as image_render  # noqa: E402
import tank  # noqa: E402

CARDS = {
    "code": {"layout": "code", "headline": "Same value, different object",
             "code": ["Integer a = 127, b = 127;", "> a == b   // true"], "lesson": "Use equals() for objects."},
    "stat": {"layout": "stat", "headline": "One number hides the other",
             "stat": {"value": "0.62", "label": "recall", "note": "8 of 13 caught"}, "lesson": "Report both."},
    "table": {"layout": "table", "headline": "VPN or Direct Connect",
              "rows": [["VPN", "hours to set up, runs over the internet"], ["Direct Connect", "weeks to provision"]]},
}


def folder_with(tmp_path, card):
    meta = {"date": "2026-11-16", "series": "dsa-in-java", "part": 2, "title": "T", "card": card}
    (tmp_path / "post.md").write_text("---\n" + yaml.safe_dump(meta) + "---\n\n## linkedin\n\ntext\n")
    return tmp_path


@pytest.mark.parametrize("layout", sorted(CARDS))
def test_each_layout_renders_a_1200_square(tmp_path, layout):
    out = image_render.render(folder_with(tmp_path, CARDS[layout]))
    assert Image.open(out).size == (1200, 1200)


def test_every_theme_of_the_selected_option_renders(tmp_path):
    folder = folder_with(tmp_path, CARDS["code"])
    opt = image_render.brand.CFG["options"][image_render.brand.CFG["selected"]]
    for theme in opt["themes"]:
        assert Image.open(image_render.render(folder, theme)).size == (1200, 1200)


def test_text_that_cannot_fit_is_an_error_not_a_clipped_image(tmp_path):
    card = {**CARDS["code"], "code": ["x" * 200]}
    with pytest.raises(ValueError):
        image_render.render(folder_with(tmp_path, card))


def test_unknown_theme_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        image_render.render(folder_with(tmp_path, CARDS["code"]), "neon")


@pytest.mark.skipif(not (ROOT / "render/short/node_modules/yaml").exists() or not shutil.which("node"),
                    reason="render/short dependencies are not installed")
def test_srt_is_written_from_short_json(tmp_path):
    (tmp_path / "short.json").write_text(
        '{"title":"t","kicker":"k","scenes":[{"type":"title","text":"a","say":"First line.","seconds":20},'
        '{"type":"outro","say":"Last line.","seconds":15}]}')
    subprocess.run(["node", str(ROOT / "render/short/render.mjs"), str(tmp_path), "--srt-only"], check=True)
    srt = (tmp_path / "short.srt").read_text()
    assert "00:00:00,000 --> 00:00:19,950\nFirst line." in srt
    assert "00:00:20,000 --> 00:00:34,950\nLast line." in srt


def test_tank_reaches_the_analytic_steady_state():
    _, h = tank.simulate(tank.K_TRUE, t_end=20000.0)
    assert h[-1] == pytest.approx(tank.steady_state(tank.K_TRUE), rel=1e-3)


def test_calibration_recovers_the_valve_coefficient():
    t_obs, h_obs = tank.sensor()
    k = tank.calibrate(t_obs, h_obs)
    assert k == pytest.approx(tank.K_TRUE, abs=2e-4)
    assert tank.rmse(k, t_obs, h_obs) < 0.03 < tank.rmse(tank.K_GUESS, t_obs, h_obs)


def test_theme_names_of_another_option_map_to_the_same_role():
    opt = image_render.brand.CFG["options"]["e"]
    assert [image_render.resolve_theme(opt, n) for n in ("paper", "ink", "copper")] == ["light", "dark", "amber"]
    assert [image_render.resolve_theme(opt, n) for n in ("night", "day", "signal")] == ["dark", "light", "amber"]
    assert image_render.resolve_theme(opt, "dark") == "dark"
