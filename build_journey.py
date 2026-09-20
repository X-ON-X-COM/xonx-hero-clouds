"""Demo 6 (journey.html / journey-m.html): Oleg's idea, whole.

The 18.09 call, 00:23:30: a screen that never stops moving, the viewer flying forward, and as
the flight goes on the situations a founder runs into come at you — the tickets, the plane,
the signing, the hard conversation, the settlement, the cap table, the model. Demo 4 is the
flight through the clouds; demo 5 is the film of the situations. This is both at once: the
cloud field of demo 4 with the shots of the film as cards in the same space, each coming out
of the distance between the clouds, passing beside the camera and going.

Page layout as Iryna asked after demo 5: Legora's, minimal — three lines bottom left, one
button, nothing else on the first screen. The sky is light, so the copy is graphite.

    python build_journey.py     # copies ../xonx-hero-video/out/shots/*.mp4 into journey/
"""
import json, pathlib, re, shutil

SRC = pathlib.Path('/Users/user/Claude/xonx-site-preview')
VID = pathlib.Path('/Users/user/Claude/xonx-hero-video/out/shots')
DST = pathlib.Path(__file__).parent
V = '20260921f'

CSS = '''
/* ── demo 6: the flight, with the situations coming at you ─────────────────── */
.xx-page::before { display: none !important; }
.xx-page::after  { opacity: 0.22; }
.xx-page { min-height: 100vh; }

/* the nav: same links, no pill, no paper */
.xx-nav { background: transparent !important; border-color: transparent !important; box-shadow: none !important; backdrop-filter: none !important; }

/* the hero: three lines bottom left, as on the film demo, graphite on the light sky */
.xx-hero { display: block !important; min-height: 100vh !important; padding: 0 !important; }
.xx-hero__inner { position: absolute !important; left: 48px; right: 48px; bottom: 64px; max-width: none !important; margin: 0 !important; display: block !important; }
.xx-hero__inner--split { grid-template-columns: 1fr !important; }
.xx-hero__logo, .xx-hero__eyebrow, .xx-hero__right, .xx-hero-dock, .xx-hero__watermark, .xx-hero__meta, .xx-hero__leftlede, .xx-cta-dock .xx-btn--ghost { display: none !important; }
.xx-hero__left { max-width: 1100px; }
.xx-hero h1 { font-weight: 400 !important; font-size: clamp(44px, 5.2vw, 96px) !important; line-height: 1.04 !important; letter-spacing: -.01em; margin: 0 0 22px !important; text-shadow: 0 1px 0 rgba(250,250,245,.7); }
.xx-hero h1 em, .xx-hero h1 br { display: none !important; }
.xx-hero__sub { color: #3a3a40; font: 400 clamp(16px, 1.25vw, 22px)/1.45 var(--font-sans, Inter, sans-serif); max-width: 640px; margin: 0 0 30px; text-shadow: 0 1px 0 rgba(250,250,245,.7); }
.xx-cta-dock { background: transparent !important; border: 0 !important; box-shadow: none !important; padding: 0 !important; margin: 0 !important; display: inline-flex !important; }
/* the copy has to stay readable under a passing card: a soft cream pool behind it */
.xx-hero__left::before { content: ''; position: absolute; left: -80px; right: -80px; top: -80px; bottom: -80px; z-index: -1; pointer-events: none;
  background: radial-gradient(ellipse 60% 60% at 30% 70%, rgba(250,250,245,.78) 0%, rgba(250,250,245,.42) 45%, transparent 75%); }
.xx-hero__left { position: relative; }
@media (max-width: 768px) {
  .xx-hero__inner { left: 20px; right: 20px; bottom: 40px; }
  .xx-hero { min-height: 100vh !important; }
}
'''

PANEL = '''
<div class="xx-proto" role="group" aria-label="sky controls">
  <button type="button" data-xx="motion">motion: on</button>
  <button type="button" data-xx="tempo">tempo: normal</button>
  <button type="button" data-xx="through">crosses text: yes</button>
  <button type="button" data-xx="veil">front: normal</button>
  <a href="film.html">demo 5: film &rarr;</a>
  <a href="field.html">demo 4: clouds &rarr;</a>
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
      } else if (k === 'through') {
        root.classList.toggle('xx-behind');
        b.textContent = 'crosses text: ' + (root.classList.contains('xx-behind') ? 'no' : 'yes');
      } else {
        v = (v + 1) % veils.length;
        root.classList.remove('xx-thin', 'xx-thick');
        if (veils[v] !== 'normal') root.classList.add('xx-' + veils[v]);
        b.textContent = 'front: ' + veils[v];
      }
    });
  });
})();
</script>
'''


def build(name, out, partner, count, clouds, clips):
    html = (SRC / name).read_text()
    html = re.sub(r'\?v=\d{8}[a-z]', f'?v={V}', html)
    html = html.replace("location.replace('m.html?", f"location.replace('{partner}?")
    html = html.replace("location.replace('index.html?", f"location.replace('{partner}?")
    html = html.replace('</head>', f'<link rel="stylesheet" href="field.css?v={V}">\n<style>{CSS}</style>\n</head>', 1)
    html = html.replace('<title>X-ON-X – Home</title>', '<title>X-ON-X – Hero demo 6: the journey</title>')
    html = re.sub(r'<h1>.*?</h1>', '<h1>We take charge of your cross-border complexity.</h1>'
                  '<p class="xx-hero__sub">A legal boutique for founders doing international business. '
                  'Corporate, tax, contracts and disputes across borders, run as one project.</p>', html, count=1, flags=re.S)
    start = html.index('<!-- ──── LATEST INSIGHTS')
    end = html.index('</div><!-- /.xx-page -->')
    html = html[:start] + html[end:]
    a = html.index('</div><!-- /.xx-page -->') + len('</div><!-- /.xx-page -->')
    b = html.index('</body>')
    journey = json.dumps([f'journey/{c}?v={V}' for c in clips]).replace('"', '&quot;')
    field = (f'<script src="js/three.min.js"></script>\n'
             f'<script src="field.js?v={V}" data-count="{count}" data-clouds="{clouds}" data-texture="clouds/puff_photo.png?v={V}" '
             f'data-sky="#ECE8E6" data-journey="{journey}"></script>\n')
    html = html[:a] + '\n' + PANEL + '\n' + field + html[b:]
    sky = ('\n  <!-- ──── SKY + JOURNEY (demo 6: the cloud field, the situations as cards in it) ──── -->\n'
           '  <div class="xx-sky" aria-hidden="true"></div>\n'
           '  <canvas class="xx-gl" id="xx-gl-back" aria-hidden="true"></canvas>\n'
           '  <canvas class="xx-gl" id="xx-gl-front" aria-hidden="true"></canvas>\n')
    html = re.sub(r'(<div class="xx-page"[^>]*>)', lambda m: m.group(1) + sky, html, count=1)
    (DST / out).write_text(html)
    print(out, len(html) // 1024, 'KB', len(clips), 'cards')


if __name__ == '__main__':
    (DST / 'journey').mkdir(exist_ok=True)
    clips = sorted(p.name for p in VID.glob('*.mp4'))
    for c in clips:
        shutil.copy(VID / c, DST / 'journey' / c)
    build('index.html', 'journey.html', 'journey-m.html', 9000, 34, clips)
    build('m.html', 'journey-m.html', 'journey.html', 3600, 22, clips)
