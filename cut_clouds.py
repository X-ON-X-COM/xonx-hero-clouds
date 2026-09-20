"""Cloud sprites cut out of photographs, for demo 3.

Three rendered passes on 20.09 all came back as «кусочки вати». A rendered cumulus is one
closed silhouette with one kind of edge and one density; a real one has a dense core,
thin translucent margins, and detail at every scale down to the pixel, and nothing short of
a full volumetric renderer gets that. So the sprites are now real clouds, matted out of
CC0 / public-domain photographs (Wikimedia Commons), and graded onto our palette.

The grading is what keeps this from looking like a collage. Every source photograph has its
own sun, sky and white balance. The cut-out keeps only the cloud's LUMINANCE and its alpha,
and the colour is rebuilt from palette.json along a ramp core -> shadow -> lit -> rim, so
every sprite carries the same golden-hour-in-brand-colours light regardless of where it was
shot. Contrast is mapped onto the profile measured off the aerial references (p5 112 / p50
170 / p95 235) so the sprites sit next to each other as one sky.

    python cut_clouds.py <photo.jpg> <name> [x0 y0 x1 y1]   crop box as fractions, optional
Writes clouds/<name>.webp and clouds/<name>-m.webp, prints the luminance profile.
"""
import json, os, pathlib, sys
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).parent
OUT = HERE / 'clouds'
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)
TARGET = np.array([112, 124, 170, 213, 235], np.float32)     # p5 p25 p50 p75 p95, measured

pal = {k: np.array(v, np.float32) for k, v in json.loads((HERE / 'palette.json').read_text())['working_rgb'].items()}
# The ramp the cloud's luminance is laid onto, dark to light. The rim colour is held back
# to the very top of the range: on the first cut a wide rim band turned every sunlit crown
# peach, and the note from Oleg is that this must not go warm-postcard.
RAMP = [(0.00, pal['cloud_core']), (0.30, pal['cloud_shadow']), (0.80, pal['cloud_lit']),
        (0.96, pal['cloud_lit'] * 0.5 + pal['cloud_rim'] * 0.5), (1.00, pal['cloud_rim'])]


def blur(a, r):
    """Separable Gaussian in float (PIL will not blur an 'F' image, scipy is not here)."""
    r = float(r)
    if r <= 0.4:
        return a.astype(np.float32)
    n = max(1, int(round(r * 3)))
    x = np.arange(-n, n + 1, dtype=np.float32)
    k = np.exp(-0.5 * (x / r) ** 2); k /= k.sum()
    out = a.astype(np.float32)
    for axis in (0, 1):
        pad = [(0, 0), (0, 0)]; pad[axis] = (n, n)
        q = np.pad(out, pad, mode='edge')
        acc = np.zeros_like(out)
        for i, w in enumerate(k):
            acc += w * (q[i:i + out.shape[0]] if axis == 0 else q[:, i:i + out.shape[1]])
        out = acc
    return out


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def matte(rgb, s_sky=None):
    """Alpha from saturation, not from colour distance.

    The first version keyed on distance from the sky colour and on being lighter than
    the sky. That keeps the sunlit crowns and drops the whole shaded body, because the
    belly of a cumulus is lit by the sky and is therefore blue-grey: close to the sky in
    colour and no lighter than it. What separates it is saturation. The sky is a
    saturated blue; a cloud, lit or in shade, is nearly grey. So alpha is low saturation,
    with the threshold set from the sky itself, and the body is then closed so the
    shaded interior does not come out as holes.
    """
    mx = rgb.max(-1); mn = rgb.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1)
    blue = (rgb[..., 2] - rgb[..., 0]) / 255.0
    # the sky's own saturation: median over the pixels that are unmistakably sky
    sky_px = (blue > 0.12) & (sat > 0.25)
    if s_sky is None:
        s_sky = float(np.median(sat[sky_px])) if sky_px.sum() > 500 else 0.45
    # hard core: clearly less saturated than the sky; soft margin above it
    core = smoothstep(s_sky * 0.62, s_sky * 0.30, sat)
    # close the body: anything surrounded by cloud is cloud, whatever its own pixel says
    body = smoothstep(0.35, 0.65, blur(core, 9))
    a = np.maximum(core, body * smoothstep(s_sky * 0.95, s_sky * 0.55, sat))
    a = blur(a, 1.2)

    # sky estimate per row, for despill of the translucent margins
    h = rgb.shape[0]
    sky = np.zeros_like(rgb); prev = None
    for y in range(h):
        row = rgb[y][sky_px[y]]
        est = np.median(row, axis=0) if len(row) > 20 else prev
        if est is None:
            est = np.median(rgb[y], axis=0)
        sky[y] = est; prev = est
    sky = np.dstack([blur(sky[..., i], 12) for i in range(3)])
    return np.clip(a, 0, 1), sky


def despill(rgb, sky, a):
    """Un-mix the sky out of the semi-transparent edge: c = (obs - (1-a) sky) / a."""
    a3 = np.clip(a, 0.05, 1)[..., None]
    return np.clip((rgb - (1 - a3) * sky) / a3, 0, 255)


