from . import create_app
from flask import render_template, Response, request, redirect, url_for, jsonify, flash
from . import settings as cfg
from .camera import Camera
from .sensors import SensorThread, get_state
from .leds import LedController
from . import settings
from . import wifi as wifimgr
import time, os

app = create_app()
cfg.init_db()

_cam = Camera()
_cam.start()

_last_frame = [None]
def _latest_frame_ref():
    return _cam.latest()

_sensors = SensorThread(cam_ref=_latest_frame_ref)
_sensors.start()
_leds = LedController()
_leds.start()

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/video")
def video():
    return render_template("video.html")

@app.route("/stream.mjpg")
def stream():
    return Response(_cam.mjpeg_generator(quality=85),
        mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/stats")
def api_stats():
    s = get_state()
    return jsonify({
        "distance_m": None if s.distance_m is None else round(s.distance_m, 1),
        "led_status": s.led_status,
        "wifi_ssid": s.wifi_ssid,
        "wifi_rssi": s.wifi_rssi,
        "cpu_temp_c": s.cpu_temp_c,
        "cpu_load": s.cpu_load,
        "battery_pct": s.batt_pct,
        "voltage": s.voltage, "current": s.current, "power": s.power,
        "lux": s.lux_approx
    })

@app.route("/api/series")
def api_series():
    minutes = int(settings.get("metrics.battery_log_minutes", "240"))
    return jsonify({
        "battery": cfg.get_battery_series(minutes),
        "motion": cfg.get_motion_series(minutes)
    })

@app.route("/settings", methods=["GET","POST"])
def settings_page():
    if request.method == "POST":
        updates = {}
        for k,v in request.form.items():
            updates[k] = v
        cfg.set_many(updates)
        flash("Settings saved", "ok")
        return redirect(url_for("settings_page"))
    data = {
        "camera": cfg.get_all("camera."),
        "overlay": cfg.get_all("overlay."),
        "guideline1": cfg.get_all("guideline1."),
        "guideline2": cfg.get_all("guideline2."),
        "distance": cfg.get_all("distance."),
        "warning": cfg.get_all("warning."),
        "led": cfg.get_all("led."),
        "battery": cfg.get_all("battery."),
        "wifi": cfg.get_all("wifi.")
    }
    return render_template("settings.html", data=data)

@app.route("/wifi/scan")
def wifi_scan():
    return jsonify({"networks": wifimgr.scan()})

@app.route("/wifi/connect", methods=["POST"])
def wifi_connect():
    ssid = request.form.get("ssid"); pwd = request.form.get("password","")
    ok = wifimgr.save_and_connect(ssid, pwd if pwd else None)
    if ok:
        flash(f"Connecting to {ssid}...", "ok")
    else:
        flash("Failed to connect", "err")
    return redirect(url_for("settings_page"))

@app.route("/shutdown-if-low")
def shutdown_if_low():
    if cfg.get("battery.shutdown_enabled","0") != "1":
        return "disabled", 200
    import subprocess
    s = get_state()
    thr = float(cfg.get("battery.shutdown_voltage","3.4"))
    if s.voltage is not None and s.voltage <= thr:
        subprocess.Popen(["sudo","/sbin/shutdown","-h","now"])
        return "shutting down", 200
    return "ok", 200

def main():
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, threaded=True)

if __name__ == "__main__":
    main()
