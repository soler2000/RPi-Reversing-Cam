import subprocess, shlex
from . import settings

def nm(cmd):
    return subprocess.check_output(["bash","-lc", cmd], text=True, timeout=10)

def scan():
    out = nm("nmcli -t -f SSID,SIGNAL,SECURITY dev wifi")
    nets = []
    seen = set()
    for line in out.strip().splitlines():
        ssid, sig, sec = (line.split(':',2)+["","",""])[:3]
        if ssid and ssid not in seen:
            nets.append({"ssid": ssid, "signal": int(sig or 0), "security": sec})
            seen.add(ssid)
    return sorted(nets, key=lambda n: n["signal"], reverse=True)

def save_and_connect(ssid, password=None):
    # create connection profile and connect
    if password:
        nm(f"nmcli dev wifi connect {shlex.quote(ssid)} password {shlex.quote(password)}")
    else:
        nm(f"nmcli dev wifi connect {shlex.quote(ssid)}")
    return True

def ensure_ap_exists():
    ssid = settings.get("wifi.ap.ssid","RPiCam")
    pwd  = settings.get("wifi.ap.password","raspberry")
    # ensure AP connection profile exists
    try:
        nm("nmcli -t -f NAME con show | grep -q '^rpirc-ap$' || "
           f"nmcli con add type wifi ifname wlan0 con-name rpirc-ap autoconnect no ssid {shlex.quote(ssid)}")
        nm("nmcli con modify rpirc-ap 802-11-wireless.mode ap 802-11-wireless.band bg ipv4.method shared")
        nm(f"nmcli con modify rpirc-ap wifi-sec.key-mgmt wpa-psk wifi-sec.psk {shlex.quote(pwd)}")
    except Exception as e:
        return False
    return True

def up_ap():
    ensure_ap_exists()
    nm("nmcli con up rpirc-ap || true")
    return True

def down_ap():
    nm("nmcli con down rpirc-ap || true")
    return True

def is_connected():
    try:
        out = nm("nmcli -t -f DEVICE,STATE dev | grep '^wlan0'")
        return ":connected" in out
    except Exception:
        return False
