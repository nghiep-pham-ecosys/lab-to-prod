"""tools/monthly_report.py on synthetic metrics and state (Example Co and Acme posts, year 2030)."""
import csv
import datetime as dt
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import monthly_report as mr  # noqa: E402

TZ = dt.timezone(dt.timedelta(hours=7))
FIELDS = ["measured_on", "item", "channel", "url", "impressions", "views", "reactions", "comments", "shares",
          "followers", "avg_view_seconds", "avg_view_pct"]


def csv_text(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, FIELDS)
    w.writeheader()
    for r in rows:
        w.writerow({**dict.fromkeys(FIELDS, ""), **r})
    return buf.getvalue()


def rec(at, **extra):
    return {"at": at, "url": "https://example.com/p", **extra}


META = {
    "2030-01-07": mr.Meta("Example Co queue", "ai-engineering", "2030-W02",
                          {"linkedin": "12 retries hid one bug.", "youtube": "Retries #Shorts"}),
    "2030-01-08": mr.Meta("Acme cache", "cloud-devops", "2030-W02", {"linkedin": "3 caches, one stale key."}, pdf=True),
    "2030-01-14": mr.Meta("Example Co flash drum", "simulation", "2030-W03", {"linkedin": "1 equation | 2 ends."}),
}
EXPERIMENTS = {"2030-W02": "baseline", "2030-W03": "hook opens with a number"}


def report(rows, state, month="2030-01", meta=META):
    return mr.build_report(month, csv_text(rows), state, meta, EXPERIMENTS, TZ)


def section(text, title):
    start = text.index(f"## {title}")
    end = text.find("\n## ", start + 1)
    return text[start:end if end != -1 else None]


# ---------------------------------------------------------------- engagement rate

def test_engagement_rate_is_engaged_over_reach():
    assert mr.engagement_rate("3", "1", "1", "100") == 0.05
    assert mr.engagement_rate("0", "0", "", "40") == 0.0


def test_engagement_rate_has_no_value_without_reach_or_counts():
    assert mr.engagement_rate("2", "0", "0", "0") is None
    assert mr.engagement_rate("2", "0", "0", "") is None
    assert mr.engagement_rate("", "", "", "50") is None


def test_impressions_win_over_views():
    p = mr.Post("k", "linkedin", dt.date(2030, 1, 7), mr.Meta("t"),
                {"impressions": "200", "views": "50", "reactions": "10", "comments": "", "shares": ""})
    assert p.reach == 200
    assert p.rate == 0.05


# ---------------------------------------------------------------- no data

def test_channel_without_metrics_is_no_data_never_zero():
    state = {"2030-01-07": {"linkedin": rec("2030-01-07T01:15:00+00:00"), "youtube": rec("2030-01-07T12:00:00+00:00")},
             "2030-01-08": {"linkedin": rec("2030-01-08T01:15:00+00:00")}}
    rows = [{"measured_on": "2030-01-20", "item": "2030-01-07", "channel": "youtube", "views": "40",
             "reactions": "2", "comments": "0"}]
    table = section(report(rows, state), "Per channel")
    assert "| linkedin | 2 | 0 | no data | no data | no data | no data | no data | no data |" in table
    # youtube is measured, but nobody measures its shares: that column is no data, not 0
    assert "| youtube | 1 | 1 | 40 | 2 | 0 | no data | no data | 5.0 % |" in table


def test_follower_change_comes_from_account_rows_in_the_month():
    state = {"2030-01-07": {"youtube": rec("2030-01-07T12:00:00+00:00")}}
    rows = [{"measured_on": "2029-12-31", "item": "_account", "channel": "youtube", "followers": "1"},
            {"measured_on": "2030-01-02", "item": "_account", "channel": "youtube", "followers": "10"},
            {"measured_on": "2030-01-30", "item": "_account", "channel": "youtube", "followers": "17"}]
    table = section(report(rows, state), "Per channel")
    assert "| youtube | 1 | 0 | no data | no data | no data | no data | +7 | no data |" in table


def test_proposals_ask_for_data_on_unmeasured_channels():
    state = {"2030-01-07": {"linkedin": rec("2030-01-07T01:15:00+00:00")}}
    text = section(report([], state), "Proposals for next month")
    assert "1. Measure the channels with no data before judging them: linkedin (1 posts" in text
    assert text.count("\n3. ") == 1


# ---------------------------------------------------------------- top and bottom

