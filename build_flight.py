"""Demo 3 (flight.html / flight-m.html): golden hour, everything flying, through the text.

Same slicing as build_halo.py — nav + hero cut out of the live builds, the old sky off —
but the sky is generated here rather than written by hand. Every cloud is one <span> with
its own trajectory, so the field has no repeating band in it and nothing sits still.

The trajectories are laid out in python because the distribution is the whole trick: the
angles have to cover the circle without clumping, the delays have to spread across the
cycle so the sky is never empty, and the near clouds have to come in groups that start on
top of each other and are pulled apart by their own divergence. That is what makes a cloud
tear as it passes, with no separate mechanism for tearing.

    python build_flight.py
"""
import math, pathlib, random, re

SRC = pathlib.Path('/Users/user/Claude/xonx-site-preview')
DST = pathlib.Path(__file__).parent
V = '20260920a'

NEAR_TEX = [f'clouds/g_near{i}.webp' for i in range(1, 7)]
FAR_TEX = [f'clouds/g_far{i}.webp' for i in range(1, 6)]


def sprite(rng, tex, *, r0, r1, s0, s1, dur, delay, opacity, angle, drop=False, half=False):
    """One cloud. --uy is squashed: a viewport is wider than it is tall, and clouds
    should leave the frame through the sides more often than over the top."""
    ux = math.cos(math.radians(angle))
    uy = math.sin(math.radians(angle)) * 0.62
    rot = rng.uniform(-9, 9)
    css = (f'--ux:{ux:.4f};--uy:{uy:.4f};--r0:{r0:.2f}vmax;--r1:{r1:.1f}vmax;'
           f'--s0:{s0:.3f};--s1:{s1:.2f};--dur:{dur:.1f}s;--d:{delay:.2f}s;'
           f'--o:{opacity:.2f};--rot:{rot:.1f}deg;'
           f'background-image:url({tex[:-5] + "-m.webp" if half else tex}?v={V})')
    cls = 'xx-cl xx-cl--drop' if drop else 'xx-cl'
    return f'    <span class="{cls}" style="{css}"></span>\n'


def plane(name, sprites):
    return (f'  <div class="xx-flight xx-flight--{name}" aria-hidden="true">\n'
            + ''.join(sprites) + '  </div>\n')


def field(seed=20260920, half=False):
    rng = random.Random(seed)
    out = []

    # ── far: many small clouds, slow, low contrast. This is the depth that demo 2
    # faked with a tiled band, and the reason that band looked stuck on.
    far = []
    n = 9
    for i in range(n):
        dur = rng.uniform(46, 60)
        far.append(sprite(
            rng, FAR_TEX[i % len(FAR_TEX)],
            angle=(i * 360 / n) + rng.uniform(-14, 14),
            r0=rng.uniform(1.0, 5.0), r1=rng.uniform(72, 104),
            s0=rng.uniform(0.06, 0.12), s1=rng.uniform(0.95, 1.55),
            dur=dur, delay=-dur * i / n + rng.uniform(-1.5, 1.5),
            opacity=rng.uniform(0.80, 1.00),
            drop=(i % 2 == 1), half=half))
    out.append(plane('far', far))

    # ── mid: crosses the headline. Fewer, bigger, faster.
    mid = []
    n = 8
    for i in range(n):
        dur = rng.uniform(30, 40)
        mid.append(sprite(
            rng, (FAR_TEX + NEAR_TEX)[i % (len(FAR_TEX) + len(NEAR_TEX))],
            angle=(i * 360 / n) + rng.uniform(-18, 18) + 22,
            r0=rng.uniform(0.5, 4.0), r1=rng.uniform(88, 124),
            s0=rng.uniform(0.09, 0.17), s1=rng.uniform(2.30, 3.40),
            dur=dur, delay=-dur * i / n + rng.uniform(-1.2, 1.2),
            opacity=rng.uniform(0.85, 1.00),
            drop=(i % 2 == 1), half=half))
    out.append(plane('mid', mid))

    # ── near: the clouds that reach the cockpit. Each one is a group of two or three
    # sprites launched on almost the same vector; the divergence pulls them apart on
    # the way in, so the cloud holds together far away and comes apart as it passes.
    near = []
    groups = 3
    for gi in range(groups):
        dur = rng.uniform(21, 27)
        base_angle = gi * 360 / groups + rng.uniform(-20, 20) + 40
        base_delay = -dur * gi / groups
        members = rng.choice([2, 3]) if hasattr(rng, 'choice') else 3
        members = rng.randint(2, 3)
        for mi in range(members):
            near.append(sprite(
                rng, NEAR_TEX[(gi * 3 + mi) % len(NEAR_TEX)],
                angle=base_angle + rng.uniform(-9, 9),
                r0=rng.uniform(0.3, 2.0), r1=rng.uniform(104, 152),
                s0=rng.uniform(0.12, 0.20), s1=rng.uniform(3.00, 4.20),
                dur=dur, delay=base_delay + rng.uniform(-1.0, 1.0),
                opacity=rng.uniform(0.85, 1.00),
                drop=(mi == 2), half=half))
    out.append(plane('near', near))
    return ''.join(out)


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
    # the viewport switch must move between the demo 3 pair, not back to demo 1
    html = html.replace("location.replace('m.html?", f"location.replace('{partner}?")
    html = html.replace("location.replace('index.html?", f"location.replace('{partner}?")
    html = html.replace('</head>', f'<link rel="stylesheet" href="flight.css?v={V}">\n</head>', 1)
    html = html.replace('<title>X-ON-X – Home</title>', '<title>X-ON-X – Sky demo 3: flight</title>')
    # keep nav + hero only
    start = html.index('<!-- ──── LATEST INSIGHTS')
    end = html.index('</div><!-- /.xx-page -->')
    html = html[:start] + html[end:]
    # drop the WIP modal and the scripts after the page, add the control panel
    a = html.index('</div><!-- /.xx-page -->') + len('</div><!-- /.xx-page -->')
    b = html.index('</body>')
    html = html[:a] + '\n' + PANEL + '\n' + html[b:]
    sky = ('\n  <!-- ──── SKY (demo 3: golden hour, three planes, everything flying) ──── -->\n'
           '  <div class="xx-sky" aria-hidden="true"></div>\n' + HALO + field(half=half))
    html = re.sub(r'(<div class="xx-page"[^>]*>)', lambda m: m.group(1) + sky, html, count=1)
    (DST / out).write_text(html)
    print(out, len(html) // 1024, 'KB')


if __name__ == '__main__':
    build('index.html', 'flight.html', 'flight-m.html')
    # phones get the half-size textures: same field, a quarter of the pixels
    build('m.html', 'flight-m.html', 'flight.html', half=True)
