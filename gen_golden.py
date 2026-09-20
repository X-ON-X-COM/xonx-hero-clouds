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
import os, sys
import numpy as np
from PIL import Image, ImageFilter

from gen_puffs import fbm, smoothstep, soften
from gen_palette import load as load_palette

OUT = sys.argv[1] if len(sys.argv) > 1 else 'clouds'
SIZE = 1152

pal = load_palette()

# A few degrees above the horizon and off to the right. This is the whole difference
# between "cloud at noon" and "cloud at golden hour": the crown stops being the brightest
# thing on the cloud and the sunward flank takes over.
SUN = np.array([0.92, -0.17, 0.36], np.float32)
SUN /= np.linalg.norm(SUN)

LIT = pal['cloud_lit']          # the flank the sun reaches
SHADE = pal['cloud_shadow']     # the belly, lit by the blue sky alone
WARM = pal['cloud_rim']         # sun coming through where the cloud is thin

# Exposure knobs. Sweep these rather than editing the body.
GOLD = dict(
    relief=0.62,     # how much the height gradient tilts the surface normal
    wrap=0.26,       # wrap light; smaller = harder terminator, more golden hour
    gamma=0.74,      # tone curve on the lit side
    sky=0.18,        # ambient from the sky, added to everything facing up
    crease=0.34,     # shadow where two lobes meet
    rim=0.90,        # sun through the thin edges
)


def lobes_cumulus(rng, n, spread, flat):
    """Cluster of spheres: a wide flat base with smaller lobes piled on top."""
    out = []
    for i in range(n):
        t = i / max(1, n - 1)                       # 0 = base, 1 = crown
        cx = 0.5 + rng.uniform(-spread[0], spread[0]) * (1.0 - 0.45 * t)
        cy = 0.64 - t * rng.uniform(0.10, 0.40) * spread[1] / 0.30
        rad = rng.uniform(0.11, 0.21) * (1.0 - 0.42 * t) * flat
        out.append((cx, cy, rad))
    return out


def height_field(size, lobes, seed, warp=0.26):
    """Union of spheres (p-norm, so the seams stay round), silhouette bitten by noise."""
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
    hs = soften(h, max(3.0, size[0] * 0.016))
    gy, gx = np.gradient(hs * size[0])         # height in pixels, so the slopes are real slopes
    nx, ny, nz = -gx * g['relief'], -gy * g['relief'], np.ones_like(h)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx * inv, ny * inv, nz * inv

    lam = nx * SUN[0] + ny * SUN[1] + nz * SUN[2]
    light = np.clip((lam + g['wrap']) / (1 + g['wrap']), 0, 1) ** g['gamma']
    sky = np.clip(0.5 - ny * 0.5, 0, 1)                         # faces up = more sky light
    light = np.clip(light * 0.88 + sky * g['sky'], 0, 1)

    crease = np.clip(soften(h, max(6.0, size[0] * 0.05)) - h, 0, None)
    crease = crease / max(float(crease.max()), 1e-6)
    light = np.clip(light * (1 - crease * g['crease']), 0, 1)   # shadow where lobes meet

    hn = np.clip(h / max(hmax, 1e-6), 0, 1)
    thin = (1 - hn) ** 1.6                                      # sun through the thin edges
    col = SHADE[None, None] * (1 - light[..., None]) + LIT[None, None] * light[..., None]
    col = col + WARM[None, None] * (thin * light * g['rim'])[..., None]

    fringe = fbm(size[0], size[1], 22, 4, seed + 5001)
    alpha = smoothstep(0.010, 0.30, hn * (0.68 + 0.60 * fringe))   # wide band = soft, vapoury rim
    alpha = soften(alpha, max(2.0, size[0] * 0.004))
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