def _rated(n):
    """n youtube posts with rates 1 %, 2 %, ... n % on 100 views each."""
    state, rows = {}, []
    for i in range(1, n + 1):
        key = f"2030-01-{i:02d}"
        state[key] = {"youtube": rec(f"{key}T12:00:00+00:00")}
        rows.append({"measured_on": "2030-01-25", "item": key, "channel": "youtube", "views": "100",
                     "reactions": str(i), "comments": "0"})
    return state, rows


def _posts(state, rows):
    return mr.build_posts(state, mr.parse_metrics(csv_text(rows)), {}, TZ)


def test_top_and_bottom_three_by_rate():
    state, rows = _rated(8)
    top, bottom = mr.pick_top_bottom(_posts(state, rows))
    assert [p.key for p in top] == ["2030-01-08", "2030-01-07", "2030-01-06"]
    assert [p.key for p in bottom] == ["2030-01-01", "2030-01-02", "2030-01-03"]


def test_bottom_skips_top_posts_when_fewer_than_six():
    state, rows = _rated(4)
    top, bottom = mr.pick_top_bottom(_posts(state, rows))
    assert [p.key for p in top] == ["2030-01-04", "2030-01-03", "2030-01-02"]
    assert [p.key for p in bottom] == ["2030-01-01"]


def test_posts_without_a_rate_are_not_ranked_and_ties_prefer_reach():
    state = {"2030-01-01": {"youtube": rec("2030-01-01T12:00:00+00:00")},
             "2030-01-02": {"youtube": rec("2030-01-02T12:00:00+00:00")},
             "2030-01-03": {"youtube": rec("2030-01-03T12:00:00+00:00")},
             "2030-01-04": {"linkedin": rec("2030-01-04T01:00:00+00:00")}}
    rows = [{"measured_on": "2030-01-20", "item": "2030-01-01", "channel": "youtube", "views": "3", "reactions": "0"},
            {"measured_on": "2030-01-20", "item": "2030-01-02", "channel": "youtube", "views": "30", "reactions": "0"},
            {"measured_on": "2030-01-20", "item": "2030-01-03", "channel": "youtube", "views": "0", "reactions": "0"}]
    top, bottom = mr.pick_top_bottom(_posts(state, rows))
    assert [p.key for p in top] == ["2030-01-02", "2030-01-01"]
    assert bottom == []


def test_last_measurement_is_used():
    state = {"2030-01-07": {"youtube": rec("2030-01-07T12:00:00+00:00")}}
    rows = [{"measured_on": "2030-01-09", "item": "2030-01-07", "channel": "youtube", "views": "10", "reactions": "5"},
            {"measured_on": "2030-01-20", "item": "2030-01-07", "channel": "youtube", "views": "100", "reactions": "5"}]
    (p,) = _posts(state, rows)
    assert p.reach == 100 and p.rate == 0.05


def test_top_table_shows_hook_and_series_and_escapes_pipes():
    state = {"2030-01-14": {"linkedin": rec("2030-01-14T01:15:00+00:00")}}
    rows = [{"measured_on": "2030-01-20", "item": "2030-01-14", "channel": "linkedin", "impressions": "300",
             "reactions": "6", "comments": "3", "shares": "0"}]
    text = section(report(rows, state), "Top and bottom posts")
    assert "| 3.0 % | 300 | linkedin | 2030-01-14 | Example Co flash drum | simulation | 1 equation \\| 2 ends. |" in text


# ---------------------------------------------------------------- month, keys, formats

def test_month_uses_local_schedule_date_and_skips_sub_records():
    state = {
        "2030-01-07": {"facebook": rec("2029-12-20T05:00:00+00:00", scheduled_for="2030-01-07T08:30:00+07:00"),
                       "x": rec("2030-01-31T20:00:00+00:00")},          # 1 Feb 03:00 local: next month
        "2030-01-07:reply": {"x": rec("2030-01-07T02:00:00+00:00")},
    }
    posts = [p for p in _posts(state, []) if mr.in_month(p.posted, "2030-01")]
    assert [(p.key, p.channel) for p in posts] == [("2030-01-07", "facebook")]


def test_formats():
    state = {"2030-01-07": {"youtube": rec("2030-01-07T12:00:00+00:00"), "linkedin": rec("2030-01-07T01:00:00+00:00")},
             "2030-01-08": {"linkedin": rec("2030-01-08T01:00:00+00:00"), "x": rec("2030-01-08T01:00:00+00:00")},
             "article:acme": {"devto": rec("2030-01-12T01:00:00+00:00")},
             "notes:acme-1": {"x": rec("2030-01-03T01:00:00+00:00")}}
    meta = {**META, "article:acme": mr.Meta("Acme article", "build-log", "2030-W02", article=True)}
    fmts = {(p.key, p.channel): p.fmt for p in mr.build_posts(state, [], meta, TZ)}
    assert fmts == {("2030-01-07", "youtube"): "Short", ("2030-01-07", "linkedin"): "image",
                    ("2030-01-08", "linkedin"): "PDF document", ("2030-01-08", "x"): "image",
                    ("article:acme", "devto"): "article", ("notes:acme-1", "x"): "unknown"}


