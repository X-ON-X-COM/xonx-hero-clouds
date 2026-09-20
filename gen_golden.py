"""Golden hour cumulus sprites for demo 3: one cloud per file, lit by a low sun.

Demo 2 painted distance with two tiled bands, and that is exactly what Oleg objected to
on the 18.09 call: "статичні позаду ... наліплені, they look bad". A tiled strip cannot
fly at you, so it sits there looking stuck on. Demo 3 has no bands at all, only individual
clouds on their own trajectories, which is what this renders.

The renderer is the lit-surface model of the 17.09 morning build (the p_puff set), not the
volumetric one that replaced it. Compositing all three sets over the new sky settles the
argument: the volumetric clouds come out as translucent grey smudges that the sky shows
straight through, while the lit-surface ones read as solid cumulus with a crown, a flank
and a belly. A cloud you are about to fly into has to have a lit side and a dark side, and
only the surface model gives that. What is new here is the light: a sun a few degrees above
the horizon instead of high up, wider contrast between flank and belly, and much more
light through the thin edges. Colours come from palette.json, measured by gen_palette.py.

Two grades come out:
  g_near1..6   full contrast, the clouds that reach the cockpit
  g_far1..5    hazed toward the sky colour and thinned, for the depth behind them

    python gen_palette.py && python gen_golden.py clouds
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageFilter

from gen_puffs import fbm, smoothstep


def blur_f(a, r):
    """Separable Gaussian blur in float, done by hand.

    gen_puffs.soften() normalises to 8 bits before handing the array to PIL, which is fine
    for an alpha mask and quietly disastrous for a height field: 256 levels across a smooth
    dome band it into terraces, and the gradient of a terrace is a ridge. That is where the
    moire squiggle over the first pass came from. PIL will not blur an 'F' image and scipy
    is not installed, so the kernel is applied directly. Surface normals are gradients, so
    everything they are built on stays float.
    """
    r = float(r)
    if r <= 0.4:
        return a.astype(np.float32)
    n = max(1, int(round(r * 3)))
    x = np.arange(-n, n + 1, dtype=np.float32)
    k = np.exp(-0.5 * (x / r) ** 2)
    k /= k.sum()
    out = a.astype(np.float32)
    for axis in (0, 1):
        pad = [(0, 0), (0, 0)]
        pad[axis] = (n, n)
        q = np.pad(out, pad, mode='edge')
        acc = np.zeros_like(out)
        for i, w in enumerate(k):
            if w == 0:
                continue
            acc += w * (q[i:i + out.shape[0]] if axis == 0 else q[:, i:i + out.shape[1]])
        out = acc
    return out
from gen_palette import load as load_palette

OUT = sys.argv[1] if len(sys.argv) > 1 else 'clouds'
SIZE = 1152

pal = load_palette()

# Low and off to the right, but not on the horizon. Golden hour gives the colour; the
# structure comes from the aerial photographs in refs/, which are daytime, and a sun laid
# flat against the horizon cannot reproduce the light/dark split those show. This angle is
# the compromise: the sunward flank carries the light, the tops still read, the far side
# goes properly dark.
SUN = np.array([0.72, -0.52, 0.46], np.float32)
SUN /= np.linalg.norm(SUN)

LIT = pal['cloud_lit']          # the flank the sun reaches
SHADE = pal['cloud_core']       # the belly, lit by the sky alone
WARM = pal['cloud_rim']         # sun coming through where the cloud is thin

# Exposure knobs, fitted rather than chosen. The luminance profile of a real cumulus was
# measured off refs/ (the aerial photographs): p5 112, p25 124, p50 170, p75 213, p95 235,
# so a spread of 123 with a median well down in the midtones. The first pass rendered a
# spread of 62 with a median of 234, which is why it read as cotton wool: almost the whole
# cloud was near white. These values come out of a grid search against that profile and
# land at [102, 124, 164, 198, 229].
GOLD = dict(
    relief=0.62,     # how much the height gradient tilts the surface normal
    smooth=0.006,    # how much the normals ignore: bigger = only the large lobes shade
    wrap=0.02,       # wrap light; small = a hard terminator, which is what the photos show
    gamma=0.95,      # tone curve on the lit side
    sky=0.12,        # ambient from the sky, added to everything facing up
    crease=0.85,     # shadow where two lobes meet
    crease_r=0.05,   # how wide a neighbourhood that crevice shadow looks at
    rim=0.90,        # sun through the thin edges
    base=0.40,       # how much darker the flat underside is
    edge=0.085,      # where the silhouette cuts off
    ragged=0.055,    # how much noise moves that cut about
    ramp=0.030,      # width of the cut: small = crisp
    wisp=0.22,       # the thin vapour that survives outside the cut
)


def lobes_cumulus(rng, n, spread, flat, bubbles=2.6):
    """Cluster of spheres: a wide flat base with smaller lobes piled on top.

    Two populations, because one is what made the first pass look like cotton wool.
    The large lobes carry the silhouette; on top of them sits a much denser population
    of small bubbles, weighted to the upper surface. Aerial photographs of cumulus are
    covered in those small cauliflower heads, and their absence is most of what reads
    as unreal.
    """
    out = []
    for i in range(n):
        t = i / max(1, n - 1)                       # 0 = base, 1 = crown
        cx = 0.5 + rng.uniform(-spread[0], spread[0]) * (1.0 - 0.45 * t)
        cy = 0.64 - t * rng.uniform(0.10, 0.40) * spread[1] / 0.30
        rad = rng.uniform(0.11, 0.21) * (1.0 - 0.42 * t) * flat
        out.append((cx, cy, rad))
    big = list(out)
    for _ in range(int(n * bubbles)):
        bx, by, br = big[int(rng.integers(len(big)))]
        ang = rng.uniform(0, 6.2832)
        # sit the bubble on the shell of a big lobe, biased to its sunward top
        r = br * rng.uniform(0.55, 1.00)
        out.append((bx + math.cos(ang) * r * 1.05,
                    by + math.sin(ang) * r * 0.80 - br * 0.18,
                    br * rng.uniform(0.16, 0.38)))
    return out


def height_field(size, lobes, seed, warp=0.26, p=7.0):
    """Union of spheres, silhouette bitten by noise.

    p is how sharp that union is. A low p melts neighbouring spheres into one smooth mass,
    which is what the first pass did and why the surface had no separate heads. Raising it
    moves the union toward a plain maximum, so each lobe keeps its own crown and the seam
    between two of them stays as a crevice, which is what the aerial photographs show.
    """
    yy, xx = np.mgrid[0:size[1], 0:size[0]].astype(np.float32)
    xx /= size[0]; yy /= size[1]
    aspect = size[0] / size[1]
    bump = (fbm(size[0], size[1], 7, 5, seed + 3001) - 0.5) * 2
    fine = (fbm(size[0], size[1], 19, 4, seed + 4001) - 0.5) * 2
    acc = np.zeros((size[1], size[0]), np.float32)
    for cx, cy, rad in lobes:
        dx = (xx - cx) * aspect
        dy = yy - cy
        d = np.sqrt(dx * dx + dy * dy)
        d = d * (1.0 + warp * bump + 0.22 * warp * fine)   # cauliflower, not a ball
        inside = np.clip(rad * rad - d * d, 0, None)
        acc += np.sqrt(inside) ** 3
    return acc ** (1.0 / 3.0)


def shade(h, hmax, seed, size):
    """Light the height field like a solid: sunward flank warm, belly sky-blue."""
    g = GOLD
    # normals read the big lobes only: micro-noise on the surface makes it look like rock
    hs = blur_f(h, max(1.0, size[0] * g['smooth']))
    gy, gx = np.gradient(hs * size[0])         # height in pixels, so the slopes are real slopes
    nx, ny, nz = -gx * g['relief'], -gy * g['relief'], np.ones_like(h)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx * inv, ny * inv, nz * inv

    lam = nx * SUN[0] + ny * SUN[1] + nz * SUN[2]
    light = np.clip((lam + g['wrap']) / (1 + g['wrap']), 0, 1) ** g['gamma']
    sky = np.clip(0.5 - ny * 0.5, 0, 1)                         # faces up = more sky light
    light = np.clip(light * (1 - g['sky']) + sky * g['sky'], 0, 1)

    crease = np.clip(blur_f(h, max(4.0, size[0] * g['crease_r'])) - h, 0, None)
    crease = crease / max(float(crease.max()), 1e-6)
    light = np.clip(light * (1 - crease * g['crease']), 0, 1)   # shadow where lobes meet

    hn = np.clip(h / max(hmax, 1e-6), 0, 1)

    # the base of a cumulus is flat and clearly darker than anything above it
    yy = np.linspace(0, 1, size[1], dtype=np.float32)[:, None]
    base = fbm(size[0], size[1], 6, 3, seed + 9101) * 0.05
    light = light * (1 - g['base'] * smoothstep(0.60, 0.80, yy - base))

    thin = (1 - hn) ** 1.6                                      # sun through the thin edges
    col = SHADE[None, None] * (1 - light[..., None]) + LIT[None, None] * light[..., None]
    # Rim light blends in rather than adding: the lit colour is already at the top of the
    # range a real sunlit cumulus reaches (235 over the reference photographs), and adding
    # to it just blows the thin edges out to pure white, which is the one thing no cloud
    # in any of the references does.
    k = np.clip(thin * light * g['rim'], 0, 1)[..., None]
    col = col * (1 - k) + WARM[None, None] * k

    # A crisp but ragged silhouette. The first pass ramped alpha across a third of the
    # height field, which fogs the whole outline: against a real sky a sunlit cumulus has
    # an almost cut edge, ragged rather than soft. So the threshold itself is what the
    # noise moves, and the ramp across it is narrow.
    ragged = fbm(size[0], size[1], 13, 5, seed + 5001)
    thr = g['edge'] + g['ragged'] * (ragged - 0.5) * 2
    alpha = smoothstep(thr, thr + g['ramp'], hn)
    wisp = smoothstep(thr - g['ragged'] * 1.6, thr, hn) * g['wisp']   # a thin vapour fringe
    alpha = np.clip(alpha + wisp * (1 - alpha), 0, 1)
    alpha = blur_f(alpha, max(0.8, size[0] * 0.0022))
    return col, alpha


def render(size, lobes, seed, blur=1.0):
    h = height_field(size, lobes, seed)
    col, alpha = shade(h, float(h.max()), seed, size)
    rgba = np.dstack([col, alpha * 255]).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(rgba, 'RGBA')
    return img.filter(ImageFilter.GaussianBlur(blur)) if blur else img


def make(name, seed, n, spread, flat, blur, haze=0.0, alpha=1.0):
    rng = np.random.default_rng(seed)
    img = render((SIZE, SIZE), lobes_cumulus(rng, n, spread, flat), seed, blur=blur)
    a = np.asarray(img, np.float32).copy()

    # aerial perspective: distance mixes the cloud toward the sky and thins it out
    if haze:
        a[..., :3] = a[..., :3] * (1 - haze) + pal['sky_mid'][None, None] * haze
    a[..., 3] *= alpha

    # nothing may touch the border, or the sprite shows its own square edge in flight
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32) / SIZE
    rad = np.sqrt((xx - 0.5) ** 2 + ((yy - 0.55) * 1.05) ** 2)
    a[..., 3] *= smoothstep(0.50, 0.40, rad)

    img = Image.fromarray(a.clip(0, 255).astype(np.uint8), 'RGBA')
    p = os.path.join(OUT, f'{name}.webp')
    img.save(p, 'WEBP', quality=84, method=6)
    img.resize((SIZE // 2, SIZE // 2), Image.LANCZOS).save(
        os.path.join(OUT, f'{name}-m.webp'), 'WEBP', quality=80, method=6)
    print(name, os.path.getsize(p) // 1024, 'KB')


# Lobe counts and spreads sit around the shape that read best against the new sky: wide
# base, cauliflower crowns, a belly you can see. Fewer lobes gives a cotton ball (what
# Oleg called анімешне), many more breaks the silhouette into scraps.
NEAR = [(1, 41, 24, (0.38, 0.26), 1.05, 1.0), (2, 57, 21, (0.42, 0.22), 1.12, 0.9),
        (3, 73, 26, (0.35, 0.30), 1.00, 1.1), (4, 89, 19, (0.44, 0.20), 1.16, 0.9),
        (5, 97, 23, (0.39, 0.25), 1.06, 1.0), (6, 113, 20, (0.45, 0.21), 1.14, 0.9)]
FAR = [(1, 211, 16, (0.30, 0.17), 1.28, 1.3), (2, 227, 14, (0.34, 0.15), 1.34, 1.4),
       (3, 241, 18, (0.28, 0.19), 1.24, 1.3), (4, 257, 13, (0.36, 0.14), 1.38, 1.5),
       (5, 269, 15, (0.32, 0.16), 1.30, 1.4)]

if __name__ == '__main__':
    for i, seed, n, spread, flat, blur in NEAR:
        make(f'g_near{i}', seed, n, spread, flat, blur)
    # far: smaller, hazier, thinner. These carry the depth the tiled bands used to fake.
    for i, seed, n, spread, flat, blur in FAR:
        make(f'g_far{i}', seed, n, spread, flat, blur, haze=0.46, alpha=0.84)
