"""far2 / mid2 bands for the halo demo, built from the same cumulus renderer as the puffs.

Each band is a strip of individually rendered clouds pasted into a 2048x1024 canvas that
tiles in x (anything crossing an edge is pasted again on the other side). The far band is
pushed toward the sky colour and thinned out — aerial perspective, so distance reads.
    python gen_sky.py clouds
"""
import numpy as np, sys, os
from PIL import Image
from gen_puffs import lobes_cumulus, render, smoothstep

OUT = sys.argv[1] if len(sys.argv) > 1 else 'clouds'
W, H = 2048, 1024
SKY = np.array([223, 232, 241], np.float32)          # what a cloud fades into at distance


def one(seed, px, flat):
    rng = np.random.default_rng(seed)
    n = int(rng.integers(8, 15))
    lobes = lobes_cumulus(rng, n, (float(rng.uniform(0.24, 0.34)), 0.26), flat)
    img = render((px, px), lobes, seed, blur=max(0.6, px / 700))
    a = np.asarray(img, np.float32)
    yy, xx = np.mgrid[0:px, 0:px].astype(np.float32) / px
    rad = np.sqrt((xx - 0.5) ** 2 + ((yy - 0.55) * 1.05) ** 2)
    a[..., 3] *= smoothstep(0.50, 0.40, rad)
    return a


def band(name, count, size_range, yband, haze, alpha, seed0, flat=1.0):
    canvas = np.zeros((H, W, 4), np.float32)
    rng = np.random.default_rng(seed0)
    for i in range(count):
        px = int(rng.uniform(*size_range) * W)
        a = one(seed0 + i * 37, px, flat * float(rng.uniform(0.9, 1.15)))
        # aerial perspective: the smaller and higher it sits, the more sky is in front of it
        t = haze * float(rng.uniform(0.75, 1.15))
        a[..., :3] = a[..., :3] * (1 - t) + SKY[None, None] * t
        a[..., 3] *= alpha * float(rng.uniform(0.80, 1.05))
        cx = int(rng.uniform(0, W)); cy = int(rng.uniform(*yband) * H)
        for shift in (-W, 0, W):                     # keep the band tileable in x
            x0, y0 = cx - px // 2 + shift, cy - px // 2
            xs, xe = max(0, x0), min(W, x0 + px)
            ys, ye = max(0, y0), min(H, y0 + px)
            if xs >= xe or ys >= ye:
                continue
            src = a[ys - y0:ye - y0, xs - x0:xe - x0]
            dst = canvas[ys:ye, xs:xe]
            sa = src[..., 3:4] / 255.0
            da = dst[..., 3:4] / 255.0
            out_a = sa + da * (1 - sa)
            rgb = (src[..., :3] * sa + dst[..., :3] * da * (1 - sa)) / np.maximum(out_a, 1e-6)
            dst[..., :3] = rgb
            dst[..., 3:4] = out_a * 255.0
    img = Image.fromarray(canvas.clip(0, 255).astype(np.uint8), 'RGBA')
    p = os.path.join(OUT, f'{name}.webp')
    img.save(p, 'WEBP', quality=84, method=6)
    img.resize((W // 2, H // 2), Image.LANCZOS).save(
        os.path.join(OUT, f'{name}-m.webp'), 'WEBP', quality=80, method=6)
    print(name, os.path.getsize(p) // 1024, 'KB')


if __name__ == '__main__':
    band('far2', 26, (0.06, 0.13), (0.30, 0.62), haze=0.42, alpha=0.80, seed0=1201, flat=1.15)
    band('mid2', 14, (0.14, 0.26), (0.42, 0.80), haze=0.16, alpha=0.95, seed0=2301, flat=1.05)
