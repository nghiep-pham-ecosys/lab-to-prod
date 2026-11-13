import csv
import datetime as dt
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import automerge_gate as gate  # noqa: E402
from metrics import collect  # noqa: E402
from test_publish import ENV, MONDAY, Resp, ctx_for, repo, write_post  # noqa: E402,F401


class MetricsHTTP:
    def __init__(self, fail=(), fb_days_left=40):
        self.fail, self.fb_days_left = fail, fb_days_left

    def get(self, url, **kw):
        if any(f in url for f in self.fail):
            return Resp(500, {"error": "boom"})
        if "debug_token" in url:
            exp = int((MONDAY + dt.timedelta(days=self.fb_days_left)).timestamp())
            return Resp(200, {"data": {"is_valid": True, "expires_at": 0, "data_access_expires_at": exp}})
        if url.endswith("/42"):
            return Resp(200, {"followers_count": 12})
        if "graph.facebook.com" in url:
            return Resp(200, {"reactions": {"summary": {"total_count": 7}}, "comments": {"summary": {"total_count": 2}}})
        if "/channels" in url:
            return Resp(200, {"items": [{"statistics": {"subscriberCount": "30"}}]})
        if "/videos" in url:
            return Resp(200, {"items": [{"id": "VIDEO123", "statistics": {"viewCount": "150", "likeCount": "9", "commentCount": "1"}}]})
        if "youtubeanalytics" in url:
            return Resp(200, {"rows": [["VIDEO123", 21, 46.5]]})
        if "getChatMemberCount" in url:
            return Resp(200, {"ok": True, "result": 55})
        if "articles/me/all" in url:
            return Resp(200, [{"id": 77, "url": "https://dev.to/x/why", "page_views_count": 90, "public_reactions_count": 4, "comments_count": 0}])
        raise AssertionError(url)

    def post(self, url, **kw):
        if "oauth2.googleapis.com" in url:
            return Resp(400 if "oauth2" in self.fail else 200, {"access_token": "ya29"})
        raise AssertionError(url)


STATE = {"2026-11-16": {"facebook": {"id": "42_777", "url": "fb"}, "youtube": {"id": "VIDEO123", "url": "yt"}},
         "article:why": {"devto": {"id": 77, "url": "dev"}}}


def rows(repo):
    with (repo / "metrics" / "metrics.csv").open() as fh:
        return {(r["item"], r["channel"]): r for r in csv.DictReader(fh)}


@pytest.fixture
def mrepo(repo):
    (repo / "metrics" / "inbox").mkdir(parents=True)
    (repo / "published.json").write_text(json.dumps(STATE))
    return repo


def test_collect_writes_one_row_per_item_and_channel(mrepo):
    (mrepo / "metrics/inbox/linkedin-2026-W47.csv").write_text("date,impressions,reactions,comments,shares,followers\n2026-11-16,412,18,3,1,\n,,,,,1530\n")
    assert collect.collect(ctx_for(mrepo, MONDAY, http=MetricsHTTP())) == 0
    r = rows(mrepo)
    assert r[("2026-11-16", "facebook")]["reactions"] == "7" and r[("_account", "facebook")]["followers"] == "12"
    assert r[("2026-11-16", "youtube")]["views"] == "150" and r[("2026-11-16", "youtube")]["avg_view_pct"] == "46.5"
    assert r[("_account", "telegram")]["followers"] == "55" and r[("article:why", "devto")]["views"] == "90"
    assert r[("2026-11-16", "linkedin")]["impressions"] == "412" and r[("_account", "linkedin")]["followers"] == "1530"


def test_collect_twice_on_the_same_day_does_not_duplicate(mrepo):
    for _ in range(2):
        collect.collect(ctx_for(mrepo, MONDAY, http=MetricsHTTP()))
    assert len(rows(mrepo)) == 6
    assert len((mrepo / "metrics/metrics.csv").read_text().splitlines()) == 7


def test_one_failing_source_keeps_the_others(mrepo):
    ctx = ctx_for(mrepo, MONDAY, http=MetricsHTTP(fail=("api.telegram.org",)))
    assert collect.collect(ctx) == 1
    assert ("_account", "telegram") not in rows(mrepo) and ("2026-11-16", "youtube") in rows(mrepo)
    assert not any("111:tg-token" in line for line in ctx.log)


def test_unconnected_channels_are_skipped_not_failed(mrepo):
    env = {"FB_PAGE_ID": "42", "FB_PAGE_TOKEN": "fb-token"}
    ctx = ctx_for(mrepo, MONDAY, http=MetricsHTTP(), env=env)
    assert collect.collect(ctx) == 0
    assert ("_account", "facebook") in rows(mrepo)
    assert any("telegram: not connected" in line for line in ctx.log)
    partial = ctx_for(mrepo, MONDAY, http=MetricsHTTP(), env={**env, "TELEGRAM_BOT_TOKEN": "111:tg-token"})
    assert collect.collect(partial) == 1   # half-configured is still an error


