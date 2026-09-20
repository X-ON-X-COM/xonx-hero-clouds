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
2. **golden hour, measured, then pulled onto the brand.** `gen_palette.py` pulls eight freely
   licensed cumulus-at-sunset photographs off Wikimedia Commons, drops the land, k-means the sky,
   and finds the two hue families every one of those frames contains: **warm 22.3°** and
   **cool 213.0°**. Measured golden hour is salmon on a screen, and Oleg's note on 20.09 was that
   it has to sit in the company's colours and must not go pink. So the families are dragged toward
   the brand — `--warm #F0EDE6` at 40° and `--graphite #111116` at 240° — by 66% and 34%, giving
   working hues of **34°** and **222°**, with saturation cut hard. Result in `palette.json` /
   `palette.png`: lit `#F0EAE3`, rim `#FFF1DE`, shadow `#898F9E`, core `#5E6473`, sky `#AAB9DB`
   → `#D1D9ED` → `#FAF2E8` → `--cream #FAFAF5`.
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
lit-surface ones read as solid cumulus with a crown, a flank and a belly. `gen_golden.py` holds
that renderer.

## Making the clouds believable, 20.09

First pass still read as cotton wool. Rather than keep guessing, the reference is now
**24 aerial photographs of clouds taken from a flight window** (Wikimedia Commons, free licences,
cached in `refs/`), and four things came out of measuring against them:

- **Contrast, fitted not chosen.** A real sunlit cumulus has a luminance profile of
  p5 112 / p25 124 / p50 170 / p75 213 / p95 235: a spread of 123, with the median well down in
  the midtones. The first pass rendered a spread of 62 with a median of 234 — almost the whole
  cloud sat near white, which is exactly what reads as fake. The knobs in `GOLD` come out of a
  grid search against that profile and land at [102, 124, 164, 198, 229]. Note also that a real
  cloud tops out near 235 and is never blown to pure white, so rim light now **blends** into the
  lit colour instead of adding to it.
- **A crisp, ragged silhouette.** The first pass ramped alpha across a third of the height field,
  which fogs the whole outline. Photographed against sky, a sunlit cumulus has an almost cut edge
  that is ragged rather than soft, so the noise now moves the cut-off threshold and the ramp
  across it is narrow (`edge` / `ragged` / `ramp`), with a thin vapour fringe outside it (`wisp`).
- **Separate heads, not one mass.** Two things did it: a second, much denser population of small
  bubbles sitting on the shell of each large lobe, weighted to the sunward top; and a sharper
  union between spheres (`p=7` instead of `3`), so neighbouring lobes stop melting together and
  the seam between them stays as a crevice.
- **A blur bug that was making it look carved.** `gen_puffs.soften()` normalises to 8 bits before
  handing the array to PIL. For an alpha mask that is fine; for a height field it bands a smooth
  dome into terraces, and the gradient of a terrace is a ridge — which is where the moire squiggle
  all over the surface came from. Normals are gradients, so `gen_golden.blur_f()` does the blur in
  float (by hand: PIL will not blur an `F` image and scipy is not installed).

## Real clouds, 20.09 evening

After three rendered passes Iryna's verdict was still «кусочки вати», with the note that the
clouds may have a different structure altogether. A rendered cumulus is one closed silhouette
with one kind of edge and one density; a real one has a dense core, translucent margins and
detail at every scale, and nothing short of a full volumetric renderer gets there. So the
sprites are now real clouds, matted out of photographs by `cut_clouds.py`.

- **Sources, all CC0 or public domain on Wikimedia Commons**, so no attribution or share-alike
  obligation follows them onto the site: *Cumulus congestus over Gåseberg 1, 2, 4* (CC0, the
  three that key cleanly: sky at saturation ≈ 0.6, cloud at ≈ 0.1, under 8% ambiguous). The
  aerial window series that served as the contrast reference is CC BY-SA and is used for
  measurement only, never cut.
- **Matte on saturation, not colour distance.** The belly of a cumulus is lit by the sky and is
  therefore blue-grey: close to the sky in colour and no lighter than it, so a colour-distance
  key keeps the crowns and punches holes in the body. What separates it is saturation. The
  threshold comes from the sky itself, the body is closed so the shaded interior does not fall
  out, and the largest connected blob is kept so a sprite is one cloud, not a frame of scraps.
