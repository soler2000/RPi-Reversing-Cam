cat > ~/RPi-Reversing-Cam/rpi_reversing_cam/app.py <<'PY'
from __future__ import annotations
from flask import Flask, Response, render_template, request, redirect, url_for, jsonify
from . import config as cfgmod
from .camera import Camera

_cam: Camera | None = None
_cfg = None

def create_app():
    global _cam, _cfg
    app = Flask(__name__)
    _cfg = cfgmod.load_config()
    _cam = Camera(_cfg)

    @app.get("/healthz")
    def healthz():
        return ("ok", 200)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/stream.mjpg")
    def stream():
        boundary = b"--frame"
        def gen():
            assert _cam is not None
            while True:
                frame = _cam.jpeg_frame()
                yield boundary + b"\r\n" + b"Content-Type: image/jpeg\r\n" + b"Content-Length: " + str(len(frame)).encode() + b"\r\n\r\n" + frame + b"\r\n"
        return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.get("/settings")
    def settings_get():
        return render_template("settings.html", cfg=_cfg)

    @app.post("/settings")
    def settings_post():
        global _cfg, _cam
        cam = _cfg["camera"]
        ov  = _cfg["overlay"]
        # camera
        cam["width"] = int(request.form.get("width", cam["width"]))
        cam["height"] = int(request.form.get("height", cam["height"]))
        cam["fps"] = int(request.form.get("fps", cam["fps"]))
        cam["rotation"] = int(request.form.get("rotation", cam["rotation"]))
        # overlay
        ov["enabled"] = request.form.get("ov_enabled") == "on"
        ov["text"]["enabled"] = request.form.get("ov_text_enabled") == "on"
        ov["text"]["content"] = request.form.get("ov_text_content", ov["text"]["content"])
        ov["text"]["position"] = request.form.get("ov_text_pos", ov["text"]["position"])
        ov["text"]["font_size"] = int(request.form.get("ov_text_size", ov["text"]["font_size"]))
        ov["text"]["margin"] = int(request.form.get("ov_text_margin", ov["text"]["margin"]))
        ov["line"]["enabled"] = request.form.get("ov_line_enabled") == "on"
        ov["line"]["color"] = request.form.get("ov_line_color", ov["line"]["color"])
        ov["line"]["width_px"] = int(request.form.get("ov_line_width", ov["line"]["width_px"]))
        try:
            sx = float(request.form.get("ov_line_sx", ov["line"]["start"][0]))
            sy = float(request.form.get("ov_line_sy", ov["line"]["start"][1]))
            ex = float(request.form.get("ov_line_ex", ov["line"]["end"][0]))
            ey = float(request.form.get("ov_line_ey", ov["line"]["end"][1]))
            ov["line"]["start"] = [max(0,min(1,sx)), max(0,min(1,sy))]
            ov["line"]["end"]   = [max(0,min(1,ex)), max(0,min(1,ey))]
        except Exception:
            pass

        cfgmod.save_config(_cfg)
        if _cam: _cam.reconfigure(_cfg)
        return redirect(url_for("settings_get"))

    return app
PY
