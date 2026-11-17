import datetime as dt
import hashlib
import struct
import sys
from pathlib import Path

import pytest
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import validate as v  # noqa: E402

CAL = {
    "pillars": {"learning-in-public": {"target": 0.5}, "climate-materials": {"target": 0.5}},
    "series": {
        "dsa-in-java": {"pillar": "learning-in-public", "kind": "post"},
        "climate-ai": {"pillar": "climate-materials", "kind": "post", "sources_required": True},
    },
    "weeks": [{"week": "2026-W47", "items": [
        {"date": dt.date(2026, 11, 16), "series": "dsa-in-java", "part": 2, "slug": "dsa-p2", "topic": "t",
         "short": {"publish_at": "2026-11-17T19:00:00+07:00", "topic": "s"}},
        {"date": dt.date(2026, 11, 20), "series": "climate-ai", "part": 1, "slug": "climate-p1", "topic": "t"},
    ]}],
}
BODY = " ".join(["word"] * 200)


def post_text(**over):
    meta = {"date": dt.date(2026, 11, 20), "series": "climate-ai", "part": 1, "title": "T",
            "channels": ["linkedin", "facebook", "telegram", "x_manual"], "short_publish_at": None,
            "sources": ["https://example.org/paper"], "image_alt": "alt", "status": "approved"}
    sections = {"linkedin": f"3 things. {BODY}\n\nPart 1 of my Climate x AI notes.\n\n#a #b #c",
                "x": "3 things about weather models.", "facebook": " ".join(["word"] * 90),
                "telegram": "short", "youtube": None}
    for k, val in over.items():
        (sections if k in sections else meta)[k] = val
    out = "---\n" + yaml.safe_dump(meta) + "---\n"
    for name, text in sections.items():
        if text is not None:
            out += f"\n## {name}\n\n{text}\n"
    return out


def make_mp4(path, w=1080, h=1920, secs=45):
    tkhd = b"\x00" * 76 + struct.pack(">II", w << 16, h << 16)
    tkhd = struct.pack(">I4s", 8 + len(tkhd), b"tkhd") + tkhd
    trak = struct.pack(">I4s", 8 + len(tkhd), b"trak") + tkhd
    mvhd = b"\x00" * 12 + struct.pack(">II", 1000, secs * 1000) + b"\x00" * 80
    mvhd = struct.pack(">I4s", 8 + len(mvhd), b"mvhd") + mvhd
    moov = struct.pack(">I4s", 8 + len(mvhd) + len(trak), b"moov") + mvhd + trak
    path.write_bytes(struct.pack(">I4s", 16, b"ftyp") + b"isom\x00\x00\x00\x00" + moov)


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "content").mkdir()
    (tmp_path / "tools").mkdir()
    (tmp_path / "content" / "calendar.yaml").write_text(yaml.safe_dump(CAL))
    sha = lambda s: hashlib.sha256(s.encode()).hexdigest()  # noqa: E731
    (tmp_path / "tools" / "banned_terms.yaml").write_text(
        yaml.safe_dump({"token_sha256": [sha("zebracorp"), sha("acme widgets"), sha("zz billing")]}))
    (tmp_path / "tools" / "banned_terms.local.yaml").write_text(
        yaml.safe_dump({"patterns": [r"\bZZ[-_][A-Za-z0-9]+"]}))
    return tmp_path


def add_post(repo, name="2026-11-20-climate-p1", image=(1200, 1200), **over):
    folder = repo / "content" / "2026-W47" / name
    folder.mkdir(parents=True)
    (folder / "post.md").write_text(post_text(**over))
    if image:
        Image.new("RGB", image).save(folder / "image.png")
    return folder


def errors(repo):
    return v.validate(repo).errors


def test_good_post_passes(repo):
    add_post(repo)
    rep = v.validate(repo)
    assert rep.errors == [] and rep.warnings == []


def test_x_over_280_fails(repo):
    add_post(repo, x="x" * 281)
    assert any("x post 1 is 281" in e for e in errors(repo))


def test_x_counts_emoji_as_two():
    assert v.x_length("a" * 278 + "🧵") == 280
    assert v.x_length("it’s — fine") == 11


def test_linkedin_over_3000_and_link_fail(repo):
    add_post(repo, linkedin="x" * 3001 + " https://example.org")
    errs = errors(repo)
    assert any("limit 3000" in e for e in errs) and any("contains a link" in e for e in errs)


def test_wrong_image_size_fails(repo):
    add_post(repo, image=(1200, 630))
    assert any("1200x630" in e for e in errors(repo))


def test_missing_image_fails_when_approved_but_only_warns_for_draft(repo):
    add_post(repo, image=None)
    assert any("image.png is missing" in e for e in errors(repo))
    (repo / "content/2026-W47/2026-11-20-climate-p1/post.md").write_text(post_text(status="draft"))
    rep = v.validate(repo)
    assert rep.ok and any("image.png is missing" in w for w in rep.warnings)


def test_date_not_in_calendar_fails(repo):
    add_post(repo, name="2026-11-18-climate-p1", date=dt.date(2026, 11, 18))
    assert any("not in content/calendar.yaml" in e for e in errors(repo))


