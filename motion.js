/* X-ON-X hero, demo 8: motion design on a timeline (Theatre.js).
 *
 * 01.10, Iryna: «давай пограємось в мовшн дизайн». Demo 4's clouds (approved) with a Theatre.js
 * studio on top: a keyframe timeline like After Effects, in the browser. Every knob below is a
 * prop on a sheet object; field.js reads window.xxMotion each frame, the text layers are styled
 * directly. Nothing here changes demo 4 itself.
 *
 *   motion.html            studio open: keyframe, scrub (space = play), export
 *   motion.html?play=1     no studio: just the choreography, looping, as it would ship
 *
 * The starting choreography is motion-state.js (window.xxMotionState). When Iryna exports her
 * own from the studio (project panel → Export), that JSON replaces it and the page plays hers.
 * Studio is AGPL; the shipped page would load core-only (Apache 2.0) with the state baked in. */
(function () {
  'use strict';
  if (!window.Theatre) return;
  var core = Theatre.core, studio = Theatre.studio, t = core.types;
  var playOnly = /[?&]play=1/.test(location.search);
  var root = document.documentElement;
  // with the full bundle the core waits for the studio, so ?play=1 initialises it and hides it
  // (the shipped page would load core-only instead and skip this)
  if (studio) { studio.initialize(); if (playOnly) studio.ui.hide(); else root.classList.add('xx-studio'); }
  if (playOnly) root.classList.add('xx-play');   // as it would ship: no demo panels either

  var project = core.getProject('X-ON-X hero', window.xxMotionState ? { state: window.xxMotionState } : {});
  var sheet = project.sheet('Hero');
  var M = window.xxMotion = {};

  function n(v, lo, hi, nudge) { return t.number(v, { range: [lo, hi], nudgeMultiplier: nudge || 1 }); }

  var flight = sheet.object('Flight', {
    speed: n(1, 0, 5, 0.05),          // × demo 4's cruise; 0 = hover, 3 = rush
    push: n(0, -3000, 3000, 10),      // offset along the line of flight: a surge forward, a pull back
    camX: n(0, -500, 500, 5),         // sideways drift
    camY: n(0, -400, 400, 5),         // climb / dive
    roll: n(0, -0.4, 0.4, 0.005),     // bank, radians
    fov: n(58, 30, 90, 0.5),          // lens: 30 long and flat, 80 wide and fast
    shake: n(0, 0, 1, 0.01)           // turbulence: a small fast buffet of the camera
  });
  flight.onValuesChange(function (v) {
    M.speed = v.speed; M.push = v.push; M.camX = v.camX; M.camY = v.camY; M.roll = v.roll; M.fov = v.fov; M.shake = v.shake;
  });

  var clouds = sheet.object('Clouds', {
    lining: n(0.6, 0, 1.5, 0.02),     // silver lining
    billow: n(0.5, 0, 1.5, 0.02),     // churn
    haze: n(2600, 900, 2600, 10),     // how far you see before the clouds dissolve into the sky
    front: n(0.40, 0, 1, 0.01)        // how much of the cloud in front of the words shows
  });
  clouds.onValuesChange(function (v) {
    M.rim = v.lining; M.billow = v.billow; M.haze = v.haze;
    root.style.setProperty('--xx-front-o', v.front.toFixed(3));
  });

  function mix(a, b, k) { return a.map(function (x, i) { return x + (b[i] - x) * k; }); }
  function hex(c) { return '#' + c.map(function (v) { return ('0' + Math.round(v).toString(16)).slice(-2); }).join(''); }
  var sky = sheet.object('Sky', {
    sunX: n(62, 0, 100, 0.5),         // where the warm glow sits, % of the screen
    sunY: n(46, 0, 100, 0.5),
    blue: n(0, 0, 1, 0.01),           // deeper blue at the zenith
    warm: n(0, 0, 1, 0.01)            // more of the warm band above the horizon
  });
  sky.onValuesChange(function (v) {
    root.style.setProperty('--cx', v.sunX.toFixed(1) + '%');
    root.style.setProperty('--cy', v.sunY.toFixed(1) + '%');
    root.style.setProperty('--g-sky-high', hex(mix([0xAA, 0xB9, 0xDB], [0x8A, 0xA2, 0xD2], v.blue)));
    root.style.setProperty('--g-sky-warm', hex(mix([0xFA, 0xEF, 0xE0], [0xF6, 0xE3, 0xC9], v.warm)));
  });

  // ── the veil: the page opens inside a cloud, and the cloud tears open from the sun ──
  // Not a CSS radial gradient: a perfect circle opening reads as a porthole. The veil is a
  // small canvas (scaled up, it is vapour, softness is free) whose edge is pushed in and out
  // by fBm noise, so it tears into ragged wisps; the noise also shades the inside of the
  // cloud a little, so the white has a body. It is redrawn only while its values change.
  var css = document.createElement('style');
  css.textContent =
    '.xx-veil-blur{position:fixed;inset:0;z-index:54;pointer-events:none;' +
    'backdrop-filter:blur(var(--vb,0px));-webkit-backdrop-filter:blur(var(--vb,0px))}' +
    '.xx-veil{position:fixed;left:-16px;top:-16px;width:calc(100vw + 32px);height:calc(100vh + 32px);z-index:55;pointer-events:none;filter:blur(3px)}' +   // oversized: the blur must not thin the screen edges
    '';
  document.head.appendChild(css);
  var vblur = document.createElement('div'); vblur.className = 'xx-veil-blur';
  var veil = document.createElement('canvas'); veil.className = 'xx-veil';
  [vblur, veil].forEach(function (el) { el.setAttribute('aria-hidden', 'true'); document.body.appendChild(el); });
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
  var veilObj = sheet.object('Veil', {
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

  // The words do not move (Iryna, 01.10: «букви не треба рухати. грайся тільки з хмарами»):
  // no text objects on the timeline, no mouse depth on the words. Only the sky moves.

  project.ready.then(function () {
    // the intro plays once, then the rest loops; in the studio, space pauses and the playhead scrubs
    var seq = sheet.sequence;
    var intro = window.xxMotionIntro || 0;
    var end = core.val(seq.pointer.length);
    if (intro > 0 && intro < end) {
      seq.play({ range: [0, intro] }).then(function (done) {
        if (done) seq.play({ range: [intro, end], iterationCount: Infinity });
      });
    } else {
      seq.play({ iterationCount: Infinity });
    }
    window.xxSheet = sheet;
  });
})();
