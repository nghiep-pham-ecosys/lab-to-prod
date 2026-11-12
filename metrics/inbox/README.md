# Manual metric exports

LinkedIn has no self-serve analytics API for personal profiles. Once a week, save a file here
named `linkedin-2026-W47.csv` with one row per post plus one row for the account:

```csv
date,impressions,reactions,comments,shares,followers
2026-11-16,412,18,3,1,
2026-11-17,280,9,0,0,
,,,,,1530
```

`date` is the post's date; leave it empty on the row that only carries the follower count.
`metrics/collect.py` picks the file up on its next run.
