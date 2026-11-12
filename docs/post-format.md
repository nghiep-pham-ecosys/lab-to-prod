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
| `short.json` | when there is a Short | scenes for `render/short`, see below |
| `*.java` + `*.expected`, `*.py` | when the post quotes code output | the sample and its expected output; CI runs the Java ones |
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

## The image: `card:` in the front matter

`render/image/render.py` draws `image.png` from this block. Three layouts:

```yaml
card:
  layout: code            # code | stat | table
  theme: light            # optional, a theme of the selected brand option; a name from another
                          # option (paper, ink, copper) maps to the same role: light, dark, accent
                          # (yellow under option D)
  headline: "Same value, different object"
  code: ["Integer c = 128, d = 128;", "> c == d   // false"]   # "> " highlights a line
  # stat: {value: "0.62", label: "recall of the gate", note: "8 of 13 caught"}
  # rows: [["VPN", "hours to set up"], ["Direct Connect", "weeks to provision"]]
  lesson: "== compares references. equals() compares values."
```

Text that does not fit raises an error; it is never clipped. Look at the image before committing.

## The Short: `short.json`

`render/short/render.mjs` writes `short.mp4` and `short.srt` from it. Total length 30-60 s.
Every scene needs a `say` line: it is the burned-in caption and the subtitle.

```json
{
  "title": "Why is 128 == 128 false in Java?",
  "kicker": "DSA in Java · Part 2",
  "scenes": [
    {"type": "title", "text": "128 == 128\nis false in Java", "say": "...", "seconds": 5},
    {"type": "code", "code": ["Integer c = 128, d = 128;", "> c == d   // false"], "say": "...", "seconds": 6},
    {"type": "text", "text": "== asks:\nsame object?", "note": "not: same value?", "say": "...", "seconds": 8},
    {"type": "outro", "say": "Part 2 of my DSA in Java notes.", "seconds": 3}
  ]
}
```

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
