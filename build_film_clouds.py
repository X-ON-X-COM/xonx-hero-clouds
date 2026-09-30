"""Demo 9 (film-clouds.html / film-clouds-m.html): demo 5's film with demo 4's clouds over it
and cloud wipes across the cuts, on a Theatre.js timeline synced to the film.

Built from demo 5's page as it stands (film.html); the copy and its styling are untouched.
Layers inside .xx-film: video, the dark veil, the cloud field (two canvases, faded to nothing
in the distance instead of to the sky colour: data-fogalpha), the torn cloud wipe. The copy
sits above all of it and does not move.

    python gen_film_state.py && python build_film_clouds.py
"""
import pathlib

DST = pathlib.Path(__file__).parent
V = '20261001a'

CSS = '''<style>
.xx-film .xx-gl { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; display: block;
  opacity: var(--xx-cloud-o, .15); }
.xx-film #xx-gl-back { z-index: 1; } .xx-film #xx-gl-front { z-index: 2; }
html.xx-studio .xx-proto, html.xx-play .xx-proto { display: none !important; }
/* the dark scrim stays on top of the clouds and the wipe: the white copy must read even at the
   whitest moment of a wipe */
.xx-film .xx-film__veil { z-index: 4; }
</style>
'''


def build(src, out, partner_src, partner, count, nclouds):
    html = (DST / src).read_text()
    html = html.replace('</head>', CSS + '</head>', 1)
    t0 = html.index('<title>'); t1 = html.index('</title>')
    html = html[:t0] + '<title>X-ON-X – Sky demo 9: film with clouds' + html[t1:]
    a = '    <div class="xx-film__veil"></div>\n'
    assert html.count(a) == 1
    html = html.replace(a, a + '    <canvas class="xx-gl" id="xx-gl-back"></canvas>\n    <canvas class="xx-gl" id="xx-gl-front"></canvas>\n')
    scripts = (f'<script src="js/three.min.js"></script>\n'
               f'<script src="field.js?v={V}" data-count="{count}" data-clouds="{nclouds}" data-texture="clouds/puff_photo.png?v={V}" '
               f'data-sky="#ECE8E6" data-fogalpha="1"></script>\n'
               '<script>window.process = window.process || { env: { NODE_ENV: "production" } };</script>\n'
               f'<script src="js/theatre-core-and-studio.js?v={V}"></script>\n'
               f'<script src="film-state.js?v={V}"></script>\n'
               f'<script src="veil.js?v={V}"></script>\n'
               f'<script src="film-motion.js?v={V}"></script>\n')
    i = html.rindex('</body>')
    html = html[:i] + scripts + html[i:]
    html = html.replace('<a href="journey.html">demo 6: journey &rarr;</a>',
                        '<a href="film.html">demo 5: film &rarr;</a>\n  <a href="journey.html">demo 6: journey &rarr;</a>')
    html = html.replace(f"location.replace('{partner_src}?", f"location.replace('{partner}?")
    (DST / out).write_text(html)
    print(out, len(html) // 1024, 'KB')


if __name__ == '__main__':
    build('film.html', 'film-clouds.html', 'film-m.html', 'film-clouds-m.html', 9000, 34)
    build('film-m.html', 'film-clouds-m.html', 'film.html', 'film-clouds.html', 3600, 22)
