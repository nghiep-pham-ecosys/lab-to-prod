# Manual metric exports (LinkedIn and X)

LinkedIn has no self-serve analytics API for a personal profile, and the X API is paid. Their
numbers come only from CSV files in this folder. `metrics/collect.py` reads every
`linkedin-*.csv` and `x-*.csv` here on each `metrics` run and writes the rows to
`metrics/metrics.csv` on the `publish-state` branch. A post with no row is "no data" in the
monthly report, never 0.

## When

- Once a week, on the last working day of the week.
- On the last working day of the month, before the monthly report (`tools/monthly_report.py`).

## Who and how

The main session does it in Chrome, signed in as the author. Read only: no like, comment or other
action on the page.

1. LinkedIn: open the profile, then Activity → Posts. For each post of the period, open
   "View analytics" under the post. Copy Impressions, Reactions, Comments and Reposts. For the
   follower count, open the profile analytics (Followers).
2. X: open the profile and each post of the period, then "View post analytics" (the bar-chart
   icon). Copy Impressions, Likes, Replies and Reposts. The follower count is on the profile.
3. Add the rows to the file of the month, `linkedin-YYYY-MM.csv` or `x-YYYY-MM.csv`. Keep earlier
   rows: each line is one reading of one post on one day.
4. Open a small pull request with the file (`chore: linkedin and x metrics YYYY-MM-DD`). The
   `metrics` run picks it up after the merge, at 22:00 or when the workflow is started by hand.
   On the last working day of the month, merge and run it before the report.

## Columns

```csv
item,date,measured_on,impressions,reactions,comments,shares,followers
notes:toy-example,,2026-11-30,300,12,2,1,
,2026-11-16,2026-11-30,412,18,3,1,
,,2026-11-30,,,,,1530
```

| Column | Meaning |
| --- | --- |
| `item` | the post's key in `published.json` (for example `notes:toy-example`) |
| `date` | the post's date; enough for a daily post, whose key is its date. Used when `item` is empty |
| `measured_on` | the day the numbers were read, `YYYY-MM-DD`. Always fill it: without it the file's modification date is used, which is the checkout time on GitHub Actions |
| `impressions` | LinkedIn Impressions, X Impressions |
| `reactions` | LinkedIn Reactions, X Likes |
| `comments` | LinkedIn Comments, X Replies |
| `shares` | LinkedIn Reposts, X Reposts |
| `followers` | only on the account row, where `item` and `date` are empty |

An optional `views` column and an optional `url` column are read too. Leave a number empty
when the page does not show it. An empty cell stays "no data" in the report.

Numbers only, no names: never copy who reacted or commented (CLAUDE.md rule 6).
