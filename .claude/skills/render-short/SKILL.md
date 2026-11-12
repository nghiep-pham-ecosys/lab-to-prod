---
name: render-short
description: Write short.json and render the 1080x1920 Short (30-60 s) with SRT subtitles for a post. Use for posts whose calendar item has a short block.
---

# Render a Short

Input: a post folder whose calendar item has `short:`. Output in the same folder: `short.json`,
`short.mp4`, `short.srt`.

## Write `short.json`

Format in `docs/post-format.md`. 6 to 9 scenes, 30 to 60 seconds in total (aim for 40-50).

1. **Scene 1 is the hook** (`title`, 4-5 s): the surprising fact in at most 8 words on screen.
2. **Show, then explain.** A `code` scene with the evidence, then a `text` scene with the reason.
3. **One step per scene.** If a caption needs two sentences, split the scene.
4. **Second to last: the rule** the viewer keeps (`text`).
5. **Last: `outro`** (3 s) with the Part line.

Timing: about 2.5 words per second of caption, and never under 4 seconds for a scene with code.
Captions (`say`) are read, not heard: there is no voice-over. Write `==`, not "equals-equals".
Code lines stay under 30 characters so they are readable on a phone. Code is copied from the
sample file in the post folder.

No music (or YouTube Audio Library only). No footage, no faces, no logos of other companies.

## Render

```bash
node render/short/render.mjs content/<week>/<folder>
```

First time on a machine: `cd render/short && npm ci`.

## Look at it (required)

```bash
ffmpeg -y -loglevel error -ss <t> -i short.mp4 -frames:v 1 frame.png
```

Extract one frame from the middle of every scene and open each with the Read tool:

- [ ] Text is inside the safe area (nothing under the caption, nothing at the very top).
- [ ] Each scene is readable in the time it is on screen.
- [ ] The caption matches the scene.
- [ ] The last frame shows the brand and the Part line.

Then set the `## youtube` section and `short_publish_at` in `post.md`, add `youtube` to
`channels`, and run `python tools/validate.py --week <week>`.
