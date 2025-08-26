from __future__ import annotations
import io
import threading
import time
from typing import Dict, Optional

import numpy as np
from PIL import Image

from . import config as cfg
from .overlay import draw_overlays
from .system_status import approx_lux_from_frame_mean, cpu_temp_c, load_avg

try:
    from picamera2 import Picamera2
    from libcamera import Transform
except Exception:  # pragma: no cover (unit tests / non-Pi envs)
    Picamera2 = None  # type: ignore
    Transform = None  # type: ignore


class CameraStream:
    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._frame_lock = threading.Lock()
        self._latest_jpeg: Optional[bytes] = None
        self._last_stats: Dict[str, float | int | str] = {}

        self._w = 640
        self._h = 480
        self._fps = 20
        self._rot = 0
        self._jpeg_q = 85

        self._pcam: Optional[Picamera2] = None

    def start(self) -> None:
        c = cfg.get()
        cam = c.get("camera", {})
        self._w = int(cam.get("width", 640))
        self._h = int(cam.get("height", 480))
        self._fps = int(cam.get("fps", 20))
        self._rot = int(cam.get("rotation_deg", 0)) % 360
        self._jpeg_q = int(cam.get("jpeg_quality", 85))

        if Picamera2 is None:
            raise RuntimeError("picamera2 not available; install python3-picamera2")

        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="CameraStream", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def update_settings(self, new_cfg: Dict) -> None:
        # MVP: restart to apply settings
        self.stop()
        self.start()

    def latest_jpeg(self) -> Optional[bytes]:
        with self._frame_lock:
            return self._latest_jpeg

    def mjpeg_generator(self):
        boundary = b"--frame"
        while not self._stop.is_set():
            frame = self.latest_jpeg()
            if frame is not None:
                yield boundary + b"\r\n" + b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            time.sleep(max(0.001, 1.0 / max(1, self._fps)))

    def _run(self) -> None:
        pc = Picamera2()
        # RGB output for PIL; rotate via numpy when needed (0/180 only for MVP)
        transform = Transform(hflip=False, vflip=False)
        config = pc.create_video_configuration(
            main={"size": (self._w, self._h), "format": "RGB888"},
            transform=transform,
        )
        pc.configure(config)
        pc.start()

        target_dt = 1.0 / float(max(1, self._fps))
        next_t = time.time()

        try:
            while not self._stop.is_set():
                frame = pc.capture_array()
                if frame is None:
                    continue

                # 180° rotation if requested
                if self._rot == 180:
                    frame = np.ascontiguousarray(np.rot90(frame, 2))

                # Compute rough lux from luma
                luma = (0.299 * frame[:, :, 0] + 0.587 * frame[:, :, 1] + 0.114 * frame[:, :, 2]).mean()
                lux = approx_lux_from_frame_mean(float(luma))

                # Optional stats string
                o = cfg.get().get("overlay", {})
                stats_text = None
                if o.get("show_stats", True):
                    t = cpu_temp_c()
                    la = load_avg()
                    stats_text = f"CPU {t:.1f}°C | load {la:.2f} | ~{lux} lux"

                pil_img = Image.fromarray(frame)
                pil_img = draw_overlays(pil_img, o, stats_text=stats_text)

                # Encode JPEG
                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=self._jpeg_q, subsampling=0)
                jpeg = buf.getvalue()

                with self._frame_lock:
                    self._latest_jpeg = jpeg
                    self._last_stats = {"lux": lux}

                # pacing
                next_t += target_dt
                sleep_t = next_t - time.time()
                if sleep_t > 0:
                    time.sleep(sleep_t)
                else:
                    next_t = time.time()
        finally:
            try:
                pc.stop()
            except Exception:
                pass