def test_series_part_and_folder_must_match_calendar(repo):
    add_post(repo, name="2026-11-20-wrong", part=7)
    errs = errors(repo)
    assert any("part is 7" in e for e in errs) and any("folder should be named" in e for e in errs)


def test_climate_needs_sources(repo):
    add_post(repo, sources=[])
    assert any("needs at least one source" in e for e in errors(repo))


@pytest.mark.parametrize("text", ["I built this at Acme  Widgets.", "at ACME-Widgets we", "from zebracorp days",
                                  "the ZZ-Billing service", "see ZZ-123", "https://claude.ai/chat/abc"])
def test_banned_terms_fail(repo, text):
    add_post(repo, telegram=text)
    assert any("banned term" in e for e in errors(repo))


def test_public_hashes_work_without_the_local_file(repo):
    (repo / "tools" / "banned_terms.local.yaml").unlink()
    add_post(repo, telegram="at ACME-Widgets we")
    assert any("banned term: acme widgets" in e for e in errors(repo))


def test_banned_terms_do_not_fire_on_normal_text(repo):
    add_post(repo, telegram="ZZZ batteries, a widgets shop called Acme-like, Claude is a model.")
    assert errors(repo) == []


def test_real_public_list_holds_only_hashes():
    cfg = yaml.safe_load((ROOT / "tools" / "banned_terms.yaml").read_text())
    assert set(cfg) == {"token_sha256"}
    assert all(len(x) == 64 and set(x) <= set("0123456789abcdef") for x in cfg["token_sha256"])


def test_committed_secret_fails(repo):
    add_post(repo)
    (repo / "notes.md").write_text("token gho_" + "a" * 36)
    assert any("committed secret" in e for e in errors(repo))


def short_post(repo, **mp4):
    folder = add_post(repo, name="2026-11-16-dsa-p2", date=dt.date(2026, 11, 16), series="dsa-in-java", part=2,
                      sources=[], channels=["linkedin", "x_manual", "youtube"], facebook=None, telegram=None,
                      linkedin=f"3 things. {BODY}\n\nPart 2 of my DSA in Java notes.\n\n#a #b #c",
                      short_publish_at="2026-11-17T19:00:00+07:00", youtube="Java == vs equals in 45s #Shorts\nDesc")
    make_mp4(folder / "short.mp4", **mp4)
    (folder / "short.srt").write_text("1\n00:00:00,000 --> 00:00:02,000\nHi\n")
    return folder


def test_short_passes(repo):
    short_post(repo)
    assert errors(repo) == []


def test_short_wrong_size_and_length_fail(repo):
    short_post(repo, w=1920, h=1080, secs=75)
    errs = errors(repo)
    assert any("1920x1080" in e for e in errs) and any("75.0s" in e for e in errs)


def test_short_needs_srt_and_shorts_tag(repo):
    folder = short_post(repo)
    (folder / "short.srt").unlink()
    (folder / "post.md").write_text((folder / "post.md").read_text().replace(" #Shorts", ""))
    errs = errors(repo)
    assert any("short.srt is missing" in e for e in errs) and any("#Shorts" in e for e in errs)


def test_short_time_must_match_calendar(repo):
    folder = short_post(repo)
    (folder / "post.md").write_text((folder / "post.md").read_text().replace("T19:00", "T20:00"))
    assert any("the calendar says" in e for e in errors(repo))


def test_calendar_rejects_wrong_week_and_weekend_post(repo):
    cal = yaml.safe_load(yaml.safe_dump(CAL))
    cal["weeks"][0]["items"][1]["date"] = dt.date(2026, 11, 28)
    (repo / "content" / "calendar.yaml").write_text(yaml.safe_dump(cal))
    errs = errors(repo)
    assert any("belongs to 2026-W48" in e for e in errs) and any("must fall on a weekday" in e for e in errs)


def test_real_calendar_and_ledger_are_valid():
    rep = v.Report()
    ledger = v.check_work(v.load_work(ROOT), rep, ROOT / "content" / "work.yaml")
    cal = v.load_calendar(ROOT)
    by_date = v.check_calendar(cal, rep, ROOT / "content" / "calendar.yaml", ledger)
    assert rep.errors == []
    assert len(ledger) >= 5
    for d, item in by_date.items():
        if v.needs_work(d):
            assert item["work"] and set(item["work"]) <= set(ledger), d


# ---------------------------------------------------------------- work ledger

W48 = dt.date(2026, 11, 25)
LEDGER = {
    "repos": {"public": ["demo-lab"], "private": ["course-vi"]},
    "entries": [
        {"id": "demo-unit", "repo": "demo-lab", "ref": "https://github.com/nghiep-pham-ecosys/demo-lab/pull/3",
         "merged": dt.date(2026, 11, 17), "what": "A toy unit with tests."},
        {"id": "course-rag", "repo": "course-vi", "ref": "private@abc1234",
         "merged": dt.date(2026, 11, 16), "what": "A course module on retrieval."},
    ],
}


