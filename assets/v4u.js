/* Vis4Und shared runtime: theme toggle, KaTeX rendering, TOC, small helpers for visualizations.
   Loaded synchronously in <head>; KaTeX itself is deferred. Page scripts run inside V4U.ready(fn). */
(function () {
  const V = (window.V4U = {});
  const root = document.documentElement;
  const themeCbs = [];
  const readyCbs = [];
  let isReady = false;

  // ---- theme: follow the system unless the reader picked one ----
  try {
    const saved = localStorage.getItem('v4u-theme');
    if (saved === 'light' || saved === 'dark') root.dataset.theme = saved;
  } catch (e) {}
  V.isDark = () =>
    root.dataset.theme ? root.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
  V.onTheme = (fn) => themeCbs.push(fn);
  const fireTheme = () => themeCbs.forEach((fn) => { try { fn(V.isDark()); } catch (e) { console.error(e); } });
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', fireTheme);

  /** Read a CSS colour token, e.g. V4U.css('--c1'). Use it for canvas drawing so both themes work. */
  V.css = (name) => getComputedStyle(root).getPropertyValue(name).trim();

  /** Render a TeX string into an element. */
  V.tex = (el, src, display) => {
    if (!window.katex) { el.textContent = src; return; }
    window.katex.render(src, el, { displayMode: !!display, throwOnError: false, strict: 'ignore' });
  };

  /** Size a canvas for the device pixel ratio. cssHeight in px; width follows the element.
      Calls draw(ctx, w, h) now and again on resize / theme change. Returns a redraw function. */
  V.canvas = (cv, cssHeight, draw) => {
    const ctx = cv.getContext('2d');
    const paint = () => {
      const w = Math.max(1, cv.clientWidth || cv.parentElement.clientWidth);
      const h = typeof cssHeight === 'function' ? cssHeight(w) : cssHeight;
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      cv.style.height = h + 'px';
      if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) {
        cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      draw(ctx, w, h);
    };
    new ResizeObserver(paint).observe(cv);
    V.onTheme(paint);
    paint();
    return paint;
  };

  /** Pointer drag on an element: cb(x, y, phase, event) with coordinates in the element's own
      coordinate system (SVG viewBox units for an <svg>, CSS px otherwise). phase: 'down' | 'move' | 'up'. */
  V.drag = (el, cb) => {
    const pt = (e) => {
      if (el instanceof SVGSVGElement) {
        const p = el.createSVGPoint(); p.x = e.clientX; p.y = e.clientY;
        const q = p.matrixTransform(el.getScreenCTM().inverse());
        return [q.x, q.y];
      }
      const r = el.getBoundingClientRect();
      return [e.clientX - r.left, e.clientY - r.top];
    };
    let on = false;
    el.style.touchAction = 'none';
    el.addEventListener('pointerdown', (e) => { on = true; el.setPointerCapture(e.pointerId); cb(...pt(e), 'down', e); });
    el.addEventListener('pointermove', (e) => { if (on) cb(...pt(e), 'move', e); });
    const end = (e) => { if (on) { on = false; cb(...pt(e), 'up', e); } };
    el.addEventListener('pointerup', end);
    el.addEventListener('pointercancel', end);
  };

  /** Segmented control: <div class="seg" id=..><button data-v="a">..</button>..</div>. cb(value) on change and once at start. */
  V.seg = (el, cb) => {
    const btns = [...el.querySelectorAll('button')];
    const set = (v) => {
      btns.forEach((b) => b.setAttribute('aria-pressed', b.dataset.v === v ? 'true' : 'false'));
      cb(v);
    };
    btns.forEach((b) => b.addEventListener('click', () => set(b.dataset.v)));
    const first = btns.find((b) => b.getAttribute('aria-pressed') === 'true') || btns[0];
    if (first) set(first.dataset.v);
    return set;
  };

  /** Run fn(t_seconds, dt) every frame while the element is on screen; pauses when off screen.
      Honors prefers-reduced-motion by calling fn once with t = 0. Returns {stop()}. */
  V.loop = (el, fn) => {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) { fn(0, 0); return { stop() {} }; }
    let raf = 0, last = 0, t = 0, vis = false, dead = false;
    const tick = (now) => {
      if (!vis || dead) { raf = 0; return; }
      const dt = last ? Math.min(0.05, (now - last) / 1000) : 0;
      last = now; t += dt; fn(t, dt);
      raf = requestAnimationFrame(tick);
    };
    new IntersectionObserver((es) => {
      vis = es[0].isIntersecting;
      if (vis && !raf) { last = 0; raf = requestAnimationFrame(tick); }
    }).observe(el);
    return { stop() { dead = true; } };
  };

  /** Minimal 3D view on a 2D canvas (world is right-handed, z up). Drag horizontally to orbit
      (vertical drag tilts with a mouse; on touch, vertical swipes keep scrolling the page).
      opts: {height, yaw, pitch (rad), dist, target:[x,y,z], fov (deg), drag (default true)}
      draw(ctx, P, w, h) gets a projector P:
        P.project([x,y,z]) -> {x, y, d (depth), s (px per world unit at that depth)} or null if behind the camera
        P.line(a, b, color, width), P.point(p, radiusPx, color), P.poly([p..], fill, stroke)
        P.text(p, str, color, font), P.frame(origin, R, len, width)  // R: 3x3 rows, columns are the x/y/z axes
        P.depth(p) for painter's sorting (larger = farther)
      Returns {redraw, view} where view holds yaw/pitch/dist/target and can be changed before redraw(). */
  V.orbit3d = (cv, opts, draw) => {
    const view = Object.assign({ height: 360, yaw: -0.9, pitch: 0.45, dist: 3, target: [0, 0, 0], fov: 40, drag: true }, opts);
    const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
    const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
    const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
    const norm = (a) => { const n = Math.hypot(...a) || 1; return [a[0] / n, a[1] / n, a[2] / n]; };
    let redraw;
    redraw = V.canvas(cv, view.height, (ctx, w, h) => {
      const t = view.target, cp = Math.cos(view.pitch);
      const eye = [t[0] + view.dist * cp * Math.cos(view.yaw), t[1] + view.dist * cp * Math.sin(view.yaw), t[2] + view.dist * Math.sin(view.pitch)];
      const f = norm(sub(t, eye)), r = norm(cross(f, [0, 0, 1])), u = cross(r, f);
      const foc = (h / 2) / Math.tan((view.fov * Math.PI) / 360);
      const P = {};
      P.project = (p) => {
        const d = sub(p, eye), z = dot(d, f);
        if (z < 1e-3) return null;
        return { x: w / 2 + (foc * dot(d, r)) / z, y: h / 2 - (foc * dot(d, u)) / z, d: z, s: foc / z };
      };
      P.depth = (p) => dot(sub(p, eye), f);
      P.line = (a, b, color, width = 1.5) => {
        const A = P.project(a), B = P.project(b); if (!A || !B) return;
        ctx.strokeStyle = color; ctx.lineWidth = width; ctx.beginPath(); ctx.moveTo(A.x, A.y); ctx.lineTo(B.x, B.y); ctx.stroke();
      };
      P.point = (p, rad, color) => {
        const A = P.project(p); if (!A) return;
        ctx.fillStyle = color; ctx.beginPath(); ctx.arc(A.x, A.y, rad, 0, 2 * Math.PI); ctx.fill();
      };
      P.poly = (pts, fill, stroke, width = 1) => {
        const Q = pts.map(P.project); if (Q.some((q) => !q)) return;
        ctx.beginPath(); Q.forEach((q, i) => (i ? ctx.lineTo(q.x, q.y) : ctx.moveTo(q.x, q.y))); ctx.closePath();
        if (fill) { ctx.fillStyle = fill; ctx.fill(); }
        if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.stroke(); }
      };
      P.text = (p, str, color, font) => {
        const A = P.project(p); if (!A) return;
        ctx.fillStyle = color || V.css('--ink-2'); ctx.font = font || '12px ' + V.css('--f-mono');
        ctx.fillText(str, A.x + 4, A.y - 4);
      };
      P.frame = (o, R, len = 0.3, width = 2) => {
        const cols = [V.css('--bad'), V.css('--ok'), V.css('--c1')];
        for (let k = 0; k < 3; k++) P.line(o, [o[0] + len * R[0][k], o[1] + len * R[1][k], o[2] + len * R[2][k]], cols[k], width);
      };
      draw(ctx, P, w, h);
    });
    if (view.drag) {
      let last = null;
      cv.style.touchAction = 'pan-y';
      cv.style.cursor = 'grab';
      cv.addEventListener('pointerdown', (e) => { last = [e.clientX, e.clientY]; cv.setPointerCapture(e.pointerId); });
      cv.addEventListener('pointermove', (e) => {
        if (!last) return;
        view.yaw -= (e.clientX - last[0]) * 0.01;
        if (e.pointerType === 'mouse') view.pitch = V.clamp(view.pitch + (e.clientY - last[1]) * 0.01, -1.45, 1.45);
        last = [e.clientX, e.clientY]; redraw();
      });
      const end = () => { last = null; };
      cv.addEventListener('pointerup', end); cv.addEventListener('pointercancel', end);
    }
    return { redraw: () => redraw(), view };
  };

  V.clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  V.lerp = (a, b, t) => a + (b - a) * t;
  V.fmt = (x, d = 2) => (Object.is(x, -0) ? 0 : x).toFixed(d);

  V.ready = (fn) => { if (isReady) fn(); else readyCbs.push(fn); };

  function renderMath() {
    if (!window.renderMathInElement) return;
    window.renderMathInElement(document.body, {
      delimiters: [
        { left: '$$', right: '$$', display: true },
        { left: '\\[', right: '\\]', display: true },
        { left: '\\(', right: '\\)', display: false },
        { left: '$', right: '$', display: false },
      ],
      ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code', 'svg'],
      throwOnError: false,
      strict: 'ignore',
    });
  }

  function buildToc() {
    const toc = document.getElementById('toc');
    const heads = [...document.querySelectorAll('main > section[id] > h2')];
    if (!toc || !heads.length) return;
    const ol = document.createElement('ol');
    const links = heads.map((h) => {
      const a = document.createElement('a');
      a.href = '#' + h.parentElement.id;
      a.textContent = h.dataset.toc || h.textContent.replace(/^\s*\d+\s*/, '');
      const li = document.createElement('li'); li.appendChild(a); ol.appendChild(li);
      return a;
    });
    const p = document.createElement('p'); p.textContent = '本页目录';
    toc.append(p, ol);
    const io = new IntersectionObserver((es) => {
      es.forEach((e) => {
        if (!e.isIntersecting) return;
        const i = heads.indexOf(e.target.querySelector('h2'));
        links.forEach((a, j) => a.classList.toggle('on', i === j));
      });
    }, { rootMargin: '-20% 0px -70% 0px' });
    heads.forEach((h) => io.observe(h.parentElement));
  }

  function wireTheme() {
    const b = document.querySelector('.v4u-theme');
    if (!b) return;
    const label = () => { b.textContent = V.isDark() ? '浅色' : '深色'; };
    label();
    b.addEventListener('click', () => {
      const next = V.isDark() ? 'light' : 'dark';
      root.dataset.theme = next;
      try { localStorage.setItem('v4u-theme', next); } catch (e) {}
      label(); fireTheme();
    });
    V.onTheme(label);
  }

  document.addEventListener('DOMContentLoaded', () => {
    renderMath(); buildToc(); wireTheme();
    isReady = true;
    readyCbs.forEach((fn) => { try { fn(); } catch (e) { console.error(e); } });
  });
})();
