#!/usr/bin/env python3
"""
server.py — lokálny webový server pre aplikáciu (bez frameworkov, iba stdlib).

Obsluhuje:
  - statické súbory z priečinka ./web  (frontend HTML/CSS/JS)
  - JSON API, ktoré z frontendu spúšťa experimenty cez chsh_experiment.py

API (všetko POST s JSON telom, okrem /api/health):
  GET  /api/health                 -> stav (či je dostupný spinqit)
  POST /api/bell    {backend, shots, device?}
  POST /api/chsh    {backend, shots, device?}            -> celý CHSH test
  POST /api/sweep   {backend, shots, alice_angle, points, device?}

Spustenie:
    python3 server.py            # http://localhost:8000
    python3 server.py --port 9000 --config config.json
"""
import argparse
import json
import os
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import chsh_experiment as ex

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")

# voliteľné defaultné pripojenie k zariadeniu (načítané pri štarte)
DEVICE_DEFAULTS: dict = {}

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


def merge_device(payload: dict) -> dict | None:
    """Zlúči defaultný config zariadenia s tým, čo prišlo z frontendu."""
    if payload.get("backend") != "nmr":
        return None
    device = dict(DEVICE_DEFAULTS)
    device.update({k: v for k, v in (payload.get("device") or {}).items() if v not in (None, "")})
    return device


class Handler(BaseHTTPRequestHandler):
    server_version = "SpinQGeminiLab/1.0"

    # ---- pomocné odpovede -------------------------------------------------
    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, msg, status=400):
        self._json({"ok": False, "error": str(msg)}, status)

    def log_message(self, fmt, *args):  # tichší log
        return

    # ---- GET: statika + health -------------------------------------------
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/health":
            return self._json({
                "ok": True,
                "spinqit_available": ex.spinqit_available(),
                "backends": ["ideal"] + (list(ex.SPINQIT_BACKENDS) if ex.spinqit_available() else []),
                "device_configured": bool(DEVICE_DEFAULTS),
                "classical_bound": ex.CLASSICAL_BOUND,
                "quantum_bound": ex.QUANTUM_BOUND,
            })
        return self._serve_static(path)

    def _serve_static(self, path):
        rel = "index.html" if path in ("/", "") else path.lstrip("/")
        full = os.path.normpath(os.path.join(WEB_DIR, rel))
        if not full.startswith(WEB_DIR) or not os.path.isfile(full):
            return self._error("Not found", 404)
        ext = os.path.splitext(full)[1].lower()
        with open(full, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---- POST: API --------------------------------------------------------
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception as e:
            return self._error(f"Neplatné JSON telo: {e}")

        backend = payload.get("backend", "ideal")
        shots = int(payload.get("shots", 1024))

        if backend in ex.SPINQIT_BACKENDS and not ex.spinqit_available():
            return self._error("spinqit nie je nainštalovaný na serveri.", 503)

        try:
            device = merge_device(payload)
            if self.path == "/api/bell":
                probs, counts = ex.run_bell(backend, shots, device)
                return self._json({
                    "ok": True, "backend": backend, "shots": shots,
                    "probabilities": probs, "counts": counts,
                    "E_zz": ex.correlation(probs),
                })

            if self.path == "/api/chsh":
                res = ex.run_chsh(backend, shots, device=device)
                return self._json({"ok": True, **res.to_dict()})

            if self.path == "/api/sweep":
                alice = float(payload.get("alice_angle", 0.0))
                points = int(payload.get("points", 25))
                pts = ex.run_sweep(backend, shots, alice, points, device)
                return self._json({"ok": True, "backend": backend, "shots": shots,
                                   "alice_angle": alice, "points": pts})

            return self._error("Neznámy endpoint", 404)
        except Exception as e:
            traceback.print_exc()
            return self._error(f"{type(e).__name__}: {e}", 500)


def main():
    global DEVICE_DEFAULTS
    ap = argparse.ArgumentParser(description="Lokálny server pre SpinQ Gemini lab.")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--config", default="config.json", help="JSON s defaultným pripojením k zariadeniu")
    args = ap.parse_args()

    if os.path.exists(args.config):
        try:
            with open(args.config, "r", encoding="utf-8") as f:
                DEVICE_DEFAULTS = json.load(f).get("device", {}) or {}
            print(f"[config] načítané pripojenie k zariadeniu z {args.config}")
        except Exception as e:
            print(f"[config] varovanie: nepodarilo sa načítať {args.config}: {e}")

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"  SpinQ Gemini lab beží na  http://{args.host}:{args.port}")
    print(f"  spinqit dostupný: {ex.spinqit_available()}   |   Ctrl+C pre ukončenie")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nUkončené.")
        srv.server_close()


if __name__ == "__main__":
    main()
