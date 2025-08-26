from __future__ import annotations
"content": "RPi Reversing Cam",
"position": "top-left",
"font_size": 20,
"margin": 10,
},
"lines": {
"line1": {
"enabled": True,
"start": [0.15, 0.75],
"end": [0.85, 0.75],
"width_px": 4,
"color": "#00FF00",
"alpha": 0.7,
},
"line2": {
"enabled": True,
"start": [0.25, 0.9],
"end": [0.75, 0.9],
"width_px": 4,
"color": "#00FF00",
"alpha": 0.5,
},
},
},
"system": {"shutdown_on_voltage": {"enabled": False, "threshold_v": 3.3}},
"wifi": {"ap_fallback_seconds": 30},
}


_lock = threading.RLock()
_state: Dict[str, Any] = {}




def _deep_merge(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
for k, v in src.items():
if isinstance(v, dict):
dst[k] = _deep_merge(dst.get(k, {}), v)
else:
dst[k] = v
return dst




def load(path: str = DEFAULT_PATH) -> Dict[str, Any]:
global _state
with _lock:
data: Dict[str, Any] = {}
if os.path.exists(path):
with open(path, "r") as f:
data = yaml.safe_load(f) or {}
_state = _deep_merge(_DEFAULTS.copy(), data)
return _state




def get() -> Dict[str, Any]:
with _lock:
if not _state:
return load()
return _state




def save(new_cfg: Dict[str, Any], path: str = DEFAULT_PATH) -> None:
with _lock:
# merge onto current state (defaults already applied)
merged = _deep_merge(get().copy(), new_cfg)
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w") as f:
yaml.safe_dump(merged, f, sort_keys=False)
_state.clear()
load(path)