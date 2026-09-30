/* X-ON-X hero, demo 9: the film with clouds flying across its cuts (Theatre.js).
 *
 * 01.10, after demo 8: «давай ще пограємось з демо де відео роблять», with the rule from the
 * same evening: the words never move, only the clouds do. Demo 5's film plays full screen;
 * demo 4's cloud field flies over the footage (under the copy), and at the cuts into and out
 * of the flight shots a cloud sweeps through the frame and tears open on the next shot.
 *
 * The timeline IS the film: while the film plays, the sequence position follows
 * video.currentTime every frame, so a keyframe at 7.72 s lands on the cut at 7.72 s. To scrub:
 * pause the film (the FILM button at the top), then drag the playhead and the
 * film shows the frame under it. Press space and Theatre leads, the film follows.
 *
 *   film-clouds.html          studio open
 *   film-clouds.html?play=1   as it would ship */
(function () {
  'use strict';
  if (!window.Theatre) return;
  var core = Theatre.core, studio = Theatre.studio, t = core.types;
  var playOnly = /[?&]play=1/.test(location.search);
  var root = document.documentElement;
  if (studio) { studio.initialize(); if (playOnly) studio.ui.hide(); else root.classList.add('xx-studio'); }
  if (playOnly) root.classList.add('xx-play');

  var project = core.getProject('X-ON-X film', window.xxFilmState ? { state: window.xxFilmState } : {});
  var sheet = project.sheet('Film');
  var M = window.xxMotion = {};
  function n(v, lo, hi, nudge) { return t.number(v, { range: [lo, hi], nudgeMultiplier: nudge || 1 }); }

  var flight = sheet.object('Flight', {
    speed: n(1, 0, 5, 0.05),          // × cruise: ramp it into a cut and the clouds rush at the lens
    push: n(0, -3000, 3000, 10),
    camX: n(0, -500, 500, 5),
    camY: n(0, -400, 400, 5),
    roll: n(0, -0.4, 0.4, 0.005),
    shake: n(0, 0, 1, 0.01)
  });
  flight.onValuesChange(function (v) {
    M.speed = v.speed; M.push = v.push; M.camX = v.camX; M.camY = v.camY; M.roll = v.roll; M.shake = v.shake;
  });

  var clouds = sheet.object('Clouds over the film', {
    amount: n(0.15, 0, 1, 0.01),      // how much of the cloud field shows over the footage
    lining: n(0.6, 0, 1.5, 0.02),
    billow: n(0.5, 0, 1.5, 0.02),
    haze: n(2600, 900, 2600, 10)
  });
  clouds.onValuesChange(function (v) {
    root.style.setProperty('--xx-cloud-o', v.amount.toFixed(3));
    M.off = v.amount < 0.005;
    M.rim = v.lining; M.billow = v.billow; M.haze = v.haze;
  });

  var film = document.querySelector('.xx-film');
  window.xxVeil(sheet, n, { parent: film, z: 3, name: 'Cloud wipe' });

  // ── the film is the clock ──
  var video = document.querySelector('.xx-film video');
  project.ready.then(function () {
    var seq = sheet.sequence, len = core.val(seq.pointer.length);
    window.xxSheet = sheet;
    // Start the film ourselves too: demo 5 starts it on window load, and a browser that
    // refuses (no gesture yet) gets another go on the first click, key or touch.
    var kick = function () { if (video.paused && !core.val(seq.pointer.playing)) video.play().catch(function () {}); };
    kick();
    ['pointerdown', 'keydown', 'touchstart'].forEach(function (ev) { window.addEventListener(ev, kick, { once: true, passive: true }); });
    (function sync() {
      // The film is the clock and nothing here ever seeks a playing film: an earlier version
      // told a dragged playhead from normal progress by comparing positions, and on a slow
      // frame rate ordinary progress looked like a drag, so it kept seeking the film back.
      if (core.val(seq.pointer.playing)) {
        // space in the studio: Theatre leads, the film follows
        if (Math.abs(video.currentTime - seq.position) > 0.25) video.currentTime = seq.position;
        if (video.paused) video.play().catch(function () {});
      } else if (!playOnly && video.paused) {
        // film paused, studio open: the playhead leads, so a drag shows the frame under it
        if (Math.abs(video.currentTime - seq.position) > 0.04 && !video.seeking) video.currentTime = seq.position;
      } else if (video.readyState >= 1) {
        seq.position = Math.min(video.currentTime, len);
      }
      requestAnimationFrame(sync);
    })();
  });
})();
