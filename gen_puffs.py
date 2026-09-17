"""Cumulus puffs with alpha, for the halo demo: a cloud you fly into and tear apart.

Not thresholded noise — each puff is a union of spheres rendered as a height field and
lit like a solid: that is what gives round cauliflower lobes, a shaded belly and a bright
sunward crown instead of a grey smudge. The same renderer builds the far/mid bands in
gen_sky.py, so every cloud on the page comes from one model.
    python gen_puffs.py clouds
"""
import numpy as np, sys, os
from PIL import Image, ImageFilter

OUT = sys.argv[1] if len(sys.argv) > 1 else 'clouds'
SIZE = 1280

SUN = np.array([0.42, -0.58, 0.70], np.float32)     # x right, y down, z toward the viewer
SUN /= np.linalg.norm(SUN)
LIT = np.array([255, 253, 250], np.float32)         # crown in full sun
SHADE = np.array([178, 192, 212], np.float32)       # belly, lit by the blue sky only
WARM = np.array([255, 226, 188], np.float32)        # sun coming through the thin edges


def value_noise(w, h, cells_x, cells_y, seed, tile_x=False):
    r = np.random.default_rng(seed)
    g = r.random((cells_y + 1, cells_x + 1)).astype(np.float32)
    if tile_x:
        g[:, -1] = g[:, 0]
    img = Image.fromarray((g * 255).astype(np.uint8), 'L').resize((w, h), Image.BICUBIC)
    return np.asarray(img, dtype=np.float32) / 255.0


def fbm(w, h, cells, octaves, seed, tile_x=False):
    total = np.zeros((h, w), np.float32); amp = 1.0; c = cells; norm = 0.0
    for o in range(octaves):
        total += amp * value_noise(w, h, max(2, int(c)), max(2, int(c * h / w)), seed + o * 101, tile_x)
        norm += amp; amp *= 0.5; c *= 2
    return total / norm


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def soften(a, r):
    lo, hi = float(a.min()), float(a.max())
    if hi - lo < 1e-6:
        return a.copy()
    q = (a - lo) / (hi - lo)
    q = np.asarray(Image.fromarray((q * 255).astype(np.uint8), 'L')
                   .filter(ImageFilter.GaussianBlur(r)), dtype=np.float32) / 255.0
    return q * (hi - lo) + lo


def lobes_cumulus(rng, n, spread, flat):
    """Cluster of spheres: a wide flat base with smaller lobes piled on top."""
    out = []
    for i in range(n):
        t = i / max(1, n - 1)                       # 0 = base, 1 = crown
        cx = 0.5 + rng.uniform(-spread[0], spread[0]) * (1.0 - 0.45 * t)
        cy = 0.64 - t * rng.uniform(0.10, 0.40) * spread[1] / 0.30
        big = rng.random() < 0.28                      # a couple of domes carry the silhouette
        rad = rng.uniform(0.17, 0.26) if big else rng.uniform(0.07, 0.15)
        rad *= (1.0 - 0.38 * t) * flat
        out.append((cx, cy, rad))
    return out


def height_field(size, lobes, seed, warp=0.13, tile_x=False):
    """Union of spheres (p-norm, so the seams stay round), silhouette bitten by noise."""
    yy, xx = np.mgrid[0:size[1], 0:size[0]].astype(np.float32)
    xx /= size[0]; yy /= size[1]
    aspect = size[0] / size[1]
    bump = (fbm(size[0], size[1], 7, 5, seed + 3001, tile_x) - 0.5) * 2
    fine = (fbm(size[0], size[1], 19, 4, seed + 4001, tile_x) - 0.5) * 2
    acc = np.zeros((size[1], size[0]), np.float32)
    for cx, cy, rad in lobes:
        shifts = (-1.0, 0.0, 1.0) if tile_x else (0.0,)
        for sh in shifts:
            dx = (xx - cx - sh) * aspect
            dy = yy - cy
            d = np.sqrt(dx * dx + dy * dy)
            d = d * (1.0 + warp * bump + 0.22 * warp * fine)  # cauliflower, not a ball
            inside = np.clip(rad * rad - d * d, 0, None)
            acc += np.sqrt(inside) ** 3
    return acc ** (1.0 / 3.0)


def warp_field(a, seed, size, amp, cells, tile_x=False):
    """Remap the field through two noise offsets: turbulence, not a row of balls."""
    h, w = a.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ox = (fbm(w, h, cells, 4, seed + 7001, tile_x) - 0.5) * 2 * amp
    oy = (fbm(w, h, cells, 4, seed + 7301, tile_x) - 0.5) * 2 * amp
    sx = (xx + ox) % w if tile_x else np.clip(xx + ox, 0, w - 1)
    sy = np.clip(yy + oy, 0, h - 1)
    return a[sy.astype(np.int32), sx.astype(np.int32)]


def erode(dens, seed, size, tile_x=False):
    """Bite fractal detail out of the silhouette: cores stay solid, edges break into wisps."""
    det = np.zeros_like(dens)
    amp, cells, norm = 1.0, 9, 0.0
    for o in range(5):
        det += amp * (fbm(size[0], size[1], cells, 2, seed + 6100 + o * 37, tile_x) - 0.5) * 2
        norm += amp; amp *= 0.55; cells = int(cells * 2.1)
    det /= norm
    out = np.clip(dens - (1 - dens) * 0.72 * np.clip(det, -1, 1) - 0.03, 0, 1)
    # erosion may only nibble at the cloud, never scatter crumbs across the sky
    near = smoothstep(0.03, 0.22, soften(dens, max(8.0, size[0] * 0.03)))
    return out * near


