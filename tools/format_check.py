#!/usr/bin/env python3
"""Per-channel format check of a week's posts against common channel norms. Never calls a model.

    python tools/format_check.py --week 2026-W47

It measures length and structure only (LinkedIn, Facebook, X, the Short). The result is
informational: tools/judge_file.py writes it into judge.json under "format" so the weekly review
can show it next to the scores. The silent-approval gate does not read it.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate as v  # noqa: E402

LINKEDIN_WORDS = (150, 300)
LINKEDIN_HOOK_LINES = 2
PARAGRAPH_MAX_LINES = 3
PARAGRAPH_MAX_WORDS = 60
FACEBOOK_WORDS = (80, 120)
X_CHARS = v.X_LIMIT
SHORT_SECONDS = v.SHORT_SECONDS
_HASHTAG_LINE = re.compile(r"^(#\w+\s*)+$")
_SIGN_OFF = re.compile(r"(?i)^part \d+ of my\b")


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _prose(paragraphs: list[str]) -> list[str]:
    """Paragraphs without the hashtag line and the 'Part N of my ... notes' sign-off."""
    return [p for p in paragraphs if not _HASHTAG_LINE.match(p) and not _SIGN_OFF.match(p)]


def check_linkedin(text: str) -> dict:
    paras = _prose(_paragraphs(text))
    words = v.word_count("\n".join(paras))
    hook_lines = len(paras[0].splitlines()) if paras else 0
    long_paras = sum(1 for p in paras if len(p.splitlines()) > PARAGRAPH_MAX_LINES or v.word_count(p) > PARAGRAPH_MAX_WORDS)
    question = any("?" in p for p in paras[-2:])
    warnings = []
    if not LINKEDIN_WORDS[0] <= words <= LINKEDIN_WORDS[1]:
        warnings.append(f"linkedin: {words} words, norm {LINKEDIN_WORDS[0]}-{LINKEDIN_WORDS[1]}")
    if hook_lines > LINKEDIN_HOOK_LINES:
        warnings.append(f"linkedin: hook is {hook_lines} lines, norm 1-{LINKEDIN_HOOK_LINES}")
    if long_paras:
        warnings.append(f"linkedin: {long_paras} paragraph(s) over {PARAGRAPH_MAX_LINES} lines or {PARAGRAPH_MAX_WORDS} words")
    if not question:
        warnings.append("linkedin: no open question at the end")
    return {"words": words, "hook_lines": hook_lines, "long_paragraphs": long_paras,
            "ends_with_question": question, "warnings": warnings}


def check_facebook(text: str) -> dict:
    words = v.word_count("\n".join(_prose(_paragraphs(text))))
    warnings = [] if FACEBOOK_WORDS[0] <= words <= FACEBOOK_WORDS[1] else [
        f"facebook: {words} words, norm {FACEBOOK_WORDS[0]}-{FACEBOOK_WORDS[1]}"]
    return {"words": words, "warnings": warnings}


def check_x(text: str) -> dict:
    posts = v.split_x_posts(text)
    lengths = [v.x_length(p) for p in posts]
    hook = posts[0].splitlines()[0] if posts else ""
    has_number = bool(re.search(r"\d", hook))
    warnings = [f"x: post {i + 1} is {n} characters, limit {X_CHARS}" for i, n in enumerate(lengths) if n > X_CHARS]
    if not has_number:
        warnings.append("x: hook has no number")
    return {"posts": len(posts), "chars": lengths, "hook_has_number": has_number, "warnings": warnings}


def check_short(path: Path) -> dict:
    try:
        scenes = json.loads(path.read_text(encoding="utf-8")).get("scenes") or []
        seconds = round(sum(float(s.get("seconds", 0)) for s in scenes), 1)
    except (OSError, ValueError, AttributeError, TypeError):
        return {"seconds": None, "warnings": ["short: short.json is unreadable"]}
    warnings = [] if SHORT_SECONDS[0] <= seconds <= SHORT_SECONDS[1] else [
        f"short: {seconds:g} s, norm {SHORT_SECONDS[0]:g}-{SHORT_SECONDS[1]:g} s"]
    return {"seconds": seconds, "warnings": warnings}


def check_folder(folder: Path) -> dict:
    """Format report of one post folder: one entry per channel present, plus all warnings."""
    _, sections = v.parse_post(folder / "post.md")
    report: dict = {}
    if sections.get("linkedin"):
        report["linkedin"] = check_linkedin(sections["linkedin"])
    if sections.get("facebook"):
        report["facebook"] = check_facebook(sections["facebook"])
    if sections.get("x"):
        report["x"] = check_x(sections["x"])
    if (folder / "short.json").exists():
        report["short"] = check_short(folder / "short.json")
    report["warnings"] = [w for entry in report.values() for w in entry["warnings"]]
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--week", required=True)
    ap.add_argument("--root", type=Path, default=v.ROOT)
    args = ap.parse_args(argv)
    for folder in v.post_folders(args.root, args.week):
        warnings = check_folder(folder)["warnings"]
        print(f"{'OK  ' if not warnings else 'WARN'} {folder.name}" + ("" if not warnings else ": " + "; ".join(warnings)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
