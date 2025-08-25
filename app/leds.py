import threading, time, math
from . import settings
from .sensors import get_state
import board, neopixel

class LedController(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self._stop = threading.Event()
        self.n = int(settings.get("led.count", 16))
        pin = getattr(board, f"D{settings.get('led.pin','18')}")
        self.pixels = neopixel.NeoPixel(pin, self.n, brightness=float(settings.get("led.brightness", 0.4)),
                                        auto_write=False)
        self._phase = 0
        self._last_toggle = time.monotonic()
        self._on_white = True

    def stop(self):
        self._stop.set()
        try:
            self.pixels.fill((0,0,0)); self.pixels.show()
        except Exception:
            pass

    def _hex_to_rgb(self, hx):
        hx = hx.lstrip("#")
        return tuple(int(hx[i:i+2], 16) for i in (0,2,4))

    def run(self):
        white = self._hex_to_rgb(settings.get("led.white_color","#FFFFFF"))
        red   = self._hex_to_rgb(settings.get("led.red_color","#FF0000"))
        master = settings.get("led.master_on","1") == "1"
        while not self._stop.is_set():
            state = get_state()
            master = settings.get("led.master_on","1") == "1"
            if not master:
                self.pixels.fill((0,0,0)); self.pixels.show(); time.sleep(0.1); continue

            # Illumination on dark
            illum = False
            if settings.get("led.illum_on_dark","1") == "1" and state.lux_approx is not None:
                illum = state.lux_approx < float(settings.get("led.dark_lux_threshold","40"))

            # Distance warning
            warn_enabled = settings.get("warning.enabled","1") == "1"
            fmin = float(settings.get("warning.freq_min_hz","0.1"))
            fmax = float(settings.get("warning.freq_max_hz","20.0"))
            dmin = float(settings.get("distance.min_m","0.2"))
            dmax = float(settings.get("distance.max_m","4.0"))
            f = 0.0
            if warn_enabled and state.distance_m is not None:
                d = max(dmin, min(dmax, state.distance_m))
                # map dmax->fmin, dmin->fmax
                f = fmin + ( (dmax - d) / max(0.001, (dmax - dmin)) ) * (fmax - fmin)

            color = white
            now = time.monotonic()
            if f > 0:
                # alternate white <-> red according to frequency f
                period = 1.0 / f
                if now - self._last_toggle >= period / 2.0:
                    self._on_white = not self._on_white
                    self._last_toggle = now
                color = white if self._on_white else red
            elif illum:
                color = white
            else:
                color = (0,0,0)

            self.pixels.fill(color)
            self.pixels.show()
            state.led_status = "white" if color == white else ("red" if color==red else "off")
            time.sleep(0.01)
