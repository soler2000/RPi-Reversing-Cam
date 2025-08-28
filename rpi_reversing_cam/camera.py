from __future__ import annotations
from typing import Dict, Any
import io, time
import numpy as np
from PIL import Image
from picamera2 import Picamera2
from .overlay import apply_overlay

class Camera:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        self.pc: Picamera2 | None = None
        self._configure()

    def _configure(self):
        cam = self.cfg.get("camera", {})
        w = int(cam.get("width", 640)); h = int(cam.get("height", 480))
        fps = int(cam.get("fps", 20)); rot = int(cam.get("rotation", 0))
        if self.pc is None:
            self.pc = Picamera2()
        # RGB888 gives easy numpy RGB frames
        cfg = self.pc.create_video_configuration(main={"size": (w, h), "format": "RGB888"})
        self.pc.configure(cfg)
        # rotation is applied after capture by numpy rot90 to keep things simple
        self.rot = rot
        self.fps = max(1, min(fps, 30))
        if not self.pc.started:
            self.pc.start()
            time.sleep(0.2)

    def reconfigure(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        # Stop and reconfigure cleanly
        if self.pc:
            try: self.pc.stop()
            except Exception: pass
        self._configure()

    def jpeg_frame(self) -> bytes:
        assert self.pc is not None
        arr = self.pc.capture_array("main")  # HxWx3 RGB
        if self.rot in (90, 180, 270):
            k = {90:1, 180:2, 270:3}[self.rot]
            arr = np.rot90(arr, k)
        arr = apply_overlay(arr, self.cfg)
        # encode JPEG via Pillow
        im = Image.fromarray(arr, mode="RGB")
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=85)
        return buf.getvalue()
