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
    coverage: 0.50,         // how much of the sky is cloud
    density: 1.0,           // how thick the vapour is
    lining: 1.0,            // forward scattering: the glow at the edges looking into the sun
    shade: 1.0,             // how dark the shaded side goes
    scale: +(script.dataset.scale || (mobile ? 0.33 : 0.5)),   // render resolution / screen
    steps: +(script.dataset.steps || (mobile ? 40 : 64)),
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
    'uniform vec2 res; uniform vec3 cam; uniform float time; uniform float tanHalf;',
    'uniform float tNear; uniform float tFar; uniform int steps;',
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
    'const float BASE = -240.0; const float TOP = 560.0;',
    'float remap(float v, float a, float b){ return clamp((v - a) / (b - a), 0.0, 1.0); }',
    'float cloud(vec3 p, bool fine){',
    '  float h = (p.y - BASE) / (TOP - BASE);',
    '  if (h < 0.0 || h > 1.0) return 0.0;',
    '  vec3 q = p * 0.0010 + vec3(0.0, 0.0, time * 0.000015);',
    '  float n = noise(q) * 0.62 + noise(ROT * q * 2.03) * 0.25 + noise(ROT * ROT * q * 4.01) * 0.13;',
    '  float c = remap(n, 1.0 - coverage, 1.0);',
    '  float prof = smoothstep(0.0, 0.06, h) * remap(h, 0.25 + c * 0.75, 0.1 + c * 0.35);',
    '  float d = c * prof;',
    '  if (d <= 0.0) return 0.0;',
    '  if (fine) {',
    '    vec3 r = p * 0.0085 + vec3(time * 0.00003, -time * 0.00002, 0.0);',
    '    float e = noise(r) * 0.55 + noise(ROT * r * 2.2) * 0.3 + noise(ROT * ROT * r * 4.7) * 0.15;',
    '    e = mix(1.0 - e, e, clamp(h * 3.0, 0.0, 1.0));',
    '    d = remap(d, e * 0.42, 1.0);',
    '  }',
    '  return d * 2.2 * density;',
    '}',
    '',
    'float hg(float c, float g){ float g2 = g * g; return (1.0 - g2) / pow(1.0 + g2 - 2.0 * g * c, 1.5) * 0.0796; }',
    '',
    'void main(){',
    '  vec2 uv = vUv * 2.0 - 1.0;',
    '  vec3 rd = normalize(vec3(uv.x * tanHalf * res.x / res.y, uv.y * tanHalf, -1.0));',
    '  vec3 ro = cam;',
    '  float cosT = dot(rd, sunDir);',
    '  float phase = mix(hg(cosT, 0.62), hg(cosT, -0.18), 0.3);',
    '  float phaseN = phase / hg(1.0, 0.62) ;',                               // 0..1, 1 = looking into the sun
    '  float T = 1.0; vec3 col = vec3(0.0);',
    '  float span = tFar - tNear;',
    // steps grow with distance: fine near the lens, coarse in the haze
    '  float jitter = hash(vec3(gl_FragCoord.xy, time * 0.001));',
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
    '      for (int j = 1; j <= 6; j++) od += cloud(p + sunDir * float(j * j) * 16.0, false) * float(2 * j - 1) * 16.0;',
    '      od *= 0.012 * shade;',
    '      float sunL = 0.0; float am = 1.0, bm = 1.0, gm = 1.0;',
    '      for (int k = 0; k < 3; k++) { sunL += am * exp(-od * bm) * mix(0.6, phaseN * 4.0 * lining + 0.6, gm); am *= 0.55; bm *= 0.35; gm *= 0.4; }',
    '      float powder = 1.0 - exp(-d * 6.0);',
    '      float h = clamp((p.y - BASE) / (TOP - BASE), 0.0, 1.0);',
    '      vec3 amb = mix(skyLow * 0.80, mix(skyHigh, vec3(1.0), 0.62), h);',
    '      vec3 c = amb * (0.62 + 0.25 * h) + vec3(1.0, 0.975, 0.945) * sunL * (0.35 + 0.65 * powder) * 0.62;',
    '      float fog = smoothstep(600.0, 4200.0, t);',
    '      c = mix(c, fogCol, fog * 0.9);',
    '      float a = 1.0 - exp(-d * 0.030 * dt);',
    '      a *= smoothstep(40.0, 260.0, t);',
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
    ['res', 'cam', 'time', 'tanHalf', 'tNear', 'tFar', 'steps', 'coverage', 'density', 'lining', 'shade',
     'sunDir', 'skyHigh', 'skyLow', 'fogCol'].forEach(function (n) { U[n] = gl.getUniformLocation(prog, n); });
    return { gl: gl, U: U, canvas: canvas, near: near, far: far };
  }

  function rgb(hex) { var n = parseInt(hex.replace('#', ''), 16); return [(n >> 16 & 255) / 255, (n >> 8 & 255) / 255, (n & 255) / 255]; }
  var sun = [0.30, 0.42, -0.86], l = Math.hypot(sun[0], sun[1], sun[2]); sun = sun.map(function (v) { return v / l; });

  var back = document.getElementById('xx-gl-back'), front = document.getElementById('xx-gl-front');
  var L = [layer(back, cfg.split - 120, 5200), layer(front, 1, cfg.split)].filter(Boolean);
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

  function frame() {
    var t = (typeof window.xxTime === 'number') ? window.xxTime : (paused || reduce ? frozen : (Date.now() - start));
    var tempo = parseFloat(getComputedStyle(root).getPropertyValue('--xx-tempo')) || 1;
    camX += (mouseX - camX) * 0.01; camY += (-mouseY - camY) * 0.01;
    var cs = getComputedStyle(root);
    var high = rgb(cs.getPropertyValue('--g-sky-high').trim() || '#AAB9DB');
    var low = rgb(cs.getPropertyValue('--g-sky-warm').trim() || '#FAEFE0');
    L.forEach(function (x) {
      var gl = x.gl, U = x.U;
      gl.uniform2f(U.res, x.canvas.width, x.canvas.height);
      gl.uniform3f(U.cam, camX, camY, -t * cfg.speed / tempo);
      gl.uniform1f(U.time, t % 3600000);
      gl.uniform1f(U.tanHalf, Math.tan(58 / 2 * Math.PI / 180));
      gl.uniform1f(U.tNear, x.near); gl.uniform1f(U.tFar, x.far);
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
