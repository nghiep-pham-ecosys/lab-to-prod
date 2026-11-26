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
| `linkedin.pdf` | optional | LinkedIn only: when present, LinkedIn gets a document post with this PDF instead of `image.png` (at most 100 MB and 300 pages); other channels still use `image.png`. See "LinkedIn document posts" below |
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
| `document_title` | optional; title shown on the LinkedIn document when `linkedin.pdf` exists (defaults to `title`) |
| `status` | `draft`, `approved` or `published` |
| `work` | from 2026-W48: the id (or list of ids) of the merged work in `content/work.yaml` the post is about; must match the calendar item |

## The work ledger: `content/work.yaml`

Posts take their content only from project work that is already merged. Each ledger entry has
an `id`, a `repo`, a `ref`, the `merged` date and one or two sentences of `what`. A public repo's
`ref` is the merged pull request URL; a private repo's `ref` is `private@<sha>` and the repo is
named, never linked. Only the repos listed under `repos:` in the ledger can be a source. From
2026-W48 on, `tools/validate.py` fails a calendar item or a post without a `work:` ref, a ref
that is not in the ledger, and work merged after the post date. Calendar items with no merged
work behind them wait in the calendar's `parked:` list, without a date.

## Paper notes as work: `notes/papers/`

A paper the author has read becomes post material only through a merged note in `notes/papers/`
(format and template: `notes/papers/README.md`). After the merge, the note gets a work entry
(`id: paper-<slug>`, `repo: lab-to-prod`, `ref` = the merged pull request URL). Unmerged reading,
the lesson log and Notion pages are never a post source.

## LinkedIn document posts: `linkedin.pdf`

A post folder with `linkedin.pdf` next to `image.png` goes to LinkedIn as a document post: the
publisher uploads the PDF with the Documents API and creates the post with the Posts API, the
`## linkedin` section is the commentary, and the blog link still goes in the first comment. Without
the file, LinkedIn gets today's image post. The dry run (`describe`) names the path that will run.
This is a document post, not a carousel: the API does not support organic carousels. Person-authored
document posts are not yet verified live; if LinkedIn refuses one, remove `linkedin.pdf` and the image
post runs. `image.png` stays required for the other channels.

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
| `## linkedin` | 3,000 characters, no links | 180-280 words, 3-5 hashtags, an open question, then "Part N of my ... notes" |
| `## x` | 280 characters per post (X weighting), no links | one post |
| `## facebook` | none | 80-120 words |
| `## telegram` | 1,024 characters (photo caption limit) | |
| `## youtube` | first line is the title: at most 100 characters, contains `#Shorts` | keyword first |

Channel norms checked by `tools/format_check.py` (warnings only, recorded in `judge.json` under
`format` for the weekly review): LinkedIn 150-300 words, a hook of 1-2 lines, paragraphs of at most
3 lines or 60 words, an open question in the last two paragraphs before the sign-off; Facebook
80-120 words; X at most 280 characters with a number in the hook; Short 30-60 s.

Sources (same file, same `format` entry, warning only): a post whose prose states a number (any digit
outside the hashtag line and the "Part N of my ... notes" sign-off) needs at least one link in
`sources` or a reproducing script in its folder, that is a `*.py` file with a `*.expected` file of the
same name. With neither, `format` gets the warning "the post states numbers but has no source and no
reproducing script". `python tools/format_check.py --week <week>` prints a `sources:` line per post.
This only counts whether a backing exists; whether the source supports the claim is still the judge's
`sources` score, and links are checked by `validate.py --check-links`.

Saturday long articles are not post folders: they live in `blog/src/content/posts/`.
From 2026-W48 on, an article's front matter also has `work:`, the same ids as its calendar item.

## Checking

```bash
uv run --with-requirements tools/requirements.txt python tools/validate.py
```

`--week 2026-W47` limits the run to one week. `--check-links` also requires every source, and
every pull request URL in the work ledger, to answer HTTP 200 (used by the silent-approval gate).
