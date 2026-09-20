"""Golden hour colour-coding, derived from photographs rather than guessed.

Oleg on the 18.09 call: "знайдемо фото декількох цих Golden Hour, знаходимо відтінки
по них, знаходимо щось середнє, задаємо йому хекс". This does that:

  1. pull freely licensed cumulus-at-sunset photographs from Wikimedia Commons
  2. keep the upper sky, drop the land, k-means what is left into 8 clusters
  3. every one of those frames splits into the same two hue families, which is the
     whole signature of golden hour: a warm family near 20 deg and a cool family near
     211 deg. The measured hues are what we take.
  4. hold those hues, and put saturation and lightness where our cream hero needs them

Step 4 is deliberate. The references are late golden hour and genuinely dark; dropping
their values onto the page would give a dusk sky, and the lesson from 17.09 is that the
hero has to stay light. The photographs decide the hues, we decide the exposure.

    python gen_palette.py            # writes palette.json + palette.png
"""
import json, pathlib, colorsys, subprocess
import numpy as np
from PIL import Image, ImageDraw

HERE = pathlib.Path(__file__).parent
CACHE = HERE / 'refs'
OUT = HERE / 'palette.json'

REFS = {
    'latvia': 'https://thumb.wikimedia.org/wikipedia/commons/thumb/8/8b/Sunset_-_cumulus_clouds_-_Latvia.jpg/1920px-Sunset_-_cumulus_clouds_-_Latvia.jpg',
    'chermside1': 'https://thumb.wikimedia.org/wikipedia/commons/thumb/b/b5/Cumulus_and_fractus_at_sunset_7th_Brigade_Park_P1050841.jpg/1920px-Cumulus_and_fractus_at_sunset_7th_Brigade_Park_P1050841.jpg',
    'chermside2': 'https://thumb.wikimedia.org/wikipedia/commons/thumb/d/dc/Cumulus_mediocris_at_sunset_7th_Brigade_Park_Chermside_P1220761.jpg/1920px-Cumulus_mediocris_at_sunset_7th_Brigade_Park_Chermside_P1220761.jpg',
    'chermside3': 'https://thumb.wikimedia.org/wikipedia/commons/thumb/e/e0/Cumulus_and_fractus_at_sunset_7th_Brigade_Park_P1050840.jpg/1920px-Cumulus_and_fractus_at_sunset_7th_Brigade_Park_P1050840.jpg',
    'aitutaki': 'https://upload.wikimedia.org/wikipedia/commons/a/ac/Aitutaki_sunset_1.jpg',
    # golden hour proper, not the pink that comes after it: towering cumulus with the sun
    # still above the horizon, which is the light Oleg asked for
    'sterling': 'https://thumb.wikimedia.org/wikipedia/commons/thumb/a/ae/2016-07-01_20_24_39_Cumulus_clouds_near_sunset_along_Old_Ox_Road_%28Virginia_State_Secondary_Route_606%29_in_Sterling%2C_Loudoun_County%2C_Virginia.jpg/1920px-2016-07-01_20_24_39_Cumulus_clouds_near_sunset_along_Old_Ox_Road_%28Virginia_State_Secondary_Route_606%29_in_Sterling%2C_Loudoun_County%2C_Virginia.jpg',
    'oakhill1': 'https://thumb.wikimedia.org/wikipedia/commons/thumb/d/de/2020-08-04_19_56_22_Towering_cumulus_cloud_viewed_from_Tranquility_Court_in_the_Franklin_Farm_section_of_Oak_Hill%2C_Fairfax_County%2C_Virginia.jpg/1920px-2020-08-04_19_56_22_Towering_cumulus_cloud_viewed_from_Tranquility_Court_in_the_Franklin_Farm_section_of_Oak_Hill%2C_Fairfax_County%2C_Virginia.jpg',
    'oakhill2': 'https://thumb.wikimedia.org/wikipedia/commons/thumb/7/73/2020-08-04_20_13_51_Towering_cumulus_cloud_near_sunset_viewed_from_Tranquility_Court_in_the_Franklin_Farm_section_of_Oak_Hill%2C_Fairfax_County%2C_Virginia.jpg/1920px-2020-08-04_20_13_51_Towering_cumulus_cloud_near_sunset_viewed_from_Tranquility_Court_in_the_Franklin_Farm_section_of_Oak_Hill%2C_Fairfax_County%2C_Virginia.jpg',
}
UA = 'xonx-hero-clouds/1.0 (iryna.oliinyk@x-on-x.com) palette extraction'
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)

