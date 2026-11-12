# Post format

One post = one folder: `content/<ISO week>/<date>-<slug>/`, for example
`content/2026-W47/2026-11-16-dsa-p2/`. The date, series, part and slug must match an item in
`content/calendar.yaml`.

| File | Required | Rule |
| --- | --- | --- |
| `post.md` | always | front matter + one `## section` per channel, see `content/_template/post.md` |
| `image.png` | when `status` is `approved` | 1200x1200, rendered by `render/image` |
| `short.mp4` | when `youtube` is in `channels` | 1080x1920, 30-60 s |
| `short.srt` | when `youtube` is in `channels` | subtitles for the whole video |
| `x.md` | generated | the X post, written out by `publish/run.py` for manual scheduling |

## Front matter

| Key | Meaning |
| --- | --- |
| `date` | publishing day, `YYYY-MM-DD` |
| `series`, `part` | must match the calendar |
| `title` | short title, also used on the image and the blog note |
| `channels` | any of `linkedin`, `facebook`, `telegram`, `x_manual`, `youtube` |
| `short_publish_at` | ISO datetime with offset, or `null` when there is no Short |
| `sources` | list of links; at least one for climate, simulation and physical AI posts |
| `image_alt` | alt text for `image.png` |
| `status` | `draft`, `approved` or `published` |

## Sections and limits

| Section | Hard limit (fails the PR) | Target (warning only) |
| --- | --- | --- |
| `## linkedin` | 3,000 characters, no links | 180-280 words, 3-5 hashtags, ends with "Part N of my ... notes" |
| `## x` | 280 characters per post (X weighting), no links | one post |
| `## facebook` | none | 80-120 words |
| `## telegram` | 1,024 characters (photo caption limit) | |
| `## youtube` | first line is the title: at most 100 characters, contains `#Shorts` | keyword first |

Saturday long articles are not post folders: they live in `blog/src/content/posts/`.

## Checking

```bash
uv run --with-requirements tools/requirements.txt python tools/validate.py
```

`--week 2026-W47` limits the run to one week. `--check-links` also requires every source to
answer HTTP 200 (used by the silent-approval gate).
