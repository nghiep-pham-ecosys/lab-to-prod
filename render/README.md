# Render

Images and videos are drawn by code from the post folder, in the brand option selected in
`brand/brand.yaml`. Formats of the inputs: `docs/post-format.md`.

## Image (Pillow)

```bash
uv run --with pillow --with pyyaml python render/image/render.py --week 2026-W47
```

Writes `image.png` (1200x1200) into each post folder. `--theme <name>` overrides the theme.

## Short (Remotion, Node 22 or newer)

```bash
cd render/short && npm ci
```

```bash
node render/short/render.mjs content/2026-W47/2026-11-16-dsa-p2
```

Writes `short.mp4` (1080x1920, 30 fps, H.264) and `short.srt`. `--srt-only` skips the video.
The first run downloads a headless Chrome build. `npm run studio` in `render/short` opens the
Remotion preview.

Shorts have no voice-over and no music: captions carry the content, and nothing needs a
licence. Remotion itself is free for individuals; see its licence before using this in a company.
