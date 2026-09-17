"""Demo 2 (halo.html / halo-m.html): the same hero, the halo sky and the bursting clouds.

Same slicing as build.py — nav + hero out of the live builds, old sky off — but the
stylesheet is halo.css, the viewport switch points at the halo pair, and the corner
panel carries the knobs Oleg will want to try (tempo, nimbus, old look).
"""
import re, pathlib
SRC = pathlib.Path('/Users/user/Claude/xonx-site-preview')
DST = pathlib.Path(__file__).parent
V = '20260917c'

SKY = '''
  <!-- ──── SKY (demo 2: halo + bursting clouds) ──── -->
  <div class="xx-sky" aria-hidden="true">
    <div class="xx-layer xx-layer--far"><div class="xx-cloud xx-cloud--a"></div><div class="xx-cloud xx-cloud--b"></div></div>
    <div class="xx-layer xx-layer--mid"><div class="xx-cloud xx-cloud--a"></div><div class="xx-cloud xx-cloud--b"></div></div>
  </div>
  <div class="xx-halo" aria-hidden="true">
    <div class="xx-halo__glow"></div>
    <div class="xx-halo__ring xx-halo__ring--in"></div>
    <div class="xx-halo__ring xx-halo__ring--out"></div>
  </div>
  <div class="xx-sky xx-sky--near" aria-hidden="true">
''' + ''.join('''    <div class="xx-burst"><span class="xx-shard"></span><span class="xx-shard"></span><span class="xx-shard"></span><span class="xx-shard"></span><span class="xx-veil"></span></div>\n''' for _ in range(3)) + '''  </div>
'''

PANEL = '''
<div class="xx-proto" role="group" aria-label="sky controls">
  <button type="button" data-xx="motion">motion: on</button>
  <button type="button" data-xx="tempo">tempo: normal</button>
  <button type="button" data-xx="halo">nimbus: on</button>
  <button type="button" data-xx="soft">clouds: crisp</button>
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
  var root = document.documentElement, tempos = ['normal', 'calm', 'quick'], t = 0;
  function label(el, text) { el.textContent = text; }
  document.querySelectorAll('.xx-proto button').forEach(function (b) {
    b.addEventListener('click', function () {
      var k = b.dataset.xx;
      if (k === 'motion') {
        root.classList.toggle('xx-still');
        label(b, 'motion: ' + (root.classList.contains('xx-still') ? 'off' : 'on'));
      } else if (k === 'tempo') {
        t = (t + 1) % tempos.length;
        root.classList.remove('xx-tempo-calm', 'xx-tempo-quick');
        if (tempos[t] !== 'normal') root.classList.add('xx-tempo-' + tempos[t]);
        label(b, 'tempo: ' + tempos[t]);
      } else if (k === 'halo') {
        root.classList.toggle('xx-nohalo');
        label(b, 'nimbus: ' + (root.classList.contains('xx-nohalo') ? 'off' : 'on'));
      } else {
        root.classList.toggle('xx-soft');
        label(b, 'clouds: ' + (root.classList.contains('xx-soft') ? 'soft' : 'crisp'));
      }
    });
  });
})();
</script>
'''


def build(name, out, partner):
    html = (SRC / name).read_text()
    html = re.sub(r"\?v=\d{8}[a-z]", f"?v={V}", html)
    # the switch must move between the halo pair, not back to demo 1
    html = html.replace("location.replace('m.html?", f"location.replace('{partner}?")
    html = html.replace("location.replace('index.html?", f"location.replace('{partner}?")
    html = html.replace('</head>', f'<link rel="stylesheet" href="halo.css?v={V}">\n</head>', 1)
    html = html.replace('<title>X-ON-X – Home</title>', '<title>X-ON-X – Sky demo 2: halo</title>')
    # keep nav + hero only
    start = html.index('<!-- ──── LATEST INSIGHTS')
    end = html.index('</div><!-- /.xx-page -->')
    html = html[:start] + html[end:]
    # drop the WIP modal + scripts after the page, add the control panel
    a = html.index('</div><!-- /.xx-page -->') + len('</div><!-- /.xx-page -->')
    b = html.index('</body>')
    html = html[:a] + '\n' + PANEL + '\n' + html[b:]
    # sky layers right after the page opens
    html = re.sub(r'(<div class="xx-page"[^>]*>)', lambda m: m.group(1) + SKY, html, count=1)
    (DST / out).write_text(html)
    print(out, len(html) // 1024, 'KB')


build('index.html', 'halo.html', 'halo-m.html')
build('m.html', 'halo-m.html', 'halo.html')
