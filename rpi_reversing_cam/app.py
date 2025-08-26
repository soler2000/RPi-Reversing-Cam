from __future__ import annotations
from flask import Flask, Response, render_template
from .camera_stream import CameraStream
from . import config as cfg
from .system_status import wifi_info, cpu_temp_c, load_avg

_stream: CameraStream | None = None

def create_app():
    global _stream
    app = Flask(__name__, static_folder="static", template_folder="templates")

    if _stream is None:
        _stream = CameraStream()
        _stream.start()

    @app.after_request
    def no_cache(resp):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        # Safety: WSGI apps must not send hop-by-hop headers (PEP 3333)
        resp.headers.pop("Connection", None)
        resp.headers.pop("Keep-Alive", None)
        return resp

    @app.route("/")
    def index():
        info = wifi_info()
        sys = {"cpu_temp": cpu_temp_c(), "load": load_avg()}
        return render_template("index.html", wifi=info, sys=sys, cfg=cfg.get())

    @app.route("/live")
    def live():
        return render_template("live.html")

    @app.route("/settings")
    def settings():
        return render_template("settings.html", cfg=cfg.get())

    @app.route("/stream.mjpg")
    def stream_route():
        gen = _stream.mjpeg_generator()  # type: ignore
        return Response(gen, mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.route("/healthz")
    def healthz():
        return ("ok", 200)

    return app
