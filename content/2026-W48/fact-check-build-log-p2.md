# Fact-check, 2026-W48: Saturday article build-log-p2

Checked on 20 Nov 2026. Merge this section into `content/2026-W48/fact-check.md` with the posts.
"Done work" means found in the merged change; "Sourced" means the page was opened and the quoted
words were found; "Record" means read from `published.json` / `metrics/metrics.csv` on branch
`publish-state` at e071199 (2026-11-20 01:15 UTC) through `python -m metrics.report --week 2026-W47`.

## build-log-2-when-github-cron-runs-8-hours-late (Build log #2)

Work: l2p-backup-cron (https://github.com/nghiep-pham-ecosys/lab-to-prod/pull/29, merged 2026-11-16),
l2p-wait-for-slot (https://github.com/nghiep-pham-ecosys/lab-to-prod/pull/33, merged 2026-11-17),
l2p-open-question (https://github.com/nghiep-pham-ecosys/lab-to-prod/pull/31, merged 2026-11-16).
All merged before 2026-11-28; `validate.py --week 2026-W48` reports no article error.

| Claim | Outcome | Evidence |
| --- | --- | --- |
| LinkedIn post on 17 Nov went out at 16:09, 7 h 54 min after 08:15 | Record | `published.json` `2026-11-17/linkedin/at` = 2026-11-17T09:09:45Z; PR #33: "On 17 Nov the LinkedIn post went out at 16:09 instead of 08:15" |
| 16 Nov: no scheduled run by 09:20, started by hand, post at 09:28 | Done work + Record | issue #28 / PR #29: "no scheduled run at all by 09:20 ... manual dispatch"; `2026-11-16/linkedin/at` = 02:28:58Z |
| Docs: "If the load is sufficiently high enough, some queued jobs may be dropped." | Sourced | docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows, schedule section |
| PR #29 added a second cron 45 min later for publish and blog | Done work | PR #29 diff: `0 2 * * 1-6` (publish), `5 2 * * *` (blog); operations.md "backup run 45 min later" |
| Publisher skips posts already in published.json | Done work | PR #29 body; PR #33 cron comment "posts already in published.json are skipped" |
| A scheduled publish run did start on 16 Nov at 14:55 local | Record | `gh run view 43827258403`: event schedule, created 2026-11-16T07:55:42Z; also issue #32 table lists 16 Nov |
| 17 Nov both crons ~8 h late | Done work | issue #32 table (7.9 h and 8.0 h); runs 44052974883 (09:09Z) and 44060551032 (09:59Z) |
| Delay table (4 rows) | Done work | copied from issue #32 "Problem" table, unchanged |
| Docs: "the `schedule` event can be delayed during periods of high loads" | Sourced | same docs page |
| Old operations doc said "several minutes late" | Done work | PR #29 diff, removed line: "GitHub's scheduler can run several minutes late." |
| Early crons 00:30 and 03:30 local, yaml excerpt | Done work | PR #33 `publish.yml`, lines 16-18, verbatim |
| `0-5` because 17:30 UTC Sunday = 00:30 Monday local | Common knowledge | UTC+7, no DST in Asia/Ho_Chi_Minh |
| `decide()` code | Done work + Ran | `tools/wait_until.py` lines 24-33, verbatim; `pytest tests/test_wait_until.py`: 10 passed |
| Max wait 5.5 h; docs: "each job in a workflow can run for up to 6 hours of execution time" | Done work + Sourced | `--max-wait-min` default 330; docs.github.com/en/actions/reference/limits |
| Decision table 00:30 skip, 02:45 wait 5h30, 05:00 wait 3h15, 06:30 wait 1h45, 16:09 go | Ran | tests `test_on_time_early_run_skips...`, `test_wait_exactly_at_limit_goes`, `test_delayed_early_run...`, `test_target_uses_local_date...`, `test_run_after_target_goes_at_once`; 10 passed |
| One waiter: skips when an older scheduled run waits; gh error = no other waiter; checkout of default branch head | Done work | `other_waiters`, `in_progress_schedule_runs` docstring ("failing here would skip the post"), workflow `ref:` lines |
| Four review findings, all fixed before merge | Done work | PR #33 body, "Checks" |
| Stale commit would ignore a PAUSE file merged meanwhile | Done work | workflow comment: "so a PAUSE file or a fix merged meanwhile counts" |
| LinkedIn times 18/19/20 Nov 08:15; runs started 06:54/06:29/06:42 and waited | Record | `at` 01:15:14Z, 01:15:13Z, 01:15:12Z; runs 44203428305, 44421177849, 44639880347: job `wait` from 23:54Z/23:29Z/23:42Z to 01:15Z |
| These runs started about 3 h late or more | Derived | latest early cron is 03:30 local; earliest start 06:29 |
| Old skill line "No question at the end to bait comments." | Done work | PR #31 diff, removed line in write-post skill |
| Reversed about two hours after the first post | Done work + Record | first post 09:28; PR #31 body "Nghiep, 16/11 11:20", merged 04:37Z (11:37 local) |
| Question rule (own paragraph, before Part N, own experience, never yes/no or "Agree?") | Done work | PR #31 write-post skill diff |
| Thursday question quote | Done work | PR #31 diff, cloud-p2 post |
| 16 Nov left alone, 4 posts edited, judge hashes stale, nothing held | Done work | PR #31 body and its Note |
| Short 1: 29 views, Short 2: 1 view, 57% average view | Record | metrics.report table; metrics.csv 2026-11-20 row avg_view_pct 57.17 |
| DEV announcement article: 15 views, 1 comment | Record | metrics.csv 2026-11-20, article:why-i-am-building-lab-to-prod-in-public |
| Facebook and YouTube 0 followers | Record | metrics.report "Followers during the week" |
| LinkedIn numbers absent (manual export) | Record | metrics.report: no LinkedIn rows; `metrics/inbox/` holds only README.md |
| Every tracked channel post due by Friday posted or scheduled; LinkedIn 3 of 5 at 08:15 | Record | metrics.report: 12 of 13, the 13th is the 21 Nov DEV article; LinkedIn `at` column |
| 00:30 cron on time would skip (7 h 45 min > 5 h 30 min) | Ran | `test_on_time_early_run_skips_when_wait_exceeds_job_limit` |
| Runbook: start by hand at 09:30 if a post is missing | Done work | PR #33 operations.md: "If a morning post is still missing at 09:30, run the workflow by hand." |
| Quality-gate deep dive promised by build log #1 is parked | Record | build log #1 last section; `content/calendar.yaml` parked deep-dive item |
| This week's experiment: hook opens with a measured number | Record | calendar 2026-W48 `experiment` |

Cut or softened: "the post I sent by hand was 'already published, skipped'" (the PR log line
is not tied to that post: cut); "every day, for every workflow" softened to "every workflow I
measured"; "the early run" in the timing table softened to "scheduled run" (the run does not say
which cron created it); "three hours after the first post" corrected to "about two hours";
"the format check now flags it" cut (the check predates PR #31).
