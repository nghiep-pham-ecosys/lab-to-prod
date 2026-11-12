# Blog

Astro site, deployed to GitHub Pages at `https://nghiep-pham-ecosys.github.io/lab-to-prod/`.

| Route | Source |
| --- | --- |
| `/` | intro, latest articles and notes |
| `/notes/` | short notes, read from the post folders in `../content/` (the `## linkedin` section) |
| `/posts/` | long articles, markdown files in `src/content/posts/` |
| `/series/` | one page per series in `../content/calendar.yaml` |
| `/about/` | short CV and links |
| `/rss.xml`, `/sitemap-index.xml`, `/robots.txt` | generated |

Dated content appears on or after its date (Asia/Ho_Chi_Minh). The site is rebuilt every
morning, so a note merged on Sunday shows up on its own day.

## Run locally (Node 24)

```bash
uv run --with pillow --with pyyaml python blog/scripts/prebuild.py
```

```bash
cd blog && npm ci && npx astro dev
```

Build and smoke test, the same steps as `blog.yml`:

```bash
cd blog && npx astro build && node scripts/check-dist.mjs
```

Set `SHOW_FUTURE=1` before the build to preview content dated in the future.

## Settings in `src/site.ts`

| Key | What to put |
| --- | --- |
| `linkedin` | full profile URL; the link is hidden while empty |
| `goatcounter` | GoatCounter site code; no script is loaded while empty |
| `searchConsole` | Google Search Console verification token |

A custom domain later: change `site` and `base` in `astro.config.mjs`.

## A new article

Add `src/content/posts/<slug>.md` with `title` (at most 70 characters, keyword first),
`description` (50-160 characters), `date`, `series` (`build-log` or `deep-dive`), `tags`.
The Open Graph image is drawn by `scripts/prebuild.py` from the title, in the selected brand theme.
