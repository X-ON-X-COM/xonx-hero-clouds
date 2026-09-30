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

  // ── the veil: the page opens inside a cloud, and the cloud parts from the sun outwards ──
  var veil = document.createElement('div');
  veil.className = 'xx-veil'; veil.setAttribute('aria-hidden', 'true');
  document.body.appendChild(veil);
  var css = document.createElement('style');
  css.textContent =
    '.xx-veil{position:fixed;inset:0;z-index:55;pointer-events:none;' +
    'background:radial-gradient(circle at var(--vx,62%) var(--vy,46%),' +
    'rgba(247,246,242,0) calc(var(--vo,0) * 140%),' +
    'rgba(247,246,242,var(--va,1)) calc(var(--vo,0) * 140% + var(--vs,26%)));' +
    'backdrop-filter:blur(var(--vb,0px));-webkit-backdrop-filter:blur(var(--vb,0px))}' +
    '.xx-hero h1 .xx-w{display:inline-block;will-change:opacity,transform,filter}';
  document.head.appendChild(css);
  var veilObj = sheet.object('Veil', {
    open: n(1, 0, 1, 0.01),           // 0 = inside the cloud, 1 = gone
    density: n(1, 0, 1, 0.01),        // how white the cloud is
    softness: n(26, 2, 80, 0.5),      // % width of the torn edge
    blur: n(0, 0, 30, 0.2),           // the world behind the vapour, out of focus
    originX: n(62, 0, 100, 0.5),      // where it tears open first: the sun
    originY: n(46, 0, 100, 0.5)
  });
  veilObj.onValuesChange(function (v) {
    veil.style.setProperty('--vo', v.open.toFixed(3));
    veil.style.setProperty('--va', v.density.toFixed(3));
    veil.style.setProperty('--vs', v.softness.toFixed(1) + '%');
    veil.style.setProperty('--vb', v.blur.toFixed(1) + 'px');
    veil.style.setProperty('--vx', v.originX.toFixed(1) + '%');
    veil.style.setProperty('--vy', v.originY.toFixed(1) + '%');
    veil.style.display = v.open >= 0.999 ? 'none' : '';
  });

  // ── depth: the words hang at different distances in the air ──
  // Each text layer moves with the mouse by its own depth, the headline most, the nav not at
  // all; `strength` on the Depth object scales the lot (0 = flat, as on the live site).
  var depthObj = sheet.object('Depth', { strength: n(1, 0, 3, 0.02), ease: n(0.06, 0.01, 0.3, 0.005) });
  var depthV = { strength: 1, ease: 0.06 };
  depthObj.onValuesChange(function (v) { depthV = v; });
  var mx = 0, my = 0, px = 0, py = 0, layers = [];
  document.addEventListener('mousemove', function (e) {
    mx = e.clientX / window.innerWidth - 0.5; my = e.clientY / window.innerHeight - 0.5;
  });

  function apply(L) {
    var v = L.v, dx = -px * L.depth * 22 * depthV.strength, dy = -py * L.depth * 14 * depthV.strength;
    L.els.forEach(function (el) {
      el.style.opacity = v.opacity;
      el.style.transform = 'translate(' + dx.toFixed(1) + 'px,' + (v.y + dy).toFixed(1) + 'px) scale(' + v.scale.toFixed(3) + ')' +
        (v.rotate ? ' rotate(' + v.rotate.toFixed(2) + 'deg)' : '');
      el.style.filter = v.blur > 0.05 ? 'blur(' + v.blur.toFixed(1) + 'px)' : '';
      if (v.tracking != null) el.style.letterSpacing = Math.abs(v.tracking) > 0.0005 ? v.tracking.toFixed(3) + 'em' : '';
      el.style.transformOrigin = L.origin;
      el.style.willChange = 'opacity, transform, filter';
    });
  }
  function layer(name, sel, depth, extra) {
    var els = typeof sel === 'string' ? [].slice.call(document.querySelectorAll(sel)) : sel;
    if (!els.length) return;
    var props = {
      opacity: n(1, 0, 1, 0.01),
      y: n(0, -120, 120, 1),          // px, + = lower
      blur: n(0, 0, 24, 0.2),         // px
      scale: n(1, 0.6, 1.4, 0.005)
    };
    Object.assign(props, extra || {});
    var o = sheet.object(name, props);
    var L = { els: els, depth: depth, v: null, origin: name.indexOf('Word') >= 0 ? '50% 80%' : '0 50%' };
    o.onValuesChange(function (v) { L.v = v; apply(L); });
    layers.push(L);
  }
  var TR = { tracking: n(0, -0.05, 0.3, 0.002) };   // letter-spacing, em
  layer('Text / Nav', '.xx-nav', 0);
  layer('Text / Logo', '.xx-hero__logo', 0.35);
  layer('Text / Eyebrow', '.xx-hero__eyebrow', 0.45);
  layer('Text / Headline', '.xx-hero h1', 0.9, TR);
  layer('Text / Lede', '.xx-hero__leftlede', 0.6);
  layer('Text / Buttons', '.xx-cta-dock--home', 0.5);
  layer('Text / Right column', '.xx-hero__right', 0.7);
  layer('Text / Situations', '.xx-hero-dock', 0.25);

  // the headline, word by word: every word its own object, so they can arrive one at a time
  var h1 = document.querySelector('.xx-hero h1'), words = [];
  if (h1) {
    (function split(node) {
      [].slice.call(node.childNodes).forEach(function (c) {
        if (c.nodeType === 3 && c.nodeValue.trim()) {
          var frag = document.createDocumentFragment();
          c.nodeValue.split(/(\s+)/).forEach(function (w) {
            if (!w) return;
            if (/^\s+$/.test(w)) { frag.appendChild(document.createTextNode(w)); return; }
            var sp = document.createElement('span'); sp.className = 'xx-w'; sp.textContent = w;
            frag.appendChild(sp); words.push(sp);
          });
          node.replaceChild(frag, c);
        } else if (c.nodeType === 1 && c.tagName !== 'BR') split(c);
      });
    })(h1);
  }
  words.forEach(function (w, i) {
    layer('Words / ' + (i + 1) + ' ' + w.textContent.replace(/\W/g, ''), [w], 0.9 + i * 0.12,
          { rotate: n(0, -20, 20, 0.1) });
  });

  (function tick() {
    // the mouse, eased, re-applied to every layer each frame
    px += (mx - px) * depthV.ease; py += (my - py) * depthV.ease;
    layers.forEach(function (L) { if (L.v) apply(L); });
    requestAnimationFrame(tick);
  })();

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
