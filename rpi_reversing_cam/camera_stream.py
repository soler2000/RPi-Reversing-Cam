from __future__ import annotations
import io, threading, time
from typing import Dict, Optional
import numpy as np
from PIL import Image
from . import config as cfg
from .overlay import draw_overlays
from .system_status import approx_lux_from_frame_mean, cpu_temp_c, load_avg

try:
    from picamera2 import Picamera2
    from libcamera import Transform
except Exception:
    Picamera2 = None  # type: ignore
    Transform = None  # type: ignore

class CameraStream:
    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._frame_lock = threading.Lock()
        self._latest_jpeg: Optional[bytes] = None
        self._last_stats: Dict[str, float | int | str] = {}
        self._w = 640; self._h = 480; self._fps = 20; self._rot = 0; self._jpeg_q = 85
        self._pcam: Optional[Picamera2] = None

    def start(self) -> None:
        c = cfg.get() or {}
        cam = c.get("camera") or {}
        if not isinstance(cam, dict):
            cam = {}
        self._w = int(cam.get("width", 640))
        self._h = int(cam.get("height", 480))
        self._fps = int(cam.get("fps", 20))
        self._rot = int(cam.get("rotation_deg", 0)) % 360
        self._jpeg_q = int(cam.get("jpeg_quality", 85))
        if self._thread and self._thread.is_alive(): return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="CameraStream", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def update_settings(self, new_cfg: Dict) -> None:
        self.stop(); self.start()

    def latest_jpeg(self) -> Optional[bytes]:
        with self._frame_lock: return self._latest_jpeg

    def mjpeg_generator(self):
        boundary = b"--frame"
        while not self._stop.is_set():
            frame = self.latest_jpeg()
            if frame is not None:
                yield boundary + b"\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            time.sleep(max(0.001, 1.0 / max(1, self._fps)))

    def _run(self) -> None:
        use_camera = Picamera2 is not None
        if use_camera:
            pc = Picamera2()
            cfg_video = pc.create_video_configuration(main={"size": (self._w, self._h), "format": "RGB888"},
                                                      transform=Transform(hflip=False, vflip=False))
            pc.configure(cfg_video); pc.start()
        else:
            pc = None  # type: ignore

        target_dt = 1.0 / float(max(1, self._fps)); next_t = time.time()
        try:
            while not self._stop.is_set():
                if use_camera:
                    frame = pc.capture_array()
                    if frame is None: continue
                    if self._rot == 180:
                        frame = np.ascontiguousarray(np.rot90(frame, 2))
                else:
                    frame = np.zeros((self._h, self._w, 3), dtype=np.uint8)
                    pos = int((time.time() * 50) % self._w)
                    frame[10:30, max(0, pos-40):min(self._w, pos+40), :] = 255

                luma = (0.299*frame[:,:,0] + 0.587*frame[:,:,1] + 0.114*frame[:,:,2]).mean()
                lux = approx_lux_from_frame_mean(float(luma))

                o = (cfg.get() or {}).get("overlay") or {}
                if not isinstance(o, dict): o = {}
                stats_text = None
                if o.get("show_stats", True):
                    stats_text = f"CPU {cpu_temp_c():.1f}°C | load {load_avg():.2f} | ~{lux} lux"

                pil_img = Image.fromarray(frame)
                pil_img = draw_overlays(pil_img, o, stats_text=stats_text)

                buf = io.BytesIO(); pil_img.save(buf, format="JPEG", quality=self._jpeg_q, subsampling=0)
                jpeg = buf.getvalue()
                with self._frame_lock:
                    self._latest_jpeg = jpeg
                    self._last_stats = {"lux": lux}

                next_t += target_dt
                sleep_t = next_t - time.time()
                time.sleep(sleep_t if sleep_t > 0 else 0)
                if sleep_t <= 0: next_t = time.time()
        finally:
            if use_camera:
                try: pc.stop()
                except Exception: pass
