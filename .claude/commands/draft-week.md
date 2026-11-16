---
description: Draft next week's 5 posts, 2 Shorts and 1 article, judge them, and open the weekly pull request
argument-hint: "[ISO week, e.g. 2026-W47; default: the week that starts next Monday]"
---

Draft the content for week `$ARGUMENTS` (if empty: the ISO week of next Monday, Asia/Ho_Chi_Minh).

Read first: `CLAUDE.md`, `docs/post-format.md`, the week's items in `content/calendar.yaml`,
`claude/lesson-log.md`, `brand/voice-samples.md`, and the latest file in `reports/` (apply its
agreed change, and the calendar's `experiment` for this week).

Stop at once, and say why, if: a `PAUSE` file exists; the week is not in the calendar; a pull
request for this week is already open.

## Idea source: Research notes

If the Notion connector is available, query the Notion database **Research notes** for pages with
Type = paper, Area = content and Status inbox, reading or done. Use them as ideas for this week's
items when they fit the calendar topic. A post built on a paper:

- links the original paper (arXiv, DOI or the publisher page) in `sources`, never a newsletter;
- is written in your own words: never copy the abstract or a newsletter summary;
- checks every number against the paper itself, in the fact-check step;
- after the weekly pull request is opened, set that page's Status to `promoted`.

No connector: say so in the pull request and draft from the calendar alone.

## Steps

1. **Branch.** `git switch main && git pull`, then `git switch -c week-<week>`.
2. **Posts.** For each weekday item, use the `write-post` skill to create
   `content/<week>/<date>-<slug>/post.md` with `status: approved` (merging is the approval).
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
- If a post cannot be made correct in time, leave it out and say so in the pull request. A
  missing post is better than a wrong one.
