---
title: "Build log #2: when GitHub cron runs 8 hours late"
description: "The first trial week: scheduled runs 4.5 to 8.5 hours late, a wait-for-slot fix that posts at 08:15, and a closing question on every LinkedIn post."
date: 2026-11-28
series: build-log
part: 2
tags: [build-in-public, github-actions, devops, llmops]
work: [l2p-backup-cron, l2p-wait-for-slot, l2p-open-question]
---

7 hours 54 minutes. That is how late my LinkedIn post went out on Tuesday 17 November, the
second day of the trial. The workflow was set for 08:15 local time (UTC+7). The post appeared
at 16:09.

This log covers the first trial week: the scheduler, two fixes, a reversed rule and a few
numbers, all as of Friday 20 November, when I drafted it.

## Monday: I called it a skipped run, and I was wrong

In the pipeline from [build log #1](/lab-to-prod/posts/build-log-1-how-the-lab-to-prod-pipeline-runs/),
a `publish` workflow posts to LinkedIn on a cron at 08:15 local time. On Monday 16
November, no scheduled run had started by 09:20. I started the workflow by hand, and the post
went out at 09:28.

My diagnosis was that GitHub had skipped the run. The
[documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
allows for that: "If the load is sufficiently high enough, some queued jobs may be dropped." So
[pull request #29](https://github.com/nghiep-pham-ecosys/lab-to-prod/pull/29) added a second
cron 45 minutes later, for `publish` and for the blog build. A second run is safe: every post that
goes out is written to `published.json`, and the publisher skips anything already in it.

The run list tells a different story. A
[scheduled run of `publish`](https://github.com/nghiep-pham-ecosys/lab-to-prod/actions/runs/43827258403)
did start on Monday, at 14:55 local time. The backup cron was merged at 09:31, after its
slot, so this was most likely the 08:15 run: not skipped, just 6 h 40 min late.

## Tuesday: the backup was just as late

On Tuesday both crons fired about 8 hours late. So I measured the scheduled runs of the past
days with `gh run list --event schedule` ([issue #32](https://github.com/nghiep-pham-ecosys/lab-to-prod/issues/32)):

| Workflow | Cron (UTC) | Started (UTC) | Late by |
| --- | --- | --- | --- |
| publish | 01:15 | 07:34-09:09 (13, 14, 16, 17 Nov) | 6.3-7.9 h |
| publish backup | 02:00 | 09:59 (17 Nov) | 8.0 h |
| blog | 01:20 | 07:37-09:14 (13-17 Nov) | 6.3-7.9 h |
| metrics | 15:00 | 19:31-23:33 (12-16 Nov) | 4.5-8.5 h |

Not one measured run was on time. The documentation does warn that "the `schedule` event can
be delayed during periods of high loads". My own operations doc said "several minutes late". In
this organisation it meant hours, for every workflow I measured.

## The fix: start early, then sleep until 08:15

If a cron cannot start on time, start it early and let the job hold the time. That is
[pull request #33](https://github.com/nghiep-pham-ecosys/lab-to-prod/pull/33). `publish` and
the blog build got two early crons, at 00:30 and 03:30 local time:

```yaml
schedule:
  # Early runs 00:30 and 03:30 (Mon-Sat local): they start late, then wait until 08:15. One waiter at a time.
  - cron: "30 17 * * 0-5"
  - cron: "30 20 * * 0-5"
```

The 08:15 and 09:00 crons stay as fallbacks.

The day field reads `0-5` because 17:30 UTC on Sunday is already 00:30 on Monday local time
(UTC+7). The first job of each run is `wait`. It runs `tools/wait_until.py`, whose core is one
function:

```python
def decide(now: dt.datetime, at: dt.time, tz: ZoneInfo, max_wait: dt.timedelta) -> tuple[bool, float, str]:
    """Return (go, seconds to wait, reason) for a run that started at `now` (timezone-aware)."""
    local = now.astimezone(tz)
    target = dt.datetime.combine(local.date(), at, tzinfo=tz)
    wait = dt.timedelta(seconds=round((target - local).total_seconds()))
    if wait <= dt.timedelta(0):
        return True, 0.0, f"started {local:%H:%M} after {at:%H:%M}: go now"
    if wait > max_wait:
        return False, 0.0, f"started {local:%H:%M}, {at:%H:%M} is {wait} away (> {max_wait}): skip, a later run covers it"
    return True, wait.total_seconds(), f"started {local:%H:%M}: wait {wait} until {at:%H:%M}"
```

The longest wait is 5.5 hours, because "each job in a workflow can run for up to 6 hours of
execution time" ([GitHub limits](https://docs.github.com/en/actions/reference/limits)). The
tests in `tests/test_wait_until.py` pin the decisions for 08:15:

| Run starts (local) | Decision |
| --- | --- |
| 00:30 | skip: 7 h 45 min is more than 5 h 30 min |
| 02:45 | wait exactly 5 h 30 min |
| 05:00 | wait 3 h 15 min |
| 06:30 | wait 1 h 45 min (the UTC date is still the day before) |
| 16:09 | go at once |

Three more rules sit around it. A run skips when an older scheduled run of the same workflow is
still in progress. If `gh` fails, the script assumes no other waiter: a second run is safe, a
skipped post is not. And after the wait, the job checks out the head of the default branch, not
the commit the run was created on.

That last rule came from a correctness review, which raised four findings, all fixed before
the merge: the run used a stale commit after the wait, two waiters could tie, a `gh` error made
the wait fail closed, and the log printed microseconds. The stale commit was the serious one: a
run that slept for hours would ignore a `PAUSE` file merged while it slept.

## Three mornings at 08:15

The LinkedIn post time for each weekday, from `published.json`, in local time:

| Day | Posted | How |
| --- | --- | --- |
| Mon 16 Nov | 09:28 | started by hand |
| Tue 17 Nov | 16:09 | scheduled run, 7 h 54 min late |
| Wed 18 Nov | 08:15 | scheduled run started 06:54, waited |
| Thu 19 Nov | 08:15 | scheduled run started 06:29, waited |
| Fri 20 Nov | 08:15 | scheduled run started 06:42, waited |

Neither early cron is due after 03:30, so these runs still started about 3 hours late or more.
The fix does not need GitHub to be on time, only early enough.

## A rule I reversed on day one

Before the trial, the drafting skill said: "No question at the end to bait comments." On Monday,
about two hours after the first LinkedIn post, I reversed it in
[pull request #31](https://github.com/nghiep-pham-ecosys/lab-to-prod/pull/31).

Every LinkedIn post now ends with one open question, in its own paragraph, before the "Part N"
line. It asks about the reader's own experience with this exact topic, and it is never a yes/no
or bait line such as "Agree?". Thursday's cloud post asked: "In your hybrid setups, did you
pick VPN, Direct Connect or both, and what decided it?"

Monday's post was already live and kept its old ending. The four posts for Tuesday to Friday
were edited before they went out, with one side effect: the grading step stores
a hash of each post, and the four edited posts no longer match their grades. It held nothing,
because the gate only reads those grades while a weekly pull request is open.

## What the numbers say after five days

Very little. The latest from the metrics job:

| Date | Channel | impressions | views | reactions | comments | shares |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-11-16 | youtube | - | 29 | 0 | 0 | - |
| 2026-11-18 | youtube | - | 1 | 0 | 0 | - |

Viewers watched 57% of the first Short on average. The article that announced this experiment
has 15 views and 1 comment on DEV. The Facebook Page and the YouTube channel still have 0
followers. LinkedIn is missing: its numbers come from a file I export by
hand, and I have not done it yet. So I cannot tell whether the closing questions brought
comments.

Delivery is clearer. Every tracked channel post due by Friday was posted or scheduled. On LinkedIn, 3 of 5
went out at 08:15; the 2 that did not are the two days before the fix.

## What surprised me

The 00:30 cron only works because GitHub is late. If it started on time, it would face 7 h 45
min of waiting and skip. The 03:30 cron would still work on time, with a wait of 4 h 45 min.
So half of the fix depends on the bug it works around.

## What comes next

This week's posts test one change: every hook opens with a measured number, like this article's.
The deep dive on quality gates that build log #1 promised for today is parked: posts now come
only from merged work, so that topic waits until the work behind it is merged.

What I still do not know:

- whether the delay belongs to this organisation, to the time of day, or to this month;
- what happens on a morning when both early runs start after 08:15: the runbook says to start
  the workflow by hand at 09:30, and I have not had to yet;
- whether a closing question changes anything on LinkedIn, until I export those numbers.

The code is at [github.com/nghiep-pham-ecosys/lab-to-prod](https://github.com/nghiep-pham-ecosys/lab-to-prod).
If you have seen GitHub cron behave like this, I would like to know how you handled it.
