# Brand

Display name: **Nghiep Pham · Lab to Prod**
Tagline: *AI engineering, ML and climate — notes from a chemist turned AI engineer*

Two options are built from `brand.yaml` by `build.py`. Open `option-a/preview.png` and
`option-b/preview.png`, pick one, and set `selected:` in `brand.yaml`. The image and video
renderers read that key, so the choice is one line.

| | Option A: Bench | Option B: Night shift |
| --- | --- | --- |
| Idea | Lab notebook. "Lab ⟶ Prod" written like a chemical reaction | Terminal. A benzene ring whose atoms are graph nodes, one lit |
| Fonts | Fraunces (display), Inter (text), JetBrains Mono (code) | Space Grotesk (display and text), JetBrains Mono (code) |
| Default | light | dark |
| Image themes | `paper`, `ink`, `copper` | `night`, `day`, `signal` |

## Files in each option folder

| File | Size | Where it goes |
| --- | --- | --- |
| `logo.png`, `logo-alt.png` | 1600x400, transparent | blog header, slides (alt = for the opposite background) |
| `avatar.png` | 800x800 | LinkedIn is your own photo; use this for YouTube, Facebook Page, GitHub social |
| `avatar-telegram.png` | 640x640 | Telegram channel photo (channels have no banner) |
| `banner-linkedin.png` | 1584x396 | LinkedIn profile background; text is kept right of the profile photo |
| `banner-youtube.png` | 2560x1440 | YouTube channel art; text is inside the 1546x423 area visible on all devices |
| `banner-facebook.png` | 1640x624 | Facebook Page cover; text is centred because phones crop the sides |
| `theme-*.png` | 1200x1200 | sample post image in each of the 3 themes |
| `preview.png` | | everything on one sheet |

## Rebuild

```bash
uv run --with pillow --with pyyaml python brand/build.py
```

## Fonts

`fonts/` holds the four variable fonts, each under the SIL Open Font License (`OFL-*.txt`).