def test_series_and_format_mean_and_median():
    state = {"2030-01-07": {"linkedin": rec("2030-01-07T01:00:00+00:00")},
             "2030-01-08": {"linkedin": rec("2030-01-08T01:00:00+00:00")},
             "2030-01-14": {"linkedin": rec("2030-01-14T01:00:00+00:00")}}
    rows = [{"measured_on": "2030-01-20", "item": k, "channel": "linkedin", "impressions": imp, "reactions": r}
            for k, imp, r in (("2030-01-07", "100", "1"), ("2030-01-08", "200", "8"), ("2030-01-14", "400", "8"))]
    text = report(rows, state)
    assert "| image | 2 | 2 | 250 | 250 | 1.5 % | 1.5 % |" in section(text, "Per format")
    assert "| PDF document | 1 | 1 | 200 | 200 | 4.0 % | 4.0 % |" in section(text, "Per format")
    assert "| simulation | 1 | 1 | 400 | 400 | 2.0 % | 2.0 % |" in section(text, "Per series")


# ---------------------------------------------------------------- experiments and follow-ups

def test_experiment_week_against_earlier_weeks():
    state = {"2030-01-07": {"linkedin": rec("2030-01-07T01:00:00+00:00")},
             "2030-01-14": {"linkedin": rec("2030-01-14T01:00:00+00:00")}}
    rows = [{"measured_on": "2030-01-20", "item": "2030-01-07", "channel": "linkedin", "impressions": "100", "reactions": "1"},
            {"measured_on": "2030-01-20", "item": "2030-01-14", "channel": "linkedin", "impressions": "100", "reactions": "4"}]
    text = report(rows, state)
    assert ("| 2030-W03 | hook opens with a number | linkedin | 1 | 100 | 4.0 % | 1 | 100 | 1.0 % |"
            in section(text, "Experiments"))
    assert ('Keep the 2030-W03 experiment ("hook opens with a number"): linkedin median rate 4.0 % over 1 posts '
            "against 1.0 % over 1 earlier posts.") in section(text, "Proposals for next month")


def test_follow_up_shows_numbers_before_and_after():
    state = {"2030-01-07": {"linkedin": rec("2030-01-07T01:00:00+00:00")},
             "2030-01-07:followup1": {"linkedin": rec("2030-01-14T02:00:00+00:00")}}
    rows = [{"measured_on": "2030-01-13", "item": "2030-01-07", "channel": "linkedin", "impressions": "100", "reactions": "2"},
            {"measured_on": "2030-01-14", "item": "2030-01-07", "channel": "linkedin", "impressions": "120", "reactions": "2"},
            {"measured_on": "2030-01-21", "item": "2030-01-07", "channel": "linkedin", "impressions": "180", "reactions": "5"}]
    text = section(report(rows, state), "Follow-up comments")
    assert "| Example Co queue | linkedin | 1 | 2030-01-14 | 120 | 180 | 2 | 5 |" in text
    assert "1 follow-up comment(s)" in text


def test_no_follow_up_is_said_plainly():
    text = section(report([], {"2030-01-07": {"linkedin": rec("2030-01-07T01:00:00+00:00")}}), "Follow-up comments")
    assert "No follow-up comment recorded in 2030-01" in text


# ---------------------------------------------------------------- CLI

def test_main_writes_the_report_from_local_files(tmp_path):
    metrics = tmp_path / "metrics.csv"
    state = tmp_path / "published.json"
    out = tmp_path / "out" / "2030-01.md"
    metrics.write_text(csv_text([{"measured_on": "2030-01-20", "item": "2030-01-07", "channel": "youtube",
                                  "views": "50", "reactions": "1", "comments": "1"}]), encoding="utf-8")
    state.write_text(json.dumps({"2030-01-07": {"youtube": rec("2030-01-07T12:00:00+00:00")}}), encoding="utf-8")
    assert mr.main(["--month", "2030-01", "--metrics", str(metrics), "--state", str(state), "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# Post performance, 2030-01")
    assert "| youtube | 1 | 1 | 50 | 1 | 1 | no data | no data | 4.0 % |" in text


def test_main_rejects_a_bad_month(tmp_path):
    assert mr.main(["--month", "2030-13", "--out", str(tmp_path / "x.md")]) == 2
