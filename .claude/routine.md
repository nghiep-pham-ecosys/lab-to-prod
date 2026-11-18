# Draft-week routine

A cloud routine runs this file every Saturday at 09:00 (Asia/Ho_Chi_Minh). Its prompt is one line:
"Read `.claude/routine.md` in lab-to-prod and follow it." The rules live here and change by pull request.

This run is a bonus. The local Saturday 13:30 session is the main path for the week's content. When that session
has already drafted the week, this run stops.

One run = one week = one pull request. The run never merges and never posts. A local session reviews and merges the
PR.

## 1. Target week

- The run works only on a Saturday in Asia/Ho_Chi_Minh. On any other day → stop.
- The target week is the ISO week of the next Monday (two days later), written `YYYY-Www`, for example `2026-W48`.
  `NN` below is its two-digit week number.

## 2. Stop checks (in this order)

Stop at the first check that fails. Write nothing, open no PR and write the reason in the run output.

1. A file named `PAUSE` exists at the repo root → stop.
2. The run is not on a Saturday → stop.
3. An open pull request already has a head branch that starts with `week-` → stop. At most one week PR is open at a
   time, whichever week it is for.
4. A branch `week-<week>` already exists on the remote, or the folder `content/<week>/` already exists on `main` →
   stop. The local session or an earlier run has the week.
5. The target week is not in `content/calendar.yaml` → stop.
6. The week has fewer ledger entries than it needs: it has no items, an item has no `work:`, or a `work:` id is
   missing from `content/work.yaml` or was merged after the item's date. Run
   `python tools/validate.py --week <week>` (command form in §4). Any error → stop.

## 3. Draft the week

Follow `.claude/commands/draft-week.md` end to end, with the limits below. Where the two disagree, this file wins.

- **Ideas come only from `content/work.yaml`.** Each post is about the merged work its `work:` names and nothing
  else. No paper feed, no newsletter, no topic from memory, no item from `parked:`. A week with fewer items posts
  fewer times.
- **No Notion connector** and no other connector. The run reads this repository and the public pull requests that
  ledger entries link to. A private repo in the ledger is named, never linked, and its code is never pasted.
- Posts: the `write-post` skill, one folder per weekday item, `status: approved`, the item's `work:` in the front
  matter. The Saturday article: the `write-blog` skill.
- Facts: the `fact-check` skill on every post and the article. A post that cannot be made correct is left out and
  named in the PR body.
- Images and Shorts: `render-image` for every post, `render-short` for items with a `short:` block. If a render
  fails in the cloud, leave that file out and name it in the PR body.
- Judge: the `judge` skill, in a fresh subagent that has not seen the drafting. It writes `content/<week>/judge.json`.
  If no fresh subagent can run, stop and open no PR.
- The run may change the `topic` of the target week's items in `content/calendar.yaml` to fit the merged work, as
  draft-week allows. It changes nothing else in the calendar.

## 4. Checks

Use the repo's own commands from `CLAUDE.md`:

```bash
uv run --with-requirements tools/requirements.txt python -m pytest -q
uv run --with-requirements tools/requirements.txt python tools/validate.py --week <week> --check-links
uv run --with-requirements tools/requirements.txt python tools/validate.py
uv run --with-requirements tools/requirements.txt python tools/automerge_gate.py --week <week>
uv run --with-requirements tools/requirements.txt python tools/format_check.py --week <week>
```

Then run the rest of draft-week step 9: `python -m publish.run --event merge` (a dry run, never `--live`) and a
build of the blog with `SHOW_FUTURE=1`. All must pass, with no LinkedIn warning from `format_check.py`, before the PR. Any red check → open no PR and write
the failing lines in the run output.

## 5. Pull request

- Branch `week-<week>` from `main`, for example `week-2026-W48`.
- One PR, titled `Week NN (<week>)`, for example `Week 48 (2026-W48)`, with the label `weekly`.
- The PR holds only that week's files: `content/<week>/`, the week's article in `blog/src/content/posts/`, and topic
  changes to the week's items in `content/calendar.yaml`. Nothing else.
- Commits: `type: description`, lower case, imperative. Never `Fixes`, `Closes` or `Resolves`.
- PR body as in draft-week step 10: a table of the posts (date, series, title, judge mean), the images, the Shorts,
  the article title, what was left out and why, anything the author must decide, and the lines
  "Minutes I spent reviewing: __" and "Edits I had to make: __".
- One PR per run.

## 6. Never

- Merge, push to `main`, force-push, or delete a branch.
- Post anything, pass `--live`, or set `PUBLISH_LIVE` or `AUTOMERGE_ENABLED`.
- Change `.github/`, `publish/`, `tools/`, `metrics/`, `reports/`, `published.json`, `CLAUDE.md`, `.claude/`
  (this file included), `content/work.yaml`, the `PAUSE` file, another week's folder, or any post whose `status`
  is `published`.
- Write about work that is not in `content/work.yaml`, name a repo the ledger does not list, invent a number or a
  source, or use employer or client material.
- Write names of people or companies other than cited authors, account ids, secrets or links to chat sessions.
- Edit labels other than its own PR's `weekly` label, the project board or issues.
- When blocked, open no PR. Write what blocks the run and what would unblock it in the run output.
