# Lab to Prod

**Nghiep Pham · Lab to Prod** — AI engineering, ML and climate: notes from a chemist turned AI engineer.

This repository is the whole publishing pipeline, in public: every post, image, short video, publisher
script and metric lives here. A weekly pull request is the single approval gate. Nothing is published
unless that pull request is merged.

Status: week 0, under construction. Trial run: 16 Nov to 13 Dec 2026.

## How it works

1. Every Saturday a Claude Code session drafts next week's content into one pull request.
2. `validate` checks lengths, assets, banned terms and the calendar on that pull request.
3. I review and merge. No merge, no posts.
4. GitHub Actions publishes to each channel through its official free API and records the result in `published.json`.
5. Metrics are collected daily into `metrics/metrics.csv`; a weekly report feeds the next calendar.

No paid APIs are used. X posts are generated as files and scheduled by hand.

## Licence

Code: MIT (`LICENSE`). Writing and images under `content/` and `blog/src/content/`: CC BY 4.0 (`LICENSE-content`).

Views are my own.
