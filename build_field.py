"""Demo 4 (field.html / field-m.html): a cloud field in WebGL, after mrdoob.

Iryna, 20.09, after four passes of demo 3: «структура хмар має бути як тут», pointing at
mrdoob.com/lab/javascript/webgl/clouds. Same slicing as the other builders — nav + hero cut
out of the live builds, the old sky off — with two canvases around the hero and field.js
doing the flight. Three r128 is vendored in js/ so the page does not depend on a CDN.

    python build_field.py
"""
import pathlib, re

SRC = pathlib.Path('/Users/user/Claude/xonx-site-preview')
DST = pathlib.Path(__file__).parent
V = '20260920p'

PANEL = '''
<div class="xx-proto" role="group" aria-label="sky controls">
  <button type="button" data-xx="motion">motion: on</button>
  <button type="button" data-xx="tempo">tempo: normal</button>
  <button type="button" data-xx="through">crosses text: yes</button>
  <button type="button" data-xx="veil">front: normal</button>
  <a href="flight.html">demo 3 &rarr;</a>
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


def build(name, out, partner, count, texture, clouds=46):
    html = (SRC / name).read_text()
    html = re.sub(r'\?v=\d{8}[a-z]', f'?v={V}', html)
    html = html.replace("location.replace('m.html?", f"location.replace('{partner}?")
    html = html.replace("location.replace('index.html?", f"location.replace('{partner}?")
    html = html.replace('</head>', f'<link rel="stylesheet" href="field.css?v={V}">\n</head>', 1)
    html = html.replace('<title>X-ON-X – Home</title>', '<title>X-ON-X – Sky demo 4: cloud field</title>')
    start = html.index('<!-- ──── LATEST INSIGHTS')
    end = html.index('</div><!-- /.xx-page -->')
    html = html[:start] + html[end:]
    a = html.index('</div><!-- /.xx-page -->') + len('</div><!-- /.xx-page -->')
    b = html.index('</body>')
    field = (f'<script src="js/three.min.js"></script>\n'
             f'<script src="field.js?v={V}" data-count="{count}" data-clouds="{clouds}" data-texture="{texture}?v={V}" '
             f'data-sky="#ECE8E6"></script>\n')
    html = html[:a] + '\n' + PANEL + '\n' + field + html[b:]
    sky = ('\n  <!-- ──── SKY (demo 4: WebGL cloud field, after mrdoob) ──── -->\n'
           '  <div class="xx-sky" aria-hidden="true"></div>\n'
           '  <canvas class="xx-gl" id="xx-gl-back" aria-hidden="true"></canvas>\n'
           '  <canvas class="xx-gl" id="xx-gl-front" aria-hidden="true"></canvas>\n')
    html = re.sub(r'(<div class="xx-page"[^>]*>)', lambda m: m.group(1) + sky, html, count=1)
    (DST / out).write_text(html)
    print(out, len(html) // 1024, 'KB', count, 'puffs')


if __name__ == '__main__':
    build('index.html', 'field.html', 'field-m.html', 5000, 'clouds/puff_photo.png', 34)
    build('m.html', 'field-m.html', 'field.html', 2200, 'clouds/puff_photo.png', 22)