def shade(dens, seed, size, tile_x=False, sun_steps=26, sun_step_px=9.0):
    """2D approximation of a volumetric render: march toward the sun through the density.

    Transmittance along the sun ray gives the self-shadow — bright sunward crowns, deep
    shade underneath, and the bright fringe where the cloud is thin enough to shine through.
    """
    sx, sy = SUN[0], SUN[1]                       # y is down, so the sun is up-right
    n = np.sqrt(sx * sx + sy * sy)
    sx, sy = sx / n, sy / n
    scale = size[0] / 1024.0
    opt = np.zeros_like(dens)
    for i in range(1, sun_steps + 1):
        dx = int(round(sx * sun_step_px * scale * i))
        dy = int(round(sy * sun_step_px * scale * i))
        opt += np.roll(np.roll(dens, -dy, axis=0), -dx, axis=1)
    opt *= sun_step_px * scale / 40.0
    trans = np.exp(-0.78 * opt)                   # how much sun reaches this point

    up = np.zeros_like(dens)                      # sky light comes straight down
    for i in range(1, 9):
        up += np.roll(dens, int(round(6 * scale * i)), axis=0)
    sky = np.exp(-0.55 * up * 6 * scale / 40.0)

    powder = 1 - np.exp(-3.2 * dens)              # thin edges scatter forward and glow
    lit = np.clip(0.60 + 0.45 * trans, 0, 1)      # even the shaded side is a bright cloud
    col = (LIT[None, None] * lit[..., None]
           + SHADE[None, None] * ((1 - lit) * (0.55 + 0.45 * sky))[..., None]
           + WARM[None, None] * (trans * (1 - powder) * 0.18)[..., None])
    alpha = 1 - np.exp(-2.0 * dens)
    alpha = soften(alpha, max(2.0, size[0] * 0.011))
    return col, np.clip(alpha, 0, 1)


def render(size, lobes, seed, tile_x=False, blur=1.0, base_y=0.72):
    h = height_field(size, lobes, seed, tile_x=tile_x)
    dens = h / max(float(h.max()), 1e-6)
    # turbulence at two scales: big swirls in the body, filaments at the rim
    dens = warp_field(dens, seed, size, size[0] * 0.055, 5, tile_x)
    dens = warp_field(dens, seed + 91, size, size[0] * 0.018, 13, tile_x)
    dens = erode(dens, seed, size, tile_x)

    wisp = (fbm(size[0], size[1], 30, 4, seed + 8101, tile_x) - 0.5) * 2
    edge = np.clip(dens * (1 - dens) * 4.0, 0, 1)
    top = smoothstep(0.85, 0.35, np.linspace(0, 1, size[1], dtype=np.float32)[:, None])
    dens = np.clip(dens + edge * wisp * 0.42 * (0.35 + 0.65 * top), 0, 1)   # tendrils on top

    yy = np.linspace(0, 1, size[1], dtype=np.float32)[:, None]
    flat = fbm(size[0], size[1], 5, 4, seed + 8601, tile_x) * 0.13
    dens *= smoothstep(base_y + 0.30, base_y - 0.22, yy - flat)   # cumulus sits on a soft flat base
    dens = soften(dens, max(2.0, size[0] * 0.006))

    col, alpha = shade(dens, seed, size, tile_x)
    rgba = np.dstack([col, alpha * 255]).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(rgba, 'RGBA')
    return img.filter(ImageFilter.GaussianBlur(blur)) if blur else img


def make(name, seed, n, spread, flat, blur):
    rng = np.random.default_rng(seed)
    img = render((SIZE, SIZE), lobes_cumulus(rng, n, spread, flat), seed, blur=blur)
    # nothing may touch the border: feather the last few per cent of the canvas
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32) / SIZE
    rad = np.sqrt((xx - 0.5) ** 2 + ((yy - 0.55) * 1.05) ** 2)
    a = np.asarray(img, np.float32)
    a[..., 3] *= smoothstep(0.50, 0.40, rad)
    img = Image.fromarray(a.clip(0, 255).astype(np.uint8), 'RGBA')
    p = os.path.join(OUT, f'{name}.webp')
    img.save(p, 'WEBP', quality=84, method=6)
    img.resize((SIZE // 2, SIZE // 2), Image.LANCZOS).save(
        os.path.join(OUT, f'{name}-m.webp'), 'WEBP', quality=80, method=6)
    print(name, os.path.getsize(p) // 1024, 'KB')


if __name__ == '__main__':
    specs = [(1, 41, 18, (0.40, 0.20), 1.30, 1.2), (2, 57, 15, (0.44, 0.16), 1.40, 1.1),
             (3, 73, 20, (0.38, 0.24), 1.25, 1.3), (4, 89, 13, (0.46, 0.14), 1.50, 1.0),
             (5, 97, 17, (0.42, 0.18), 1.35, 1.2), (6, 113, 12, (0.48, 0.13), 1.55, 1.0)]
    for i, seed, n, spread, flat, blur in specs:
        make(f'puff{i}', seed, n, spread, flat, blur)
