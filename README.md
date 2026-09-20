# X-ON-X hero: sky prototypes

Prototypes of the home hero with a moving cloud sky ("flying forward through clouds").
Not the production site. The domain is untouched; this lives only at the GitHub Pages URL.

- **Demo 1** — `index.html` / `m.html`: three drifting cloud layers, the first version (16.09).
- **Demo 2** — `halo.html` / `halo-m.html`: slower flight, a nimbus around the aircraft, and
  clouds that tear into pieces as you pass through them (17.09).
- **Demo 3** — `flight.html` / `flight-m.html`: golden hour, every cloud on its own trajectory,
  perspective divergence, and clouds that cross the text (20.09). This is the one built to the
  feedback from the 18.09 call.

All three carry the same viewport switch as the live site (`?full` / `?m` force one build),
and cross-link to each other from the corner panel.

## Demo 2, what changed

- **slower** — far layer 190s, mid 130s, one cloud reaching you every ~17s; the `tempo` button
  in the corner switches calm / normal / quick (`--xx-tempo` in `halo.css`).
- **less gradient, believable cumulus** — the warm glow on `.xx-sky` is roughly half of demo 1, and
  every cloud is re-rendered. `gen_puffs.py` builds a density field (union of spheres, turbulence at
  two scales, fractal erosion, filaments at the rim, a soft flat base) and shades it by marching
  toward the sun through that density: self-shadowing, sky light from above, forward scattering at
  the thin edges. `gen_sky.py` composites the same puffs into the `far2` / `mid2` bands with aerial
  perspective. Reference for the look: the cloud on the Awwwards annual page. The `clouds` button
  flips back to demo 1's soft textures to compare.
- **the nimbus** — `.xx-halo`: a bright core plus two faint rings (warm inside, a whisper of brand
  lime outside) sitting at the vanishing point, brightening each time a cloud passes through it.
- **breaking apart** — each near cloud is four puffs that hold together while the cloud is far away
  and pull apart along their own vectors in the last seconds of the pass, with a pale veil for the
  moment you are inside the cloud.
- **nothing over the words** — every sky layer sits at `z-index: 0`, behind the hero text: clouds
  pass behind the headline, never across it.

## Demo 3, the four points from the 18.09 call

1. **nothing sits still.** The tiled `far2` / `mid2` bands are gone. A tiled strip cannot fly at
   you, which is why they read as stuck on ("наліплені ... they look bad"). Demo 3 is 24 individual
   cloud sprites, each with its own vector, radius, scale, duration and phase, laid out by
   `build_flight.py` and written into the markup as CSS custom properties.
2. **golden hour, measured.** `gen_palette.py` pulls eight freely licensed cumulus-at-sunset
   photographs off Wikimedia Commons, drops the land, k-means the sky, and finds the two hue
   families every one of those frames contains: **warm 22.3°** and **cool 213.0°**. Those hues are
   what we keep; saturation and lightness are ours, because the references are late golden hour and
   genuinely dark while the hero has to stay light. Result in `palette.json` / `palette.png`:
   lit crown `#FFEDE3`, rim `#FFCFB2`, shadow `#AFC4DE`, sky `#9BBAE0` → `#FCF3ED` → site cream.
3. **perspective.** Clouds leave the vanishing point and diverge outward along their own radial
   vector, the way a straight street opens up as you walk down it. The radius fractions in
   `@keyframes xxFlight` are shaped by hand rather than left to a timing function, so a cloud
   crawls while it is far away and rushes past at the end. A near cloud is two or three sprites
   launched on almost the same vector: the divergence pulls them apart by itself, so the cloud
   tears as it passes with no separate mechanism for tearing.
4. **through the text.** Three planes — `--far` at `z-index: 0` behind the words, `--mid` at `2`
   across them, `--near` at `4` in front of the words and the buttons. The nav keeps `z-index: 50`,
   so nothing ever crawls over the menu. The two upper planes run at 46% and 34% so the hero stays
   readable, and the front plane has its own opacity curve (`xxFlightNear`): invisible until it is
   already large, a few seconds sweeping over the headline, gone. Without that curve a near cloud
   sits over the text as fog for most of its cycle. The `crosses text` button in the corner puts
   every plane back behind the words, for comparing against the 17.09 decision.

The clouds themselves are the **lit-surface** renderer of the 17.09 morning build, not the
volumetric one that replaced it. Compositing all three sets over the new sky settles it: the
volumetric clouds come out as translucent grey smudges the sky shows straight through, while the
lit-surface ones read as solid cumulus with a crown, a flank and a belly. A cloud you are about to
fly into needs a lit side and a dark side. `gen_golden.py` holds that renderer with a sun a few
degrees above the horizon instead of high up, wider contrast, and much more light through the
thin edges.

## Files

- `clouds.css` demo 1, `halo.css` demo 2, `flight.css` demo 3 — transform and opacity only,
  nothing else animates, no filters (a blurred element that also transforms re-renders every frame)
- `clouds/*.webp` procedurally generated textures (own generators, no third-party shaders or stock);
  `g_near*` / `g_far*` are demo 3, `-m` files are the half-size set the phone builds point at
- `gen_clouds.py` demo 1 textures; `gen_puffs.py` + `gen_sky.py` demo 2; `gen_palette.py` +
  `gen_golden.py` demo 3. `refs/` holds the cached Wikimedia photographs, re-fetched if deleted
- `build.py` rebuilds demo 1, `build_halo.py` demo 2, `build_flight.py` demo 3, all three from
  `../xonx-site-preview`. Demos 1 and 2 are patched in place, never rebuilt: their state is approved
- `motion: on/off` pauses the sky on any page. `prefers-reduced-motion` on demo 3 hides the two
  planes that cross the text and leaves a still far sky, because freezing the whole field piles
  every sprite of the cycle into one image

## Open, not decided here

- The hero italic (`Beyond Advisory.`) is set in a light grey that was chosen against the old cream
  background. Over a blue sky it is close to invisible in every demo. That is hero typography, which
  is the new hero design, not the sky.
- Pages serves HTML with a 10 min max-age. Bump `V` in the builder **and** hard-refresh after a
  deploy, or you will be looking at the previous build.
