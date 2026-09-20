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
V = '20260920t'

PANEL = '''
<div class="xx-proto" role="group" aria-label="sky controls">
  <button type="button" data-xx="motion">motion: on</button>
  <button type="button" data-xx="tempo">tempo: normal</button>
  <button type="button" data-xx="through">crosses text: yes</button>
  <button type="button" data-xx="veil">front: normal</button>
  <button type="button" data-xx="tune">tune &hellip;</button>
  <a href="flight.html">demo 3 &rarr;</a>
  <a href="halo.html">demo 2 &rarr;</a>
  <a href="index.html">demo 1 &rarr;</a>
</div>
<div class="xx-tune" id="xx-tune" hidden>
  <label>clouds <input type="range" data-k="clouds" min="14" max="70" step="1"><output></output></label>
  <label>size <input type="range" data-k="size" min="0.5" max="1.8" step="0.05"><output></output></label>
  <label>speed <input type="range" data-k="speed" min="0.02" max="0.2" step="0.005"><output></output></label>
  <label>shade <input type="range" data-k="shade" min="0" max="1.6" step="0.05"><output></output></label>
  <label>warmth <input type="range" data-k="warmth" min="0" max="1" step="0.05"><output></output></label>
  <label>sky blue <input type="range" data-k="skyblue" min="0" max="1" step="0.05"><output></output></label>
  <label>warm band <input type="range" data-k="skywarm" min="0" max="1" step="0.05"><output></output></label>
  <div class="xx-tune__row"><button type="button" data-xx="copy">copy settings</button><button type="button" data-xx="reset">reset</button></div>
  <textarea id="xx-tune-out" rows="2" readonly></textarea>
</div>
<style>
.xx-proto{position:fixed;right:14px;bottom:14px;z-index:60;display:flex;flex-direction:column;align-items:flex-end;gap:6px}
.xx-proto button,.xx-proto a{font:11px/1 "JetBrains Mono",monospace;letter-spacing:1px;text-transform:uppercase;
 padding:8px 12px;border-radius:999px;border:1px solid rgba(17,17,17,.18);background:rgba(255,254,248,.8);
 color:#111;cursor:pointer;backdrop-filter:blur(8px);text-decoration:none}
.xx-proto button:hover,.xx-proto a:hover{background:rgba(255,254,248,.98)}
@media (max-width:768px){.xx-proto{right:10px;bottom:10px;gap:4px}.xx-proto button,.xx-proto a{padding:7px 10px;font-size:10px}}
.xx-tune{position:fixed;left:14px;bottom:14px;z-index:60;width:260px;padding:12px 14px;border-radius:14px;
 border:1px solid rgba(17,17,17,.18);background:rgba(255,254,248,.9);backdrop-filter:blur(8px);
 font:11px/1.4 "JetBrains Mono",monospace;letter-spacing:.5px;color:#111}
.xx-tune label{display:grid;grid-template-columns:64px 1fr 44px;align-items:center;gap:8px;margin:4px 0;text-transform:uppercase}
.xx-tune input[type=range]{width:100%}
.xx-tune output{text-align:right}
.xx-tune__row{display:flex;gap:6px;margin-top:8px}
.xx-tune__row button{flex:1;font:inherit;text-transform:uppercase;padding:7px 8px;border-radius:999px;border:1px solid rgba(17,17,17,.18);background:#fff;cursor:pointer}
.xx-tune textarea{width:100%;margin-top:8px;font:10px/1.3 "JetBrains Mono",monospace;border:1px solid rgba(17,17,17,.18);border-radius:8px;padding:6px;resize:none;background:#fff}
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
      } else if (k === 'tune') {
        var t = document.getElementById('xx-tune'); t.hidden = !t.hidden;
      } else if (k === 'copy' || k === 'reset') {
        return;
      } else {
        v = (v + 1) % veils.length;
        root.classList.remove('xx-thin', 'xx-thick');
        if (veils[v] !== 'normal') root.classList.add('xx-' + veils[v]);
        b.textContent = 'front: ' + veils[v];
      }
    });
  });

  // ── the tuning panel: sliders write straight into the field, the sky ones into CSS ──
  var tune = document.getElementById('xx-tune'), out = document.getElementById('xx-tune-out');
  var skyBase = { high: [0xAA, 0xB9, 0xDB], warm: [0xFA, 0xEF, 0xE0] };
  var sky = { skyblue: 0.0, skywarm: 0.0 };
  try { Object.assign(sky, JSON.parse(localStorage.getItem('xx-sky') || '{}')); } catch (e) {}
  function hex(c) { return '#' + c.map(function (v) { return ('0' + Math.round(v).toString(16)).slice(-2); }).join(''); }
  function applySky() {
    // more blue at the zenith, more of the warm band above the horizon
    var hi = skyBase.high.map(function (v, i) { return v + ([0x8A, 0xA2, 0xD2][i] - v) * sky.skyblue; });
    var wa = skyBase.warm.map(function (v, i) { return v + ([0xF6, 0xE3, 0xC9][i] - v) * sky.skywarm; });
    root.style.setProperty('--g-sky-high', hex(hi));
    root.style.setProperty('--g-sky-warm', hex(wa));
    try { localStorage.setItem('xx-sky', JSON.stringify(sky)); } catch (e) {}
  }
  applySky();
  function settings() {
    var c = window.xxField ? window.xxField.cfg : {};
    return JSON.stringify({ clouds: c.clouds, count: c.count, size: c.size, speed: c.speed, shade: c.shade, warmth: c.warmth,
      skyblue: sky.skyblue, skywarm: sky.skywarm });
  }
  function sync() {
    var c = window.xxField ? window.xxField.cfg : null;
    tune.querySelectorAll('input[type=range]').forEach(function (inp) {
      var k = inp.dataset.k, v = (k in sky) ? sky[k] : (c ? c[k] : inp.value);
      inp.value = v; inp.nextElementSibling.value = (+v).toFixed(k === 'clouds' ? 0 : (k === 'speed' ? 3 : 2));
    });
    out.value = settings();
  }
  tune.querySelectorAll('input[type=range]').forEach(function (inp) {
    inp.addEventListener('input', function () {
      var k = inp.dataset.k, v = +inp.value;
      if (k in sky) { sky[k] = v; applySky(); } else if (window.xxField) { window.xxField.set(k, v); }
      sync();
    });
  });
  tune.querySelector('[data-xx=copy]').addEventListener('click', function () {
    out.value = settings(); out.select();
    try { navigator.clipboard.writeText(out.value); } catch (e) {}
  });
  tune.querySelector('[data-xx=reset]').addEventListener('click', function () {
    try { localStorage.removeItem('xx-sky'); } catch (e) {}
    if (window.xxField) window.xxField.reset(); else location.reload();
  });
  var wait = setInterval(function () { if (window.xxField) { clearInterval(wait); sync(); } }, 200);
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
