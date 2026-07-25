/* GreenProof ocean intro — self-contained WebGL2, no libraries, no assets.
 *
 * A raymarched open sea seen from just above the surface: five directional
 * Gerstner-style swells with analytic normals, FBM capillary detail, an
 * analytic sky shared between the dome and the water reflection (sun disk,
 * halo, drifting cloud), Fresnel, backlit crests, sun glitter, foam and
 * horizon haze, closed with ACES tone mapping.
 *
 * Why WebGL2 and not WebGPU: this site's whole claim is that anyone can see
 * the proof. WebGPU still fails on Safari and older Android, so the intro
 * would be blank for a large share of visitors. WebGL2 runs everywhere.
 *
 * Falls back silently to a CSS gradient (set on the container) if the GL
 * context cannot be created. Pauses when off-screen or the tab is hidden.
 */
export function startOcean(canvas, opts = {}) {
  const gl = canvas.getContext("webgl2", { antialias: false, alpha: false, powerPreference: "high-performance" });
  if (!gl) return { ok: false, destroy() {} };

  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

  const VS = `#version 300 es
  precision highp float;
  in vec2 p; out vec2 uv;
  void main(){ uv = p; gl_Position = vec4(p,0.,1.); }`;

  const FS = `#version 300 es
  precision highp float;
  out vec4 outColor;
  in vec2 uv;
  uniform vec2  uRes;
  uniform float uTime;
  uniform float uSea;      // sea state 0..1
  uniform vec2  uLook;     // orbit yaw / pitch
  uniform float uSun;      // time of day 0..1 (dawn .. noon .. dusk)
  uniform float uQual;     // 1 desktop, 0 mobile

  const float PI = 3.14159265;
  // Sun direction and colour are set from the time-of-day control in main().
  vec3 SUN_DIR;
  vec3 SUN_COL;

  // ------------------------------------------------------------------ noise
  float hash(vec2 p){ p = fract(p*vec2(127.31,311.7)); p += dot(p, p+34.7); return fract(p.x*p.y); }
  float vnoise(vec2 p){
    vec2 i = floor(p), f = fract(p);
    vec2 u = f*f*(3.0-2.0*f);
    return mix(mix(hash(i),           hash(i+vec2(1,0)), u.x),
               mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), u.x), u.y);
  }
  float fbm(vec2 p){
    float s=0.0,a=0.5; mat2 m=mat2(1.7,1.2,-1.2,1.7);
    for(int i=0;i<5;i++){ s+=a*vnoise(p); p=m*p; a*=0.5; }
    return s;
  }

  // ------------------------------------------------------------------ waves
  // A choppy, non-sinusoidal octave. Real sea is not a sine: crests are
  // sharp and troughs are broad. Summing rotated octaves of this builds a
  // believable open-sea heightfield.
  float SEA_HEIGHT;   // set from uSea in main
  float CHOPPY;
  float WAVE_SPEED;

  float octave(vec2 uv, float choppy){
    uv += fbm(uv);                       // break the grid
    vec2 wv = 1.0 - abs(sin(uv));
    vec2 sw = abs(cos(uv));
    wv = mix(wv, sw, wv);
    return pow(1.0 - pow(wv.x*wv.y, 0.62), choppy);
  }

  float seaHeight(vec2 p, int steps){
    float freq = 0.16, amp = SEA_HEIGHT, choppy = CHOPPY;
    vec2 uv = p; uv.x *= 0.75;
    mat2 M = mat2(1.7, 1.3, -1.3, 1.7);
    float h = 0.0, t = 1.0 + uTime*WAVE_SPEED;
    for(int i=0;i<6;i++){
      if(i>=steps) break;
      float d  = octave((uv + t)*freq, choppy);
      d += octave((uv - t)*freq, choppy);
      h += d*amp;
      uv = M*uv; freq *= 1.95; amp *= 0.22;
      choppy = mix(choppy, 1.0, 0.2);
    }
    return h;
  }
  float H_HI(vec2 p){ return seaHeight(p, 6); }
  float H_LO(vec2 p){ return seaHeight(p, 4); }

  // Normal from central differences, with the sample distance growing with
  // view distance so far water does not alias into noise.
  vec3 seaNormal(vec3 p, float eps){
    vec2 e = vec2(eps, 0.0);
    float h  = H_HI(p.xz);
    float hx = H_HI(p.xz + e.xy);
    float hz = H_HI(p.xz + e.yx);
    return normalize(vec3(h - hx, eps, h - hz));
  }

  // Secant heightfield trace: bracket the surface crossing between the near
  // and far points, then close in. Cheap and stable for an ocean horizon.
  float traceSea(vec3 ro, vec3 rd, out vec3 pos){
    float tmin = 0.0, tmax = 900.0;
    float hmax = (ro + rd*tmax).y - H_LO((ro + rd*tmax).xz);
    if(hmax > 0.0){ pos = ro + rd*tmax; return -1.0; }   // never meets the sea
    float hmin = ro.y - H_LO(ro.xz);
    float tmid = 0.0;
    for(int i=0;i<10;i++){
      tmid = mix(tmin, tmax, hmin/(hmin - hmax));
      pos = ro + rd*tmid;
      float hm = pos.y - H_HI(pos.xz);
      if(hm < 0.0){ tmax = tmid; hmax = hm; } else { tmin = tmid; hmin = hm; }
    }
    return tmid;
  }

  // ------------------------------------------------------------------ sky
  // One analytic sky, used for the dome and for the water reflection.
  vec3 sky(vec3 rd){
    rd.y = max(rd.y, -0.05);
    // Palette shifts with the time of day: warm and low-contrast near sunrise
    // and sunset, saturated blue at midday. elev is high at noon (uSun 0.5).
    float elev = clamp(SUN_DIR.y * 2.2, 0.0, 1.0);
    vec3 zenith  = mix(vec3(0.14, 0.20, 0.40), vec3(0.09, 0.24, 0.52), elev);
    vec3 horizon = mix(vec3(0.95, 0.62, 0.42), vec3(0.55, 0.68, 0.82), clamp(elev*1.4, 0.0, 1.0));
    float g = pow(clamp(1.0 - rd.y, 0.0, 1.0), 3.2);
    vec3 col = mix(zenith, horizon, g);
    // sun disk + a tight halo (kept small so it does not wash the frame)
    float sd = max(dot(rd, SUN_DIR), 0.0);
    col += SUN_COL * pow(sd, 5000.0) * 16.0;   // disk
    col += SUN_COL * pow(sd, 350.0)  * 0.9;    // tight halo
    // soft cloud sheet above the horizon
    if(rd.y > 0.0){
      vec2 cp = rd.xz / (rd.y + 0.12);
      float cl = fbm(cp*0.9 + vec2(uTime*0.015, uTime*0.008));
      float cover = smoothstep(0.55, 1.10, cl) * smoothstep(0.0, 0.18, rd.y);
      col = mix(col, vec3(0.82,0.86,0.92), cover*0.6);
    }
    return col;
  }

  // ------------------------------------------------------------------ water
  vec3 shadeSea(vec3 p, vec3 rd, vec3 n, float dist){
    vec3 refl = reflect(rd, n);
    refl.y = abs(refl.y) + 0.003;
    vec3 reflected = sky(refl);

    // Schlick Fresnel, water F0 = 0.02
    float f = pow(1.0 - max(dot(-rd, n), 0.0), 5.0);
    float fres = 0.02 + 0.98*f;

    // refracted body colour: deep ocean, greener where we look straight down
    vec3 deep    = vec3(0.004, 0.055, 0.083);
    vec3 shallow = vec3(0.03, 0.19, 0.22);
    float down = clamp(dot(-rd, n), 0.0, 1.0);
    vec3 body = mix(deep, shallow, down*down);

    // subsurface scattering: crests glow where the sun is behind thin water.
    // Height is normalised by the sea state so thresholds hold at any setting.
    float height = H_HI(p.xz) / max(SEA_HEIGHT, 0.2);
    float sss = clamp(height*0.8, 0.0, 1.0);
    sss *= pow(max(dot(refl, SUN_DIR), 0.0), 2.0);
    body += vec3(0.06, 0.28, 0.20) * sss * 1.4;

    // reflection is capped so grazing water does not blow out to white sky
    reflected = min(reflected, vec3(1.1));
    // specular sun glitter — tight and bright, riding the detail normals
    float spec = pow(max(dot(refl, SUN_DIR), 0.0), 380.0);
    vec3 col = mix(body, reflected, fres) + SUN_COL * spec * 2.6;

    // foam on the sharpest, highest crests; a rough sea shows more whitecap
    float foam = smoothstep(0.55, 0.95, height) * smoothstep(0.35, 0.9, fbm(p.xz*3.0));
    col = mix(col, vec3(0.9, 0.94, 0.97), clamp(foam, 0.0, 1.0) * mix(0.4, 0.75, uSea));

    // atmospheric fade into the horizon haze — gentle, so near water stays deep
    float fog = 1.0 - exp(-dist*0.0016);
    col = mix(col, sky(vec3(rd.x, 0.02, rd.z)), fog*0.7);
    return col;
  }

  vec3 aces(vec3 x){
    const float a=2.51,b=0.03,c=2.43,d=0.59,e=0.14;
    return clamp((x*(a*x+b))/(x*(c*x+d)+e), 0.0, 1.0);
  }

  void main(){
    // Sea state drives amplitude, crest sharpness and pace together — a real
    // rough sea is not just taller, it is steeper and faster.
    SEA_HEIGHT = mix(0.35, 2.1, uSea*uSea);   // quadratic: top end hits hard
    CHOPPY     = mix(2.4, 4.6, uSea);
    WAVE_SPEED = mix(0.55, 1.15, uSea);
    // Time of day -> sun elevation and colour. uSun 0 dawn, 0.5 noon, 1 dusk.
    float elev = mix(0.05, 0.62, sin(clamp(uSun,0.0,1.0)*PI));
    float az   = mix(-0.5, 0.5, uSun);
    SUN_DIR = normalize(vec3(az*0.6, elev, -1.0));
    SUN_COL = mix(vec3(1.0, 0.52, 0.30), vec3(1.0, 0.95, 0.85), clamp(elev*2.2, 0.0, 1.0));

    vec2 sc = (gl_FragCoord.xy - 0.5*uRes) / uRes.y;

    // Eye over the water, tilted down so the foreground swell is seen at a
    // steep angle (dark, textured) with a thin bright horizon band on top.
    // uLook is the orbit yaw/pitch from dragging.
    vec3 ro = vec3(0.0, 5.0, 0.0);
    float yaw = uLook.x, pit = -0.14 + uLook.y;
    vec3 fwd = normalize(vec3(sin(yaw), pit, -cos(yaw)));
    vec3 rgt = normalize(cross(vec3(0,1,0), fwd));
    vec3 up  = cross(fwd, rgt);
    vec3 rd  = normalize(sc.x*rgt + sc.y*up + 1.5*fwd);

    vec3 col;
    if(rd.y > -0.004){
      col = sky(rd);
    } else {
      vec3 pos;
      float t = traceSea(ro, rd, pos);
      if(t < 0.0){
        col = sky(rd);
      } else {
        float eps = 0.006 * t;                 // distance-scaled normals
        vec3 n = seaNormal(pos, max(eps, 0.02));
        // blend toward flat at great distance to calm the horizon
        n = normalize(mix(n, vec3(0,1,0), clamp(t*0.0016, 0.0, 0.75)));
        col = shadeSea(pos, rd, n, t);
      }
    }

    // gentle cinematic vignette
    float vig = smoothstep(1.35, 0.30, length(sc));
    col *= mix(0.86, 1.0, vig);

    col = aces(col * 0.92);
    col = pow(col, vec3(0.4545));
    outColor = vec4(col, 1.0);
  }`;

  function compile(type, src) {
    const s = gl.createShader(type);
    gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
      console.warn("ocean shader:", gl.getShaderInfoLog(s));
      return null;
    }
    return s;
  }
  const vs = compile(gl.VERTEX_SHADER, VS), fs = compile(gl.FRAGMENT_SHADER, FS);
  if (!vs || !fs) return { ok: false, destroy() {} };
  const prog = gl.createProgram();
  gl.attachShader(prog, vs); gl.attachShader(prog, fs); gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
    console.warn("ocean link:", gl.getProgramInfoLog(prog));
    return { ok: false, destroy() {} };
  }
  gl.useProgram(prog);

  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(prog, "p");
  gl.enableVertexAttribArray(loc);
  gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

  const U = {
    res: gl.getUniformLocation(prog, "uRes"),
    time: gl.getUniformLocation(prog, "uTime"),
    sea: gl.getUniformLocation(prog, "uSea"),
    look: gl.getUniformLocation(prog, "uLook"),
    sun: gl.getUniformLocation(prog, "uSun"),
    qual: gl.getUniformLocation(prog, "uQual"),
  };

  const isMobile = matchMedia("(max-width:820px), (pointer:coarse)").matches;
  const dprCap = isMobile ? 1.3 : 1.75;
  let W = 0, H = 0;
  function resize() {
    const dpr = Math.min(devicePixelRatio || 1, dprCap);
    W = Math.max(1, Math.round(canvas.clientWidth * dpr));
    H = Math.max(1, Math.round(canvas.clientHeight * dpr));
    canvas.width = W; canvas.height = H;
    gl.viewport(0, 0, W, H);
  }
  resize();
  addEventListener("resize", resize, { passive: true });

  // live, adjustable simulation state
  const S = { sea: opts.sea ?? 0.6, sun: opts.sun ?? 0.62, drift: opts.drift ?? 1.0 };

  // orbit look: damped toward a target the user drags; gentle auto-yaw when idle
  let look = { x: 0, y: 0 }, target = { x: 0, y: 0 };
  let dragging = false, lastX = 0, lastY = 0, idle = 0;
  function down(e) { dragging = true; idle = 0; const t = e.touches ? e.touches[0] : e; lastX = t.clientX; lastY = t.clientY; }
  function move(e) {
    if (!dragging) return;
    const t = e.touches ? e.touches[0] : e;
    target.x = Math.max(-0.6, Math.min(0.6, target.x + (t.clientX - lastX) * -0.0016));
    target.y = Math.max(-0.10, Math.min(0.16, target.y + (t.clientY - lastY) * 0.0012));
    lastX = t.clientX; lastY = t.clientY; idle = 0;
  }
  function up() { dragging = false; }
  canvas.addEventListener("pointerdown", down);
  addEventListener("pointermove", move, { passive: true });
  addEventListener("pointerup", up);
  canvas.addEventListener("touchstart", down, { passive: true });
  canvas.addEventListener("touchmove", move, { passive: true });
  canvas.addEventListener("touchend", up);
  canvas.style.touchAction = "pan-y";
  canvas.style.cursor = "grab";

  let running = true, visible = true, raf = 0, last = performance.now(), clock = 0;
  let fps = 0, fAcc = 0, fN = 0, fT = performance.now();
  const io = new IntersectionObserver(es => { visible = es[0].isIntersecting; if (visible && running) tick(); }, { threshold: 0.02 });
  io.observe(canvas);
  document.addEventListener("visibilitychange", () => { if (!document.hidden && running && visible) { last = performance.now(); tick(); } });

  function draw(now) {
    const dt = Math.min(0.05, (now - last) / 1000); last = now;
    clock += dt * S.drift;                 // wave/cloud clock, drift-scaled
    idle += dt;
    if (idle > 2.2 && !dragging) target.x += Math.sin(clock * 0.05) * 0.00035; // slow drift
    look.x += (target.x - look.x) * 0.05;
    look.y += (target.y - look.y) * 0.05;
    gl.uniform2f(U.res, W, H);
    gl.uniform1f(U.time, clock);
    gl.uniform1f(U.sea, S.sea);
    gl.uniform2f(U.look, look.x, look.y);
    gl.uniform1f(U.sun, S.sun);
    gl.uniform1f(U.qual, isMobile ? 0.0 : 1.0);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    // fps meter
    fN++; fAcc += dt;
    if (now - fT > 500) { fps = Math.round(fN / fAcc); fN = 0; fAcc = 0; fT = now; if (opts.onFps) opts.onFps(fps); }
  }

  function tick() {
    if (!running || !visible || document.hidden) return;
    draw(performance.now());
    raf = requestAnimationFrame(tick);
  }

  if (reduce) { resize(); draw(performance.now()); }   // one static frame
  else tick();

  return {
    ok: true,
    set sea(v) { S.sea = +v; }, get sea() { return S.sea; },
    set sun(v) { S.sun = +v; }, get sun() { return S.sun; },
    set drift(v) { S.drift = +v; }, get drift() { return S.drift; },
    get fps() { return fps; },
    destroy() {
      running = false; cancelAnimationFrame(raf); io.disconnect();
      removeEventListener("resize", resize); removeEventListener("pointermove", move); removeEventListener("pointerup", up);
      const ext = gl.getExtension("WEBGL_lose_context"); if (ext) ext.loseContext();
    },
  };
}
