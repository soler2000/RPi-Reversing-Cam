from __future__ import annotations
import subprocess
from typing import List, Dict, Optional

def _run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()

def scan_networks(ifname: str = "wlan0") -> List[Dict[str, str]]:
    """Return a list of visible Wi-Fi networks using nmcli."""
    nets: List[Dict[str, str]] = []
    try:
        # Ask NetworkManager to rescan and print concise table
        _run(["nmcli", "device", "wifi", "rescan", "ifname", ifname])
        out = _run(["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list", "ifname", ifname])
        for line in out.splitlines():
            parts = line.split(":")
            if len(parts) >= 4:
                nets.append({
                    "in_use": "yes" if parts[0].strip() == "*" else "no",
                    "ssid": parts[1].strip(),
                    "signal": parts[2].strip(),
                    "security": parts[3].strip(),
                })
    except Exception:
        pass
    return nets

def current_connection(ifname: str = "wlan0") -> Dict[str, str]:
    """Return current connection SSID and IP if available."""
    info: Dict[str, str] = {}
    try:
        out = _run(["nmcli", "-t", "-f", "GENERAL.CONNECTION,GENERAL.STATE,IP4.ADDRESS", "device", "show", ifname])
        for line in out.splitlines():
            if line.startswith("GENERAL.CONNECTION:"):
                info["ssid"] = line.split(":", 1)[1].strip()
            elif line.startswith("GENERAL.STATE:"):
                info["state"] = line.split(":", 1)[1].strip()
            elif line.startswith("IP4.ADDRESS[1]:") or line.startswith("IP4.ADDRESS:"):
                info["ip"] = line.split(":", 1)[1].split("/", 1)[0].strip()
    except Exception:
        pass
    return info

def connect_network(ssid: str, psk: Optional[str] = None, ifname: str = "wlan0") -> bool:
    """Connect to a Wi-Fi network via NetworkManager."""
    try:
        if psk:
            _run(["nmcli", "device", "wifi", "connect", ssid, "password", psk, "ifname", ifname])
        else:
            _run(["nmcli", "device", "wifi", "connect", ssid, "ifname", ifname])
        return True
    except subprocess.CalledProcessError:
        return False

def set_ap_mode(ssid: str, password: str, ifname: str = "wlan0") -> bool:
    """Start an AP (hotspot) using nmcli. Returns True on success."""
    try:
        _run(["nmcli", "device", "wifi", "hotspot", "ifname", ifname, "ssid", ssid, "password", password])
        return True
    except subprocess.CalledProcessError:
        return False

def disable_ap_mode() -> None:
    """Stop and remove the default 'Hotspot' connection if present."""
    try:
        # Down first; then delete if it exists
        _run(["nmcli", "connection", "down", "Hotspot"])
    except Exception:
        pass
    try:
        _run(["nmcli", "connection", "delete", "Hotspot"])
    except Exception:
        pass