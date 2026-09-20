"""Demo 3 (flight.html / flight-m.html): golden hour, real perspective, through the text.

Same slicing as build_halo.py — nav + hero cut out of the live builds, the old sky off —
but the sky is generated here.

Geometry, rewritten 20.09 after Iryna's screenshot. The first version scattered sprites
radially around the vanishing point: each had an angle and a radius that grew. That is not
how a sky looks, and it showed. Every cloud in flight sat at a similar radius at a similar
phase, so at any instant they lined up along an arc, evenly spaced and much the same size.
No amount of work on the texture fixes a layout that reads as a conveyor belt.

So each cloud now has a position and a size in three dimensions, and the screen position is
that projected through its distance:

    screen offset = K * X / Z          on-screen diameter = 2 * K * R / Z

and Z falls linearly, which is what flying at a constant speed does. Everything Oleg asked
for on the 18.09 call then happens by itself rather than being imitated: clouds diverge from
the vanishing point because that is what projection does; sizes vary because real sizes and
distances vary; they cluster near the horizon while far away and sweep apart as they arrive;
and a cloud whose X and Y are near zero comes straight at the camera and swallows it.

CSS cannot interpolate 1/Z, so each cloud's path is sampled here at distances spaced
geometrically (dense at the end, where everything happens) and written out as its own
@keyframes block.

    python build_flight.py
"""
import math, pathlib, random, re

SRC = pathlib.Path('/Users/user/Claude/xonx-site-preview')
DST = pathlib.Path(__file__).parent
V = '20260920d'

NEAR_TEX = [f'clouds/g_near{i}.webp' for i in range(1, 7)]
FAR_TEX = [f'clouds/g_far{i}.webp' for i in range(1, 6)]

EL = 44.0        # the sprite element is 44vmax wide; scale is relative to that
K = 170.0        # projection constant: bigger = longer lens, clouds loom sooner
Z_END = 0.55     # how close a cloud gets before it is behind the camera
STEPS = 15       # keyframes per cloud


def path(c):
    """Sample one cloud's flight and return (percent, x, y, scale, opacity) rows.

    Distances are spaced geometrically so the samples bunch up at the end, where a
    constant fall in Z turns into a very fast change on screen.
    """
    z0, ze = c['z0'], Z_END
    rows = []
    for i in range(STEPS + 1):
        z = z0 * (ze / z0) ** (i / STEPS)
        pct = (z0 - z) / (z0 - ze) * 100.0
        x = K * c['x'] / z
        y = K * c['y'] / z
        scale = 2 * K * c['r'] / z / EL
        # far away it is lost in haze; in the last stretch the camera is inside it, and a
        # cloud that has grown past the viewport is by then vapour around you, not a shape,
        # so it thins with size as well as with distance
        near = min(1.0, (z0 - z) / (z0 * 0.32))
        gone = min(1.0, (z - ze) / (z0 * 0.12))
        inside = max(0.12, min(1.0, 1.0 - (scale - 2.6) / 3.2))
        rows.append((pct, x, y, scale, c['o'] * near * gone * inside))
    return rows


def keyframes(name, c):
    out = [f'@keyframes {name}{{']
    for pct, x, y, s, o in path(c):
        out.append('%.2f%%{transform:translate(-50%%,-50%%) translate(%.2fvmax,%.2fvmax) '
                   'scale(%.4f) rotate(%.1fdeg) scaleX(%d);opacity:%.3f}'
                   % (pct, x, y, s, c['rot'], c['flip'], o))
    out.append('}')
    return ''.join(out)


def sprite(name, c, drop):
    cls = 'xx-cl xx-cl--drop' if drop else 'xx-cl'
    # only the name is inline: duration and delay go through --xx-tempo in flight.css
    return ('    <span class="%s" style="animation-name:%s;--dur:%.1fs;--d:%.2fs;'
            'background-image:url(%s?v=%s)"></span>\n'
            % (cls, name, c['dur'], c['delay'], c['tex'], V))


def make_clouds(seed=20260920):
    """A sky, not a pattern.

    Sizes and distances are drawn independently, so the same cloud can read as a small one
    nearby or a large one far off. Y is centred a little below the camera: from a window you
    are usually just above the deck, looking slightly down on it, with a few at eye level
    that you go straight through.
    """
    rng = random.Random(seed)
    clouds = []
    for _ in range(19):
        r = rng.uniform(0.40, 2.10)
        z0 = rng.uniform(14.0, 52.0)
        # spread sideways in proportion to distance, or everything far away crowds the middle
        x = rng.uniform(-0.13, 0.13) * z0 + rng.gauss(0, 0.6)
        y = rng.gauss(-0.55, 0.95) + rng.uniform(-0.04, 0.04) * z0
        speed = rng.uniform(1.35, 1.95)                 # world units per second
        dur = (z0 - Z_END) / speed
        clouds.append(dict(
            r=r, z0=z0, x=x, y=y, dur=dur,
            delay=-rng.uniform(0, dur),                 # every cloud starts mid-flight
            o=rng.uniform(0.86, 1.0),
            rot=rng.uniform(-7, 7),
            flip=rng.choice((1, -1)),                   # doubles the apparent variety
        ))
    # How close it passes decides which plane it belongs to: a cloud that leaves the frame
    # while still far off can never be in front of the text, and one that swallows the
    # camera has to be. "Close" is the distance at which its centre leaves the viewport,
    # not Z_END: a cloud far out to the side is gone long before it gets there.
    for c in clouds:
        z_exit = max(Z_END, K * abs(c['x']) / 56.0, K * abs(c['y']) / 36.0)
        reach = 2 * K * c['r'] / z_exit / EL            # how big it is when it leaves
        c['plane'] = 'far' if reach < 1.6 else ('mid' if reach < 3.2 else 'near')
        pool = FAR_TEX if c['plane'] == 'far' else NEAR_TEX
        c['tex'] = pool[int(rng.random() * len(pool))]
    return clouds


