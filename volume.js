/* X-ON-X hero, demo 7: volumetric clouds, raymarched.
 *
 * 28.09, point 4 of «роби всі 4». Demo 4 builds a cloud out of soft billboards and fakes the
 * light per puff. Here there are no puffs at all: for every pixel a ray goes out from the
 * camera through a density field, and at every step on the way the light that reaches that
 * bit of vapour from the sun is marched too. Shadows between crowns, the dark belly, the
 * silver lining looking into the sun and the haze of distance all fall out of that one
 * calculation instead of being painted on. Written from scratch (no shadertoy code, so no
 * licence question), raw WebGL 1, no library.
 *
 * Same composition as demo 4: flight forward at eye level, the sun up-right ahead where the
 * sky's warm glow is, two canvases so the near clouds cross the words. The back canvas marches
 * from SPLIT outwards, the front one only the first SPLIT units, thinned by CSS.
 *
 * Cost is the catch: the field is rendered at a fraction of the screen and scaled up
 * (the clouds are soft, that hides it), with fewer steps on phones. */
(function () {
  'use strict';
  var script = document.currentScript;
  var mobile = window.matchMedia('(max-width: 768px)').matches;
  var cfg = {
    speed: 0.085,           // world units per ms, demo 4's tempo
    coverage: 0.56,         // how much of the sky is cloud
    density: 1.0,           // how thick the vapour is
    lining: 0.6,            // forward scattering: the glow at the edges looking into the sun
    shade: 0.95,            // how dark the shaded side goes: demo 4 is light right through, so is this
    scale: +(script.dataset.scale || (mobile ? 0.33 : 0.5)),   // render resolution / screen
    steps: +(script.dataset.steps || (mobile ? 44 : 80)),
    split: 900              // nearer than this = front canvas
  };
  try { Object.assign(cfg, JSON.parse(localStorage.getItem('xx-volume') || '{}')); } catch (e) {}

  var root = document.documentElement;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var start = Date.now(), paused = false, frozen = 0, mouseX = 0, mouseY = 0, camX = 0, camY = 0;

  var VS = 'attribute vec2 p; varying vec2 vUv; void main(){ vUv = p * 0.5 + 0.5; gl_Position = vec4(p, 0.0, 1.0); }';
  var FS = [
    'precision highp float;',
    'varying vec2 vUv;',
    'uniform vec2 res; uniform vec3 cam; uniform float time; uniform float tanHalf; uniform float roll;',
    'uniform float tNear; uniform float tFar; uniform int steps; uniform float fadeA; uniform float fadeB; uniform float isFront;',
    'uniform float coverage; uniform float density; uniform float lining; uniform float shade;',
    'uniform vec3 sunDir; uniform vec3 skyHigh; uniform vec3 skyLow; uniform vec3 fogCol;',
    '',
    // value noise, hashed, no textures
    'float hash(vec3 p){ p = fract(p * 0.3183099 + 0.1); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }',
    'float noise(vec3 x){',
    '  vec3 i = floor(x); vec3 f = fract(x); f = f * f * (3.0 - 2.0 * f);',
    '  return mix(mix(mix(hash(i), hash(i + vec3(1,0,0)), f.x), mix(hash(i + vec3(0,1,0)), hash(i + vec3(1,1,0)), f.x), f.y),',
    '             mix(mix(hash(i + vec3(0,0,1)), hash(i + vec3(1,0,1)), f.x), mix(hash(i + vec3(0,1,1)), hash(i + vec3(1,1,1)), f.x), f.y), f.z);',
    '}',
    'const mat3 ROT = mat3(0.00, 0.80, 0.60, -0.80, 0.36, -0.48, -0.60, -0.48, 0.64);',
    '',
    // The layer: cumulus sit in a slab around eye level, flat bases, rounded tops.
    // Shape = a low-frequency field thresholded by coverage (where the clouds are) times the
    // height profile, then bitten by higher octaves (cauliflower crowns, ragged edges).
    // The field drifts slowly on its own, so the clouds churn while you fly through them.
    'const float BASE = -440.0; const float TOP = 560.0;',
    'float remap(float v, float a, float b){ return clamp((v - a) / (b - a), 0.0, 1.0); }',
    'float cloud(vec3 p, bool fine){',
    '  float h = (p.y - BASE) / (TOP - BASE);',
    '  if (h < 0.0 || h > 1.0) return 0.0;',
    '  vec3 q = p * 0.0010 + vec3(0.0, 0.0, time * 0.000015);',
    '  float n = noise(q) * 0.62 + noise(ROT * q * 2.03) * 0.25 + noise(ROT * ROT * q * 4.01) * 0.13;',
    '  float c = remap(n, 1.0 - coverage, 1.0);',
    '  float ht = h + (noise(q * 3.1 + 7.0) - 0.5) * 0.34;',   // a lumpy top, never a plateau: a flat top below eye level reads as a straight line
    '  float prof = smoothstep(0.0, 0.06, h) * remap(ht, 0.25 + c * 0.75, 0.1 + c * 0.35);',
    '  float d = remap(c * prof, 0.035, 1.0);',   // no thin haze: it glowed into pillars and blobs looking towards the sun
    '  if (d <= 0.0) return 0.0;',
    '  if (fine) {',
    // Cauliflower: a cumulus is rounded heads with sharp creases between them. Ridged noise
    // (1 - |2n - 1|) is high only along thin lines, so eroding by it bites narrow creases and
    // leaves round heads between, at two sizes. The base is eroded by plain noise instead:
    // ragged and wispy underneath, as in every reference photo.
    '    vec3 r = p * 0.0058 + vec3(time * 0.00003, -time * 0.00002, 0.0);',
    '    float r1 = 1.0 - abs(noise(r) * 2.0 - 1.0);',
    '    float r2 = 1.0 - abs(noise(ROT * r * 2.7 + 3.0) * 2.0 - 1.0);',
    '    float r0 = 1.0 - abs(noise(ROT * p * 0.0026 + 9.0) * 2.0 - 1.0);',   // the big towers a cloud is built of, a third of its size
    '    float cauli = r0 * 0.42 + r1 * 0.36 + r2 * 0.22;',
    '    float wisp = noise(r * 1.9) * 0.6 + noise(ROT * r * 4.3) * 0.4;',
    '    float soft = noise(r * 1.3 + 11.0) * 0.5 + noise(ROT * r * 3.4 + 5.0) * 0.32 + noise(ROT * ROT * r * 8.1 + 2.0) * 0.18;',   // the finest octave is for clouds up close                             // round, crease-free lumps for the flanks and belly
    '    float e = mix(wisp, soft, smoothstep(0.06, 0.2, h));',
    '    e = mix(e, mix(soft, cauli * cauli, 0.7), smoothstep(0.2, 0.46, h));',            // creases only up in the crowns
    '    d = remap(d, e * 0.52, 1.0);',
    // a cumulus is dense right under its surface: no translucent veil over the crowns,
    // and fewer half-transparent samples, which is what read as sand at the edges
    '    d = smoothstep(0.0, mix(0.34, 0.08, smoothstep(0.1, 0.4, h)), d);',
    '  }',
    '  return d * 2.2 * density;',
    '}',
    '',
    'float hg(float c, float g){ float g2 = g * g; return (1.0 - g2) / pow(1.0 + g2 - 2.0 * g * c, 1.5) * 0.0796; }',
    '',
    'void main(){',
    '  vec2 uv = vUv * 2.0 - 1.0;',
    '  uv = mat2(cos(roll), sin(roll), -sin(roll), cos(roll)) * vec2(uv.x * res.x / res.y, uv.y);',   // the bank
    '  vec3 rd = normalize(vec3(uv.x * tanHalf, uv.y * tanHalf, -1.0));',
    '  vec3 ro = cam;',
    '  float cosT = dot(rd, sunDir);',
    '  float phase = mix(hg(cosT, 0.62), hg(cosT, -0.18), 0.3);',
    '  float phaseN = phase / hg(1.0, 0.62) ;',                               // 0..1, 1 = looking into the sun
    '  float T = 1.0; vec3 col = vec3(0.0);',
    '  float span = tFar - tNear;',
    // steps grow with distance: fine near the lens, coarse in the haze
    // interleaved gradient noise: an even, fine dither instead of white noise, which
    // upscaled from half resolution read as sand along every edge
    '  float jitter = fract(52.9829189 * fract(dot(gl_FragCoord.xy, vec2(0.06711056, 0.00583715))) + floor(time / 16.7) * 0.618034);',   // moves every frame: in motion it is grain, not a grid
    '  for (int i = 0; i < 96; i++) {',
    '    if (i >= steps || T < 0.02) break;',
    '    float f0 = (float(i) + jitter) / float(steps);',
    '    float t = tNear + span * f0 * f0;',
    '    float dt = span * (2.0 * f0 + 1.0 / float(steps)) / float(steps);',
    '    vec3 p = ro + rd * t;',
    '    float d = cloud(p, true);',
    '    if (d > 0.001) {',
    // light: six steps towards the sun, then three orders of scattering, each weaker,
    // softer and less forward than the last: why a real cloud is bright right through
    '      float od = 0.0;',
    // the first two light steps see the full detail, so a crown shades the one behind it
    // and the creases between heads go dark: that is what gives a cumulus its structure
    '      for (int j = 1; j <= 6; j++) od += cloud(p + sunDir * float(j * j) * 16.0, j <= 2) * float(2 * j - 1) * 16.0;',
    '      od *= 0.012 * shade;',
    '      float powder = 1.0 - exp(-d * 6.0);',
    '      float sunL = 0.0; float am = 1.0, bm = 1.0, gm = 1.0;',
    '      for (int k = 0; k < 3; k++) { sunL += am * exp(-od * bm) * mix(0.6, phaseN * 1.8 * lining * powder * powder + 0.6, gm); am *= 0.55; bm *= 0.35; gm *= 0.4; }',
    '      float h = clamp((p.y - BASE) / (TOP - BASE), 0.0, 1.0);',
    // In every reference the shaded side is lit by the blue sky and the sunlit side by a
    // low warm sun: cool shadow against warm light is most of what reads as real. The
    // shadow here is skylight (cool), plus a little warm bounce from the haze below.
    '      vec3 sh = mix(skyHigh, vec3(dot(skyHigh, vec3(0.299, 0.587, 0.114))), 0.35);',   // the sky colour, a third less saturated
    '      vec3 amb = mix(sh * 0.84, mix(sh, vec3(1.0), 0.66), h) + skyLow * 0.07 * (1.0 - h);',
    '      vec3 c = amb * (0.70 + 0.18 * h) + vec3(1.0, 0.955, 0.90) * sunL * (0.35 + 0.65 * powder) * 0.66;',
    '      float fog = smoothstep(600.0, 4200.0, t);',
    '      c = mix(c, fogCol, fog * 0.9);',
    '      float a = 1.0 - exp(-d * 0.055 * dt);',
    '      a *= smoothstep(40.0, 480.0, t);',
    '      float wb = smoothstep(fadeA, fadeB, t);',            // the two canvases share a wide band, no hard cut at the split
    '      a *= mix(wb, 1.0 - wb, isFront);',
    '      col += T * a * c; T *= 1.0 - a;',
    '    }',
    '  }',
    '  float A = 1.0 - T;',
    '  gl_FragColor = vec4(min(col, vec3(1.0)), A);',                         // premultiplied already
    '}'].join('\n');

  function layer(canvas, near, far) {
    var gl = canvas.getContext('webgl', { alpha: true, premultipliedAlpha: true, antialias: false });
    if (!gl) return null;
    function sh(type, src) {
      var s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
      return s;
    }
    var prog = gl.createProgram();
    gl.attachShader(prog, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FS));
    gl.linkProgram(prog); gl.useProgram(prog);
    var buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    var loc = gl.getAttribLocation(prog, 'p'); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    var U = {};
    ['res', 'cam', 'time', 'tanHalf', 'roll', 'tNear', 'tFar', 'steps', 'fadeA', 'fadeB', 'isFront', 'coverage', 'density', 'lining', 'shade',
     'sunDir', 'skyHigh', 'skyLow', 'fogCol'].forEach(function (n) { U[n] = gl.getUniformLocation(prog, n); });
    return { gl: gl, U: U, canvas: canvas, near: near, far: far };
  }

  function rgb(hex) { var n = parseInt(hex.replace('#', ''), 16); return [(n >> 16 & 255) / 255, (n >> 8 & 255) / 255, (n & 255) / 255]; }
  var sun = [0.78, 0.42, -0.46], l = Math.hypot(sun[0], sun[1], sun[2]); sun = sun.map(function (v) { return v / l; });

  var back = document.getElementById('xx-gl-back'), front = document.getElementById('xx-gl-front');
  var L = [layer(back, cfg.split - 320, 5200), layer(front, 1, cfg.split + 120)].filter(Boolean);
  if (L[1]) L[1].front = true;
  if (!L.length) return;

  function resize() {
    L.forEach(function (x) {
      x.canvas.width = Math.max(2, Math.round(window.innerWidth * cfg.scale));
      x.canvas.height = Math.max(2, Math.round(window.innerHeight * cfg.scale));
      x.gl.viewport(0, 0, x.canvas.width, x.canvas.height);
    });
  }
  resize(); window.addEventListener('resize', resize);
  document.addEventListener('mousemove', function (e) {
    mouseX = (e.clientX - window.innerWidth / 2) * 0.06; mouseY = (e.clientY - window.innerHeight / 2) * 0.04;
  });

  // 01.10 speed: the frame time moves the render scale between 0.22 and the start value, and
  // the step count with it; a slow machine gets softer clouds instead of a stutter
  var Q = { max: cfg.scale, ema: 16.7, slow: 0, fast: 0, last: 0, steps: cfg.steps };
  function adapt() {
    var pn = performance.now();
    if (Q.last) {
      Q.ema += (Math.min(100, pn - Q.last) - Q.ema) * 0.05;
      if (Q.ema > 22) Q.slow++; else Q.slow = 0;
      if (Q.ema < 14) Q.fast++; else Q.fast = 0;
      if (Q.slow > 45 && cfg.scale > 0.22) { cfg.scale = Math.max(0.22, cfg.scale * 0.85); Q.slow = 0; resize(); }
      if (Q.fast > 240 && cfg.scale < Q.max) { cfg.scale = Math.min(Q.max, cfg.scale * 1.1); Q.fast = 0; resize(); }
      cfg.steps = Math.round(Q.steps * (0.6 + 0.4 * cfg.scale / Q.max));
    }
    Q.last = pn; window.xxQuality = { scale: cfg.scale, steps: cfg.steps, ema: Q.ema };
  }
  function frame() {
    adapt();
    var t = (typeof window.xxTime === 'number') ? window.xxTime : (paused || reduce ? frozen : (Date.now() - start));
    var tempo = parseFloat(getComputedStyle(root).getPropertyValue('--xx-tempo')) || 1;
    camX += (mouseX - camX) * 0.01; camY += (-mouseY - camY) * 0.01;
    var cs = getComputedStyle(root);
    var high = rgb(cs.getPropertyValue('--g-sky-high').trim() || '#AAB9DB');
    var low = rgb(cs.getPropertyValue('--g-sky-warm').trim() || '#FAEFE0');
    L.forEach(function (x) {
      var gl = x.gl, U = x.U;
      gl.uniform2f(U.res, x.canvas.width, x.canvas.height);
      // the same lazy path as demo 4: a breathing speed, a drifting line, a bank into the turns
      var tp = t / tempo;
      var px = 70 * Math.sin(tp * 0.000085) + 28 * Math.sin(tp * 0.00021 + 1.0), py = 32 * Math.sin(tp * 0.00007 + 2.0) + 12 * Math.sin(tp * 0.00019);
      var rl = -1.7 * (70 * 0.000085 * Math.cos(tp * 0.000085) + 28 * 0.00021 * Math.cos(tp * 0.00021 + 1.0));
      gl.uniform3f(U.cam, camX + px, camY + py, -(tp * cfg.speed + 140 * Math.sin(tp * 0.00006)));
      gl.uniform1f(U.roll, rl);
      gl.uniform1f(U.time, t % 3600000);
      gl.uniform1f(U.tanHalf, Math.tan(58 / 2 * Math.PI / 180));
      gl.uniform1f(U.tNear, x.near); gl.uniform1f(U.tFar, x.far);
      gl.uniform1f(U.fadeA, cfg.split - 320); gl.uniform1f(U.fadeB, cfg.split + 120); gl.uniform1f(U.isFront, x.front ? 1 : 0);
      gl.uniform1i(U.steps, x.near < 10 ? Math.round(cfg.steps * 0.45) : cfg.steps);
      gl.uniform1f(U.coverage, cfg.coverage); gl.uniform1f(U.density, cfg.density);
      gl.uniform1f(U.lining, cfg.lining); gl.uniform1f(U.shade, cfg.shade);
      gl.uniform3fv(U.sunDir, sun);
      gl.uniform3fv(U.skyHigh, high); gl.uniform3fv(U.skyLow, low);
      gl.uniform3fv(U.fogCol, rgb('#ECE8E6'));
      gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    });
    if (!reduce) requestAnimationFrame(frame);
  }
  var obs = new MutationObserver(function () {
    var still = root.classList.contains('xx-still');
    if (still && !paused) { frozen = Date.now() - start; paused = true; }
    if (!still && paused) { start = Date.now() - frozen; paused = false; }
  });
  obs.observe(root, { attributes: true, attributeFilter: ['class'] });
  frozen = 9000;
  frame();

  // the tuning panel talks to this, same contract as demo 4
  window.xxField = {
    cfg: cfg,
    set: function (k, v) {
      cfg[k] = v;
      if (k === 'scale') resize();
      try { localStorage.setItem('xx-volume', JSON.stringify({ speed: cfg.speed, coverage: cfg.coverage, density: cfg.density,
        lining: cfg.lining, shade: cfg.shade, scale: cfg.scale })); } catch (e) {}
    },
    reset: function () { try { localStorage.removeItem('xx-volume'); } catch (e) {} location.reload(); }
  };
})();
