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
        rad = rng.uniform(0.11, 0.21) * (1.0 - 0.42 * t) * flat
        out.append((cx, cy, rad))
    return out


def height_field(size, lobes, seed, warp=0.15, tile_x=False):
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


def shade(h, hmax, seed, size, tile_x=False, relief=0.62):
    """Light the height field like a solid: crown in sun, belly in sky-blue shadow."""
    # normals read the big lobes only: micro-noise on the surface makes it look like rock
    hs = soften(h, max(3.0, size[0] * 0.016))
    gy, gx = np.gradient(hs * size[0])         # height in pixels, so the slopes are real slopes
    nx, ny, nz = -gx * relief, -gy * relief, np.ones_like(h)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx * inv, ny * inv, nz * inv

    lam = nx * SUN[0] + ny * SUN[1] + nz * SUN[2]
    light = np.clip((lam + 0.42) / 1.42, 0, 1) ** 0.85          # wrap light, no hard terminator
    sky = np.clip(0.5 - ny * 0.5, 0, 1)                         # faces up = more sky light
    light = np.clip(light * 0.82 + sky * 0.26, 0, 1)

    crease = np.clip(soften(h, max(6.0, size[0] * 0.05)) - h, 0, None)
    crease = crease / max(float(crease.max()), 1e-6)
    light = np.clip(light * (1 - crease * 0.30), 0, 1)          # shadow where lobes meet

    hn = np.clip(h / max(hmax, 1e-6), 0, 1)
    thin = (1 - hn) ** 1.6                                      # sun through the thin edges
    col = SHADE[None, None] * (1 - light[..., None]) + LIT[None, None] * light[..., None]
    col = col + WARM[None, None] * (thin * light * 0.42)[..., None]

    fringe = fbm(size[0], size[1], 22, 4, seed + 5001, tile_x)
    alpha = smoothstep(0.010, 0.30, hn * (0.68 + 0.60 * fringe))   # wide band = soft, vapoury rim
    alpha = soften(alpha, max(2.0, size[0] * 0.004))
    return col, alpha


def render(size, lobes, seed, tile_x=False, blur=1.0, relief=0.62):
    h = height_field(size, lobes, seed, tile_x=tile_x)
    col, alpha = shade(h, float(h.max()), seed, size, tile_x, relief)
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
    specs = [(1, 41, 15, (0.26, 0.30), 1.00, 1.0), (2, 57, 12, (0.30, 0.24), 1.05, 0.9),
             (3, 73, 17, (0.24, 0.34), 0.95, 1.1), (4, 89, 10, (0.32, 0.20), 1.10, 0.8),
             (5, 97, 14, (0.28, 0.28), 1.00, 1.0), (6, 113, 9, (0.34, 0.18), 1.15, 0.8)]
    for i, seed, n, spread, flat, blur in specs:
        make(f'puff{i}', seed, n, spread, flat, blur)
