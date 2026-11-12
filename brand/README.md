# Brand

Display name: **Nghiep Pham · Lab to Prod**
Tagline: *AI engineering, ML and climate — notes from a chemist turned AI engineer*

Five options (A to E) are built from `brand.yaml` by `build.py`. Each `option-<key>/preview.png`
shows one on a sheet; `selected:` in `brand.yaml` picks the one the image, video and blog
renderers use, so the choice is one line. The selected option is **D, Signal**.

Option D in short:

- **Badge.** A glossy gold rounded square with "L→P" in bold black. A benzene ring (Kekulé, with
  its three double bonds) is pressed into the gold underneath the letters: a deep-gold groove with
  a pale lip, about 75% of the badge, cut back around the letters so they stay crisp at 64 px. The
  badge is the same bright gold in every theme, so the black letters keep full contrast. The blog
  favicon is the badge without the ring (at 16-32 px the ring is only noise).
- **Wordmark.** "Lab (→) Prod" in Space Grotesk 700, the arrow inside a gold pill.
- **Lockup** (`lockup: true`): the logo, every banner, the blog header and the Short outro set the
  badge left of the wordmark, 1.8 times the wordmark's cap height, vertically centred; in banners
  the "NGHIEP PHAM" kicker and the tagline start where the wordmark starts.
- **Avatar** (`avatar.png`, `avatar-alt.png`, `avatar-telegram.png`): the badge as a round seal,
  because every platform shows avatars as circles. A glossy gold disc fills the canvas circle, with
  a thin groove just inside its edge; the pressed-in benzene ring and L→P sit a little above the
  centre, and "NGHIEP PHAM AI" in Space Grotesk 700 runs along the bottom of the circle, letters
  upright towards the centre, reading left to right. The text keeps inside 88% of the radius, so a
  platform's circle crop or ring overlay does not touch it. It reads at 128 px; at 64 px only L→P
  does. Everywhere else (cards, logo, banners, blog header, favicon) the badge stays a rounded
  square.
- **Honeycomb** (`texture: honeycomb`): a faint hexagonal lattice over the background gradient,
  anchored on one foil benzene ring. The ring sits at the top right on the kicker line (cards,
  Open Graph images, banners inside their safe box, Shorts); the rule under a card's kicker stops
  short of it. The lattice is about 8% opaque next to that ring and fades to 3% far from it, and
  it keeps a clear halo around everything drawn on top (text, panels, marks), so it never sits
  behind a letter. On the blog it is a CSS mask, strongest at the top right and off the text
  column.
- **Themes.** `light` (default), `dark` (used by Shorts), `yellow`. A card written with another
  option's theme name keeps its role: `paper`/`ink`/`copper` become `light`/`dark`/`yellow`.

Option E (the previous choice) also uses a lockup: its benzene ring, with one lit gold node, sits
left of the `lab-to-prod` mono wordmark at 1.6 times the cap height.

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
| `avatar-alt.png`, `banner-linkedin-alt.png` | | dark variants (glossy options C, D, E) |
| `preview.png` | | everything on one sheet |

## Rebuild

```bash
uv run --with pillow --with pyyaml python brand/build.py
```

## Fonts

`fonts/` holds the four variable fonts, each under the SIL Open Font License (`OFL-*.txt`).
