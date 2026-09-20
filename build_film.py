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
V = '20260921b'

CSS = '''
/* ── demo 5: Legora's hero, ours ─────────────────────────────────────────────
   Full-screen film, a dark veil heavier at the top and the bottom, the nav floating
   transparent over it, and the copy white, bottom left, three lines: the sentence,
   one line of what we are, one button. Nothing else on the first screen.        */
.xx-page::before, .xx-page::after { display: none !important; }
.xx-page { min-height: 100vh; background: #14141A; }
.xx-film { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 0; overflow: hidden; background: #14141A; }
.xx-film video { width: 100%; height: 100%; object-fit: cover; object-position: 50% 50%; display: block; }
.xx-film__veil { position: absolute; inset: 0; pointer-events: none;
  /* the reference runs .5 / .1 / .1 / .5; our copy starts higher up the frame and half of
     the film is cream, so the lower ramp starts at the middle and goes a little deeper */
  background: linear-gradient(180deg, rgba(0,0,0,.50) 0%, rgba(0,0,0,.10) 13%, rgba(0,0,0,.12) 46%, rgba(0,0,0,.66) 100%); }

/* the nav: same links, no pill, no paper, white over the film */
.xx-nav { background: transparent !important; border-color: transparent !important; box-shadow: none !important; backdrop-filter: none !important; }
.xx-nav__wordmark, .xx-nav__link, .xx-lang, .xx-lang strong { color: #F5F3EE !important; }
.xx-nav__brand svg line { stroke: #F5F3EE !important; }

/* the hero: everything off except the sentence, the line and the button, bottom left */
.xx-hero { display: block !important; min-height: 100vh !important; padding: 0 !important; }
.xx-hero__inner { position: absolute !important; left: 48px; right: 48px; bottom: 64px; max-width: none !important; margin: 0 !important; display: block !important; }
.xx-hero__inner--split { grid-template-columns: 1fr !important; }
.xx-hero__logo, .xx-hero__eyebrow, .xx-hero__right, .xx-hero-dock, .xx-hero__watermark, .xx-hero__meta, .xx-hero__leftlede, .xx-cta-dock .xx-btn--ghost { display: none !important; }
.xx-hero__left { max-width: 1100px; }
.xx-hero h1 { color: #F5F3EE !important; font-weight: 400 !important; font-size: clamp(44px, 5.2vw, 96px) !important; line-height: 1.04 !important; letter-spacing: -.01em; margin: 0 0 22px !important; text-shadow: 0 2px 28px rgba(0,0,0,.45), 0 1px 2px rgba(0,0,0,.25); }
.xx-hero h1 em { display: none !important; }
.xx-hero h1 br { display: none; }
.xx-hero__sub { color: rgba(245,243,238,.86); text-shadow: 0 1px 12px rgba(0,0,0,.35); font: 400 clamp(16px, 1.25vw, 22px)/1.45 var(--font-sans, Inter, sans-serif); max-width: 640px; margin: 0 0 30px; }
.xx-cta-dock { background: transparent !important; border: 0 !important; box-shadow: none !important; padding: 0 !important; margin: 0 !important; display: inline-flex !important; }
@media (max-width: 768px) {
  .xx-hero__inner { left: 20px; right: 20px; bottom: 40px; }
  .xx-hero { min-height: 100vh !important; }
}
'''

PANEL = '''
<div class="xx-proto" role="group" aria-label="film controls">
  <button type="button" data-xx="veil">veil: on</button>
  <button type="button" data-xx="play">film: playing</button>
  <a href="field.html">demo 4: clouds &rarr;</a>
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
    # one sentence, as Oleg asked: the lede moves up into the headline, the old headline goes
    html = re.sub(r'<h1>.*?</h1>', '<h1>We take charge of your cross-border complexity.</h1>'
                  '<p class="xx-hero__sub">A legal boutique for founders doing international business. '
                  'Corporate, tax, contracts and disputes across borders, run as one project.</p>', html, count=1, flags=re.S)
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
