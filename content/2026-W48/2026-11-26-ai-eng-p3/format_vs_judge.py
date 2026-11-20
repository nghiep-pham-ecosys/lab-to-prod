"""The numbers behind the post: what the rule-based format check and the LLM judge each caught
on the five 2026-W47 posts, as they stood when the check was merged (lab-to-prod pull request 27).

Run from the repository root (needs git history and PyYAML):
    uv run --with-requirements tools/requirements.txt python content/2026-W48/2026-11-26-ai-eng-p3/format_vs_judge.py

It reads the W47 posts and judge.json at the merge commit with `git show`, runs
tools/format_check.py on each LinkedIn section (the file is unchanged since that commit), and
counts the judge notes that mention a question. It prints the judge's pass rule and rubric and the
write-post rule about questions at that commit. Then it runs the same rule on two toy endings to
show its limit: a "?" anywhere in the last two paragraphs passes, even a yes/no line.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import format_check as fc  # noqa: E402
import validate as v  # noqa: E402

MERGE = "20ea834"  # merge commit of lab-to-prod pull request 27
WEEK = "content/2026-W47"


def at_merge(path: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), "show", f"{MERGE}:{path}"],
                          check=True, capture_output=True, text=True).stdout


judge = json.loads(at_merge(f"{WEEK}/judge.json"))
no_question = 0
with tempfile.TemporaryDirectory() as tmp:
    for name, entry in judge["posts"].items():
        post = Path(tmp) / f"{name}.md"
        post.write_text(at_merge(f"{WEEK}/{name}/post.md"), encoding="utf-8")
        _, sections = v.parse_post(post)
        r = fc.check_linkedin(sections["linkedin"])
        no_question += not r["ends_with_question"]
        notes_say_question = "question" in entry["notes"].lower()
        print(f"{name:22} words={r['words']:3}  open question={str(r['ends_with_question']):5}  "
              f"judge mean={entry['mean']}  voice={entry['scores']['voice']}  notes mention a question={notes_say_question}")

print(f"format check: {no_question} of {len(judge['posts'])} LinkedIn posts with no open question at the end")
passed = sum(1 for e in judge["posts"].values() if e["mean"] >= 4 and min(e["scores"].values()) >= 3)
print(f"judge: {passed} of {len(judge['posts'])} passed ({judge['pass_rule']}); rubric: {', '.join(judge['rubric'])}")

# The writing rule the W47 posts followed, as it stood at the same commit.
rule = [line for line in at_merge(".claude/skills/write-post/SKILL.md").splitlines() if "question" in line.lower()]
print(f"write-post rule at merge: {rule}")

# Toy example: the rule counts a question mark, it does not read the question.
# This is the line in tools/format_check.py that the post quotes; paras are the prose paragraphs.
def question_rule(paras):
    question = any("?" in p for p in paras[-2:])
    return question


bait = "Hook with 5 numbers.\n\nBody.\n\nAgree?\n\nPart 3 of my AI Engineering notes.\n\n#AI"
plain = "Hook with 5 numbers.\n\nBody.\n\nThat is the lesson.\n\nPart 3 of my AI Engineering notes.\n\n#AI"
for label, text in (("toy ending 'Agree?'", bait), ("toy ending with no question", plain)):
    paras = fc._prose(fc._paragraphs(text))
    assert question_rule(paras) == fc.check_linkedin(text)["ends_with_question"]
    print(f"{label:28} -> open question = {question_rule(paras)}")
