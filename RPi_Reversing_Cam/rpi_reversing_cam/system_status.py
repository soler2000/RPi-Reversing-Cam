from __future__ import annotations
import os
import subprocess
from typing import Dict




def cpu_temp_c() -> float:
path = "/sys/class/thermal/thermal_zone0/temp"
try:
with open(path, "r") as f:
return int(f.read().strip()) / 1000.0
except Exception:
# fallback to vcgencmd
try:
out = subprocess.check_output(["vcgencmd", "measure_temp"], text=True)
# temp=45.2'C
return float(out.split("=")[1].split("'")[0])
except Exception:
return 0.0




def load_avg() -> float:
try:
return os.getloadavg()[0]
except Exception:
return 0.0




def wifi_info() -> Dict[str, str]:
"""Return SSID and signal percent if available."""
ssid = ""
signal = ""
# Try NetworkManager first
try:
ssid = subprocess.check_output(["iwgetid", "-r"], text=True).strip()
except Exception:
pass
try:
# `iwconfig wlan0` contains Link Quality or Signal level
out = subprocess.check_output(["iwconfig", "wlan0"], text=True, stderr=subprocess.STDOUT)
for line in out.splitlines():
if "Link Quality" in line and "Signal level" in line:
# e.g., Link Quality=70/70 Signal level=-39 dBm
parts = line.split()
for p in parts:
if p.startswith("Link") and "/" in p:
try:
val = p.split("=")[1]
cur, tot = val.split("/")
signal = str(int(int(cur) * 100 / int(tot)))
except Exception:
pass
break
except Exception:
pass
return {"ssid": ssid, "signal": signal}




def approx_lux_from_frame_mean(mean_luma_0_255: float) -> int:
# Extremely rough mapping for dashboard/overlay, not calibrated
# 0 => ~1 lux (dark), 255 => ~10000 lux (bright daylight)
lux = int((mean_luma_0_255 / 255.0) * 10000)
return max(0, lux)