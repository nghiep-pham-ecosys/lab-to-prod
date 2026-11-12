# Lab to Prod — rules for Claude Code

Public repository. Everything here is read by recruiters, engineers and strangers.
Display name: **Nghiep Pham · Lab to Prod**. Tagline: *AI engineering, ML and climate — notes
from a chemist turned AI engineer.* All published text is in English.

## Hard rules (never break)

1. **No employer or client material.** Never use code, data, numbers, screenshots, architecture
   or anecdotes from any current or past employer or client of the author, and never name them,
   their customers or colleagues. `tools/banned_terms.yaml` holds hashed terms that fail the build (plain-text
   patterns stay in the git-ignored `tools/banned_terms.local.yaml`); the rule is wider than
   the list. Never write those names in code, tests, commit messages or pull requests either.
2. **No secrets in the repo or in chat.** Tokens live only in GitHub Secrets. Scripts never print
   a token. Never commit `.env`, OAuth client files or token files.
3. **No paid APIs.** No X API, no Anthropic API, no paid media or stock services. Budget is zero.
4. **Nothing is published without a merged pull request.** Never run a publisher without
   `--dry-run` unless the author has said so in the current session. Stop and ask before the
   first real post on any channel and before enabling silent approval (`automerge.yml`).
5. **`PAUSE` file = full stop.** If a file named `PAUSE` exists at the repository root, every
   publishing workflow and script exits without posting.
6. **No automated engagement.** No auto-like, follow, reply, mass tagging or direct messages.
   The author answers comments and messages himself.
7. **No links to private chat sessions** (claude.ai links) and no pasted chat transcripts.

## Voice

- First person, one engineer talking to another. Short sentences. Plain words.
- Concrete numbers over adjectives. If a number was measured, the script that measured it is in
  the repo. If an example is made up, the post says "toy example".
- No emoji, except 🧵 on an X thread. No hype words (revolutionary, game-changing, unlock,
  supercharge). No "In today's fast-paced world" openings. No engagement bait ("Agree?").
- Admit limits: say what was not tested and what the author is still learning.
- British or American spelling is fine; be consistent inside one post.
- Reference posts for tone: `brand/voice-samples.md` (the author's own earlier posts).

## Content rules

- One post, one idea.
- Open with a sentence that makes the reader curious and contains a specific number, or with a
  common mistake. The first word of a LinkedIn or X post is a number or the mistake.
- Close with one lesson the reader can use today, then "Part N of my <series> notes."
- LinkedIn and X: no link in the body. The blog link goes in the first comment or reply.
  3 to 5 hashtags, last line only.
- Climate, simulation and physical AI posts need 1 or 2 source links (paper or report) in
  `sources`. Check every number against the source before writing it.
- Code samples must run. Run them and keep the script next to the post or in `sim/`.
- Images and videos need alt text and subtitles. Videos and images made with AI tools are
  labelled "made with AI" on X and YouTube.
- Short video music: YouTube Audio Library only, or no music.
- A wrong post is corrected with a visible comment or note. It is not deleted.
- "Views are my own" appears on the blog About page.

## Formats

| Channel | Format |
| --- | --- |
| LinkedIn | 180-280 words + 1 image, weekdays 08:30 (Asia/Ho_Chi_Minh) |
| Facebook Page | 80-120 words + image |
| Telegram | short version + image + blog link |
| X | 1 post of at most 280 characters + image, scheduled by hand (no API) |
| YouTube Shorts | 1080x1920, 30-60 s, SRT subtitles, title contains #Shorts, Tue and Thu 19:00 |
| Blog | 5 short notes a week + 1 article of 1,000-1,500 words on Saturday |
| DEV | the Saturday article, republished through the API with a canonical link |
| Hashnode | the Saturday article, pasted by hand (its API is paid) |

Exact file layout and limits: `docs/post-format.md`. Calendar: `content/calendar.yaml`.

## Layout

```
content/calendar.yaml            what is posted when (4 trial weeks + 8 backlog weeks)
content/<week>/<date>-<slug>/    post.md, image.png, short.mp4, short.srt
content/_template/post.md        copy this to start a post
claude/lesson-log.md             what the author studied; ground posts in it
tools/validate.py                the checks that gate every pull request
tools/banned_terms.yaml          hashed terms that fail the build
brand/                           brand.yaml (palettes, fonts, themes), build.py, five options (D selected)
render/image/render.py           image.png from the card: block of a post (Pillow)
render/short/render.mjs          short.mp4 + short.srt from short.json (Remotion)
sim/                             small simulations and notebooks for the simulation series
publish/                         one publisher per channel + run.py; see publish/README.md
published.json                   what was posted where (written by publish/run.py, never by hand)
metrics/collect.py                daily numbers into metrics/metrics.csv; token health check
tools/automerge_gate.py          reads content/<week>/judge.json; holds failing posts
scripts/tokens/                  local scripts that fetch tokens and store them with gh; never print them
docs/setup.md                    the author's one-time manual steps (Vietnamese)
.claude/commands/draft-week.md   /draft-week: the weekly drafting run
.claude/skills/                  write-post, write-blog, fact-check, render-image, render-short, judge, weekly-report
tools/judge_file.py              writes content/<week>/judge.json from the judging subagent's scores
metrics/report.py                tables for the weekly report
reports/                         one report per week
docs/operations.md               switches, workflows, going live, incident steps
blog/                            Astro site; articles in blog/src/content/posts/, see blog/README.md
```


## Commands

```bash
uv run --with-requirements tools/requirements.txt python -m pytest -q
uv run --with-requirements tools/requirements.txt python tools/validate.py
```

```bash
uv run --with pillow --with pyyaml python render/image/render.py --week 2026-W47
```

```bash
node render/short/render.mjs content/2026-W47/2026-11-16-dsa-p2
```

Run the first two before opening a pull request. Open every rendered image, and a few frames
of every video, before committing them. A red `validate` check blocks the merge.

## Working agreement

- One pull request per unit of work. Commit subject: `feat|fix|chore|docs|refactor: description`.
- The weekly content pull request is titled "Week NN" and contains only that week's folders.
- Do not edit a post whose `status` is `published`, except to add a correction note.
- When a rule here turns out to be wrong, propose the change in the weekly report; the author
  decides.