# X-ON-X, from the site tokens. The brand has no orange in it: its warm is a paper
# cream at about 40deg with almost no saturation, and its neutral is graphite, which
# leans very slightly blue-violet rather than sky blue.
BRAND = {
    'warm': 40.0,    # --warm #F0EDE6 / --border #E6E2DB
    'cool': 240.0,   # --graphite #111116 / --charcoal #1C1C22
}
# How far each family is dragged off the measurement and onto the brand. Oleg, 20.09:
# the golden hour has to sit in the company's colours and must not go pink. Measured
# golden hour is 22deg, which is salmon on a screen; the brand cream is 40deg. Pulling
# two thirds of the way keeps the hour and loses the postcard.
PULL = {'warm': 0.66, 'cool': 0.34}

# What each role is for, and the exposure we put it at. The hue is measured and then
# pulled; saturation and value are ours, and they are deliberately low: this is a
# muted sky in a graphite-and-cream identity, not a sunset.
#                 family   sat    val
ROLES = {
    'cloud_lit':    ('warm', 0.078, 0.94),  # crown in full sun. Not 1.00: measured over
                                            # the reference photographs a sunlit cumulus
                                            # tops out near 235, it is never blown out
    'cloud_rim':    ('warm', 0.195, 1.00),  # light coming through the thin edges
    'cloud_body':   ('warm', 0.035, 0.90),  # the sunlit flank between crown and belly
    'cloud_shadow': ('cool', 0.135, 0.62),  # belly, lit by the sky alone
    'cloud_core':   ('cool', 0.180, 0.45),  # deepest shade inside the cloud
    'sky_high':     ('cool', 0.225, 0.86),  # zenith
    'sky_mid':      ('cool', 0.120, 0.93),
    'sky_warm':     ('warm', 0.105, 0.98),  # the warm band standing above the horizon
    'sky_low':      ('warm', 0.030, 0.99),  # meets the site cream
    'sun_glow':     ('warm', 0.150, 1.00),
}


