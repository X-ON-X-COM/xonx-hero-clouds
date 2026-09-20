/* X-ON-X hero, demo 4: a cloud field, after mrdoob's WebGL clouds.
 *
 * Iryna, 20.09: «структура хмар має бути як тут» — mrdoob.com/lab/javascript/webgl/clouds.
 * The structure there is the whole point. No sprite is a cloud. Eight thousand small, soft,
 * mostly transparent billboards are scattered down a long box, and a cloud is what a few
 * hundred of them add up to where they overlap; the camera flies down the box. Overlap is
 * what reads as volume, and a single cut-out or rendered cloud, however good, never will.
 *
 * Two canvases share one field: the back one draws everything beyond FRONT_DEPTH and sits
 * behind the hero text, the front one draws only what is nearer and sits in front of the
 * text and the buttons, thinned, so the clouds pass through the words (Oleg, 18.09) and the
 * words stay readable. A soft depth fade across the boundary keeps a puff that straddles it
 * from being cut in half.
 *
 * Knobs are the data-* attributes on the script tag, set by build_field.py. */
(function () {
  'use strict';
  var script = document.currentScript;
  var cfg = {
    count: +script.dataset.count || 5000,       // puffs across all clouds
    clouds: +script.dataset.clouds || 46,        // clouds in one box length
    length: 8000,           // the box the field fills, in world units; the loop is this long
    width: 760,             // sideways spread; clouds are placed by a gaussian, so most come near the line of flight
    puff: 140,              // big and soft: the puffs must overlap into one mass, not read one by one
    speed: +script.dataset.speed || 0.085,      // world units per millisecond. mrdoob flies at 0.03, which
                                                // is a crawl on a wide lens: at this speed a cloud on the far
                                                // edge reaches you in about 25 s, the tempo demo 3 had
    fov: 58,                // mrdoob's 30 is a long lens: it flattens the approach, and a cloud
                            // seems to slide past instead of coming at you. A wide lens is what
                            // makes flight feel like flight
    frontDepth: 700,        // puffs nearer than this draw on the front canvas
    fogNear: 300, fogFar: 2600,
    texture: script.dataset.texture,
    sky: script.dataset.sky || '#c9d5ea',
    seed: 20260920,
    // the tuning panel changes these live; `copy` in the panel prints them to bake in
    size: 1.0,              // cloud radius multiplier
    shade: 0.85,            // 0 = no shade at all, 1 = the shade colour below, >1 deeper
    warmth: 0.35,           // 0 = neutral white crown, 1 = the palette's warm cream
    lit: 0xfbf8f3, shadeColor: 0xc4cad6   // the shade is light too: a cumulus in shade is still a white thing
  };
  try { Object.assign(cfg, JSON.parse(localStorage.getItem('xx-field') || '{}')); } catch (e) {}
  if (!window.WebGLRenderingContext) return;

  var root = document.documentElement;
  var back = document.getElementById('xx-gl-back');
  var front = document.getElementById('xx-gl-front');
  var mouseX = 0, mouseY = 0, start = Date.now(), paused = false, frozen = 0, rebuiltWhilePaused = false;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // one seeded field, so the two canvases and every reload agree
  function rng(seed) { return function () { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; }; }

  var vs = [
    'varying vec2 vUv; varying vec3 vTint;',
    'void main() {',
    '  vUv = uv;',
    '  #ifdef USE_INSTANCING_COLOR',
    '  vTint = instanceColor;',
    '  #else',
    '  vTint = vec3(1.0);',
    '  #endif',
    '  gl_Position = projectionMatrix * modelViewMatrix * instanceMatrix * vec4(position, 1.0);',
    '}'].join('\n');
  var fs = [
    'uniform sampler2D map; uniform vec3 fogColor; uniform float fogNear; uniform float fogFar;',
    'uniform float splitNear; uniform float splitFar; uniform float tint;',
    'varying vec2 vUv; varying vec3 vTint;',
    'void main() {',
    '  float depth = gl_FragCoord.z / gl_FragCoord.w;',
    '  vec4 c = texture2D(map, vUv);',
    '  c.rgb *= vTint;',                                     // per-puff shade: where it sits in its cloud
    '  c.a *= pow(gl_FragCoord.z, 20.0);',                 // the puff at the lens goes to vapour
    '  c.a *= smoothstep(70.0, 360.0, depth);',           // and a cloud you are inside dissolves instead of filling the frame
    '  c.a *= smoothstep(splitNear, splitFar, depth);',    // which canvas this puff belongs to
    '  float f = smoothstep(fogNear, fogFar, depth);',
    '  c = mix(c, vec4(fogColor, c.a), f);',
    '  gl_FragColor = vec4(c.rgb * c.a, c.a);',              // premultiplied, see makeLayer
    '}'].join('\n');

  function makeLayer(canvas, splitNear, splitFar, tex) {
    // A transparent canvas over the page has to be premultiplied, or every soft edge goes
    // dark: with straight alpha the first puff over the cleared (0,0,0,0) framebuffer lands
    // as colour * alpha, and the browser then reads that darkened colour as if it were
    // straight. The shader outputs premultiplied colour and the blend is One / OneMinusSrcAlpha.
    var renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: false, alpha: true, premultipliedAlpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    renderer.setClearColor(0x000000, 0);
    var scene = new THREE.Scene();
    var camera = new THREE.PerspectiveCamera(cfg.fov, 1, 1, cfg.fogFar);
    var mat = new THREE.ShaderMaterial({
      uniforms: {
        map: { value: tex },
        fogColor: { value: new THREE.Color(cfg.sky) },
        fogNear: { value: cfg.fogNear }, fogFar: { value: cfg.fogFar },
        splitNear: { value: splitNear }, splitFar: { value: splitFar },
        tint: { value: 1.0 }
      },
      vertexShader: vs, fragmentShader: fs,
      depthWrite: false, depthTest: true, transparent: true,
      blending: THREE.CustomBlending, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor,
      blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneMinusSrcAlphaFactor
    });
    var geo = new THREE.PlaneGeometry(cfg.puff, cfg.puff);
    var L = { renderer: renderer, scene: scene, camera: camera, mat: mat, mesh: null };
    L.build = function () { buildField(L, geo); };
    L.build();
    return L;
  }

  function buildField(L, geo) {
    if (L.mesh) { L.scene.remove(L.mesh); L.mesh.dispose(); }
    var mat = L.mat, scene = L.scene;
    // The field is demo 3's: separate clouds, each with a place and a size in three
    // dimensions, scattered down the box the camera flies through, so they come at the
    // viewer, diverge, and pass through the text as before. What changed is only what a
    // cloud is made of. It is not one sprite any more: it is a cluster of soft, mostly
    // transparent puffs that overlap, and the overlap is what reads as volume. That is
    // the structure of mrdoob's clouds, kept; his flat deck below the camera is not.
    var r = rng(cfg.seed), m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3();
    var z = new THREE.Vector3(0, 0, 1);
    function gauss() { return (r() + r() + r() - 1.5) * 1.15; }
    var clouds = [];
    for (var c = 0; c < cfg.clouds; c++) {
      var R = (120 + r() * r() * 400) * cfg.size;           // radius, small clouds common
      // a cumulus is not one blob: a flat base with two to four crowns piled on it, the
      // cauliflower silhouette. Each crown is a smaller sphere set into the upper half.
      var lobes = [], nl = 2 + Math.floor(r() * 3);
      for (var l = 0; l < nl; l++) {
        lobes.push({ x: (r() - 0.5) * 1.0, y: 0.20 + r() * 0.45, z: (r() - 0.5) * 0.6, s: 0.32 + r() * 0.30 });
      }
      clouds.push({
        x: gauss() * cfg.width * 1.05,                        // most near the line of flight, a few wide
        y: gauss() * 215 - 20,                                // at eye level: that is where the text is
        z: r() * cfg.length,
        R: R, lobes: lobes,
        n: Math.round(cfg.count * (R * R) / (cfg.clouds * 300 * 300))
      });
    }
    var total = 0;
    clouds.forEach(function (cl) { total += cl.n; });
    var mesh = new THREE.InstancedMesh(geo, mat, total * 2);
    // Shading is per puff, not per pixel: a cumulus is lit on top and on the sunward
    // flank and sits in blue-grey shade underneath. Each puff is tinted by where it is
    // in its cloud, and the overlap blends those tints into a graded volume.
    var white = new THREE.Color(0xf7f7f5), cream = new THREE.Color(cfg.lit);
    var lit = white.clone().lerp(cream, cfg.warmth);
    var shade = lit.clone().lerp(new THREE.Color(cfg.shadeColor), Math.min(1.6, cfg.shade));
    var tintC = new THREE.Color();
    var i = 0;
    clouds.forEach(function (cl) {
      for (var k = 0; k < cl.n; k++) {
        // a cumulus: wider than tall, flat underneath, lumpy on top, densest in the middle.
        // A third of the puffs go to the crowns, the rest to the body.
        var gx, gy, gz;
        if (r() < 0.25) {
          var lb = cl.lobes[Math.floor(r() * cl.lobes.length)];
          gx = lb.x + gauss() * 0.5 * lb.s; gy = lb.y + gauss() * 0.5 * lb.s; gz = lb.z + gauss() * 0.5 * lb.s;
        } else {
          gx = gauss() * 0.62; gy = gauss(); gz = gauss() * 0.45;
          gy = gy < 0 ? gy * 0.28 : gy * 0.45;
        }
        var px = cl.x + gx * cl.R, py = cl.y + gy * cl.R, pz = cl.z + gz * cl.R;
        var d = Math.sqrt(gx * gx + gy * gy + gz * gz);
        var sc = (0.7 + r() * 0.8) * (cl.R / 200) * (d < 0.8 ? 1.2 : 1.0);
        q.setFromAxisAngle(z, r() * Math.PI); s.set(sc, sc, 1);
        p.set(px, py, pz); m.compose(p, q, s); mesh.setMatrixAt(i, m);
        p.set(px, py, pz - cfg.length); m.compose(p, q, s); mesh.setMatrixAt(total + i, m);
        // 0 = deep in the belly, 1 = crown in the sun; the sun is up and a little to the right
        var t = 0.62 + gy * 0.45 + gx * 0.12 - Math.max(0, 0.8 - d) * 0.22;   // lit by default, shade only underneath
        tintC.copy(shade).lerp(lit, Math.min(1, Math.max(0, t)));
        mesh.setColorAt(i, tintC); mesh.setColorAt(total + i, tintC);
        i++;
      }
    });
    mesh.renderOrder = 1;
    scene.add(mesh);
    L.mesh = mesh;
  }

  /* ── the journey: Oleg's brief from the 18.09 call ──────────────────────────
     "летиш вперед, і по мірі польоту з'являються ситуації, з якими стикається
     фаундер". The situations are the shots of the film, each on a card that lives
     in the same space as the clouds: it comes out of the distance, passes beside
     the camera and is gone, with cloud in front of it and behind it. Cards write
     depth and the puffs test it, so a puff nearer than the card draws over it and
     one behind it does not. Twelve cards along the box, one every ~600 units, so
     at flight speed a situation arrives every six or seven seconds.
     Enabled by data-journey on the script tag: a JSON list of clip urls.       */
  var journey = null;
  try { journey = script.dataset.journey ? JSON.parse(script.dataset.journey) : null; } catch (e) {}

  function makeJourney(L) {
    if (!journey || !journey.length) return;
    var cw = 400, ch = cw * 9 / 16, gap = cfg.length / journey.length;
    var geo = new THREE.PlaneGeometry(cw, ch);
    var r = rng(cfg.seed + 7);
    var fs2 = [
      'uniform sampler2D map; uniform float fogNear; uniform float fogFar; uniform vec3 fogColor; uniform float alpha;',
      'varying vec2 vUv;',
      'void main() {',
      '  vec4 c = texture2D(map, vUv);',
      // rounded corners and a soft edge, in uv space
      '  vec2 p = abs(vUv - 0.5) - vec2(0.5 - 0.035, 0.5 - 0.062);',
      '  float d = length(max(p, 0.0)) - 0.035;',
      '  float edge = 1.0 - smoothstep(-0.004, 0.004, d);',
      '  float depth = gl_FragCoord.z / gl_FragCoord.w;',
      '  float f = smoothstep(fogNear, fogFar, depth);',
      '  c.rgb = mix(c.rgb, fogColor, f * 0.85);',
      '  float a = edge * alpha * (1.0 - f * 0.9);',
      '  gl_FragColor = vec4(c.rgb * a, a);',
      '}'].join('\n');
    L.cards = journey.map(function (url, k) {
      var video = document.createElement('video');
      video.src = url; video.muted = true; video.loop = true; video.playsInline = true; video.preload = 'auto';
      video.setAttribute('muted', ''); video.setAttribute('playsinline', '');
      var tex = new THREE.VideoTexture(video); tex.minFilter = THREE.LinearFilter; tex.magFilter = THREE.LinearFilter;
      var mat = new THREE.ShaderMaterial({
        uniforms: { map: { value: tex }, fogNear: { value: 900 }, fogFar: { value: cfg.fogFar }, fogColor: { value: new THREE.Color(cfg.sky) }, alpha: { value: 1 } },
        vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
        fragmentShader: fs2, transparent: true, depthWrite: true, depthTest: true,
        blending: THREE.CustomBlending, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor,
        blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneMinusSrcAlphaFactor
      });
      var mesh = new THREE.Mesh(geo, mat);
      // beside the line of flight, never on it: the copy sits bottom left, so the cards
      // favour the right and the upper half, alternating a little so the flight has rhythm
      // well off the line of flight, mostly right and up, so a card passes beside the copy
      // rather than over it, and never gets to fill the frame before it fades
      var side = (k % 2 === 0) ? 1 : -1;
      mesh.position.set(side * (300 + r() * 220) + 160, 110 + r() * 200 - (k % 3 === 2 ? 240 : 0), (k + 0.5) * gap);
      mesh.userData = { video: video, z: mesh.position.z };
      L.scene.add(mesh);
      return mesh;
    });
  }

  function updateJourney(L, camZ) {
    if (!L.cards) return;
    L.cards.forEach(function (m) {
      // the card, or its copy one box back, whichever is ahead of the camera and nearest
      var z = m.userData.z, dz = camZ - z;
      if (dz < -cfg.length / 2) dz += cfg.length;            // wrap: treat the far copy as this one
      if (dz > cfg.length / 2) dz -= cfg.length;
      m.position.z = camZ - dz;
      var ahead = dz > 0 && dz < cfg.fogFar;
      var near = Math.min(1, Math.max(0, (dz - 260) / 420));  // gone well before it reaches the lens
      m.material.uniforms.alpha.value = ahead ? near : 0;
      m.visible = ahead;
      var v = m.userData.video;
      if (ahead && dz < cfg.fogFar * 0.8) { if (v.paused) v.play().catch(function () {}); }
      else if (!v.paused) v.pause();
    });
  }

  var loader = new THREE.TextureLoader();
  loader.load(cfg.texture, function (tex) {
    tex.minFilter = THREE.LinearMipMapLinearFilter; tex.magFilter = THREE.LinearFilter;
    var layers = [
      makeLayer(back, cfg.frontDepth - 160, cfg.frontDepth, tex),
      makeLayer(front, cfg.frontDepth, cfg.frontDepth - 160, tex)
    ];
    makeJourney(layers[0]);
    function resize() {
      var w = window.innerWidth, h = window.innerHeight;
      layers.forEach(function (L) {
        L.camera.aspect = w / h; L.camera.updateProjectionMatrix(); L.renderer.setSize(w, h, false);
      });
    }
    function frame() {
      var t = paused || reduce ? frozen : (Date.now() - start);
      var tempo = parseFloat(getComputedStyle(root).getPropertyValue('--xx-tempo')) || 1;
      var pos = (t * cfg.speed / tempo) % cfg.length;
      if (paused && !rebuiltWhilePaused) { rebuiltWhilePaused = false; }
      layers.forEach(function (L) {
        L.camera.position.x += (mouseX - L.camera.position.x) * 0.01;
        L.camera.position.y += (-mouseY - L.camera.position.y) * 0.01;
        L.camera.position.z = -pos + cfg.length;
        updateJourney(L, L.camera.position.z);
        L.renderer.render(L.scene, L.camera);
      });
      if (!reduce) requestAnimationFrame(frame);
    }
    resize();
    window.addEventListener('resize', resize);
    document.addEventListener('mousemove', function (e) {
      mouseX = (e.clientX - window.innerWidth / 2) * 0.06;   // a hint of parallax, not a sideways drift
      mouseY = (e.clientY - window.innerHeight / 2) * 0.04;
    });
    // `motion: off` in the corner panel freezes the flight where it is
    var obs = new MutationObserver(function () {
      var still = root.classList.contains('xx-still');
      if (still && !paused) { frozen = Date.now() - start; paused = true; }
      if (!still && paused) { start = Date.now() - frozen; paused = false; }
    });
    obs.observe(root, { attributes: true, attributeFilter: ['class'] });
    frozen = 9000;                          // reduced motion: one frame, a way into the field
    frame();

    // the tuning panel talks to this
    window.xxField = {
      cfg: cfg,
      set: function (k, v) {
        cfg[k] = v;
        if (k === 'clouds' || k === 'count' || k === 'size' || k === 'shade' || k === 'warmth') {
          layers.forEach(function (L) { L.build(); });
        }
        try { localStorage.setItem('xx-field', JSON.stringify({
          clouds: cfg.clouds, count: cfg.count, size: cfg.size, speed: cfg.speed, shade: cfg.shade, warmth: cfg.warmth })); } catch (e) {}
      },
      reset: function () { try { localStorage.removeItem('xx-field'); } catch (e) {} location.reload(); }
    };
  });
})();
