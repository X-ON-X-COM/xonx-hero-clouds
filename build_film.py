"""Demo 5 (film.html / film-m.html): the hero film behind the text, Legora's construction.

The same slicing as the other builders — nav + hero cut out of the live builds — with the
rough cut from ../xonx-hero-video behind the words instead of a sky. Legora's markup, taken
from their page: a muted, looping, playsinline video with preload="none" and a poster, under
a dark vertical gradient (0.5 → 0.1 → 0.1 → 0.5) so the copy reads over any frame. The text
turns light for it, which is the one place this demo touches the hero's own styling.

    python build_film.py        # copies out/rough_cut.mp4 + poster.jpg into film/ first
"""
import pathlib, re, shutil

SRC = pathlib.Path('/Users/user/Claude/xonx-site-preview')
VID = pathlib.Path('/Users/user/Claude/xonx-hero-video/out')
DST = pathlib.Path(__file__).parent
V = '20260920y'

CSS = '''
/* ── demo 5: the film behind the hero ─────────────────────────────────────── */
.xx-page::before { display: none !important; }
.xx-page::after  { opacity: 0.22; }
.xx-page { min-height: 100vh; }
.xx-film { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 0; overflow: hidden; background: #FAFAF5; }
.xx-film video { width: 100%; height: 100%; object-fit: cover; object-position: 50% 50%; display: block; }
/* Legora veils a dark film so light copy reads; ours is golden hour and cream throughout, so
   the veil is light and the copy stays graphite, exactly as it is on the site. Same shape:
   heavier at the top and the bottom, almost nothing across the middle. */
.xx-film__veil { position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(180deg, rgba(250,250,245,.62) 0%, rgba(250,250,245,.14) 16%, rgba(250,250,245,.10) 70%, rgba(250,250,245,.60) 100%); }
.xx-hero h1, .xx-hero__lede { text-shadow: 0 1px 0 rgba(250,250,245,.6); }
.xx-hero h1 em { color: rgba(17,17,22,.42) !important; }
.xx-btn--ghost { background: rgba(250,250,245,.55) !important; }
/* Demo only: the hero goes down to what Oleg asked for on the 18.09 call, one sentence and the
   buttons. The right column and the dock come off, so the film's inserts have the right half. */
.xx-hero__right, .xx-hero-dock { display: none !important; }
.xx-hero__inner--split { grid-template-columns: 1fr !important; }
@media (max-width: 768px) { .xx-hero { min-height: calc(100vh - 72px) !important; } }
'''

PANEL = '''
<div class="xx-proto" role="group" aria-label="film controls">
  <button type="button" data-xx="veil">veil: on</button>
  <button type="button" data-xx="play">film: playing</button>
  <a href="field.html">demo 4 &rarr;</a>
  <a href="flight.html">demo 3 &rarr;</a>
</div>
<style>
.xx-proto{position:fixed;right:14px;bottom:14px;z-index:60;display:flex;flex-direction:column;align-items:flex-end;gap:6px}
.xx-proto button,.xx-proto a{font:11px/1 "JetBrains Mono",monospace;letter-spacing:1px;text-transform:uppercase;
 padding:8px 12px;border-radius:999px;border:1px solid rgba(255,255,255,.22);background:rgba(28,28,34,.7);
 color:#F5F3EE;cursor:pointer;backdrop-filter:blur(8px);text-decoration:none}
.xx-proto button:hover,.xx-proto a:hover{background:rgba(28,28,34,.95)}
@media (max-width:768px){.xx-proto{right:10px;bottom:10px;gap:4px}.xx-proto button,.xx-proto a{padding:7px 10px;font-size:10px}}
</style>
<script>
(function () {
  var v = document.querySelector('.xx-film video'), veil = document.querySelector('.xx-film__veil');
  // preload="none" as on the reference: start it by hand once the page is up
  var play = function () { v.play().catch(function () {}); };
  if (document.readyState === 'complete') play(); else window.addEventListener('load', play);
  document.querySelectorAll('.xx-proto button').forEach(function (b) {
    b.addEventListener('click', function () {
      if (b.dataset.xx === 'veil') { veil.hidden = !veil.hidden; b.textContent = 'veil: ' + (veil.hidden ? 'off' : 'on'); }
      else { if (v.paused) { v.play(); b.textContent = 'film: playing'; } else { v.pause(); b.textContent = 'film: paused'; } }
    });
  });
})();
</script>
'''


def build(name, out, partner):
    html = (SRC / name).read_text()
    html = re.sub(r'\?v=\d{8}[a-z]', f'?v={V}', html)
    html = html.replace("location.replace('m.html?", f"location.replace('{partner}?")
    html = html.replace("location.replace('index.html?", f"location.replace('{partner}?")
    html = html.replace('</head>', f'<style>{CSS}</style>\n</head>', 1)
    html = html.replace('<title>X-ON-X – Home</title>', '<title>X-ON-X – Hero demo 5: film</title>')
    start = html.index('<!-- ──── LATEST INSIGHTS')
    end = html.index('</div><!-- /.xx-page -->')
    html = html[:start] + html[end:]
    a = html.index('</div><!-- /.xx-page -->') + len('</div><!-- /.xx-page -->')
    b = html.index('</body>')
    html = html[:a] + '\n' + PANEL + '\n' + html[b:]
    film = (f'\n  <!-- ──── FILM (demo 5: the rough cut behind the hero, Legora\'s construction) ──── -->\n'
            f'  <div class="xx-film" aria-hidden="true">\n'
            f'    <video src="film/rough_cut.mp4?v={V}" poster="film/poster.jpg?v={V}" loop muted playsinline preload="none"></video>\n'
            f'    <div class="xx-film__veil"></div>\n'
            f'  </div>\n')
    html = re.sub(r'(<div class="xx-page"[^>]*>)', lambda m: m.group(1) + film, html, count=1)
    (DST / out).write_text(html)
    print(out, len(html) // 1024, 'KB')


if __name__ == '__main__':
    (DST / 'film').mkdir(exist_ok=True)
    shutil.copy(VID / 'rough_cut.mp4', DST / 'film' / 'rough_cut.mp4')
    shutil.copy(VID / 'poster.jpg', DST / 'film' / 'poster.jpg')
    build('index.html', 'film.html', 'film-m.html')
    build('m.html', 'film-m.html', 'film.html')
