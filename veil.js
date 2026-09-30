/* The torn cloud veil, shared by demo 8 (motion.js: the page opens inside a cloud) and demo 9
 * (film-motion.js: cloud wipes across the film's cuts). A Theatre.js sheet object whose values
 * redraw a small noise-torn canvas; see the comment inside. */
window.xxVeil = function (sheet, n, opts) {
  'use strict';
  // ── the veil: the page opens inside a cloud, and the cloud tears open from the sun ──
  // Not a CSS radial gradient: a perfect circle opening reads as a porthole. The veil is a
  // small canvas (scaled up, it is vapour, softness is free) whose edge is pushed in and out
  // by fBm noise, so it tears into ragged wisps; the noise also shades the inside of the
  // cloud a little, so the white has a body. It is redrawn only while its values change.
  opts = opts || {};
  var z = opts.z == null ? 55 : opts.z, parent = opts.parent || document.body, name = opts.name || 'Veil';
  var fixed = parent === document.body ? 'fixed' : 'absolute';
  var css = document.createElement('style');
  css.textContent =
    '.xx-veil-blur{position:' + fixed + ';inset:0;z-index:' + (z - 1) + ';pointer-events:none;' +
    'backdrop-filter:blur(var(--vb,0px));-webkit-backdrop-filter:blur(var(--vb,0px))}' +
    '.xx-veil{position:' + fixed + ';left:-16px;top:-16px;width:calc(100% + 32px);height:calc(100% + 32px);z-index:' + z + ';pointer-events:none;filter:blur(3px)}';   // oversized: the blur must not thin the screen edges
  document.head.appendChild(css);
  var vblur = document.createElement('div'); vblur.className = 'xx-veil-blur';
  var veil = document.createElement('canvas'); veil.className = 'xx-veil';
  [vblur, veil].forEach(function (el) { el.setAttribute('aria-hidden', 'true'); parent.appendChild(el); });
  var VW = 256, VH = Math.max(90, Math.round(256 * window.innerHeight / window.innerWidth));
  veil.width = VW; veil.height = VH;
  var vctx = veil.getContext('2d'), vimg = vctx.createImageData(VW, VH);
  // fBm on a tile twice as wide as the veil, so the tear can drift sideways as it opens
  var NW = VW * 2, noiseT = new Float32Array(NW * VH);
  (function () {
    var seed = 20261001;
    function rnd() { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; }
    var total = 0;
    [[8, 0.5], [16, 0.25], [32, 0.15], [64, 0.1]].forEach(function (o) {
      var gx = o[0] + 1, gy = Math.ceil(o[0] * VH / NW) + 2, g = [];
      for (var i = 0; i < gx * gy; i++) g.push(rnd());
      for (var y = 0; y < VH; y++) for (var x = 0; x < NW; x++) {
        var fx = x / NW * o[0], fy = y / NW * o[0], ix = Math.floor(fx), iy = Math.floor(fy);
        var tx = fx - ix, ty = fy - iy; tx = tx * tx * (3 - 2 * tx); ty = ty * ty * (3 - 2 * ty);
        var a = g[iy * gx + ix], b = g[iy * gx + ix + 1], c = g[(iy + 1) * gx + ix], d = g[(iy + 1) * gx + ix + 1];
        noiseT[y * NW + x] += ((a + (b - a) * tx) * (1 - ty) + (c + (d - c) * tx) * ty) * o[1];
      }
      total += o[1];
    });
    for (var j = 0; j < noiseT.length; j++) noiseT[j] /= total;
  })();
  function drawVeil(v) {
    var data = vimg.data, ox = v.originX / 100 * VW, oy = v.originY / 100 * VH;
    var diag = Math.sqrt(VW * VW + VH * VH), sft = Math.max(0.02, v.softness / 100);
    var reach = v.open * 1.75 - 0.25, drift = Math.round(v.open * VW * 0.35);
    for (var y = 0; y < VH; y++) for (var x = 0; x < VW; x++) {
      var nz = noiseT[y * NW + x + drift];
      var dx = x - ox, dy = (y - oy) * 1.15, r = Math.sqrt(dx * dx + dy * dy) / diag;
      var e = r + (nz - 0.5) * v.ragged - reach;               // < 0 = torn away, > 0 = still cloud
      var a = Math.min(1, Math.max(0, (e + sft) / (2 * sft)));
      a = a * a * (3 - 2 * a) * v.density;
      var k = (y * VW + x) * 4, shade = (nz - 0.5) * 38 * v.body;   // a little tone inside the white
      data[k] = 247 - shade * 0.9; data[k + 1] = 246 - shade * 0.8; data[k + 2] = 242 - shade * 0.35;
      data[k + 3] = a * 255;
    }
    vctx.putImageData(vimg, 0, 0);
  }
  var veilObj = sheet.object(name, {
    open: n(1, 0, 1, 0.01),           // 0 = inside the cloud, 1 = gone
    density: n(1, 0, 1, 0.01),        // how white the cloud is
    softness: n(12, 2, 60, 0.5),      // width of the torn edge
    ragged: n(0.55, 0, 1.5, 0.01),    // how far the noise pushes the edge in and out: 0 = a circle
    body: n(1, 0, 2, 0.02),           // tone inside the white
    blur: n(0, 0, 30, 0.2),           // the world behind the vapour, out of focus
    originX: n(62, 0, 100, 0.5),      // where it tears open first: the sun
    originY: n(46, 0, 100, 0.5)
  });
  veilObj.onValuesChange(function (v) {
    var gone = v.open >= 0.999 || v.density <= 0.001;
    veil.style.display = gone ? 'none' : '';
    vblur.style.display = v.blur > 0.05 ? '' : 'none';
    vblur.style.setProperty('--vb', v.blur.toFixed(1) + 'px');
    if (!gone) drawVeil(v);
  });

  return veilObj;
};
