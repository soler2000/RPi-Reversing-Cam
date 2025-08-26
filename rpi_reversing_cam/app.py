from __future__ import annotations
from typing import Dict, Any
from flask import Flask, Response, jsonify, redirect, render_template, request, url_for

from . import config as cfg
from .camera_stream import CameraStream
from .system_status import cpu_temp_c, load_avg, wifi_info

_stream: CameraStream | None = None


def create_app() -> Flask:
    app = Flask(__name__)

    # Load config and start camera stream
    cfg.load()
    global _stream
    _stream = CameraStream()
    _stream.start()

    @app.route("/")
    def index():
        wi = wifi_info()
        return render_template(
            "index.html",
            wifi_ssid=wi.get("ssid", ""),
            wifi_signal=wi.get("signal", ""),
            cpu_temp=f"{cpu_temp_c():.1f}",
            load_avg=f"{load_avg():.2f}",
        )

    @app.route("/live")
    def live():
        return render_template("live.html")

    @app.route("/stream.mjpg")
    def stream_mjpg():
        if _stream is None:
            return Response(status=503)
        resp = Response(
            _stream.mjpeg_generator(),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )
        # Reduce client buffering (iOS/Safari especially)
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Connection"] = "keep-alive"
        return resp

    @app.route("/snapshot.jpg")
    def snapshot():
        if _stream is None:
            return Response(status=503)
        frame = _stream.latest_jpeg()
        return Response(frame, mimetype="image/jpeg") if frame else Response(status=503)

    @app.route("/api/status")
    def api_status():
        wi = wifi_info()
        return jsonify(
            {
                "cpu_temp_c": cpu_temp_c(),
                "load_avg": load_avg(),
                "wifi": wi,
            }
        )

    @app.route("/settings", methods=["GET", "POST"])
    def settings():
        current = cfg.get()
        if request.method == "POST":
            new: Dict[str, Any] = {
                "camera": {
                    "width": int(request.form.get("width", current["camera"]["width"])),
                    "height": int(request.form.get("height", current["camera"]["height"])),
                    "fps": int(request.form.get("fps", current["camera"]["fps"])),
                    "rotation_deg": int(
                        request.form.get("rotation_deg", current["camera"].get("rotation_deg", 0))
                    ),
                    "jpeg_quality": int(
                        request.form.get("jpeg_quality", current["camera"].get("jpeg_quality", 85))
                    ),
                },
                "overlay": {
                    "enabled": request.form.get("overlay_enabled") == "on",
                    "show_stats": request.form.get("show_stats") == "on",
                    "text": {
                        "enabled": request.form.get("text_enabled") == "on",
                        "content": request.form.get("text_content", ""),
                        "position": request.form.get("text_position", "top-left"),
                        "font_size": int(request.form.get("font_size", 20)),
                        "margin": int(request.form.get("margin", 10)),
                    },
                    "lines": {
                        "line1": _line_from_form("1", current),
                        "line2": _line_from_form("2", current),
                    },
                },
            }
            cfg.save(new)
            if _stream:
                _stream.update_settings(new)  # restart camera with new settings
            return redirect(url_for("settings"))

        return render_template("settings.html", cfg=current)

    return app


def _line_from_form(idx: str, current: Dict[str, Any]) -> Dict[str, Any]:
    """Extract a line's settings from the HTML form, clamping normalized coords to [0,1]."""
    def norm_pair(name: str, default_xy):
        try:
            x = float(request.form.get(f"l{idx}_{name}_x", default_xy[0]))
            y = float(request.form.get(f"l{idx}_{name}_y", default_xy[1]))
            return [min(max(x, 0.0), 1.0), min(max(y, 0.0), 1.0)]
        except Exception:
            return default_xy

    line_key = f"line{idx}"
    d = current.get("overlay", {}).get("lines", {}).get(line_key, {})
    return {
        "enabled": request.form.get(f"l{idx}_enabled") == "on",
        "start": norm_pair("start", d.get("start", [0.1, 0.8])),
        "end": norm_pair("end", d.get("end", [0.9, 0.8])),
        "width_px": int(request.form.get(f"l{idx}_width_px", d.get("width_px", 4))),
        "color": request.form.get(f"l{idx}_color", d.get("color", "#00FF00")),
        "alpha": float(request.form.get(f"l{idx}_alpha", d.get("alpha", 0.7))),
    }


if __name__ == "__main__":
    app = create_app()
    host = cfg.get()["app"]["host"]
    port = int(cfg.get()["app"]["port"])
    app.run(host=host, port=port, debug=False, threaded=True)