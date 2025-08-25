import threading, time, math, subprocess, os, psutil
from . import settings
from piina219 import INA219 as _INA219  # alias, but we’ll fallback if not found
try:
    from ina219 import INA219  # pi-ina219 naming
except Exception:
    INA219 = _INA219  # either way
import board, busio
try:
    import adafruit_vl53l1x
except Exception:
    adafruit_vl53l1x = None
import numpy as np

class SensorState:
    def __init__(self):
        self.voltage = None
        self.current = None
        self.power = None
        self.batt_pct = None
        self.distance_m = None
        self.cpu_temp_c = None
        self.cpu_load = None
        self.wifi_ssid = None
        self.wifi_rssi = None
        self.led_status = "off"
        self.lux_approx = None  # 0..255 (mean luma)
        self.ap_mode = False

S = SensorState()

def _read_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp","r") as f:
            return int(f.read().strip())/1000.0
    except Exception:
        return None

def _read_wifi_info():
    ssid, rssi = None, None
    try:
        out = subprocess.check_output(["nmcli","-t","-f","ACTIVE,SSID,SIGNAL","dev","wifi"], text=True, timeout=2)
        for line in out.strip().splitlines():
            active, s, sig = line.split(':', 2)
            if active == "yes":
                ssid, rssi = s, int(sig)
                break
    except Exception:
        pass
    return ssid, rssi

def _map_pct(v, vmin, vmax):
    if v is None: return None
    return float(max(0.0, min(100.0, ( (v - vmin) / max(0.01, (vmax - vmin)) ) * 100.0)))

class SensorThread(threading.Thread):
    def __init__(self, cam_ref):
        super().__init__(daemon=True)
        self._stop = threading.Event()
        self.cam_ref = cam_ref
        self._i2c = busio.I2C(board.SCL, board.SDA)
        # INA219 @ 0x43
        self._ina = INA219(shunt_ohms=0.1, address=0x43, busnum=None)
        self._ina.configure()
        # VL53L1X @ 0x29
        if adafruit_vl53l1x:
            self._tof = adafruit_vl53l1x.VL53L1X(self._i2c)
            self._tof.start_ranging()
        else:
            self._tof = None

    def stop(self): self._stop.set()

    def run(self):
        last_batt_log = 0
        while not self._stop.is_set():
            try:
                S.voltage = self._ina.voltage()  # V
                S.current = self._ina.current() / 1000.0  # A (library returns mA)
                S.power   = self._ina.power() / 1000.0    # W (mW -> W)
            except Exception:
                pass

            vmin = float(settings.get("battery.v_min", 3.3))
            vmax = float(settings.get("battery.v_max", 4.2))
            S.batt_pct = _map_pct(S.voltage, vmin, vmax)

            # Distance (in meters, 1 decimal place)
            if self._tof:
                try:
                    mm = self._tof.distance
                    S.distance_m = None if mm is None else max(0.0, mm/1000.0)
                except Exception:
                    S.distance_m = None

            S.cpu_temp_c = _read_cpu_temp()
            l1, l5, l15 = psutil.getloadavg()
            S.cpu_load = l1
            S.wifi_ssid, S.wifi_rssi = _read_wifi_info()

            # Approx "lux": pull from camera mean luma (0..255)
            frm = self.cam_ref() if self.cam_ref else None
            if frm is not None:
                gray = np.mean(0.2126*frm[:,:,2] + 0.7152*frm[:,:,1] + 0.0722*frm[:,:,0])
                S.lux_approx = float(gray)

            # periodic battery history (1 min)
            now = int(time.time())
            if now - last_batt_log >= 60 and S.batt_pct is not None:
                settings.log_battery(now, S.batt_pct, S.voltage or 0, S.current or 0, S.power or 0)
                last_batt_log = now

            time.sleep(0.5)

def get_state():
    return S
