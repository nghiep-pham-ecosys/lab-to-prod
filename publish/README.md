# Publish

`run.py` posts approved content through each platform's free official API and records every
success in `published.json` at the repository root. It is a dry run unless `--live` is given.

| Channel | Mode | Trigger | What happens | Secrets |
| --- | --- | --- | --- | --- |
| Facebook Page | api | merge | photo post, scheduled by Facebook for 08:30 on the post's day | `FB_PAGE_ID`, `FB_PAGE_TOKEN` |
| YouTube | api | merge | Short uploaded as private with `publishAt`, then the SRT as captions | `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` |
| YouTube (long videos) | api | by hand | staged batch from a draft release, uploaded as private with `publishAt`, then the SRTs as captions (see below) | the same three |
| LinkedIn | api | daily | post with image, or a document post when the folder has `linkedin.pdf`; then the blog link as first comment (best effort) | `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_PERSON_URN` |
| Telegram | api | daily | image with caption and blog link | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL` |
| DEV | api | daily | Saturday article with `canonical_url` to the blog | `DEVTO_API_KEY` |
| Hashnode | manual | export | `hashnode-<slug>.md` to paste; the API needs a paid plan since 13 May 2026 | none |
| X | manual | export | `x.md` per post and `x-schedule.md` per week; the API is pay-per-use | none |

Switch a channel between `api`, `manual` and `off` in `config.yaml`.

## Commands

```bash
uv run --with-requirements tools/requirements.txt python -m publish.run --event merge
```

```bash
uv run --with-requirements tools/requirements.txt python -m publish.run --event daily --date 2026-11-16
```

```bash
uv run --with-requirements tools/requirements.txt python -m publish.run export --week 2026-W47
```

Add `--only telegram` to limit a run to one channel. Add `--live` to really post; never do
that without the author's go-ahead for that channel.

## Long videos from nghiep-motion-studio

Long videos (10-20 minutes) and their Shorts do not live in this repository. `motion-studio stage-upload` checks
that the video passed its quality gate, builds the metadata (title, description with chapter timestamps, tags,
language, publish time, the "made with AI" label) and stages the mp4s, their SRTs and `manifest.json` as assets of a
**draft** release here. Draft releases are visible only to people with push access, so nothing is public yet.

The `youtube-upload` workflow (`.github/workflows/youtube-upload.yml`) is started by hand only, after the author
approves the weekly batch:

```bash
gh workflow run youtube-upload.yml -f tag=<tag>
```

```bash
gh workflow run youtube-upload.yml -f tag=<tag> -f live=true
```

The first is a dry run: it downloads the batch, checks `manifest.json` and prints the plan without calling Google.
The second runs `python -m publish.youtube_release`, which uploads every item as **private** with `publishAt`
(YouTube makes it public then), adds the SRT as captions and logs the quota of every call. `-f publish_at=<ISO time>`
moves the whole batch, keeping the spacing between the video and its Shorts. A publish time in the past is refused.

- `result.json` (video ids, links, quota) is written after every upload and kept on the draft release, so a re-run
  skips what is already up. It also goes to the job summary and to the artifact `youtube-upload-<tag>`, which
  `motion-studio finish-upload` reads to write its upload record and free the disk.
- An item with a `playlist` block (`title`, optional `description`, optional `privacy`: `public` by default,
  `unlisted` or `private`) lands in that playlist. The playlist is found by exact title among the channel's own
  playlists (`playlists.list` with `mine=true`, every page), created when missing (`playlists.insert`), and the video
  is added (`playlistItems.insert`) unless `playlistItems.list` shows it is already there. The playlist id is kept in
  `result.json`, so a re-run neither creates a second playlist nor adds a video twice. A failed playlist step leaves
  the batch incomplete; the re-run retries only that step. Quota: 1 unit per list call, 50 per insert. The dry run
  prints the playlist plan and calls nothing.
- The draft release is deleted only when every item is uploaded (and added to its playlist, when it has one).
- The YouTube secrets are the same three as for Shorts; they reach only the upload step.
- The `PAUSE` file stops the run before any call.

## Comments

`comments.py` lists the comments on our YouTube videos and Facebook Page posts that we have not answered yet, and
posts the replies the author approved. LinkedIn and X comments are read and answered by hand in the browser. The daily
flow is one approval a day:

1. The main session runs the `comments` workflow (`.github/workflows/comments.yml`, started by hand only) in `list`
   mode. The job summary and the artifact `comments-list` hold only the channel, post URL, comment id and time
   (`--redact`).
2. It reads each comment on the platform itself (post URL plus comment id), drafts one reply per comment and asks
   the author. Nothing is posted before his yes. A reply never names or quotes the commenter: the reply text
   is public in the run log.
3. It runs the workflow in `reply` mode with the approved replies as a JSON string.

```bash
gh workflow run comments.yml -f mode=list -f days=7
```

```bash
gh workflow run comments.yml -f mode=reply -f replies='[{"channel":"youtube","comment_id":"<id>","text":"<reply>"}]'
```

Locally (`reply` prints the plan and calls nothing without `--live`):

```bash
uv run --with-requirements tools/requirements.txt python -m publish.comments list --days 7
```

```bash
uv run --with-requirements tools/requirements.txt python -m publish.comments reply --file replies.json
```

- **Which posts.** The `youtube` and `facebook` entries of `published.json` (merged with the `publish-state` branch
  in the workflow, read only) that are public and at most `--post-days` old (default 60).
- **Which comments.** Top-level comments from the last `--days` days (default 7), not written by us, without a
  reply from our own channel (YouTube) or Page (Facebook). YouTube answers only top-level comments. Output, one entry
  per comment: `channel`, `post_key`, `post_url`, `comment_id`, `author`, `text`, `at` (UTC).
- **Idempotent.** Before each reply the tool reads the comment's replies again; one from our channel or Page means
  `skipped`. A comment listed twice in one file is posted once.
- **Refused scope.** Facebook replies need `pages_manage_engagement` (with `pages_read_user_content`). A Page token
  made before 27 Nov 2026 lacks it, so every Facebook reply is `refused` until the author renews the token
  (`docs/setup.md`, section 4, steps 3 and 6). YouTube uses `youtube.force-ssl`, already in the token.
- **Quota.** YouTube: 1 unit per `commentThreads.list`, `comments.list` and `channels.list` call, 50 per
  `comments.insert`. The run prints the units used.
- **Log.** Every reply (channel, comment id, status, reply id, text) goes to the job summary and to the artifact
  `comments-reply`. The `PAUSE` file stops a reply run before any call.
- **Public logs.** This repository is public, so its run logs and artifacts are too. Names and comment text are
  left out of the summary, stdout and artifacts (`--redact`, always on in the workflow); the author reads them on
  the post itself. Never drop `--redact` from the workflow.

## Follow-up comments

`followup.py` plans one comment from the author 7 days after a post, and a second one 14 days after it only when the
post earned it. Never more than 2 per post and channel. The channels are LinkedIn, the Facebook Page, YouTube and X.
The daily flow sits in the same approval as replies (ecosys skill daily-start, step "Bình luận"):

1. The main session runs the `followup` workflow (`.github/workflows/followup.yml`, started by hand only) in `due`
   mode, or `followup.py due` locally. It reads `published.json` and `metrics/metrics.csv` and calls no API.
2. On the day a follow-up is due, it drafts the text from facts only: the post, its blog note, a later merged change
   in `content/work.yaml`, or the next part of the series. A follow-up never names or quotes a commenter, and never
   asks for engagement. The author approves the drafts in the daily comment batch. Nothing is posted before his yes.
3. It runs the workflow in `plan` mode (a dry run of the approved list), then in `post` mode with the same JSON.
4. X is posted by hand in Chrome and recorded with `record_manual` under the follow-up key (see below). So is any
   LinkedIn follow-up that LinkedIn refuses.

```bash
gh workflow run followup.yml -f mode=due
```

```bash
gh workflow run followup.yml -f mode=post -f approved='[{"channel":"linkedin","post_key":"2026-11-20","number":1,"text":"<approved text>"}]'
```

Locally (`post` prints the plan and calls nothing without `--live`):

```bash
uv run --with-requirements tools/requirements.txt python -m publish.followup due --date 2026-11-27
```

```bash
uv run --with-requirements tools/requirements.txt python -m publish.followup post --file approved.json
```

- **When.** Follow-up 1 is due 7 days after the day the post went public (its `scheduled_for`, else its `at`, in
  local time) and stays due for 2 more days. Follow-up 2 is due on day 14 (and 2 more days) when follow-up 1 is
  recorded and the post has comments from other people (the latest `comments` count minus our own first comment and
  follow-up 1) or reach above the median of that channel's posts (`impressions`, or `views` for YouTube) in the latest
  metrics. X has no metrics, so it only ever gets follow-up 1. A held-back follow-up 2 is noted on stderr.
- **Output of `due`.** One entry per follow-up: `channel`, `post_key`, `post_url`, `number`, `key`, `due_on`,
  `mode` (`api` or `manual`), `metrics` (latest counts) and `comments`. Counts only, no names, no comment text.
- **Approved file.** A JSON list of `{channel, post_key, number, text}`. `post` checks again: the post is in
  `published.json`, the number is 1 or 2, follow-up 1 comes before 2, the day has come, and the key is not recorded.
- **Record.** A posted follow-up goes into `published.json` at once under `<post key>:followup1` or
  `<post key>:followup2` (`id` = the new comment, `post_id`, `url` of the post). A re-run skips it. In the workflow the
  file is pushed to the `publish-state` branch. `comments.py` and `metrics/collect.py` skip these keys.
- **Calls.** LinkedIn: `POST /v2/socialActions/{post URN}/comments`, the same call as the first comment, which works
  live with the self-serve token; a refusal is reported and the comment goes by hand. Facebook:
  `POST /{post-id}/comments`, needs `pages_manage_engagement` (lab-to-prod#61). YouTube: `commentThreads.insert` on
  our own video (50 units, `youtube.force-ssl`).
- **X by hand.** `post` never calls X. The item comes back as `manual` with the two commands:

```bash
uv run --with-requirements tools/requirements.txt python -m publish.record_manual check --key 2026-11-20:followup1 --channel x
```

```bash
uv run --with-requirements tools/requirements.txt python -m publish.record_manual record --key 2026-11-20:followup1 --channel x --url https://x.com/<handle>/status/<id> --via chrome
```

- **Public logs.** The job summary and the artifacts `followup-due`, `followup-plan` and `followup-post` hold channels, keys, counts,
  statuses and our own approved text only. The `PAUSE` file stops a `post` run before any call.

## Manual posts

X and Hashnode are posted by hand, and any channel can be. Record every manual post so `published.json`
stays the single answer to "is it live?":

```bash
uv run --with-requirements tools/requirements.txt python -m publish.record_manual check --key 2026-11-16 --channel x
```

```bash
uv run --with-requirements tools/requirements.txt python -m publish.record_manual record --key 2026-11-16 --channel x --url https://x.com/<handle>/status/<id> --via chrome
```

`check` exits 1 when the post is already recorded. `record` refuses a second entry for the same key and channel.
Posts made outside the weekly folders use a stable slug key, for example `notes:en-4-agent-loop`.

## Guarantees

- **Approved only.** Posts with `status: draft` are ignored.
- **Idempotent.** A success is written to `published.json` immediately; a re-run skips it. DEV is
  also checked by canonical URL in case the file was lost.
- **Isolated failures.** One channel failing does not stop the others; the exit code is 1 so
  the workflow goes red and GitHub sends the email.
- **No back-posting.** A date in the past is skipped, not posted late.
- **`PAUSE` file** at the repository root stops everything.
- **No token in logs.** Errors print the platform's message, never a secret or a URL holding one.

## What the API documentation says (checked 12 Nov 2026)

| Platform | Finding that shaped the code |
| --- | --- |
| LinkedIn | The self-serve "Share on LinkedIn" product documents `/v2/ugcPosts` + `/v2/assets?action=registerUpload` with scope `w_member_social`. Tokens last 60 days; refresh tokens are for selected partners only. The comments documentation lists a different scope, so the first comment may be refused: the post is kept and the link is added by hand. A folder with `linkedin.pdf` uses `/rest/documents?action=initializeUpload` + `/rest/posts` instead (same scope, `LinkedIn-Version` header; person-authored document posts not yet verified live). |
| Facebook | Graph API v27.0. `/{page-id}/photos` with `published=false` and `scheduled_publish_time`, between 10 minutes and 30 days ahead. PNG uploads are capped at 1 MB, so images go up as JPEG. Long-lived Page tokens do not expire by date. Comments (checked 27 Nov 2026): `GET /{object-id}/comments` with `filter=stream` returns every level; `POST /{comment-id}/comments` replies and needs `pages_manage_engagement` and the MODERATE task; comment ids are hidden from tokens without MODERATE. |
| YouTube | `publishAt` needs `privacyStatus: private`. `videos.insert` has its own quota of 100 calls a day; `captions.insert` costs 400 units. The 2 Nov 2026 revision says uploads from unverified projects are no longer locked to private. There is no Shorts flag. Playlists (checked 26 Nov 2026): `playlists.list` and `playlistItems.list` cost 1 unit, `playlists.insert` and `playlistItems.insert` 50; list pages hold at most 50 items; the inserts accept the `youtube.force-ssl` scope. Comments (checked 27 Nov 2026): `commentThreads.list` and `comments.list` cost 1 unit and return at most 100 items a page; a thread carries only some of its replies; `comments.insert` costs 50 units, replies only to top-level comments and needs `youtube.force-ssl`. |
| Telegram | `sendPhoto`, caption up to 1,024 characters, photo up to 10 MB. No method returns channel view counts. |
| DEV | `POST /api/articles` with the `api-key` header; at most 4 tags, sent as a comma-separated string. |
| Hashnode | Free API access was retired on 13 May 2026; every request needs a Pro plan. Not used. |
