from __future__ import annotations
from flask import Flask, Response, render_template, request
from .camera_stream import CameraStream
from . import config as cfg
from .system_status import wifi_info, cpu_temp_c, load_avg

_stream: CameraStream | None = None

def _b(val: str | None) -> bool:
    return str(val).lower() in ("1","true","on","yes","y")

def _i(val: str | None, default: int, lo: int | None=None, hi: int | None=None) -> int:
    try:
        n = int(str(val))
    except Exception:
        n = default
    if lo is not None: n = max(lo, n)
    if hi is not None: n = min(hi, n)
    return n

def _f(val: str | None, default: float, lo: float | None=None, hi: float | None=None) -> float:
    try:
        x = float(str(val))
    except Exception:
        x = default
    if lo is not None: x = max(lo, x)
    if hi is not None: x = min(hi, x)
    return x

def _norm(v: str | None, default: float) -> float:
    return _f(v, default, 0.0, 1.0)

def create_app():
    global _stream
    app = Flask(__name__, static_folder="static", template_folder="templates")

    if _stream is None:
        _stream = CameraStream()
        _stream.start()

    @app.after_request
    def strip_hop_by_hop(resp):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        for h in ("Connection","Keep-Alive","Proxy-Authenticate","Proxy-Authorization","TE","Trailer","Transfer-Encoding","Upgrade"):
            resp.headers.pop(h, None)
        return resp

    @app.route("/")
    def index():
        info = wifi_info()
        sys = {"cpu_temp": cpu_temp_c(), "load": load_avg()}
        return render_template("index.html", wifi=info, sys=sys, cfg=cfg.get())

    @app.route("/live")
    def live():
        return render_template("live.html")

    @app.route("/settings", methods=["GET","POST"])
    def settings():
        saved = False
        current = cfg.get()
        if request.method == "POST":
            # CAMERA
            cam = {
                "width": _i(request.form.get("camera_width"), current["camera"].get("width", 640), 160, 1920),
                "height": _i(request.form.get("camera_height"), current["camera"].get("height", 480), 120, 1080),
                "fps": _i(request.form.get("camera_fps"), current["camera"].get("fps", 20), 1, 60),
                "rotation_deg": 180 if _i(request.form.get("camera_rotation"), 0) == 180 else 0,
                "jpeg_quality": _i(request.form.get("camera_jpeg_q"), current["camera"].get("jpeg_quality", 85), 60, 95),
            }
            # OVERLAY
            ov = request.form
            text = {
                "enabled": _b(ov.get("ov_text_enabled")),
                "content": ov.get("ov_text_content","")[:120],
                "position": ov.get("ov_text_position","top-left"),
                "font_size": _i(ov.get("ov_text_font"), 20, 8, 64),
                "margin": _i(ov.get("ov_text_margin"), 10, 0, 100),
            }
            def line(prefix: str, dflt):
                return {
                    "enabled": _b(ov.get(f"{prefix}_enabled")),
                    "start": [_norm(ov.get(f"{prefix}_sx"), dflt["start"][0]),
                              _norm(ov.get(f"{prefix}_sy"), dflt["start"][1])],
                    "end":   [_norm(ov.get(f"{prefix}_ex"), dflt["end"][0]),
                              _norm(ov.get(f"{prefix}_ey"), dflt["end"][1])],
                    "width_px": _i(ov.get(f"{prefix}_w"), dflt["width_px"], 1, 20),
                    "color": ov.get(f"{prefix}_color", dflt["color"])[:7],
                    "alpha": _f(ov.get(f"{prefix}_alpha"), dflt["alpha"], 0.0, 1.0)
                }
            defaults = current.get("overlay", {}).get("lines", {})
            l1d = defaults.get("line1", {"start":[0.15,0.75], "end":[0.85,0.75], "width_px":4, "color":"#00FF00", "alpha":0.7})
            l2d = defaults.get("line2", {"start":[0.25,0.90], "end":[0.75,0.90], "width_px":4, "color":"#00FF00", "alpha":0.5})
            overlay = {
                "enabled": _b(ov.get("ov_enabled")),
                "show_stats": _b(ov.get("ov_stats")),
                "text": text,
                "lines": {
                    "line1": line("l1", l1d),
                    "line2": line("l2", l2d),
                },
            }
            new_cfg = {"camera": cam, "overlay": overlay}
            cfg.save(new_cfg)          # write to config.yaml + reload state
            current = cfg.get()        # re-read merged config
            if _stream:
                _stream.update_settings(current)  # stop/start with new config
            saved = True
        return render_template("settings.html", cfg=current, saved=saved)

    @app.route("/stream.mjpg")
    def stream_route():
        gen = _stream.mjpeg_generator()  # type: ignore
        headers = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache", "Expires": "0"}
        return Response(gen, mimetype="multipart/x-mixed-replace; boundary=frame", headers=headers, direct_passthrough=True)

    @app.route("/healthz")
    def healthz():
        return ("ok", 200)

    return app