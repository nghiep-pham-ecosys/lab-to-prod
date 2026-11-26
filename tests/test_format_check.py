import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import format_check as fc  # noqa: E402
import judge_file  # noqa: E402

GOOD_LINKEDIN = "\n\n".join(
    ["128 == 128 can be false in Java."]
    + ["This paragraph explains one small step of the idea in plain words for the reader today."] * 12
    + ["Have you hit this in a code review?", "Part 2 of my DSA in Java notes.", "#Java #DSA #LearningInPublic"]
)


def write_post(folder: Path, linkedin: str, x: str = "128 is not 128.", facebook: str = "word " * 90, scenes=None):
    folder.mkdir(parents=True)
    meta = "date: 2026-11-16\nseries: dsa\npart: 2\ntitle: T\nchannels: [linkedin]\nshort_publish_at: null\nsources: []\nstatus: approved\nimage_alt: a\n"
    (folder / "post.md").write_text(f"---\n{meta}---\n\n## linkedin\n\n{linkedin}\n\n## x\n\n{x}\n\n## facebook\n\n{facebook}\n")
    if scenes is not None:
        (folder / "short.json").write_text(json.dumps({"scenes": [{"seconds": s} for s in scenes]}))
    return folder


def test_good_post_has_no_warnings(tmp_path):
    folder = write_post(tmp_path / "p", GOOD_LINKEDIN, scenes=[20, 25])
    (folder / "java_cache.py").write_text("print(128 == 128)\n")
    (folder / "java_cache.expected").write_text("True\n")
    report = fc.check_folder(folder)
    assert report["warnings"] == []
    assert report["linkedin"]["ends_with_question"] is True
    assert report["linkedin"]["hook_lines"] == 1
    assert report["short"]["seconds"] == 45.0


def test_sign_off_and_hashtags_are_not_counted_as_the_ending():
    text = "Hook line.\n\nBody without a question.\n\nPart 2 of my notes.\n\n#a #b"
    r = fc.check_linkedin(text)
    assert r["ends_with_question"] is False
    assert "linkedin: no open question at the end" in r["warnings"]


def test_linkedin_length_hook_and_long_paragraphs():
    text = "Line one\nline two\nline three\n\n" + ("word " * 70).strip() + "\n\nWhat do you think?"
    r = fc.check_linkedin(text)
    assert r["hook_lines"] == 3
    assert r["long_paragraphs"] == 1
    assert any("words, norm 150-300" in w for w in r["warnings"])
    assert any("hook is 3 lines" in w for w in r["warnings"])


def test_x_limit_and_hook_number():
    r = fc.check_x("No number here.\n---\n" + "a" * 281)
    assert r["posts"] == 2 and r["chars"][1] == 281
    assert "x: hook has no number" in r["warnings"]
    assert any("post 2 is 281 characters" in w for w in r["warnings"])


def test_short_out_of_range_and_unreadable(tmp_path):
    p = tmp_path / "short.json"
    p.write_text(json.dumps({"scenes": [{"seconds": 10}, {"seconds": 5}]}))
    assert fc.check_short(p)["warnings"] == ["short: 15 s, norm 30-60 s"]
    p.write_text("not json")
    assert fc.check_short(p)["warnings"] == ["short: short.json is unreadable"]


def test_judge_file_records_format(tmp_path, monkeypatch):
    folder = write_post(tmp_path / "content" / "2026-W47" / "2026-11-16-dsa-p2", "Short body.")
    monkeypatch.setattr(judge_file.v, "post_folders", lambda root, week: [folder])
    scores = {"2026-11-16-dsa-p2": {"scores": {k: 5 for k in judge_file.gate.RUBRIC}, "notes": "ok"}}
    data = judge_file.build(tmp_path, "2026-W47", scores)
    fmt = data["posts"]["2026-11-16-dsa-p2"]["format"]
    assert fmt["linkedin"]["words"] == 2
    assert "linkedin: no open question at the end" in fmt["warnings"]


SOURCE_WARNING = "sources: the post states numbers but has no source and no reproducing script (*.py + *.expected)"


def test_numbers_with_no_source_and_no_script_warn(tmp_path):
    report = fc.check_folder(write_post(tmp_path / "p", GOOD_LINKEDIN))
    assert report["sources"]["states_numbers"] is True
    assert report["sources"]["sources"] == 0 and report["sources"]["scripts"] == []
    assert SOURCE_WARNING in report["warnings"]


def test_reproducing_script_needs_a_matching_expected_file(tmp_path):
    folder = write_post(tmp_path / "p", GOOD_LINKEDIN)
    (folder / "numbers.py").write_text("print(128)\n")
    assert SOURCE_WARNING in fc.check_folder(folder)["warnings"]
    (folder / "numbers.expected").write_text("128\n")
    report = fc.check_folder(folder)
    assert report["sources"]["scripts"] == ["numbers.py"]
    assert SOURCE_WARNING not in report["warnings"]


def test_a_source_link_is_enough(tmp_path):
    folder = write_post(tmp_path / "p", GOOD_LINKEDIN)
    post = folder / "post.md"
    post.write_text(post.read_text().replace("sources: []", "sources: [https://example.com/paper]"))
    report = fc.check_folder(folder)
    assert report["sources"]["sources"] == 1
    assert SOURCE_WARNING not in report["warnings"]


def test_no_numbers_needs_no_source():
    r = fc.check_sources({"sources": []}, {"linkedin": "No digits here.\n\nPart 2 of my notes.\n\n#Python3"}, Path("/nonexistent"))
    assert r["states_numbers"] is False and r["warnings"] == []


def test_ai_eng_p3_passes_through_its_script():
    folder = ROOT / "content" / "2026-W48" / "2026-11-26-ai-eng-p3"
    report = fc.check_folder(folder)
    assert report["sources"]["states_numbers"] is True
    assert report["sources"]["sources"] == 0
    assert "format_vs_judge.py" in report["sources"]["scripts"]
    assert SOURCE_WARNING not in report["warnings"]