def largest_blob(a, thr=0.25, cell=6):
    """Mask of the biggest connected cloud, on a coarse grid (no scipy here).

    A photograph has scraps all over the sky, and the sprite should be one cloud, not the
    frame's worth of scraps around it. Label the coarse mask by flood fill, keep the
    largest component, and let a little margin around it back in.
    """
    h, w = a.shape
    H, W = h // cell, w // cell
    coarse = a[:H * cell, :W * cell].reshape(H, cell, W, cell).mean((1, 3)) > thr
    label = np.zeros((H, W), np.int32); n = 0; sizes = {}
    for y in range(H):
        for x in range(W):
            if coarse[y, x] and not label[y, x]:
                n += 1; stack = [(y, x)]; label[y, x] = n; cnt = 0
                while stack:
                    cy, cx = stack.pop(); cnt += 1
                    for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                        if 0 <= ny < H and 0 <= nx < W and coarse[ny, nx] and not label[ny, nx]:
                            label[ny, nx] = n; stack.append((ny, nx))
                sizes[n] = cnt
    if not sizes:
        return np.ones_like(a)
    keep = (label == max(sizes, key=sizes.get)).astype(np.float32)
    keep = np.asarray(Image.fromarray((keep * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR), np.float32) / 255
    return smoothstep(0.05, 0.5, blur(keep, 10))            # a soft margin, so nothing is sliced


def regrade(lum, a):
    """Map the cloud's luminance onto the measured profile, then onto the palette ramp."""
    body = a > 0.5
    src = np.percentile(lum[body], [5, 25, 50, 75, 95]) if body.sum() > 500 else np.array([60, 90, 140, 190, 230])
    t = np.interp(lum, src, TARGET)                       # piecewise: match the five points
    # The thin margin of a cloud is where the sun shines through it: it is the brightest
    # part, never the darkest. After despill a half-transparent pixel comes out dim, and
    # mapping that dimness to the core paints a dark outline round every cloud. So the
    # margin is pulled toward the lit value as alpha falls.
    t = t + (TARGET[3] - t) * np.clip((0.55 - a) / 0.55, 0, 1) * 0.9
    u = np.clip((t - 96) / (240 - 96), 0, 1)              # 0 = core, 1 = rim
    col = np.zeros(lum.shape + (3,), np.float32)
    for (t0, c0), (t1, c1) in zip(RAMP[:-1], RAMP[1:]):
        m = (u >= t0) & (u <= t1)
        w = ((u - t0) / max(t1 - t0, 1e-6))[..., None]
        col[m] = (c0 * (1 - w) + c1 * w)[m]
    return col


def cut(path, name, box=None, size=1152):
    im = Image.open(path).convert('RGB')
    if box:
        W, H = im.size
        im = im.crop((int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H)))
    rgb = np.asarray(im, np.float32)
    a, sky = matte(rgb)
    a = a * largest_blob(a)
    # Luminance comes from the photograph as shot, not from the despilled pixel. Despill
    # un-mixes the sky out of a half-transparent margin, and where the sky estimate runs
    # bright it overshoots dark, which drew a grey outline round every cloud on the first
    # cut. A margin pixel's own luminance is already about the cloud's; alpha carries the
    # transparency, so nothing needs un-mixing for the colour.
    lum = blur(rgb @ LUMA, 0.6)
    # trim the last sliver of fringe: erode alpha by about a pixel, then soften it back
    a = np.clip(blur(np.clip(a * 1.25 - 0.18, 0, 1), 0.9), 0, 1)
    col = regrade(lum, a)

    # crop to the cloud, then feather the border of the canvas so nothing shows an edge
    ys, xs = np.where(a > 0.08)
    if len(ys) < 100:
        raise SystemExit('no cloud found in ' + str(path))
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    pad = int(0.06 * max(y1 - y0, x1 - x0))
    y0, y1 = max(0, y0 - pad), min(a.shape[0], y1 + pad)
    x0, x1 = max(0, x0 - pad), min(a.shape[1], x1 + pad)
    a, col = a[y0:y1, x0:x1], col[y0:y1, x0:x1]
    h, w = a.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    edge = np.minimum(np.minimum(xx, w - 1 - xx) / (0.08 * w), np.minimum(yy, h - 1 - yy) / (0.08 * h))
    a = a * smoothstep(0, 1, edge)

    # square canvas, cloud centred, so build_flight.py can treat every sprite alike
    side = max(h, w)
    canvas = np.zeros((side, side, 4), np.float32)
    oy, ox = (side - h) // 2, (side - w) // 2
    canvas[oy:oy + h, ox:ox + w, :3] = col
    canvas[oy:oy + h, ox:ox + w, 3] = a * 255
    img = Image.fromarray(canvas.clip(0, 255).astype(np.uint8), 'RGBA').resize((size, size), Image.LANCZOS)
    OUT.mkdir(exist_ok=True)
    p = OUT / f'{name}.webp'
    img.save(p, 'WEBP', quality=86, method=6)
    img.resize((size // 2, size // 2), Image.LANCZOS).save(OUT / f'{name}-m.webp', 'WEBP', quality=82, method=6)

    # the same cloud seen from far off: mixed toward the sky and thinned, for the far plane
    far = np.asarray(img, np.float32).copy()
    far[..., :3] = far[..., :3] * 0.56 + pal['sky_mid'][None, None] * 0.44
    far[..., 3] *= 0.86
    fimg = Image.fromarray(far.clip(0, 255).astype(np.uint8), 'RGBA')
    fimg.save(OUT / f'{name}_far.webp', 'WEBP', quality=84, method=6)
    fimg.resize((size // 2, size // 2), Image.LANCZOS).save(OUT / f'{name}_far-m.webp', 'WEBP', quality=80, method=6)

    a2 = np.asarray(img, np.float32)
    body = a2[..., 3] > 200
    prof = np.percentile((a2[..., :3][body]) @ LUMA, [5, 50, 95]).round(0) if body.any() else None
    print(name, os.path.getsize(p) // 1024, 'KB', 'profile', prof, 'cover %.0f%%' % (100 * body.mean()))


if __name__ == '__main__':
    src, name = sys.argv[1], sys.argv[2]
    box = tuple(float(v) for v in sys.argv[3:7]) if len(sys.argv) >= 7 else None
    cut(src, name, box)
