---
name: write-blog
description: Write the Saturday long article (1,000-1,500 words) in blog/src/content/posts/ with SEO front matter. Use for build logs and deep dives.
---

# Write the Saturday article

Output: `blog/src/content/posts/<slug>.md`. The slug is lowercase words from the title joined by
hyphens; it never changes after publishing.

## Two kinds

**Build log** (`series: build-log`): what the pipeline did this week. Required content:
the numbers from `metrics/metrics.csv` and `published.json` (use the `weekly-report` skill's
table, do not retype numbers), what broke and how it was fixed (link the commit or pull request),
one thing that surprised the author, and what changes next week. Failures are the interesting
part; do not hide them. If there are no numbers yet, say so plainly.

**Deep dive** (`series: deep-dive`): a longer version of the week's best note. It must add
something the note did not have: a derivation, a runnable experiment, a counter-example.

## Front matter

```yaml
title: "Keyword first, at most 70 characters"
description: "50-160 characters. What the reader gets. Contains the main keyword."
date: 2026-11-21          # the Saturday in the calendar
series: build-log         # or deep-dive
part: 1                   # the calendar's part number
tags: [llmops, ai-engineering]   # 2-4 lowercase tags; DEV accepts at most 4
```

## Writing

- 1,000 to 1,500 words. Count them (`wc -w`).
- Open with a number or a concrete situation, not with background.
- `##` headings every 150-300 words, each saying something ("The gate caught 2 of 5 posts"), not
  a label ("Results").
- Code in fenced blocks with a language. Every block was run; the script is in the repo.
- Tables for anything compared across 3 or more items.
- Links: to the repository file or pull request being discussed, and to primary sources.
  Internal links start with `/lab-to-prod/`.
- End with what is still unknown or what comes next, not with a summary.
- Same voice rules as posts (`CLAUDE.md`). No employer or client material.

## After writing

1. Run the `fact-check` skill on it.
2. `uv run --with pillow --with pyyaml python blog/scripts/prebuild.py`, then build the blog
   with `SHOW_FUTURE=1` and run `node scripts/check-dist.mjs`. Open the Open Graph image in
   `blog/public/og/posts/` and check that the title fits.
3. `python -m publish.run export --week <week>` to write the Hashnode file.
