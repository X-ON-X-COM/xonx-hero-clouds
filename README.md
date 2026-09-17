# X-ON-X hero: sky prototypes

Prototypes of the home hero with a moving cloud sky ("flying forward through clouds").
Not the production site. The domain is untouched; this lives only at the GitHub Pages URL.

- **Demo 1** — `index.html` / `m.html`: three drifting cloud layers, the first version (16.09).
- **Demo 2** — `halo.html` / `halo-m.html`: slower flight, a nimbus around the aircraft, and
  clouds that tear into pieces as you pass through them (17.09).

Both pages carry the same viewport switch as the live site (`?full` / `?m` force one build),
and cross-link to each other from the corner panel.

## Demo 2, what changed

- **slower** — far layer 190s, mid 130s, one cloud reaching you every ~17s; the `tempo` button
  in the corner switches calm / normal / quick (`--xx-tempo` in `halo.css`).
- **less gradient** — the warm glow on `.xx-sky` is roughly half of demo 1 and the textures are
  regenerated denser and less blurred (`gen_clouds.py clouds crisp` → `far2/mid2`), so the clouds
  read as shapes rather than haze. The `clouds` button flips back to the old soft look to compare.
- **the nimbus** — `.xx-halo`: a bright core plus two faint rings (warm inside, a whisper of brand
  lime outside) sitting at the vanishing point, brightening each time a cloud passes through it.
- **breaking apart** — each near cloud is four puffs (`gen_puffs.py`) that hold together while the
  cloud is far away and pull apart along their own vectors in the last seconds of the pass, with a
  pale veil for the moment you are inside the cloud.

## Files

- `clouds.css` demo 1, `halo.css` demo 2 — transform + opacity only, nothing else animates
- `clouds/*.webp` procedurally generated textures (own generators, no third-party shaders or stock)
- `gen_clouds.py` layer textures (`crisp` argument for the demo 2 pair), `gen_puffs.py` single puffs
- `build.py` rebuilds demo 1, `build_halo.py` rebuilds demo 2, both from `../xonx-site-preview`
- `motion: on/off` pauses the sky on either page; `prefers-reduced-motion` gives a still frame
