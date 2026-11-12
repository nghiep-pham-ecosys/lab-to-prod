---
name: render-image
description: Render the 1200x1200 image of a post from its card block and check it by eye. Use after a post's card is written or changed.
---

# Render the post image

```bash
uv run --with pillow --with pyyaml python render/image/render.py --week <week>
```

or one folder: `... render.py content/<week>/<folder>`. The card format is in
`docs/post-format.md`.

## Choosing

- **Layout:** `code` for a snippet of 2-6 lines; `stat` for one number that carries the post;
  `table` for 2-4 rows compared on one dimension.
- **Theme:** rotate through the three themes of the selected brand option across the week, so
  the feed is not five identical squares. Use the accent-heavy third theme for the post with a
  result or a warning.
- The image must make sense alone, without the post text: someone who only sees the image should
  get the idea.

## Look at it (required)

Open every `image.png` with the Read tool and check:

- [ ] Nothing is clipped, overlapping or touching the edge.
- [ ] The headline is at most 3 lines and the eye lands on it first.
- [ ] The highlighted line or the number is the point of the post.
- [ ] Code is exactly the code in the sample file (copy, do not retype).
- [ ] No typo. Read every word.
- [ ] `image_alt` in the front matter describes this image, including its number or code.

If the renderer raises "does not fit", shorten the text. Do not shrink it below readability and
do not edit the renderer to squeeze it in.
