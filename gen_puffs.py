"""Single cloud puffs with alpha, for the halo demo: a cloud you fly into and tear apart.

Same look as gen_clouds.py (fBm + gaussian blobs, sun low upper-right), but each file
holds one isolated cumulus on transparency, so several of them can drift apart on screen.
    python gen_puffs.py clouds
"""
import numpy as np, sys, os
from PIL import Image, ImageFilter

OUT = sys.argv[1] if len(sys.argv) > 1 else 'clouds'
N = 6                                   # puff1 … puff6
SIZE = 1024


def value_noise(w, h, cells_x, cells_y, seed):
    r = np.random.default_rng(seed)
    g = r.random((cells_y + 1, cells_x + 1)).astype(np.float32)
    img = Image.fromarray((g * 255).astype(np.uint8), 'L').resize((w, h), Image.BICUBIC)
    return np.asarray(img, dtype=np.float32) / 255.0


def fbm(w, h, base_cells, octaves, seed, gain=0.5, lac=2.0):
    total = np.zeros((h, w), np.float32); amp = 1.0; c = base_cells; norm = 0.0
    for o in range(octaves):
        total += amp * value_noise(w, h, int(c), int(c), seed + o * 101)
        norm += amp; amp *= gain; c *= lac
    return total / norm


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def shift(a, dy, dx):
    return np.roll(np.roll(a, dy, axis=0), dx, axis=1)


def warp(a, wx, wy, amt):
    """Domain-warp a field by two noise maps (pixel shifts via coordinate remap)."""
    h, w = a.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    sx = np.clip(xx + (wx - 0.5) * amt, 0, w - 1)
    sy = np.clip(yy + (wy - 0.5) * amt, 0, h - 1)
    return a[sy.astype(np.int32), sx.astype(np.int32)]


def puff(seed, size=SIZE, lobes=9, flat=1.0):
    """A cauliflower cluster: fat lobes low and wide, smaller ones stacked on top."""
    r = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) / size
    field = np.zeros((size, size), np.float32)
    for i in range(lobes):
        t = i / max(1, lobes - 1)
        cx = 0.5 + r.uniform(-0.30, 0.30) * (0.55 + 0.45 * t)
        cy = 0.66 - t * r.uniform(0.10, 0.34)
        rx = r.uniform(0.16, 0.30) * (1.0 - 0.45 * t)
        ry = rx * r.uniform(0.60, 0.95) / flat
        d = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
        field += np.exp(-d * 1.3) * r.uniform(0.7, 1.0)
    return field


def soften(a, r):
    return np.asarray(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), 'L')
                      .filter(ImageFilter.GaussianBlur(r)), dtype=np.float32) / 255.0


def make(name, seed, lobes, flat, blur):
    base = puff(seed, lobes=lobes, flat=flat)
    n1 = fbm(SIZE, SIZE, 4, 7, seed)
    n2 = fbm(SIZE, SIZE, 10, 6, seed + 500)
    n3 = fbm(SIZE, SIZE, 22, 5, seed + 700)
    wx = fbm(SIZE, SIZE, 3, 4, seed + 900)
    wy = fbm(SIZE, SIZE, 3, 4, seed + 1300)
    base = warp(base, wx, wy, SIZE * 0.12)              # lumpy silhouette, not a pancake

    dens = base * 0.66 + n1 * 0.42 + n2 * 0.26 + n3 * 0.12 - 0.34
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32) / SIZE
    rad = np.sqrt((xx - 0.5) ** 2 + ((yy - 0.55) * 1.10) ** 2)
    dens *= smoothstep(0.52, 0.26, rad)                 # nothing touches the border

    alpha_f = smoothstep(0.03, 0.34, dens)              # wide, noisy band = fractal edge

    # shading reads the big lobes, not the fringe: blur first, then look toward the sun
    form = soften(dens, 18)
    detail = soften(dens, 6)
    fine = soften(dens, 2)
    grad = ((form - shift(form, 16, 13)) + (detail - shift(detail, 7, 6)) * 0.9
            + (fine - shift(fine, 3, 2)) * 0.5)
    vert = smoothstep(0.92, 0.10, yy)                   # tops catch the light, bellies do not
    light = np.clip(0.70 + grad * 3.0 + vert * 0.22 - 0.10, 0.12, 1.0)
    edge = np.clip(alpha_f * (1 - alpha_f) * 4.0, 0, 1)
    rim = edge * np.clip(grad * 5.0, 0, 1)              # only the sunward fringe glows

    lit = np.array([255, 253, 249], np.float32)
    shade = np.array([176, 189, 210], np.float32)
    warm = np.array([255, 224, 182], np.float32)
    col = shade[None, None] * (1 - light[..., None]) + lit[None, None] * light[..., None]
    col = col * (1 - rim[..., None] * 0.32) + warm[None, None] * rim[..., None] * 0.32

    alpha = (alpha_f ** 0.85) * 255
    img = Image.fromarray(np.dstack([col, alpha]).clip(0, 255).astype(np.uint8), 'RGBA')
    img = img.filter(ImageFilter.GaussianBlur(blur))
    p = os.path.join(OUT, f'{name}.webp')
    img.save(p, 'WEBP', quality=82, method=6)
    img.resize((SIZE // 2, SIZE // 2), Image.LANCZOS).save(
        os.path.join(OUT, f'{name}-m.webp'), 'WEBP', quality=78, method=6)
    print(name, os.path.getsize(p) // 1024, 'KB')


if __name__ == '__main__':
    # a mix of fat cumulus and flatter shreds, so a torn cloud has pieces of both
    specs = [(1, 41, 10, 1.00, 1.6), (2, 57, 8, 1.15, 1.4), (3, 73, 11, 0.90, 1.8),
             (4, 89, 7, 1.30, 1.3), (5, 97, 9, 1.05, 1.6), (6, 113, 6, 1.40, 1.2)]
    for i, seed, lobes, flat, blur in specs[:N]:
        make(f'puff{i}', seed, lobes, flat, blur)
