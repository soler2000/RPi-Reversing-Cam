cat > ~/RPi-Reversing-Cam/rpi_reversing_cam/config.py <<'PY'
from __future__ import annotations
import json, os, tempfile, shutil
from typing import Any, Dict

# Default config (safe, small)
DEFAULT: Dict[str, Any] = {
    "camera": {"width": 640, "height": 480, "fps": 20, "rotation": 0},
    "overlay": {
        "enabled": True,
        "text": {"enabled": False, "content": "RPi Cam", "position": "top-left", "font_size": 20, "margin": 8},
        "line": {
            "enabled": True,
            "color": "#00FF00",
            "width_px": 4,
            "start": [0.1, 0.7],   # normalized (x,y)
            "end":   [0.9, 0.7]
        }
    }
}

CONF_ENV = "RCAM_CONFIG"
CONF_NAME = "config.json"
CONF_PATHS = [
    os.environ.get(CONF_ENV) or "",
    "/opt/rpi-reversing-cam/config.json",
    os.path.expanduser("~/.config/rpi-reversing-cam/config.json"),
    os.path.join(os.path.dirname(__file__), "config.json"),
]

def _first_writable_path() -> str:
    # prefer /opt if it exists
    candidates = [
        "/opt/rpi-reversing-cam/config.json",
        os.path.expanduser("~/.config/rpi-reversing-cam/config.json"),
        os.path.join(os.path.dirname(__file__), "config.json"),
    ]
    for p in candidates:
        d = os.path.dirname(p)
        try:
            os.makedirs(d, exist_ok=True)
            open(p, "a").close()
            return p
        except Exception:
            continue
    # fallback to a temp file (not persisted across reboot)
    return os.path.join(tempfile.gettempdir(), CONF_NAME)

def load_config() -> Dict[str, Any]:
    for p in CONF_PATHS:
        if not p:
            continue
        try:
            with open(p, "r") as f:
                data = json.load(f)
                return _merge(DEFAULT, data)
        except FileNotFoundError:
            continue
        except Exception:
            continue
    return DEFAULT.copy()

def save_config(cfg: Dict[str, Any]) -> str:
    path = os.environ.get(CONF_ENV) or _first_writable_path()
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cfg, f, indent=2)
    shutil.move(tmp, path)
    return path

def _merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            out[k] = _merge(base[k], v)
        else:
            out[k] = v
    return out
PY
