"""Plant one bug at a time in three process-sim-lab models and see which of their tests catch it.

Companion script of the deep dive "Three process models, each tested against a closed-form answer"
(2026-12-05). Each mutation replaces one line of the model source in a temporary copy of the
repo, then runs that model's own test file. A test that still passes did not notice the bug.

Run (Python 3.12, stdlib only), with a checkout of process-sim-lab at the merge commit of PR #7,
which holds the CSTR (PR #2), the PFR (PR #6) and the flash drum (PR #7):

    git clone https://github.com/nghiep-pham-ecosys/process-sim-lab
    git -C process-sim-lab checkout 370a2aa3693a70c75b411a6e2a9407558c1c44bf
    python closed_form_mutations.py process-sim-lab
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

UNITS = "src/process_sim_lab/units/"
MUTATIONS = [  # (label, file, line as merged, line with the bug, test file)
    ("CSTR: plug-flow formula", UNITS + "cstr.py",
     "conversion = damkohler / (1.0 + damkohler)", "conversion = 1.0 - math.exp(-damkohler)", "test_cstr"),
    ("PFR: stirred-tank formula", UNITS + "pfr.py",
     "conversion = -math.expm1(-damkohler)", "conversion = damkohler / (1.0 + damkohler)", "test_pfr"),
    ("PFR: 1 - exp(-Da) instead of expm1", UNITS + "pfr.py",
     "conversion = -math.expm1(-damkohler)", "conversion = 1.0 - math.exp(-damkohler)", "test_pfr"),
    ("Flash: z_i left out of Rachford-Rice", UNITS + "flash.py",
     "return sum(zi * (k_values[c] - 1.0)", "return sum(1.0 * (k_values[c] - 1.0)", "test_flash"),
    ("Flash: no bubble-point check", UNITS + "flash.py",
     "if sum(z[c] * k[c] for c in z) - 1.0 <= 0.0:", "if False:", "test_flash"),
]


def run(repo: Path, test: str) -> tuple[int, int, list[str]]:
    out = subprocess.run([sys.executable, "-m", "unittest", "-v", f"tests.{test}"], cwd=repo,
                         env={"PYTHONPATH": str(repo / "src"), "PYTHONDONTWRITEBYTECODE": "1"},
                         capture_output=True, text=True).stderr
    # One line per test, plus one per failing subTest: "test_x (...) [(z1=0.3)] ... ok|FAIL|ERROR".
    lines = re.findall(r"^\s*(test_\w+) \(.*?\.\.\. ?(ok|FAIL|ERROR)?$", out, re.M)
    names = {name for name, _ in lines}
    failed = sorted({name for name, status in lines if status in ("FAIL", "ERROR")})
    return len(names) - len(failed), len(names), failed


src = Path(sys.argv[1]).resolve()
for label, rel, old, new, test in [("no bug", None, None, None, t) for t in ("test_cstr", "test_pfr", "test_flash")] + MUTATIONS:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        shutil.copytree(src, repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        if rel:
            path = repo / rel
            text = path.read_text()
            assert text.count(old) == 1, f"{label}: line not found once"
            text = text.replace(old, new)
            if "math." in new and "\nimport math\n" not in text:   # the bug needs math
                text = text.replace("from __future__ import annotations\n",
                                    "from __future__ import annotations\n\nimport math\n", 1)
            path.write_text(text)
        passed, total, failed = run(repo, test)
    print(f"{label:38s} {test:10s} {passed:2d}/{total} pass; caught by: {', '.join(failed) or 'nothing'}")
