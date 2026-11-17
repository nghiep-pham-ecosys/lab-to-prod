---
description: Draft next week's 5 posts, 2 Shorts and 1 article, judge them, and open the weekly pull request
argument-hint: "[ISO week, e.g. 2026-W47; default: the week that starts next Monday]"
---

Draft the content for week `$ARGUMENTS` (if empty: the ISO week of next Monday, Asia/Ho_Chi_Minh).

Read first: `CLAUDE.md`, `docs/post-format.md`, the week's items in `content/calendar.yaml`,
`content/work.yaml`, `brand/voice-samples.md`, and the latest file in `reports/` (apply its
agreed change, and the calendar's `experiment` for this week).

Stop at once, and say why, if: a `PAUSE` file exists; the week is not in the calendar; a pull
request for this week is already open; an item of the week has no `work:` ref (run
`python tools/validate.py --week <week>` first).

## Idea source: the work ledger only

Posts take their content only from project work that is already merged. The ledger
`content/work.yaml` is the only idea source: no paper feed, no newsletter, no topic from memory.

- Each item's `work:` names one or more ledger entries. The post is about that work and nothing
  else: what was built, the number it measured, the bug it hit, the test that proved it.
- Read the merged change behind each entry before writing (the `write-post` skill says how).
- If the merged work does not support the item's `topic`, change the topic to fit the work, in
  the calendar, in the same pull request. If nothing fits, leave the post out.
- A week with fewer items than weekdays posts fewer times. Never fill a gap with an item from
  `parked:` or with a topic that has no merged work behind it.

## Steps

1. **Branch.** `git switch main && git pull`, then `git switch -c week-<week>`.
2. **Posts.** For each weekday item, use the `write-post` skill to create
   `content/<week>/<date>-<slug>/post.md` with `status: approved` (merging is the approval) and
   the item's `work:` copied into the front matter.
   Every LinkedIn section ends with one open question before the "Part N" line (see
   `write-post`); `tools/format_check.py --week <week>` must show no LinkedIn warning.
3. **Article.** For the Saturday item, use `write-blog`.
4. **Facts.** Run the `fact-check` skill on every post and the article. Fix or cut what fails.
5. **Images.** `render-image` for all five posts. Look at every image.
6. **Shorts.** `render-short` for the posts whose calendar item has a `short:` block
   (also for an earlier week's post if its Short is scheduled in this week).
7. **Manual channels.** `python -m publish.run export --week <week>` writes `x.md`,
   `x-schedule.md` and the Hashnode file.
8. **Judge.** Use the `judge` skill. It must run in a subagent that has not seen this session.
   It writes `content/<week>/judge.json`. Do not edit a post after it is judged; if you must,
   judge that post again.
9. **Checks.** All of these must pass:
   `python -m pytest -q`, `python tools/validate.py --week <week> --check-links`,
   `python tools/automerge_gate.py --week <week>`, `python -m publish.run --event merge`,
   and a build of the blog with `SHOW_FUTURE=1`.
10. **Pull request.** Commit, push, open a pull request titled `Week NN (<week>)` with the label
    `weekly`. Body: a table of the 5 posts (date, series, title, judge mean), each image embedded,
    the Shorts, the article title, anything the author must decide, and the lines
    "Minutes I spent reviewing: __" and "Edits I had to make: __" for the author to fill in.
11. **Report.** One line to the author: the pull request link and anything that needs a decision.

## Never

- Never post, never pass `--live`, never set `PUBLISH_LIVE` or `AUTOMERGE_ENABLED`, never merge.
- Never use material from an employer or client, and never invent a number or a source.
- Never write about work that is not in `content/work.yaml`, and never name a repo that the
  ledger does not list.
- If a post cannot be made correct in time, leave it out and say so in the pull request. A
  missing post is better than a wrong one.