def test_token_health(mrepo):
    ok = ctx_for(mrepo, MONDAY, http=MetricsHTTP(), env={**ENV, "LINKEDIN_TOKEN_ISSUED": "2026-11-14"})
    assert collect.check_tokens(ok) == 0
    late = ctx_for(mrepo, MONDAY, http=MetricsHTTP(fb_days_left=5), env={**ENV, "LINKEDIN_TOKEN_ISSUED": "2026-09-20"})
    assert collect.check_tokens(late) == 1
    text = "\n".join(late.log)
    assert "LinkedIn: token expires in 3 day(s)" in text and "Facebook: data access expires in 5 day(s)" in text
    assert collect.check_tokens(ctx_for(mrepo, MONDAY, http=MetricsHTTP(), env={})) == 0   # no secrets yet: nothing to warn about


def judge_file(repo, scores_by_post, stale=()):
    week = repo / "content" / "2026-W47"
    posts = {}
    for folder in sorted(p for p in week.iterdir() if p.is_dir()):
        if folder.name in scores_by_post:
            sha = "0" * 64 if folder.name in stale else gate.post_hash(folder)
            posts[folder.name] = {"sha256": sha, "scores": dict(zip(gate.RUBRIC, scores_by_post[folder.name])), "notes": "n"}
    (week / "judge.json").write_text(json.dumps({"week": "2026-W47", "posts": posts}))


GOOD = [5, 4, 5, 4, 5]
NAMES = ["2026-11-16-dsa-p2", "2026-11-17-ml-p1", "2026-11-18-ai-eng-p2"]


def test_gate_passes_when_every_post_scores_well(repo):
    judge_file(repo, dict.fromkeys(NAMES, GOOD))
    code, results = gate.gate(repo, "2026-W47")
    assert code == 0 and all(r == [] for r in results.values())


def test_gate_holds_only_the_failing_posts_and_sets_them_to_draft(repo):
    judge_file(repo, {NAMES[0]: GOOD, NAMES[1]: [5, 5, 5, 5, 2], NAMES[2]: [4, 4, 4, 3, 3]})
    code, results = gate.gate(repo, "2026-W47", apply=True)
    assert code == 0
    assert results[NAMES[0]] == [] and "below 3 on no_banned_info" in results[NAMES[1]][0] and "mean score 3.6" in results[NAMES[2]][0]
    assert "status: draft" in (repo / "content/2026-W47" / NAMES[1] / "post.md").read_text()
    assert "status: approved" in (repo / "content/2026-W47" / NAMES[0] / "post.md").read_text()


def test_gate_rejects_a_post_edited_after_judging_or_not_judged(repo):
    judge_file(repo, {NAMES[0]: GOOD, NAMES[1]: GOOD}, stale=(NAMES[1],))
    _, results = gate.gate(repo, "2026-W47")
    assert results[NAMES[1]] == ["post.md changed after it was judged"] and results[NAMES[2]] == ["not judged"]


def test_gate_refuses_to_merge_without_judge_json_or_when_nothing_passes(repo):
    assert gate.gate(repo, "2026-W47")[0] == 1
    judge_file(repo, dict.fromkeys(NAMES, [1, 1, 1, 1, 1]))
    assert gate.gate(repo, "2026-W47")[0] == 1


def test_gate_rejects_malformed_scores(repo):
    judge_file(repo, dict.fromkeys(NAMES, [5, 5, 5, 5, 9]))
    assert gate.gate(repo, "2026-W47")[0] == 1


def test_judge_file_adds_hashes_and_the_gate_accepts_it(repo, tmp_path):
    import judge_file
    from metrics import report
    scores = {n: {"scores": dict(zip(gate.RUBRIC, GOOD)), "notes": "ok"} for n in NAMES}
    data = judge_file.build(repo, "2026-W47", scores)
    (repo / "content/2026-W47/judge.json").write_text(json.dumps(data))
    assert data["posts"][NAMES[0]]["mean"] == 4.6 and gate.gate(repo, "2026-W47")[0] == 0
    with pytest.raises(ValueError):
        judge_file.build(repo, "2026-W47", {NAMES[0]: {"scores": {"voice": 5}}})
    with pytest.raises(ValueError):
        judge_file.build(repo, "2026-W47", {"not-a-folder": scores[NAMES[0]]})
    one = judge_file.build(repo, "2026-W47", {NAMES[1]: {"scores": dict(zip(gate.RUBRIC, [4, 4, 4, 4, 4]))}}, merge=True)
    assert set(one["posts"]) == set(NAMES) and one["posts"][NAMES[1]]["mean"] == 4.0


def test_weekly_report_tables(mrepo):
    from metrics import report
    collect.collect(ctx_for(mrepo, MONDAY, http=MetricsHTTP()))
    text = report.report(mrepo, "2026-W47")
    assert "| 2026-11-16 | Title dsa-p2 | facebook | published" in text
    assert "| 2026-11-16 | Title dsa-p2 | linkedin | not published" in text
    assert "| 2026-11-16 | youtube | - | 150 | 9 | 1 | - |" in text
    assert "| telegram | 55 | 55 | +0 |" in text and "On schedule: 3 of" in text
