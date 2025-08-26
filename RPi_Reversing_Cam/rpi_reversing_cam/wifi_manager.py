from __future__ import annotations
import subprocess
from typing import List, Dict


# NOTE: This is a minimal scaffold for later Wi‑Fi UI.
# Requires NetworkManager (nmcli). Running as root simplifies permissions.




def scan() -> List[Dict[str, str]]:
networks: List[Dict[str, str]] = []
try:
out = subprocess.check_output(["nmcli", "-t", "-f", "SSID,SECURITY,SIGNAL", "dev", "wifi"], text=True)
for line in out.splitlines():
if not line.strip():
continue
ssid, sec, sig = (line.split(":", 2) + ["", ""])[:3]
networks.append({"ssid": ssid, "security": sec, "signal": sig})
except Exception:
pass
return networks




def connect(ssid: str, password: str | None = None) -> bool:
try:
cmd = ["nmcli", "dev", "wifi", "connect", ssid]
if password:
cmd += ["password", password]
subprocess.check_call(cmd)
return True
except Exception:
return False