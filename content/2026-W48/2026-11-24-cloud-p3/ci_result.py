"""Toy example: one aggregate CI check that a merge step can read.

The real check is a GitHub Actions job with `if: always()` and `needs:` on every other job.
This script replays its rule on four made-up runs and compares it with a naive rule.

Run: python ci_result.py   (standard library only)
"""

MUST_SUCCEED = ("test", "gitleaks")       # jobs that must run and pass
ALLOWED = ("success", "skipped")          # what every other job may end as


def naive(results):
    """Green when nothing failed."""
    return all(r != "failure" for r in results.values())


def ci_result(results):
    """Green when the key jobs succeeded and no job failed or was cancelled."""
    key_ok = all(results.get(job) == "success" for job in MUST_SUCCEED)
    rest_ok = all(r in ALLOWED for r in results.values())
    return key_ok and rest_ok


RUNS = {
    "normal PR": {"test": "success", "gitleaks": "success",
                  "live-smoke": "skipped", "model-sync": "skipped"},
    "tests skipped": {"test": "skipped", "gitleaks": "success",
                      "live-smoke": "skipped", "model-sync": "skipped"},
    "scan cancelled": {"test": "success", "gitleaks": "cancelled",
                       "live-smoke": "skipped", "model-sync": "skipped"},
    "test failed": {"test": "failure", "gitleaks": "success",
                    "live-smoke": "skipped", "model-sync": "skipped"},
}

for name, results in RUNS.items():
    print(f"{name:15} naive={'green' if naive(results) else 'red':5}  "
          f"ci_result={'green' if ci_result(results) else 'red'}")

bad = [n for n in RUNS if n != "normal PR"]
leaks = sum(naive(RUNS[n]) for n in bad)
print(f"naive rule lets {leaks} of {len(bad)} broken runs through")
print(f"ci_result lets {sum(ci_result(RUNS[n]) for n in bad)} of {len(bad)} through")