- **Graded, not copied.** Only the cloud's luminance and alpha survive. The colour is rebuilt
  from `palette.json` along core → shadow → lit → rim, and the luminance is first mapped onto
  the measured profile (p5 112 / p50 170 / p95 235), so sprites from different photographs
  share one light and sit next to each other as one sky. The rim colour is held back to the
  top 4% of the range; a wider band turned every crown peach.
- **No despill into the colour.** Un-mixing the sky out of the half-transparent margin
  overshoots dark wherever the sky estimate runs bright, which drew a grey outline round every
  cloud. A margin pixel's own luminance is already about the cloud's, and alpha carries the
  transparency. Alpha is eroded by about a pixel and softened back to trim the last fringe.
- Each cut writes a `_far` variant, mixed toward `sky_mid` and thinned, for the far plane.

## Demo 4, 20.09 night: demo 3's flight, mrdoob's cloud structure

Iryna, after the photographic sprites: «структура хмар має бути як тут», pointing at
[mrdoob.com/lab/javascript/webgl/clouds](https://mrdoob.com/lab/javascript/webgl/clouds/). And
after the first build of this page: «я просила лише структуру хмарок, а не змінювати все». So
demo 4 is demo 3's composition exactly — separate clouds with a place and a size in three
dimensions, coming at the viewer, diverging in perspective, passing through the text, on the
same measured-and-pulled golden hour sky — and only what a cloud is made of has changed.

**A cloud is not one sprite any more.** It is a cluster of a hundred or so small, soft, mostly
transparent puffs that overlap, and the overlap is what reads as volume. That is mrdoob's
structure, kept. His flat deck below the camera is not: it replaced the whole scene, and that
was the mistake of the first build.

`field.html` / `field-m.html`, `field.css`, `field.js`, `build_field.py`, Three r128 vendored in
`js/` so nothing depends on a CDN.

- **Clouds**: 46 per box length, radius 110–470 units with small ones common, spread across
  ±1170 sideways and −460..+300 vertically (some above the camera, more below), scattered along
  an 8000-unit box with a second copy one box back for a seamless loop. Puffs per cloud scale
  with its area, 6000 in all. Inside a cloud the puffs are laid out as a cumulus: wider than
  tall, flattened underneath, lumpy on top, densest and largest in the middle.
- **Rendering as the reference**: one `InstancedMesh` of 64-unit planes, `depthTest: false`,
  fog mixed in the fragment shader, the puff at the lens fading with `pow(gl_FragCoord.z, 20)`,
  camera at fov 30 flying at 0.03 units/ms with a little mouse parallax.
- **Through the text, still.** Two canvases share the same seeded field. The back one draws
  everything beyond 700 units and sits behind the hero; the front one draws only what is nearer
  and sits in front of the words and the buttons at 55%. A 160-unit depth fade across the
  boundary keeps a puff that straddles it from being cut in half. `crosses text` in the corner
  drops the front canvas behind the text; `front` cycles its strength.
- **The puff is photographic.** mrdoob's `cloud10.png` is clearly cut from a photograph, and a
  noise puff stacks into smoke. Ours is the densest 256px window of the CC0 Gåseberg cut
  (`ph_3`), luminance kept, radially faded with a wobbling radius so it is not a disc, and
  coloured from `palette.json` shadow → lit. It is mostly lit, with the variation in alpha: a
  shaded puff stacked a hundred times goes grey.
- **Premultiplied, or it halos.** A transparent WebGL canvas over the page has to be
  premultiplied. With straight alpha the first puff over the cleared black framebuffer lands as
  colour × alpha and the browser reads that darkened colour as if it were straight, which drew a
  thick dark halo round every soft edge. The shader outputs premultiplied colour, the blend is
  One / OneMinusSrcAlpha. Fog is the horizon colour, not the zenith, or the far edge of a cloud
  goes blue-grey against the warm band.
- **Tempo** goes through `--xx-tempo` as on the other demos; `motion: off` freezes the flight in
  place; `prefers-reduced-motion` renders one frame a way into the field and stops.

Open: on this light cream sky the clouds read far softer than on mrdoob's deep blue; contrast
is the next knob (denser puffs, or a little more blue at the zenith).

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
