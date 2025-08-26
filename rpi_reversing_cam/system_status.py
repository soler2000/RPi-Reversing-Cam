from __future__ import annotations
import os
import socket
import subprocess
from typing import Dict

def cpu_temp_c() -> float:
    # Kernel thermal zone
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return int(f.read().strip()) / 1000.0
    except Exception:
        pass
    # vcgencmd fallback
    try:
        out = subprocess.check_output(["vcgencmd", "measure_temp"], text=True).strip()
        # e.g. temp=39.8'C
        return float(out.split("=")[1].split("'")[0])
    except Exception:
        return 0.0

def load_avg() -> float:
    try:
        return float(os.getloadavg()[0])
    except Exception:
        return 0.0

def approx_lux_from_frame_mean(luma_mean: float) -> int:
    """Very rough mapping: 0..255 (luma) -> ~0..2000 lux using a curve."""
    x = max(0.0, min(255.0, float(luma_mean)))
    # compress highlights a bit
    lux = 2000.0 * (x / 255.0) ** 1.2
    return int(round(lux))

def _run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()

def wifi_info() -> Dict[str, str]:
    info: Dict[str, str] = {}
    # SSID
    try:
        ssid = _run(["iwgetid", "-r"])
        if ssid:
            info["ssid"] = ssid
    except Exception:
        pass
    # Signal (dBm)
    try:
        link = _run(["iw", "dev", "wlan0", "link"])
        for line in link.splitlines():
            line = line.strip()
            if line.startswith("signal:"):
                # "signal: -54 dBm"
                info["signal"] = line.split("signal:")[-1].strip()
                break
    except Exception:
        pass
    # IP address
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if ip and not ip.startswith("127."):
            info["ip"] = ip
    except Exception:
        pass
    return info