def fetch():
    CACHE.mkdir(exist_ok=True)
    for name, url in REFS.items():
        p = CACHE / f'{name}.jpg'
        if not p.exists():
            # curl, not urllib: this python has no CA bundle of its own
            subprocess.run(['curl', '-sfL', '-A', UA, '-o', str(p), url], check=True)
            print('fetched', p.name, p.stat().st_size // 1024, 'KB')
    return sorted(CACHE.glob('*.jpg'))


def kmeans(X, k, iters=60, seed=3):
    rng = np.random.default_rng(seed)
    C = X[rng.choice(len(X), k, replace=False)].copy()
    for _ in range(iters):
        lab = ((X[:, None, :] - C[None]) ** 2).sum(2).argmin(1)
        for i in range(k):
            m = lab == i
            if m.any():
                C[i] = X[m].mean(0)
    return C, np.bincount(lab, minlength=k).astype(np.float32)


def clusters(path, k=8):
    """Upper 45% of the frame only: that is sky and cloud, never land or silhouette."""
    im = Image.open(path).convert('RGB')
    w, h = im.size
    im = im.crop((0, 0, w, int(h * 0.45)))
    im = im.resize((360, max(1, int(360 * im.size[1] / w))), Image.LANCZOS)
    a = np.asarray(im, np.float32).reshape(-1, 3)
    a = a[(a @ LUMA) > 70]                       # anything darker is a tree or a roof
    idx = np.random.default_rng(1).choice(len(a), min(14000, len(a)), replace=False)
    C, counts = kmeans(a[idx], k)
    hsv = np.array([colorsys.rgb_to_hsv(*(c / 255)) for c in C], np.float32)
    return C, counts, hsv[:, 0] * 360, hsv[:, 1], hsv[:, 2]


def circular_mean(deg, weights):
    a = np.radians(deg)
    return float(np.degrees(np.arctan2((np.sin(a) * weights).sum(),
                                       (np.cos(a) * weights).sum())) % 360)


def hexs(c):
    return '#%02X%02X%02X' % tuple(int(round(v)) for v in c)


def main():
    files = fetch()
    warm_h, warm_w, cool_h, cool_w, per_ref = [], [], [], [], {}
    for f in files:
        C, counts, hue, sat, val = clusters(f)
        warm = ((hue < 70) | (hue > 330)) & (sat > 0.15)
        cool = (hue > 170) & (hue < 280) & (sat > 0.15)
        # weight a cluster by how much of the frame it covers, how decisive its colour is
        # and how sunlit it is: the bright warm clusters are the crowns we are after,
        # the dark ones are already dusk and would drag the hue toward pink
        w = counts * sat * val ** 3
        warm_h += list(hue[warm]); warm_w += list(w[warm])
        cool_h += list(hue[cool]); cool_w += list(w[cool])
        per_ref[f.stem] = {
            'warm': [f'{hexs(C[i])} H{hue[i]:.0f} S{sat[i]:.2f}' for i in np.where(warm)[0]],
            'cool': [f'{hexs(C[i])} H{hue[i]:.0f} S{sat[i]:.2f}' for i in np.where(cool)[0]],
        }
    measured = {
        'warm': circular_mean(np.array(warm_h), np.array(warm_w)),
        'cool': circular_mean(np.array(cool_h), np.array(cool_w)),
    }
    hues = {}
    for fam, h in measured.items():
        d = (BRAND[fam] - h + 180) % 360 - 180          # shortest way round the wheel
        hues[fam] = (h + d * PULL[fam]) % 360

    work = {}
    for role, (fam, s, v) in ROLES.items():
        r, g, b = colorsys.hsv_to_rgb(hues[fam] / 360, s, v)
        work[role] = [int(round(r * 255)), int(round(g * 255)), int(round(b * 255))]

    OUT.write_text(json.dumps({
        'source': 'Wikimedia Commons, cumulus at sunset, free licences',
        'refs': REFS,
        'measured_hues': {k: round(v, 1) for k, v in measured.items()},
        'brand_hues': BRAND,
        'pull_toward_brand': PULL,
        'working_hues': {k: round(v, 1) for k, v in hues.items()},
        'per_reference': per_ref,
        'roles': {k: {'family': f, 'sat': s, 'val': v} for k, (f, s, v) in ROLES.items()},
        'working': {k: hexs(v) for k, v in work.items()},
        'working_rgb': work,
    }, indent=2) + '\n')

    sw = Image.new('RGB', (len(work) * 150, 200), '#FAF5E9')
    d = ImageDraw.Draw(sw)
    for i, (k, v) in enumerate(work.items()):
        d.rectangle([i * 150, 0, i * 150 + 149, 144], fill=tuple(v))
        d.text((i * 150 + 10, 156), k, fill='#111111')
        d.text((i * 150 + 10, 174), hexs(v), fill='#111111')
    sw.save(HERE / 'palette.png')

    print('measured:', {k: round(v, 1) for k, v in measured.items()},
          '-> working:', {k: round(v, 1) for k, v in hues.items()})
    for k, v in work.items():
        print(f'  {k:13s} {hexs(v)}')


def load():
    """Palette for the generators; regenerate with `python gen_palette.py` if missing."""
    return {k: np.array(v, np.float32)
            for k, v in json.loads(OUT.read_text())['working_rgb'].items()}


if __name__ == '__main__':
    main()
