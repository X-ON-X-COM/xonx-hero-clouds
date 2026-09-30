/* X-ON-X hero, demo 9: the film with clouds flying across its cuts (Theatre.js).
 *
 * 01.10, after demo 8: «давай ще пограємось з демо де відео роблять», with the rule from the
 * same evening: the words never move, only the clouds do. Demo 5's film plays full screen;
 * demo 4's cloud field flies over the footage (under the copy), and at the cuts into and out
 * of the flight shots a cloud sweeps through the frame and tears open on the next shot.
 *
 * The timeline IS the film: the sequence position follows video.currentTime every frame, so
 * the cuts sit where they are in the cut and a keyframe at 7.72 s lands on the cut at 7.72 s.
 * Scrub the playhead in the studio and the film seeks with it; press space and Theatre leads,
 * the film follows.
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
    M.rim = v.lining; M.billow = v.billow; M.haze = v.haze;
  });

  var film = document.querySelector('.xx-film');
  window.xxVeil(sheet, n, { parent: film, z: 3, name: 'Cloud wipe' });

  // ── the film is the clock ──
  var video = document.querySelector('.xx-film video');
  project.ready.then(function () {
    var seq = sheet.sequence, lastSet = -1;
    window.xxSheet = sheet;
    (function sync() {
      var theatrePlaying = core.val(seq.pointer.playing);
      if (theatrePlaying) {
        // space in the studio: Theatre leads, the film follows
        if (Math.abs(video.currentTime - seq.position) > 0.15) video.currentTime = seq.position;
        if (video.paused) video.play().catch(function () {});
      } else if (lastSet >= 0 && Math.abs(seq.position - lastSet) > 0.05) {
        // the playhead was dragged: seek the film there
        video.currentTime = seq.position;
        lastSet = seq.position;
      } else if (video.readyState >= 1) {
        seq.position = Math.min(video.currentTime, core.val(seq.pointer.length));
        lastSet = seq.position;
      }
      requestAnimationFrame(sync);
    })();
  });
})();