def plan_w48(repo, work="demo-unit", ledger=None, **item_over):
    cal = yaml.safe_load(yaml.safe_dump(CAL))
    item = {"date": W48, "series": "climate-ai", "part": 2, "slug": "climate-p2", "topic": "t", **item_over}
    if work is not None:
        item["work"] = work
    cal["weeks"].append({"week": "2026-W48", "items": [item]})
    (repo / "content" / "calendar.yaml").write_text(yaml.safe_dump(cal))
    (repo / "content" / "work.yaml").write_text(yaml.safe_dump(ledger or LEDGER))


def add_w48_post(repo, **over):
    folder = repo / "content" / "2026-W48" / "2026-11-25-climate-p2"
    folder.mkdir(parents=True)
    (folder / "post.md").write_text(post_text(date=W48, part=2, linkedin=f"3 things. {BODY}\n\n"
                                              "Part 2 of my Climate x AI notes.\n\n#a #b #c", **over))
    Image.new("RGB", (1200, 1200)).save(folder / "image.png")
    return folder


def test_item_with_ledger_work_passes(repo):
    plan_w48(repo)
    add_w48_post(repo, work="demo-unit")
    assert errors(repo) == []


def test_item_from_w48_without_work_fails(repo):
    plan_w48(repo, work=None)
    assert any("every item needs work" in e for e in errors(repo))


def test_items_before_w48_need_no_work(repo):
    (repo / "content" / "work.yaml").write_text(yaml.safe_dump(LEDGER))
    add_post(repo)
    assert errors(repo) == []


def test_unknown_work_and_work_merged_after_the_post_fail(repo):
    plan_w48(repo, work=["demo-unit", "nope"])
    assert any("'nope' is not in content/work.yaml" in e for e in errors(repo))
    late = yaml.safe_load(yaml.safe_dump(LEDGER))
    late["entries"][0]["merged"] = dt.date(2026, 11, 26)
    plan_w48(repo, ledger=late)
    assert any("merged on 2026-11-26, after 2026-11-25" in e for e in errors(repo))


def test_post_from_w48_needs_the_calendar_work(repo):
    plan_w48(repo)
    folder = add_w48_post(repo)
    assert any("post: from 2026-W48 every item needs work" in e for e in errors(repo))
    (folder / "post.md").write_text(post_text(date=W48, part=2, work="course-rag"))
    assert any("but the calendar says ['demo-unit']" in e for e in errors(repo))


def test_ledger_rejects_an_unlisted_repo_without_naming_it(repo):
    bad = yaml.safe_load(yaml.safe_dump(LEDGER))
    bad["entries"][0]["repo"] = "secret-side-thing"
    plan_w48(repo, ledger=bad)
    errs = errors(repo)
    assert any("repo is not listed under repos" in e for e in errs)
    assert not any("secret-side-thing" in e for e in errs)


@pytest.mark.parametrize("field, value, message", [
    ("ref", "https://github.com/nghiep-pham-ecosys/demo-lab/commit/abc", "merged pull request URL"),
    ("ref", "https://github.com/someone-else/demo-lab/pull/3", "merged pull request URL"),
    ("merged", "soon", "merged must be a date"),
    ("merged", dt.date(2099, 1, 1), "is in the future"),
    ("what", "", "what is empty"),
    ("id", "Demo_Unit", "lowercase words"),
])
def test_ledger_entry_rules(repo, field, value, message):
    bad = yaml.safe_load(yaml.safe_dump(LEDGER))
    bad["entries"][0][field] = value
    plan_w48(repo, work="course-rag", ledger=bad)
    assert any(message in e for e in errors(repo))


def test_private_repo_is_named_by_sha_never_linked(repo):
    bad = yaml.safe_load(yaml.safe_dump(LEDGER))
    bad["entries"][1]["ref"] = "https://github.com/nghiep-pham-ecosys/course-vi/pull/1"
    plan_w48(repo, ledger=bad)
    errs = errors(repo)
    assert any("private@<commit sha>" in e for e in errs) and any("named, never linked" in e for e in errs)


def test_post_linking_a_private_repo_fails(repo):
    plan_w48(repo)
    add_w48_post(repo, work="demo-unit", telegram="code: github.com/nghiep-pham-ecosys/course-vi/tree/main")
    assert any("links a private repo" in e for e in errors(repo))


def test_duplicate_ids_fail(repo):
    dup = yaml.safe_load(yaml.safe_dump(LEDGER))
    dup["entries"].append(dict(dup["entries"][0]))
    plan_w48(repo, ledger=dup)
    assert any("id appears twice" in e for e in errors(repo))


def test_parked_items_have_a_series_and_no_date(repo):
    cal = yaml.safe_load(yaml.safe_dump(CAL))
    cal["parked"] = [{"series": "dsa-in-java", "topic": "ok"}, {"series": "nope", "topic": "x"},
                     {"series": "dsa-in-java", "topic": "y", "date": dt.date(2026, 12, 1)}]
    (repo / "content" / "calendar.yaml").write_text(yaml.safe_dump(cal))
    errs = errors(repo)
    assert any("parked item 2" in e for e in errs) and any("parked item 3: a parked item has no date" in e
                                                             for e in errs)
    assert not any("parked item 1" in e for e in errs)
