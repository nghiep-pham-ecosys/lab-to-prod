# Publish

`run.py` posts approved content through each platform's free official API and records every
success in `published.json` at the repository root. It is a dry run unless `--live` is given.

| Channel | Mode | Trigger | What happens | Secrets |
| --- | --- | --- | --- | --- |
| Facebook Page | api | merge | photo post, scheduled by Facebook for 08:30 on the post's day | `FB_PAGE_ID`, `FB_PAGE_TOKEN` |
| YouTube | api | merge | Short uploaded as private with `publishAt`, then the SRT as captions | `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` |
| LinkedIn | api | daily | post with image, then the blog link as first comment (best effort) | `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_PERSON_URN` |
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
| LinkedIn | The self-serve "Share on LinkedIn" product documents `/v2/ugcPosts` + `/v2/assets?action=registerUpload` with scope `w_member_social`. Tokens last 60 days; refresh tokens are for selected partners only. The comments documentation lists a different scope, so the first comment may be refused: the post is kept and the link is added by hand. |
| Facebook | Graph API v27.0. `/{page-id}/photos` with `published=false` and `scheduled_publish_time`, between 10 minutes and 30 days ahead. PNG uploads are capped at 1 MB, so images go up as JPEG. Long-lived Page tokens do not expire by date. |
| YouTube | `publishAt` needs `privacyStatus: private`. `videos.insert` has its own quota of 100 calls a day; `captions.insert` costs 400 units. The 2 Nov 2026 revision says uploads from unverified projects are no longer locked to private. There is no Shorts flag. |
| Telegram | `sendPhoto`, caption up to 1,024 characters, photo up to 10 MB. No method returns channel view counts. |
| DEV | `POST /api/articles` with the `api-key` header; at most 4 tags, sent as a comma-separated string. |
| Hashnode | Free API access was retired on 13 May 2026; every request needs a Pro plan. Not used. |
