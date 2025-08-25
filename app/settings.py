import sqlite3, os, json, threading, time
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'settings.db')
DB_PATH = os.path.abspath(DB_PATH)
_lock = threading.RLock()

DEFAULTS = {
    # Camera & overlays
    "camera.resolution": "1280x720",
    "camera.framerate": "30",
    "camera.rotation": "0",              # 0 or 180
    "overlay.enabled": "1",
    "overlay.text_pos": "0.02,0.10",     # normalized x,y
    "overlay.text_scale": "1.0",
    "overlay.show_cpu": "1",
    "overlay.show_battery": "1",
    "overlay.show_distance": "1",

    # Guide lines (normalized 0..1 coords)
    "guideline1.color": "#00FF00",
    "guideline1.alpha": "0.6",
    "guideline1.width": "4",
    "guideline1.start": "0.25,0.80",
    "guideline1.end":   "0.25,0.95",

    "guideline2.color": "#00FF00",
    "guideline2.alpha": "0.6",
    "guideline2.width": "4",
    "guideline2.start": "0.75,0.80",
    "guideline2.end":   "0.75,0.95",

    # Distance & warnings
    "distance.min_m": "0.2",
    "distance.max_m": "4.0",
    "warning.freq_min_hz": "0.1",
    "warning.freq_max_hz": "20.0",
    "warning.enabled": "1",
    "warning.threshold_m": "2.5",

    # LEDs
    "led.master_on": "1",
    "led.brightness": "0.4",             # 0..1
    "led.pin": "18",
    "led.count": "16",
    "led.illum_on_dark": "1",
    "led.dark_lux_threshold": "40",      # approx brightness 0..255
    "led.white_color": "#FFFFFF",
    "led.red_color": "#FF0000",

    # Battery estimation
    "battery.v_min": "3.3",
    "battery.v_max": "4.2",
    "battery.shutdown_enabled": "0",
    "battery.shutdown_voltage": "3.4",

    # Wi-Fi
    "wifi.ap.ssid": "RPiCam",
    "wifi.ap.password": "raspberry",
    "wifi.fallback_timeout_s": "30",
    "wifi.try_known_timeout_s": "30",

    # Logging windows
    "metrics.battery_log_minutes": "240"  # 4 hours
}

def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    with _lock, _conn() as c:
        c.execute("CREATE TABLE IF NOT EXISTS settings (k TEXT PRIMARY KEY, v TEXT)")
        c.execute("""CREATE TABLE IF NOT EXISTS sensor_log (
            ts INTEGER PRIMARY KEY,
            batt_pct REAL, voltage REAL, current REAL, power REAL
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS motion_events (
            ts INTEGER PRIMARY KEY,
            magnitude REAL
        )""")
        # seed defaults if missing
        for k,v in DEFAULTS.items():
            c.execute("INSERT OR IGNORE INTO settings(k,v) VALUES(?,?)", (k,str(v)))
        c.commit()

def get(k, fallback=None):
    with _lock, _conn() as c:
        row = c.execute("SELECT v FROM settings WHERE k=?", (k,)).fetchone()
        return row[0] if row else (DEFAULTS.get(k, fallback))

def set_many(d: dict):
    with _lock, _conn() as c:
        for k,v in d.items():
            c.execute("INSERT INTO settings(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k,str(v)))
        c.commit()

def get_all(prefix=None):
    with _lock, _conn() as c:
        if prefix:
            rows = c.execute("SELECT k,v FROM settings WHERE k LIKE ?", (prefix+'%',)).fetchall()
        else:
            rows = c.execute("SELECT k,v FROM settings", ()).fetchall()
        return {k:v for k,v in rows}

def log_battery(ts, pct, v, i, p):
    with _lock, _conn() as c:
        c.execute("INSERT OR REPLACE INTO sensor_log(ts,batt_pct,voltage,current,power) VALUES (?,?,?,?,?)", (ts,pct,v,i,p))
        c.commit()

def get_battery_series(minutes):
    cutoff = int(time.time()) - minutes*60
    with _lock, _conn() as c:
        rows = c.execute("SELECT ts,batt_pct FROM sensor_log WHERE ts>=? ORDER BY ts", (cutoff,)).fetchall()
        return [{"t": ts, "pct": pct} for ts, pct in rows]

def log_motion(ts, mag):
    with _lock, _conn() as c:
        c.execute("INSERT OR REPLACE INTO motion_events(ts,magnitude) VALUES (?,?)", (ts, mag))
        c.commit()

def get_motion_series(minutes):
    cutoff = int(time.time()) - minutes*60
    with _lock, _conn() as c:
        rows = c.execute("SELECT ts,magnitude FROM motion_events WHERE ts>=? ORDER BY ts", (cutoff,)).fetchall()
        return [{"t": ts, "m": m} for ts, m in rows]
