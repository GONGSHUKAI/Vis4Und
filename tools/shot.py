#!/usr/bin/env python3
"""Screenshot a page at desktop and phone width, light and dark, via headless Chrome (CDP).

  python3 tools/shot.py pages/<slug>/ [--out DIR] [--full] [--only desktop-light,phone-dark]

Serves the repo on a local port, opens the page, waits for fonts + KaTeX, and writes PNGs:
  <out>/<slug>-desktop-light.png, -desktop-dark.png, -phone-light.png, -phone-dark.png
(--full captures the whole page, split into tiles <slug>-<shot>-2.png ... for long pages; default is the first 2.5 screens).
Prints, per shot: console errors / uncaught exceptions, KaTeX parse errors, and whether the body
scrolls horizontally (with the widest offending elements). Exit code 1 if any of those occur.
Needs the websocket-client package (pip install websocket-client) and google-chrome.
"""
import argparse
import base64
import functools
import http.server
import json
import os
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time

import websocket

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = {
    "desktop-light": dict(width=1360, height=900, mobile=False, scale=1, dark=False),
    "desktop-dark": dict(width=1360, height=900, mobile=False, scale=1, dark=True),
    "phone-light": dict(width=390, height=844, mobile=True, scale=2, dark=False),
    "phone-dark": dict(width=390, height=844, mobile=True, scale=2, dark=True),
}


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve():
    handler = functools.partial(Quiet, directory=ROOT)
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


class CDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=60, suppress_origin=True)
        self.i = 0
        self.events = []

    def call(self, method, params=None, session=None):
        self.i += 1
        msg = {"id": self.i, "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = session
        self.ws.send(json.dumps(msg))
        while True:
            r = json.loads(self.ws.recv())
            if r.get("id") == self.i:
                if "error" in r:
                    raise RuntimeError(f"{method}: {r['error']}")
                return r.get("result", {})
            self.events.append(r)

    def drain(self, secs):
        end = time.time() + secs
        self.ws.settimeout(0.2)
        while time.time() < end:
            try:
                self.events.append(json.loads(self.ws.recv()))
            except Exception:
                pass
        self.ws.settimeout(60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("page")
    ap.add_argument("--out", default=None)
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--wait", type=float, default=3.0)
    a = ap.parse_args()
    rel = a.page.strip("/")
    slug = os.path.basename(rel) or "home"
    if rel in ("", "."):
        rel, slug = "", "home"
    out = a.out or os.path.join(tempfile.gettempdir(), "v4u-shots")
    os.makedirs(out, exist_ok=True)
    srv, port = serve()
    prof = tempfile.mkdtemp(prefix="v4u-chrome-")
    args = [
        shutil.which("google-chrome") or "google-chrome", "--headless=new", "--remote-debugging-port=0",
        f"--user-data-dir={prof}", "--remote-allow-origins=*", "--no-first-run", "--hide-scrollbars",
        "--disable-gpu", "--no-default-browser-check",
    ]
    proxy = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")
    if proxy:
        args += [f"--proxy-server={proxy}", "--proxy-bypass-list=127.0.0.1;localhost"]
    chrome = subprocess.Popen(args + ["about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    bad = False
    try:
        portfile = os.path.join(prof, "DevToolsActivePort")
        for _ in range(100):
            if os.path.exists(portfile) and len(open(portfile).read().split()) >= 2:
                break
            time.sleep(0.1)
        dport, path = open(portfile).read().split()[:2]
        cdp = CDP(f"ws://127.0.0.1:{dport}{path}")
        names = [n for n in SHOTS if not a.only or n in a.only.split(",")]
        for name in names:
            cfg = SHOTS[name]
            tid = cdp.call("Target.createTarget", {"url": "about:blank"})["targetId"]
            sid = cdp.call("Target.attachToTarget", {"targetId": tid, "flatten": True})["sessionId"]
            for dom in ("Page", "Runtime", "Log"):
                cdp.call(f"{dom}.enable", session=sid)
            cdp.call("Emulation.setDeviceMetricsOverride", {
                "width": cfg["width"], "height": cfg["height"], "deviceScaleFactor": cfg["scale"], "mobile": cfg["mobile"],
            }, session=sid)
            cdp.call("Emulation.setEmulatedMedia", {"features": [
                {"name": "prefers-color-scheme", "value": "dark" if cfg["dark"] else "light"}]}, session=sid)
            cdp.events.clear()
            url = f"http://127.0.0.1:{port}/{rel}{'/' if rel else ''}"
            cdp.call("Page.navigate", {"url": url}, session=sid)
            cdp.drain(a.wait)
            cdp.call("Runtime.evaluate", {"expression": "document.fonts.ready.then(()=>1)", "awaitPromise": True}, session=sid)
            cdp.drain(0.5)
            probe = r"""(() => {
              const W = document.documentElement.clientWidth;
              const over = document.documentElement.scrollWidth > W + 1;
              const wide = [];
              if (over) for (const el of document.querySelectorAll('body *')) {
                const r = el.getBoundingClientRect();
                if (r.right > W + 1 && r.width > 0) {
                  let p = el.parentElement, clipped = false;
                  while (p && p !== document.body) { const s = getComputedStyle(p); if (/(auto|scroll|hidden|clip)/.test(s.overflowX)) { clipped = true; break; } p = p.parentElement; }
                  if (!clipped) wide.push((el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.className && typeof el.className === 'string' ? '.' + el.className.split(' ').join('.') : '')) + ' right=' + Math.round(r.right));
                }
                if (wide.length > 8) break;
              }
              const katexErr = [...document.querySelectorAll('.katex-error')].map(e => e.getAttribute('title') || e.textContent).slice(0, 8);
              const rawTex = (document.body.innerText.match(/\$[^$\n]{2,60}\$/g) || []).slice(0, 5);
              return JSON.stringify({over, wide, katexErr, rawTex, h: document.documentElement.scrollHeight, katex: !!window.katex});
            })()"""
            res = json.loads(cdp.call("Runtime.evaluate", {"expression": probe, "returnByValue": True}, session=sid)["result"]["value"])
            errs = []
            for ev in cdp.events:
                m = ev.get("method")
                if m == "Runtime.exceptionThrown":
                    d = ev["params"]["exceptionDetails"]
                    errs.append("exception: " + (d.get("exception", {}).get("description") or d.get("text", "")).split("\n")[0])
                elif m == "Runtime.consoleAPICalled" and ev["params"]["type"] in ("error", "assert"):
                    errs.append("console.error: " + " ".join(str(x.get("value", x.get("description", ""))) for x in ev["params"]["args"])[:300])
                elif m == "Log.entryAdded" and ev["params"]["entry"]["level"] == "error":
                    e = ev["params"]["entry"]
                    errs.append(f"log: {e.get('text', '')[:200]} {e.get('url', '')}")
            total = res["h"] if a.full else min(res["h"], cfg["height"] * 2.5)
            tile = 8000 if cfg["scale"] == 1 else 5000  # Chrome refuses very tall captures; long pages become -2, -3 ... tiles
            fns = []
            for k, y0 in enumerate(range(0, int(total), tile)):
                clip = {"x": 0, "y": y0, "width": cfg["width"], "height": max(1, min(tile, total - y0)), "scale": 1}
                shot = cdp.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True, "clip": clip}, session=sid)
                fn = os.path.join(out, f"{slug}-{name}{'' if k == 0 else '-' + str(k + 1)}.png")
                with open(fn, "wb") as f:
                    f.write(base64.b64decode(shot["data"]))
                fns.append(fn)
            fn = fns[0] + (f" (+{len(fns) - 1} more tiles)" if len(fns) > 1 else "")
            status = []
            if errs:
                status.append(f"{len(errs)} error(s)")
            if res["over"]:
                status.append("HORIZONTAL OVERFLOW")
            if res["katexErr"]:
                status.append(f"{len(res['katexErr'])} KaTeX error(s)")
            if not res["katex"]:
                status.append("KaTeX not loaded")
            print(f"{name}: {fn}  page height {res['h']}px  {'; '.join(status) or 'clean'}")
            for e in errs[:10]:
                print("   ", e)
            for w in res["wide"]:
                print("    too wide:", w)
            for k in res["katexErr"]:
                print("    katex:", k[:200])
            for t in res["rawTex"]:
                print("    unrendered TeX?:", t)
            bad |= bool(errs or res["over"] or res["katexErr"])
            cdp.call("Target.closeTarget", {"targetId": tid})
    finally:
        chrome.terminate()
        try:
            chrome.wait(5)
        except Exception:
            chrome.kill()
        shutil.rmtree(prof, ignore_errors=True)
        srv.shutdown()
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
