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
    count: +script.dataset.count || 5000,
    length: 8000,           // the box the field fills, in world units; the loop is this long
    width: 1000,
    puff: 64,
    speed: +script.dataset.speed || 0.03,       // world units per millisecond, as mrdoob
    fov: 30,
    frontDepth: 700,        // puffs nearer than this draw on the front canvas
    fogNear: -100, fogFar: 2200,
    texture: script.dataset.texture,
    sky: script.dataset.sky || '#c9d5ea',
    seed: 20260920
  };
  if (!window.WebGLRenderingContext) return;

  var root = document.documentElement;
  var back = document.getElementById('xx-gl-back');
  var front = document.getElementById('xx-gl-front');
  var mouseX = 0, mouseY = 0, start = Date.now(), paused = false, frozen = 0;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // one seeded field, so the two canvases and every reload agree
  function rng(seed) { return function () { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; }; }

  var vs = [
    'varying vec2 vUv;',
    'void main() {',
    '  vUv = uv;',
    '  gl_Position = projectionMatrix * modelViewMatrix * instanceMatrix * vec4(position, 1.0);',
    '}'].join('\n');
  var fs = [
    'uniform sampler2D map; uniform vec3 fogColor; uniform float fogNear; uniform float fogFar;',
    'uniform float splitNear; uniform float splitFar; uniform float tint;',
    'varying vec2 vUv;',
    'void main() {',
    '  float depth = gl_FragCoord.z / gl_FragCoord.w;',
    '  vec4 c = texture2D(map, vUv);',
    '  c.rgb = mix(c.rgb, c.rgb * vec3(1.0, 0.985, 0.96), tint);',
    '  c.a *= pow(gl_FragCoord.z, 20.0);',                 // the puff at the lens goes to vapour
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
      depthWrite: false, depthTest: false, transparent: true,
      blending: THREE.CustomBlending, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor,
      blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneMinusSrcAlphaFactor
    });
    var geo = new THREE.PlaneGeometry(cfg.puff, cfg.puff);
    // the field, then a second copy one box further back so the loop has no seam
    var r = rng(cfg.seed), m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3();
    var z = new THREE.Vector3(0, 0, 1);
    var mesh = new THREE.InstancedMesh(geo, mat, cfg.count * 2);
    for (var i = 0; i < cfg.count; i++) {
      var x = r() * cfg.width - cfg.width / 2;
      var y = -r() * r() * 260 - 70;                      // a deck below the camera, as mrdoob, set a little lower so it sits under the copy
      var zz = i * (cfg.length / cfg.count);
      var rot = r() * Math.PI, sc = r() * r() * 1.5 + 0.5;
      q.setFromAxisAngle(z, rot); s.set(sc, sc, 1);
      p.set(x, y, zz); m.compose(p, q, s); mesh.setMatrixAt(i, m);
      p.set(x, y, zz - cfg.length); m.compose(p, q, s); mesh.setMatrixAt(cfg.count + i, m);
    }
    scene.add(mesh);
    return { renderer: renderer, scene: scene, camera: camera };
  }

  var loader = new THREE.TextureLoader();
  loader.load(cfg.texture, function (tex) {
    tex.minFilter = THREE.LinearMipMapLinearFilter; tex.magFilter = THREE.LinearFilter;
    var layers = [
      makeLayer(back, cfg.frontDepth - 160, cfg.frontDepth, tex),
      makeLayer(front, cfg.frontDepth, cfg.frontDepth - 160, tex)
    ];
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
      layers.forEach(function (L) {
        L.camera.position.x += (mouseX - L.camera.position.x) * 0.01;
        L.camera.position.y += (-mouseY - L.camera.position.y) * 0.01;
        L.camera.position.z = -pos + cfg.length;
        L.renderer.render(L.scene, L.camera);
      });
      if (!reduce) requestAnimationFrame(frame);
    }
    resize();
    window.addEventListener('resize', resize);
    document.addEventListener('mousemove', function (e) {
      mouseX = (e.clientX - window.innerWidth / 2) * 0.25;
      mouseY = (e.clientY - window.innerHeight / 2) * 0.15;
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
  });
})();
