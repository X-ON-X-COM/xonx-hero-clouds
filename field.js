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
    fogAlpha: +script.dataset.fogalpha || 0,   // demo 9, over a film: far clouds thin to nothing instead of to the sky colour
    seed: 20260920,
    // the tuning panel changes these live; `copy` in the panel prints them to bake in
    size: 1.0,              // cloud radius multiplier
    shade: 0.85,            // 0 = no shade at all, 1 = the shade colour below, >1 deeper
    warmth: 0.35,           // 0 = neutral white crown, 1 = the palette's warm cream
    lit: 0xfbf8f3, shadeColor: 0xc4cad6,  // the shade is light too: a cumulus in shade is still a white thing
    // 28.09, three things a photographed cumulus has and ours did not. Each is a slider;
    // at 0 it is exactly the approved 20.09 build.
    light: 1.0,             // 0 = tint by where a puff sits (20.09), 1 = tint by how much cloud lies between it and the sun
    rim: 0.6,               // silver lining: the thin sunward edge glows when you look towards the sun
    billow: 0.5,            // the puffs drift, turn and breathe, so a cloud churns instead of flying past as a stone
    sun: [0.30, 0.55, -0.78] // up, right and ahead, where the sky's warm glow sits (--cx 62%, --cy 46%)
  };
  try { Object.assign(cfg, JSON.parse(localStorage.getItem('xx-field') || '{}')); } catch (e) {}
  if (!window.WebGLRenderingContext) return;

  var root = document.documentElement;
  var back = document.getElementById('xx-gl-back');
  var front = document.getElementById('xx-gl-front');
  var mouseX = 0, mouseY = 0, start = Date.now(), paused = false, frozen = 0, rebuiltWhilePaused = false;
  // demo 8: a Theatre.js timeline writes into window.xxMotion (speed, push, camera, fog...).
  // Without it every value below falls back to what demo 4 does on its own.
  var flight = 0, lastNow = 0;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  // 01.10 «дуже підтуплює»: soft clouds do not need retina pixels. Start at 0.8 of CSS pixels
  // (×1.5 before on a retina screen: 3.5× the fill), and let the frame time move it between
  // 0.45 and the start value: a slow machine gets softer clouds instead of a stutter.
  var quality = { max: Math.min(+script.dataset.dpr || 0.8, window.devicePixelRatio || 1), scale: 0, slow: 0, fast: 0, ema: 16.7, last: 0 };
  quality.scale = quality.max;

  // one seeded field, so the two canvases and every reload agree
  function rng(seed) { return function () { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; }; }

  var vs = [
    'attribute vec4 aRnd;',                                  // phase, spin, drift amplitude, how much of an edge this puff is
    'uniform float time; uniform float billow; uniform float rim; uniform vec3 sunDir; uniform float bandNear; uniform float bandFar;',
    'varying vec2 vUv; varying vec3 vTint; varying float vRim;',
    'void main() {',
    '  vUv = uv;',
    '  #ifdef USE_INSTANCING_COLOR',
    '  vTint = instanceColor;',
    '  #else',
    '  vTint = vec3(1.0);',
    '  #endif',
    '  vec3 pos = position;',
    // billow: each puff turns slowly on its own axis and breathes, and drifts a little
    // around its place, so the overlap keeps changing and the mass churns
    '  float ph = aRnd.x;',
    '  float a = billow * aRnd.y * time * 0.00005;',
    '  pos.xy = mat2(cos(a), sin(a), -sin(a), cos(a)) * pos.xy;',
    '  pos.xy *= 1.0 + billow * 0.09 * sin(time * 0.00023 + ph);',
    '  vec4 wp = modelMatrix * instanceMatrix * vec4(pos, 1.0);',
    '  wp.xyz += billow * aRnd.z * vec3(sin(time * 0.00013 + ph * 1.7), sin(time * 0.00017 + ph * 2.3) * 0.7, sin(time * 0.00011 + ph * 0.9));',
    // silver lining: forward scattering, strongest looking straight at the sun, on the
    // thin sunward edge of a cloud only (aRnd.w, worked out when the field is built)
    // 01.10 speed: a puff outside this canvas\'s depth band never reaches the rasteriser. Before,
    // both canvases drew all 18 000 quads and hid the other half in the fragment shader.
    '  float vd = -(viewMatrix * wp).z;',
    '  if (vd < bandNear || vd > bandFar) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); vUv = vec2(0.0); vTint = vec3(0.0); vRim = 0.0; return; }',
    '  vec3 V = normalize(wp.xyz - cameraPosition);',
    '  float ct = max(dot(V, sunDir), 0.0);',
    '  vRim = rim * aRnd.w * (0.2 + 0.8 * pow(ct, 4.0));',
    '  gl_Position = projectionMatrix * viewMatrix * wp;',
    '}'].join('\n');
  var fs = [
    'uniform sampler2D map; uniform vec3 fogColor; uniform float fogNear; uniform float fogFar;',
    'uniform float splitNear; uniform float splitFar; uniform float tint; uniform float fogAlpha;',
    'varying vec2 vUv; varying vec3 vTint; varying float vRim;',
    'void main() {',
    '  float depth = gl_FragCoord.z / gl_FragCoord.w;',
    '  vec4 c = texture2D(map, vUv);',
    '  c.rgb *= vTint;',                                     // per-puff shade: how much cloud lies between it and the sun
    '  c.rgb = mix(c.rgb, vec3(1.0, 0.985, 0.955), clamp(vRim * (1.15 - c.a), 0.0, 0.9));',   // the lining glows where the puff is thin
    '  c.a *= pow(gl_FragCoord.z, 20.0);',                 // the puff at the lens goes to vapour
    '  c.a *= smoothstep(70.0, 360.0, depth);',           // and a cloud you are inside dissolves instead of filling the frame
    '  c.a *= smoothstep(splitNear, splitFar, depth);',    // which canvas this puff belongs to
    '  float f = smoothstep(fogNear, fogFar, depth);',
    '  c = mix(c, vec4(fogColor, c.a), f * (1.0 - fogAlpha));',
    '  c.a *= 1.0 - f * fogAlpha;',
    '  gl_FragColor = vec4(c.rgb * c.a, c.a);',              // premultiplied, see makeLayer
    '}'].join('\n');

  function makeLayer(canvas, splitNear, splitFar, tex) {
    // A transparent canvas over the page has to be premultiplied, or every soft edge goes
    // dark: with straight alpha the first puff over the cleared (0,0,0,0) framebuffer lands
    // as colour * alpha, and the browser then reads that darkened colour as if it were
    // straight. The shader outputs premultiplied colour and the blend is One / OneMinusSrcAlpha.
    var renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: false, alpha: true, premultipliedAlpha: true });
    renderer.setPixelRatio(quality.scale);
    renderer.setClearColor(0x000000, 0);
    var scene = new THREE.Scene();
    var camera = new THREE.PerspectiveCamera(cfg.fov, 1, 1, cfg.fogFar);
    var mat = new THREE.ShaderMaterial({
      uniforms: {
        map: { value: tex },
        fogColor: { value: new THREE.Color(cfg.sky) },
        fogNear: { value: cfg.fogNear }, fogFar: { value: cfg.fogFar },
        splitNear: { value: splitNear }, splitFar: { value: splitFar },
        bandNear: { value: splitNear < splitFar ? splitNear - 10 : 0 }, bandFar: { value: splitNear < splitFar ? 1e6 : splitNear + 10 },
        tint: { value: 1.0 }, fogAlpha: { value: cfg.fogAlpha },
        time: { value: 0 }, billow: { value: cfg.billow }, rim: { value: cfg.rim },
        sunDir: { value: new THREE.Vector3().fromArray(cfg.sun).normalize() }
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
    // new randoms come from their own stream: the field above must stay exactly as approved
    var r2 = rng(cfg.seed + 11);
    var rnd = new Float32Array(total * 2 * 4);
    var sun = new THREE.Vector3().fromArray(cfg.sun).normalize();
    var i = 0;
    clouds.forEach(function (cl) {
      // First pass: where every puff of this cloud goes, in cloud units (radius = 1).
      // Second: splat them into a coarse density grid and blur it. Third: from every
      // puff, march towards the sun through the grid; the optical depth on the way is
      // how much cloud shades it. That is what puts a crease between two crowns and
      // lets one crown shadow the next, which a tint by position never can.
      var P = [], k;
      for (k = 0; k < cl.n; k++) {
        var gx, gy, gz;
        if (r() < 0.25) {
          var lb = cl.lobes[Math.floor(r() * cl.lobes.length)];
          gx = lb.x + gauss() * 0.5 * lb.s; gy = lb.y + gauss() * 0.5 * lb.s; gz = lb.z + gauss() * 0.5 * lb.s;
        } else {
          gx = gauss() * 0.62; gy = gauss(); gz = gauss() * 0.45;
          gy = gy < 0 ? gy * 0.28 : gy * 0.45;
        }
        var d = Math.sqrt(gx * gx + gy * gy + gz * gz);
        var sc = (0.7 + r() * 0.8) * (cl.R / 200) * (d < 0.8 ? 1.2 : 1.0);
        var rot = r() * Math.PI;
        P.push([gx, gy, gz, d, sc, rot]);
      }
      var trans = lightCloud(P, cl.R, sun);
      for (k = 0; k < cl.n; k++) {
        var Q = P[k];
        // a cumulus: wider than tall, flat underneath, lumpy on top, densest in the middle.
        // A third of the puffs go to the crowns, the rest to the body.
        gx = Q[0]; gy = Q[1]; gz = Q[2]; d = Q[3]; sc = Q[4];
        var px = cl.x + gx * cl.R, py = cl.y + gy * cl.R, pz = cl.z + gz * cl.R;
        q.setFromAxisAngle(z, Q[5]); s.set(sc, sc, 1);
        p.set(px, py, pz); m.compose(p, q, s); mesh.setMatrixAt(i, m);
        p.set(px, py, pz - cfg.length); m.compose(p, q, s); mesh.setMatrixAt(total + i, m);
        // 0 = deep in the belly, 1 = crown in the sun; the sun is up and a little to the right
        var t0 = 0.62 + gy * 0.45 + gx * 0.12 - Math.max(0, 0.8 - d) * 0.22;   // 20.09: lit by default, shade only underneath
        var t1 = 0.46 + 0.54 * trans[k] + 0.10 * gy;                          // 28.09: shade = cloud between the puff and the sun, plus skylight on top
        var t = t0 + (t1 - t0) * cfg.light;
        tintC.copy(shade).lerp(lit, Math.min(1, Math.max(0, t)));
        mesh.setColorAt(i, tintC); mesh.setColorAt(total + i, tintC);
        // an edge puff: out on the silhouette as seen from behind the cloud, and in the sun
        var ex = Math.sqrt(gx * gx / (0.62 * 0.62) + (gy > 0 ? gy * gy / 0.2 : gy * gy / 0.08));
        var edge = Math.min(1, Math.max(0, (ex - 0.7) / 0.6)) * trans[k];
        var o = i * 4, o2 = (total + i) * 4;
        rnd[o] = rnd[o2] = r2() * 6.2832;                 // phase
        rnd[o + 1] = rnd[o2 + 1] = r2() * 2 - 1;          // spin, either way
        rnd[o + 2] = rnd[o2 + 2] = cl.R * (0.03 + r2() * 0.05);   // drift, in proportion to the cloud
        rnd[o + 3] = rnd[o2 + 3] = edge;
        i++;
      }
    });
    geo.setAttribute('aRnd', new THREE.InstancedBufferAttribute(rnd, 4));
    mesh.renderOrder = 1;
    scene.add(mesh);
    L.mesh = mesh;
  }

  // How much of the sun reaches each puff of one cloud, 0..1. Cloud units: radius 1.
  var GX = 24, GY = 16, GZ = 18, X0 = -1.8, X1 = 1.8, Y0 = -0.9, Y1 = 1.5, Z0 = -1.3, Z1 = 1.3;
  var grid = new Float32Array(GX * GY * GZ), tmp = new Float32Array(GX * GY * GZ);
  function lightCloud(P, R, sun) {
    grid.fill(0);
    var cx = (X1 - X0) / GX, cy = (Y1 - Y0) / GY, cz = (Z1 - Z0) / GZ;
    function idx(x, y, z) { return (z * GY + y) * GX + x; }
    P.forEach(function (Q) {
      var x = Math.floor((Q[0] - X0) / cx), y = Math.floor((Q[1] - Y0) / cy), z = Math.floor((Q[2] - Z0) / cz);
      if (x < 0 || y < 0 || z < 0 || x >= GX || y >= GY || z >= GZ) return;
      grid[idx(x, y, z)] += Q[4] * Q[4];                  // a big puff is more cloud
    });
    // blur twice along each axis: a puff is a soft ball, not a point
    for (var pass = 0; pass < 2; pass++) {
      [[1, 0, 0], [0, 1, 0], [0, 0, 1]].forEach(function (a) {
        for (var z = 0; z < GZ; z++) for (var y = 0; y < GY; y++) for (var x = 0; x < GX; x++) {
          var v = grid[idx(x, y, z)] * 2, n = 2;
          var xa = x - a[0], ya = y - a[1], za = z - a[2], xb = x + a[0], yb = y + a[1], zb = z + a[2];
          if (xa >= 0 && ya >= 0 && za >= 0) { v += grid[idx(xa, ya, za)]; n++; }
          if (xb < GX && yb < GY && zb < GZ) { v += grid[idx(xb, yb, zb)]; n++; }
          tmp[idx(x, y, z)] = v / n;
        }
        grid.set(tmp);
      });
    }
    // normalise by the cloud's own mean density, so the shading does not depend on how
    // many puffs it got: optical depth 1 = one cloud-radius of average cloud
    var sum = 0, cnt = 0;
    for (var j = 0; j < grid.length; j++) if (grid[j] > 1e-6) { sum += grid[j]; cnt++; }
    var mean = cnt ? sum / cnt : 1, K = 1.6, h = 0.09;
    return P.map(function (Q) {
      var od = 0, px = Q[0], py = Q[1], pz = Q[2];
      for (var st = 1; st <= 18; st++) {
        var x = Math.floor((px + sun.x * h * st - X0) / cx), y = Math.floor((py + sun.y * h * st - Y0) / cy), z = Math.floor((pz + sun.z * h * st - Z0) / cz);
        if (x < 0 || y < 0 || z < 0 || x >= GX || y >= GY || z >= GZ) break;
        od += grid[idx(x, y, z)] / mean * h;
      }
      return Math.exp(-K * od);
    });
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
    var cw = 420, ch = cw * 9 / 16, gap = cfg.length / journey.length;
    var geo = new THREE.PlaneGeometry(cw, ch);
    var r = rng(cfg.seed + 7);
    // Not a card. A hard rectangle in a sky is a hard rectangle in a sky, whatever is on it.
    // The shot sits inside a soft oval whose edge is feathered and slightly hazed, so it
    // surfaces out of the cloud and dissolves back into it, a memory rather than a screen.
    var fs2 = [
      'uniform sampler2D map; uniform float fogNear; uniform float fogFar; uniform vec3 fogColor; uniform float alpha;',
      'varying vec2 vUv;',
      'void main() {',
      '  vec4 c = texture2D(map, vUv);',
      '  vec2 q = (vUv - 0.5) * vec2(1.0, 1.35);',
      '  float rr = length(q) * 2.0;',
      '  float edge = 1.0 - smoothstep(0.62, 1.0, rr);',        // the oval, feathered over its outer third
      '  float depth = gl_FragCoord.z / gl_FragCoord.w;',
      '  float f = smoothstep(fogNear, fogFar, depth);',
      '  c.rgb = mix(c.rgb, fogColor, f * 0.85 + (1.0 - edge) * 0.35);',
      '  float a = edge * alpha * (1.0 - f * 0.9);',
      '  gl_FragColor = vec4(c.rgb * a, a);',
      '}'].join('\n');
    // the videos live in the page, hidden: a detached <video> plays in Chrome and not in
    // Safari, and a VideoTexture with no frame is a grey rectangle
    var pen = document.getElementById('xx-journey-pen');
    if (!pen) {
      pen = document.createElement('div'); pen.id = 'xx-journey-pen';
      pen.style.cssText = 'position:fixed;left:0;top:0;width:2px;height:2px;overflow:hidden;opacity:0.01;pointer-events:none;z-index:-1';
      document.body.appendChild(pen);
    }
    L.cards = journey.map(function (url, k) {
      var video = document.createElement('video');
      video.muted = true; video.loop = true; video.playsInline = true; video.autoplay = true; video.preload = 'auto';
      video.setAttribute('muted', ''); video.setAttribute('playsinline', ''); video.setAttribute('autoplay', ''); video.setAttribute('loop', '');
      video.src = url; video.width = 64; video.height = 36;
      pen.appendChild(video);
      video.load();
      var tex = new THREE.VideoTexture(video); tex.minFilter = THREE.LinearFilter; tex.magFilter = THREE.LinearFilter;
      var mat = new THREE.ShaderMaterial({
        uniforms: { map: { value: tex }, fogNear: { value: 900 }, fogFar: { value: cfg.fogFar }, fogColor: { value: new THREE.Color(cfg.sky) }, alpha: { value: 0 } },
        vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
        fragmentShader: fs2, transparent: true, depthWrite: true, depthTest: true,
        blending: THREE.CustomBlending, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor,
        blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneMinusSrcAlphaFactor
      });
      var mesh = new THREE.Mesh(geo, mat);
      // to the right of the line of flight and above it, always: the copy is bottom left,
      // and the shots must surface beside it, never across it
      mesh.position.set(330 + r() * 260, 90 + r() * 220, (k + 0.5) * gap);
      mesh.userData = { video: video, z: mesh.position.z };
      L.scene.add(mesh);
      return mesh;
    });
    // browsers that want a gesture before any playback: the first one starts them all
    var kick = function () { L.cards.forEach(function (m) { m.userData.video.play().catch(function () {}); }); };
    ['pointerdown', 'touchstart', 'keydown', 'scroll'].forEach(function (ev) { window.addEventListener(ev, kick, { once: true, passive: true }); });
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
      var near = Math.min(1, Math.max(0, (dz - 420) / 520));  // dissolves well before it reaches the lens
      var far = Math.min(1, Math.max(0, (cfg.fogFar * 0.85 - dz) / 500));  // and surfaces out of the haze
      var v = m.userData.video;
      var hasFrame = v.readyState >= 2;                       // no frame yet = nothing to show, not a grey plate
      m.material.uniforms.alpha.value = (ahead && hasFrame) ? near * far : 0;
      m.visible = ahead && hasFrame;
      if (ahead && dz < cfg.fogFar * 0.9) { if (v.paused) v.play().catch(function () {}); }
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
      // window.xxTime, when set, pins the flight to that millisecond: the film's cloud
      // cutaways are captured this way, one frame at a time, deterministic
      var t = (typeof window.xxTime === 'number') ? window.xxTime : (paused || reduce ? frozen : (Date.now() - start));
      // reading a computed style every frame forces a style recalc: once a second is plenty
      if (!frame.n || frame.n % 60 === 0) frame.tempo = parseFloat(getComputedStyle(root).getPropertyValue('--xx-tempo')) || 1;
      frame.n = (frame.n || 0) + 1;
      var tempo = frame.tempo;
      // adaptive resolution from the frame time
      var pn = performance.now();
      if (quality.last) {
        quality.ema += (Math.min(100, pn - quality.last) - quality.ema) * 0.05;
        if (quality.ema > 22) quality.slow++; else quality.slow = 0;
        if (quality.ema < 14) quality.fast++; else quality.fast = 0;
        var ns = quality.scale;
        if (quality.slow > 45 && ns > 0.45) { ns = Math.max(0.45, ns * 0.85); quality.slow = 0; }
        if (quality.fast > 240 && ns < quality.max) { ns = Math.min(quality.max, ns * 1.1); quality.fast = 0; }
        if (ns !== quality.scale) { quality.scale = ns; layers.forEach(function (L) { L.renderer.setPixelRatio(ns); }); resize(); }
      }
      quality.last = pn;
      window.xxQuality = quality;
      var M = window.xxMotion, pos;
      if (M && typeof window.xxTime !== 'number') {
        // speed is a multiplier the timeline can ramp, so the flight is integrated, not t * v;
        // push is a keyframable offset along the line of flight (a surge, a pull-back)
        var now = paused || reduce ? lastNow : Date.now();
        if (lastNow) flight += (now - lastNow) * cfg.speed * (M.speed == null ? 1 : M.speed) / tempo;
        lastNow = now;
        pos = (((flight + (M.push || 0)) % cfg.length) + cfg.length) % cfg.length;
      } else {
        pos = (t * cfg.speed / tempo) % cfg.length;
      }
      if (paused && !rebuiltWhilePaused) { rebuiltWhilePaused = false; }
      layers.forEach(function (L) {
        L.mx = (L.mx || 0) + (mouseX - (L.mx || 0)) * 0.01;
        L.my = (L.my || 0) + (-mouseY - (L.my || 0)) * 0.01;
        // turbulence: three incommensurate sines, so the buffet never repeats visibly
        var sk = M && M.shake || 0, tt = Date.now() * 0.001;
        var bx = sk ? sk * 9 * (Math.sin(tt * 13.1) + 0.6 * Math.sin(tt * 29.7 + 1.3)) : 0;
        var by = sk ? sk * 7 * (Math.sin(tt * 11.3 + 0.7) + 0.5 * Math.sin(tt * 31.9)) : 0;
        L.camera.position.x = L.mx + (M && M.camX || 0) + bx;
        L.camera.position.y = L.my + (M && M.camY || 0) + by;
        L.camera.rotation.z = (M && M.roll || 0) + (sk ? sk * 0.006 * Math.sin(tt * 17.3 + 2.1) : 0);
        var fov = M && M.fov || cfg.fov;
        if (L.camera.fov !== fov) { L.camera.fov = fov; L.camera.updateProjectionMatrix(); }
        if (M && M.haze) L.mat.uniforms.fogFar.value = M.haze;
        L.camera.position.z = -pos + cfg.length;
        L.mat.uniforms.time.value = t % 3600000;
        L.mat.uniforms.billow.value = reduce ? 0 : (M && M.billow != null ? M.billow : cfg.billow);
        L.mat.uniforms.rim.value = M && M.rim != null ? M.rim : cfg.rim;
        updateJourney(L, L.camera.position.z);
        // demo 9: while no cloud shows over the film, draw nothing at all, so the film
        // decoder gets the machine (a hidden field still cost every frame and stalled it)
        if (M && M.off) { if (!L.blank) { L.renderer.clear(); L.blank = true; } return; }
        L.blank = false;
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
        if (k === 'clouds' || k === 'count' || k === 'size' || k === 'shade' || k === 'warmth' || k === 'light') {
          layers.forEach(function (L) { L.build(); });
        }
        try { localStorage.setItem('xx-field', JSON.stringify({
          clouds: cfg.clouds, count: cfg.count, size: cfg.size, speed: cfg.speed, shade: cfg.shade, warmth: cfg.warmth,
          light: cfg.light, rim: cfg.rim, billow: cfg.billow })); } catch (e) {}
      },
      reset: function () { try { localStorage.removeItem('xx-field'); } catch (e) {} location.reload(); }
    };
  });
})();
