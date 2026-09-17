import numpy as np, sys, os
from PIL import Image, ImageFilter

OUT = sys.argv[1]
CRISP = len(sys.argv) > 2 and sys.argv[2] == 'crisp'   # halo demo: denser, better shaded, less blur
rng = np.random.default_rng(7)

def value_noise(w, h, cells_x, cells_y, seed):
    r = np.random.default_rng(seed)
    g = r.random((cells_y + 1, cells_x + 1)).astype(np.float32)
    g[:, -1] = g[:, 0]                       # tileable in x
    img = Image.fromarray((g * 255).astype(np.uint8), 'L')
    big = Image.new('L', (img.width * 3, img.height))
    for i in range(3): big.paste(img, (i * img.width, 0))
    big = big.resize((w * 3, h), Image.BICUBIC)
    return np.asarray(big.crop((w, 0, 2 * w, h)), dtype=np.float32) / 255.0

def fbm(w, h, base_cells, octaves, seed, gain=0.5, lac=2.0):
    total = np.zeros((h, w), np.float32); amp = 1.0; cx = base_cells; cy = max(2, int(base_cells * h / w)); norm = 0
    for o in range(octaves):
        total += amp * value_noise(w, h, int(cx), int(cy), seed + o * 101)
        norm += amp; amp *= gain; cx *= lac; cy *= lac
    return total / norm

def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

def blobs(w, h, n, seed, sx=(0.10, 0.22), sy=(0.05, 0.10), yband=(0.25, 0.75)):
    r = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); xx /= w; yy /= h
    field = np.zeros((h, w), np.float32)
    for _ in range(n):
        cx, cy = r.random(), r.uniform(*yband); rx, ry = r.uniform(*sx), r.uniform(*sy)
        for shift in (-1, 0, 1):                  # x-tileable blobs
            d = ((xx - cx - shift) / rx) ** 2 + ((yy - cy) / ry) ** 2
            field = np.maximum(field, np.exp(-d * 1.6))
    return field

def shift(a, dy, dx):
    return np.roll(np.roll(a, dy, axis=0), dx, axis=1)

def make_layer(name, w, h, kind, seed):
    n1 = fbm(w, h, 6, 7, seed)
    n2 = fbm(w, h, 14, 6, seed + 500)
    if kind == 'far':
        base = blobs(w, h, 9, seed, sx=(0.22, 0.42), sy=(0.06, 0.12), yband=(0.30, 0.70))
        d = smoothstep(0.42, 0.78, n1 * 0.8 + n2 * 0.2 + base * 0.35 - 0.10) * base
        d *= 0.85
    elif kind == 'mid':
        base = blobs(w, h, 7, seed, sx=(0.12, 0.24), sy=(0.07, 0.13), yband=(0.28, 0.72))
        d = smoothstep(0.40, 0.72, n1 * 0.65 + n2 * 0.35 + base * 0.45 - 0.14) * smoothstep(0.05, 0.6, base)
    else:  # near
        base = blobs(w, h, 3, seed, sx=(0.12, 0.22), sy=(0.07, 0.12), yband=(0.58, 0.88))
        d = smoothstep(0.40, 0.74, n1 * 0.6 + n2 * 0.4 + base * 0.45 - 0.16) * smoothstep(0.08, 0.6, base) * 0.8
    # vertical feather so the layer never shows a hard edge
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    d *= smoothstep(0.0, 0.18, yy) * smoothstep(1.0, 0.82, yy)
    d = np.clip(d, 0, 1)

    # lighting: sun low, upper right. Thinner toward the sun = lit; undersides = shadow.
    up = shift(d, 10, -8)           # density a bit above-right (toward sun)
    light = np.clip(0.55 + (d - up) * 2.4, 0, 1)
    rim = np.clip(d * (1 - d) * 3.2, 0, 1) * np.clip(0.5 + (d - up) * 3.0, 0, 1)

    lit = np.array([255, 251, 243], np.float32)
    shade = np.array([203, 208, 222], np.float32)
    warm = np.array([255, 224, 186], np.float32)
    if CRISP:                                  # deeper undersides, so the shape reads at low opacity
        shade = np.array([174, 186, 207], np.float32)
        light = np.clip((light - 0.5) * 1.35 + 0.52, 0, 1)
    col = shade[None, None] * (1 - light[..., None]) + lit[None, None] * light[..., None]
    col = col * (1 - rim[..., None] * 0.55) + warm[None, None] * rim[..., None] * 0.55
    alpha = (d ** (0.62 if CRISP else 0.85)) * 255
    rgba = np.dstack([col, alpha]).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(rgba, 'RGBA')
    blur = {'far': 0.8, 'mid': 1.3, 'near': 1.8} if CRISP else {'far': 1.2, 'mid': 2.2, 'near': 3.0}
    img = img.filter(ImageFilter.GaussianBlur(blur[kind]))
    img.save(os.path.join(OUT, f'{name}.webp'), 'WEBP', quality=80, method=6)
    img.resize((w // 2, h // 2), Image.LANCZOS).save(os.path.join(OUT, f'{name}-m.webp'), 'WEBP', quality=78, method=6)
    print(name, img.size, os.path.getsize(os.path.join(OUT, f'{name}.webp')) // 1024, 'KB /',
          os.path.getsize(os.path.join(OUT, f'{name}-m.webp')) // 1024, 'KB')

suffix = '2' if CRISP else ''
make_layer('far' + suffix, 2048, 1024, 'far', 11)
make_layer('mid' + suffix, 2048, 1024, 'mid', 23)
if not CRISP:
    make_layer('near', 2048, 1024, 'near', 37)