def field(clouds):
    css, html = [], {'far': [], 'mid': [], 'near': []}
    for i, c in enumerate(clouds):
        name = f'xxc{i}'
        css.append(keyframes(name, c))
        html[c['plane']].append(sprite(name, c, drop=(i % 3 == 2)))
    planes = ''.join(
        f'  <div class="xx-flight xx-flight--{p}" aria-hidden="true">\n{"".join(html[p])}  </div>\n'
        for p in ('far', 'mid', 'near'))
    return '<style>' + ''.join(css) + '</style>\n' + planes


HALO = '''  <div class="xx-halo" aria-hidden="true">
    <div class="xx-halo__glow"></div>
    <div class="xx-halo__ring xx-halo__ring--in"></div>
    <div class="xx-halo__ring xx-halo__ring--out"></div>
  </div>
'''

PANEL = '''
<div class="xx-proto" role="group" aria-label="sky controls">
  <button type="button" data-xx="motion">motion: on</button>
  <button type="button" data-xx="tempo">tempo: normal</button>
  <button type="button" data-xx="halo">nimbus: on</button>
  <button type="button" data-xx="through">crosses text: yes</button>
  <button type="button" data-xx="veil">density: normal</button>
  <a href="halo.html">demo 2 &rarr;</a>
  <a href="index.html">demo 1 &rarr;</a>
</div>
<style>
.xx-proto{position:fixed;right:14px;bottom:14px;z-index:60;display:flex;flex-direction:column;align-items:flex-end;gap:6px}
.xx-proto button,.xx-proto a{font:11px/1 "JetBrains Mono",monospace;letter-spacing:1px;text-transform:uppercase;
 padding:8px 12px;border-radius:999px;border:1px solid rgba(17,17,17,.18);background:rgba(255,254,248,.8);
 color:#111;cursor:pointer;backdrop-filter:blur(8px);text-decoration:none}
.xx-proto button:hover,.xx-proto a:hover{background:rgba(255,254,248,.98)}
@media (max-width:768px){.xx-proto{right:10px;bottom:10px;gap:4px}.xx-proto button,.xx-proto a{padding:7px 10px;font-size:10px}}
</style>
<script>
(function () {
  var root = document.documentElement;
  var tempos = ['normal', 'rush', 'calm'], t = 0;
  var veils = ['normal', 'thin', 'thick'], v = 0;
  document.querySelectorAll('.xx-proto button').forEach(function (b) {
    b.addEventListener('click', function () {
      var k = b.dataset.xx;
      if (k === 'motion') {
        root.classList.toggle('xx-still');
        b.textContent = 'motion: ' + (root.classList.contains('xx-still') ? 'off' : 'on');
      } else if (k === 'tempo') {
        t = (t + 1) % tempos.length;
        root.classList.remove('xx-tempo-rush', 'xx-tempo-calm');
        if (tempos[t] !== 'normal') root.classList.add('xx-tempo-' + tempos[t]);
        b.textContent = 'tempo: ' + tempos[t];
      } else if (k === 'halo') {
        root.classList.toggle('xx-nohalo');
        b.textContent = 'nimbus: ' + (root.classList.contains('xx-nohalo') ? 'off' : 'on');
      } else if (k === 'through') {
        root.classList.toggle('xx-behind');
        b.textContent = 'crosses text: ' + (root.classList.contains('xx-behind') ? 'no' : 'yes');
      } else {
        v = (v + 1) % veils.length;
        root.classList.remove('xx-thin', 'xx-thick');
        if (veils[v] !== 'normal') root.classList.add('xx-' + veils[v]);
        b.textContent = 'density: ' + veils[v];
      }
    });
  });
})();
</script>
'''


def build(name, out, partner, half=False):
    html = (SRC / name).read_text()
    html = re.sub(r'\?v=\d{8}[a-z]', f'?v={V}', html)
    html = html.replace("location.replace('m.html?", f"location.replace('{partner}?")
    html = html.replace("location.replace('index.html?", f"location.replace('{partner}?")
    html = html.replace('</head>', f'<link rel="stylesheet" href="flight.css?v={V}">\n</head>', 1)
    html = html.replace('<title>X-ON-X – Home</title>', '<title>X-ON-X – Sky demo 3: flight</title>')
    start = html.index('<!-- ──── LATEST INSIGHTS')
    end = html.index('</div><!-- /.xx-page -->')
    html = html[:start] + html[end:]
    a = html.index('</div><!-- /.xx-page -->') + len('</div><!-- /.xx-page -->')
    b = html.index('</body>')
    html = html[:a] + '\n' + PANEL + '\n' + html[b:]

    clouds = make_clouds()
    body = field(clouds)
    if half:                       # phones: same field, a quarter of the pixels
        body = re.sub(r'(clouds/g_[a-z0-9]+)\.webp', r'\1-m.webp', body)
    sky = ('\n  <!-- ──── SKY (demo 3: golden hour, projected perspective) ──── -->\n'
           '  <div class="xx-sky" aria-hidden="true"></div>\n' + HALO + body)
    html = re.sub(r'(<div class="xx-page"[^>]*>)', lambda m: m.group(1) + sky, html, count=1)
    (DST / out).write_text(html)
    counts = {}
    for c in clouds:
        counts[c['plane']] = counts.get(c['plane'], 0) + 1
    print(out, len(html) // 1024, 'KB', counts)


if __name__ == '__main__':
    build('index.html', 'flight.html', 'flight-m.html')
    build('m.html', 'flight-m.html', 'flight.html', half=True)
