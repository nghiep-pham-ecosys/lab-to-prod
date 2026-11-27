---
name: monthly-report
description: Write the monthly post performance report reports/YYYY-MM.md from metrics.csv and published.json on the publish-state branch, with per-channel numbers, top and bottom posts, series and format medians, the weekly experiments, the follow-up comments and three proposals. Use on the first working day of each month for the month that just ended.
---

# Monthly report

When: the first working day of each month, for the month that just ended. First run: 2026-12-01 for 2026-11.
Who: the main session. Output: `reports/YYYY-MM.md` in a small pull request, and a short summary to the author.

## Get the numbers (do not retype or compute by hand)

```bash
uv run --with-requirements tools/requirements.txt python tools/monthly_report.py --month YYYY-MM
```

The tool fetches the `publish-state` branch and reads `metrics/metrics.csv` and `published.json` from it with
`git show`. It never writes that branch. It calls no platform API. It writes `reports/YYYY-MM.md` with:

1. **Per channel**: posts, posts measured, reach (impressions or views), reactions, comments, shares, follower
   change inside the month, engagement rate = (reactions + comments + shares) / reach. Each post uses its last
   measurement.
2. **Top and bottom posts** by engagement rate, with the hook line and the series. Posts with no measurement or a
   reach of 0 are not ranked.
3. **Per series** and **per format** (image, PDF document, Short, article): mean and median of reach and rate.
4. **Experiments**: each week's `experiment` from `content/calendar.yaml` against all earlier weeks on the same
   channel.
5. **Follow-up comments** (`<date>:followup1` and `<date>:followup2` in `published.json`, lab-to-prod#62): reach and
   engagement before the comment and at the last measurement after it.
6. **Three proposals**, each tied to a number in the report.

"no data" means nothing was measured. Never write 0 for it, and never fill it in by hand.

## Then

1. Read the whole report. Check two numbers against `metrics.csv` on the branch by hand.
2. Edit only the proposals, and only to make them clearer: keep the number each one cites. Do not add a proposal
   without a number from the report. They are proposals; the author decides.
3. Commit the report on a branch `docs/<n>-report-YYYY-MM` and open a small pull request (`docs: monthly report
   YYYY-MM`). Do not push to `main`.
4. Send the author a summary in the main session chat: posts per channel, the one number worth knowing, the
   channels with no data, the three proposals, and the pull request link.

## Rules

- The report is public. It holds counts, post titles, hook lines and series only. Never put commenter names,
  comment text or direct messages in it.
- Do not draw conclusions the sample cannot support. Say "likely" or "a hint" when a group has fewer than 5 posts.
- Report missing data first and plainly: a channel with no data is a gap to fix, not a bad channel.
- A change the author accepts goes into `CLAUDE.md`, a skill or `content/calendar.yaml` in a later pull request.
