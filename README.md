# X-ON-X hero: sky prototype

Prototype of the home hero with a moving cloud sky ("flying forward through clouds").
Not the production site. The domain is untouched; this lives only at the GitHub Pages URL.

- `index.html` desktop, `m.html` phone (same viewport switch as the live site, `?full` / `?m` force one)
- `clouds.css` the sky: three textured layers, two copies each, transform + opacity only
- `clouds/*.webp` procedurally generated cloud textures (own generator, no third-party shaders or stock)
- `build.py` reassembles both pages from the live builds in `../xonx-site-preview` (nav + hero only)
- "motion: on/off" button bottom right pauses the sky; `prefers-reduced-motion` gives a still frame
