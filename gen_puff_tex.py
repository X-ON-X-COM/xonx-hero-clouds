"""The one texture demo 4 is built from: a soft, irregular puff with alpha.

Demo 4 follows the structure of mrdoob's WebGL clouds (mrdoob.com/lab/javascript/webgl/clouds):
thousands of small, soft, half-transparent billboards scattered through a long box, with the
camera flying down it. No billboard is a cloud on its own; the clouds are what the overlap
of hundreds of them adds up to, and that overlap is what reads as volume. So the texture has
to be a puff, not a cloud: soft everywhere, irregular, no hard edge anywhere, and mostly
transparent, so that depth accumulates instead of any single sprite showing its outline.

Colour comes from palette.json, lit toward the top and shaded toward the bottom, so the
stacked puffs carry the golden hour light in the brand's colours.

    python gen_puff_tex.py            # writes clouds/puff.png
"""
import json, pathlib
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).parent
SIZE = 256

pal = {k: np.array(v, np.float32) for k, v in json.loads((HERE / 'palette.json').read_text())['working_rgb'].items()}


def value_noise(n, cells, seed):
    r = np.random.default_rng(seed)
    g = r.random((cells + 1, cells + 1)).astype(np.float32)
    img = Image.fromarray((g * 255).astype(np.uint8), 'L').resize((n, n), Image.BICUBIC)
    return np.asarray(img, np.float32) / 255.0


def fbm(n, cells, octaves, seed):
    total = np.zeros((n, n), np.float32); amp, c, norm = 1.0, cells, 0.0
    for o in range(octaves):
        total += amp * value_noise(n, max(2, int(c)), seed + o * 101); norm += amp; amp *= 0.5; c *= 2
    return total / norm


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def main(seed=7):
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32) / (SIZE - 1)
    dx, dy = xx - 0.5, yy - 0.5
    r = np.sqrt(dx * dx + dy * dy) * 2                 # 0 centre, 1 at the inscribed circle
    # the shape: a radial falloff whose radius is pushed about by noise, so the puff is
    # lumpy rather than a disc, and a second, finer noise that breaks the density inside
    warp = (fbm(SIZE, 3, 4, seed) - 0.5) * 0.55
    fine = fbm(SIZE, 6, 5, seed + 17)
    body = smoothstep(1.0, 0.15, r + warp)
    dens = body * (0.55 + 0.45 * fine)
    alpha = np.clip(dens, 0, 1) ** 1.35                # thin: most of the puff is see-through

    # lit from above and a little from the right: the top of a puff is the sun side
    light = np.clip(0.42 + 0.58 * (0.5 - dy * 1.6 + dx * 0.4), 0, 1) * (0.7 + 0.3 * fine)
    col = pal['cloud_core'][None, None] * (1 - light[..., None]) + pal['cloud_lit'][None, None] * light[..., None]
    rim = smoothstep(0.35, 0.05, alpha) * light
    col = col * (1 - rim[..., None] * 0.35) + pal['cloud_rim'][None, None] * rim[..., None] * 0.35

    rgba = np.dstack([col, alpha * 255]).clip(0, 255).astype(np.uint8)
    (HERE / 'clouds').mkdir(exist_ok=True)
    Image.fromarray(rgba, 'RGBA').save(HERE / 'clouds' / 'puff.png')
    print('puff.png', SIZE, 'alpha mean %.2f max %.2f' % (alpha.mean(), alpha.max()))


if __name__ == '__main__':
    main()
