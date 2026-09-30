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
    fov: n(58, 30, 90, 0.5)           // lens: 30 long and flat, 80 wide and fast
  });
  flight.onValuesChange(function (v) {
    M.speed = v.speed; M.push = v.push; M.camX = v.camX; M.camY = v.camY; M.roll = v.roll; M.fov = v.fov;
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

  // The words: each layer can fade, rise, blur and scale, on its own keyframes
  function layer(name, sel) {
    var els = [].slice.call(document.querySelectorAll(sel));
    if (!els.length) return;
    var o = sheet.object('Text / ' + name, {
      opacity: n(1, 0, 1, 0.01),
      y: n(0, -120, 120, 1),          // px, + = lower
      blur: n(0, 0, 24, 0.2),         // px
      scale: n(1, 0.8, 1.3, 0.005),
      tracking: n(0, -0.05, 0.3, 0.002)   // letter-spacing, em
    });
    o.onValuesChange(function (v) {
      els.forEach(function (el) {
        el.style.opacity = v.opacity;
        el.style.transform = 'translateY(' + v.y.toFixed(1) + 'px) scale(' + v.scale.toFixed(3) + ')';
        el.style.filter = v.blur > 0.05 ? 'blur(' + v.blur.toFixed(1) + 'px)' : '';
        el.style.letterSpacing = Math.abs(v.tracking) > 0.0005 ? v.tracking.toFixed(3) + 'em' : '';
        el.style.transformOrigin = '0 50%';
        el.style.willChange = 'opacity, transform, filter';
      });
    });
  }
  layer('Logo', '.xx-hero__logo');
  layer('Eyebrow', '.xx-hero__eyebrow');
  layer('Headline', '.xx-hero h1');
  layer('Lede', '.xx-hero__leftlede');
  layer('Buttons', '.xx-cta-dock--home');
  layer('Right column', '.xx-hero__right');
  layer('Situations', '.xx-hero-dock');
  layer('Nav', '.xx-nav');

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
