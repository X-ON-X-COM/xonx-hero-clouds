"""Assemble the prototype from the live builds: nav + hero only, old sky off, cloud layers in."""
import re, pathlib
SRC = pathlib.Path('/Users/user/Claude/xonx-site-preview')
DST = pathlib.Path(__file__).parent
V = '20260916a'

SKY = '''
  <!-- ──── SKY (prototype) ──── -->
  <div class="xx-sky" aria-hidden="true">
    <div class="xx-layer xx-layer--far"><div class="xx-cloud xx-cloud--a"></div><div class="xx-cloud xx-cloud--b"></div></div>
    <div class="xx-layer xx-layer--mid"><div class="xx-cloud xx-cloud--a"></div><div class="xx-cloud xx-cloud--b"></div></div>
  </div>
  <div class="xx-sky xx-sky--near" aria-hidden="true">
    <div class="xx-layer xx-layer--near"><div class="xx-cloud xx-cloud--a"></div><div class="xx-cloud xx-cloud--b"></div></div>
  </div>
'''
TOGGLE = '''
<button class="xx-proto-toggle" type="button" onclick="document.documentElement.classList.toggle('xx-still');this.textContent=document.documentElement.classList.contains('xx-still')?'motion: off':'motion: on'">motion: on</button>
<style>.xx-proto-toggle{position:fixed;right:14px;bottom:14px;z-index:60;font:11px/1 "JetBrains Mono",monospace;letter-spacing:1px;text-transform:uppercase;padding:8px 12px;border-radius:999px;border:1px solid rgba(17,17,17,.18);background:rgba(255,254,248,.8);color:#111;cursor:pointer;backdrop-filter:blur(8px)}</style>
'''

def build(name, other_param):
    html = (SRC / name).read_text()
    # version token in the viewport switch
    html = re.sub(r"\?v=\d{8}[a-z]", f"?v={V}", html)
    # stylesheet + title
    html = html.replace('</head>', f'<link rel="stylesheet" href="clouds.css?v={V}">\n</head>', 1)
    html = html.replace('<title>X-ON-X – Home</title>', '<title>X-ON-X – Sky prototype</title>')
    # keep nav + hero only
    start = html.index('<!-- ──── LATEST INSIGHTS')
    end = html.index('</div><!-- /.xx-page -->')
    html = html[:start] + html[end:]
    # drop the WIP modal + scripts after the page
    a = html.index('</div><!-- /.xx-page -->') + len('</div><!-- /.xx-page -->')
    b = html.index('</body>')
    html = html[:a] + '\n' + TOGGLE + '\n' + html[b:]
    # sky layers right after the page opens
    html = re.sub(r'(<div class="xx-page"[^>]*>)', r'\1' + SKY, html, count=1)
    (DST / name).write_text(html)
    print(name, len(html) // 1024, 'KB')

build('index.html', 'full')
build('m.html', 'm')
