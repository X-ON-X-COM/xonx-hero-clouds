"""Demo 7 (volume.html / volume-m.html): raymarched volumetric clouds, volume.js.

28.09, point 4 of «роби всі 4»: real volume instead of billboards, for comparison with the
approved demo 4. Built from demo 4's pages as they stand (not re-sliced from the site), so
the hero, the sky and the panel are identical and only the clouds differ.

    python build_volume.py
"""
import pathlib, re

DST = pathlib.Path(__file__).parent
V = '20260928a'

TUNE = '''<div class="xx-tune" id="xx-tune" hidden>
  <label>coverage <input type="range" data-k="coverage" min="0.2" max="0.8" step="0.01"><output></output></label>
  <label>density <input type="range" data-k="density" min="0.3" max="2" step="0.05"><output></output></label>
  <label>speed <input type="range" data-k="speed" min="0.02" max="0.2" step="0.005"><output></output></label>
  <label>shade <input type="range" data-k="shade" min="0" max="2" step="0.05"><output></output></label>
  <label>lining <input type="range" data-k="lining" min="0" max="2.5" step="0.05"><output></output></label>
  <label>quality <input type="range" data-k="scale" min="0.25" max="1" step="0.05"><output></output></label>
  <label>sky blue <input type="range" data-k="skyblue" min="0" max="1" step="0.05"><output></output></label>
  <label>warm band <input type="range" data-k="skywarm" min="0" max="1" step="0.05"><output></output></label>
  <div class="xx-tune__row"><button type="button" data-xx="copy">copy settings</button><button type="button" data-xx="reset">reset</button></div>
  <textarea id="xx-tune-out" rows="2" readonly></textarea>
</div>'''


def build(src, out, partner):
    html = (DST / src).read_text()
    html = html.replace(f"location.replace('{partner.replace('volume', 'field')}?", f"location.replace('{partner}?")
    html = html.replace('Sky demo 4: cloud field', 'Sky demo 7: volumetric clouds')
    html = html.replace('(demo 4: WebGL cloud field, after mrdoob)', '(demo 7: raymarched volumetric clouds)')
    html = re.sub(r'<div class="xx-tune" id="xx-tune" hidden>.*?</textarea>\n</div>', TUNE, html, count=1, flags=re.S)
    html = re.sub(r'<script src="js/three.min.js"></script>\n<script src="field.js[^>]*></script>',
                  f'<script src="volume.js?v={V}"></script>', html, count=1)
    # the panel prints whatever the field exposes
    html = re.sub(r"return JSON.stringify\(\{ clouds: c.clouds.*?\n.*?skywarm: sky.skywarm \}\);",
                  "var o = {}; ['coverage','density','speed','shade','lining','scale'].forEach(function (k) { o[k] = c[k]; });\n"
                  "    o.skyblue = sky.skyblue; o.skywarm = sky.skywarm; return JSON.stringify(o);", html, count=1, flags=re.S)
    html = html.replace('<a href="journey.html">demo 6: journey &rarr;</a>',
                        '<a href="field.html">demo 4: field &rarr;</a>\n  <a href="journey.html">demo 6: journey &rarr;</a>')
    assert 'volume.js' in html and 'coverage' in html and 'field.js' not in html
    (DST / out).write_text(html)
    print(out, len(html) // 1024, 'KB')


if __name__ == '__main__':
    build('field.html', 'volume.html', 'volume-m.html')
    build('field-m.html', 'volume-m.html', 'volume.html')
