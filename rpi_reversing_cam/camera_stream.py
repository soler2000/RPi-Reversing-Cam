from __future__ import annotations
import io, threading, time
from typing import Dict, Any, Tuple, Optional

from PIL import Image
from picamera2 import Picamera2
from libcamera import Transform

from .overlay import draw_overlays
from . import config as cfg_mod

class CameraStream:
    def __init__(self):
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._run = False

        self._picam: Optional[Picamera2] = None
        self._latest_jpeg: Optional[bytes] = None

        self._cfg: Dict[str, Any] = {}
        self._overlay_only: Dict[str, Any] = {}
        self._cam_tuple: Tuple[int,int,int,int,int] = (640,480,20,0,85)  # w,h,fps,rot,jpeg_q

        self._pending_cfg: Optional[Dict[str, Any]] = None
        self._restart_req = False
        self._restarting = False

    # ---------- public API ----------
    def start(self):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._cfg = cfg_mod.get() or {}
            self._overlay_only = (self._cfg.get("overlay") or {})
            self._run = True
            self._thread = threading.Thread(target=self._loop, name="CameraStream", daemon=True)
            self._thread.start()

    def stop(self):
        with self._lock:
            self._run = False
        t = self._thread
        if t:
            t.join(timeout=2.0)
        self._shutdown_camera()

    def update_settings(self, new_cfg: Dict[str, Any]):
        with self._lock:
            self._overlay_only = (new_cfg.get("overlay") or {})
            new_cam_tuple = self._read_cam_tuple(new_cfg.get("camera") or {})
            if new_cam_tuple != self._cam_tuple:
                self._pending_cfg = new_cfg
                self._restart_req = True
            else:
                self._cfg = new_cfg  # overlay-only change

    def latest_jpeg(self) -> Optional[bytes]:
        with self._lock:
            return self._latest_jpeg

    def mjpeg_generator(self):
        boundary = b"--frame"
        while True:
            buf = self.latest_jpeg()
            if buf is None:
                time.sleep(0.03)
                continue
            yield boundary + b"\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(buf)).encode() + b"\r\n\r\n" + buf + b"\r\n"
            time.sleep(0.001)

    # ---------- internal ----------
    def _loop(self):
        try:
            with self._lock:
                self._apply_camera_cfg_locked(self._cfg.get("camera") or {})
            print("[CameraStream] camera started")

            last_overlay_log = 0.0
            while True:
                with self._lock:
                    if not self._run:
                        break
                    if self._restart_req and not self._restarting:
                        self._restarting = True
                        if self._pending_cfg is not None:
                            self._cfg = self._pending_cfg
                            self._pending_cfg = None
                        try:
                            self._reconfigure_locked(self._cfg.get("camera") or {})
                            print(f"[CameraStream] camera reconfigured to {self._cam_tuple}")
                        except Exception as e:
                            print("[CameraStream] reconfigure failed:", e)
                        finally:
                            self._restart_req = False
                            self._restarting = False

                    picam = self._picam

                if not picam:
                    time.sleep(0.05)
                    continue

                try:
                    arr = picam.capture_array("main")  # RGB888
                except Exception as e:
                    print("[CameraStream] capture error:", e)
                    time.sleep(0.1)
                    continue

                img = Image.fromarray(arr, mode="RGB")

                try:
                    img = draw_overlays(img, {"overlay": self._overlay_only})
                except Exception as e:
                    now = time.time()
                    if now - last_overlay_log > 2.0:
                        print("[CameraStream] overlay error:", e)
                        last_overlay_log = now

                out = io.BytesIO()
                q = self._cam_tuple[4]
                img.save(out, format="JPEG", quality=q, optimize=False)
                with self._lock:
                    self._latest_jpeg = out.getvalue()
        finally:
            self._shutdown_camera()
            print("[CameraStream] stopped")

    def _read_cam_tuple(self, cam: Dict[str, Any]) -> Tuple[int,int,int,int,int]:
        w = int(cam.get("width", 640))
        h = int(cam.get("height", 480))
        fps = max(1, min(60, int(cam.get("fps", 20))))
        rot = 180 if int(cam.get("rotation_deg", 0)) == 180 else 0
        q = max(60, min(95, int(cam.get("jpeg_quality", 85))))
        return (w, h, fps, rot, q)

    def _open_and_configure(self, w: int, h: int, fps: int, rot: int) -> Picamera2:
        last_exc = None
        for attempt in range(1, 4):  # 3 attempts with backoff
            try:
                pc = Picamera2()
                transform = Transform(hflip=(rot == 180), vflip=(rot == 180))
                conf = pc.create_preview_configuration(
                    main={"size": (w, h), "format": "RGB888"},
                    transform=transform
                )
                pc.configure(conf)
                try:
                    frame_time_us = int(1_000_000 / max(1, fps))
                    pc.set_controls({"FrameDurationLimits": (frame_time_us, frame_time_us)})
                except Exception:
                    pass
                pc.start()
                return pc
            except Exception as e:
                last_exc = e
                print(f"[CameraStream] open retry {attempt}/3 after shutdown: {e}")
                try:
                    pc.close()  # type: ignore
                except Exception:
                    pass
                time.sleep(0.4 * attempt)  # backoff
        raise RuntimeError(f"Camera init failed after retries: {last_exc}")

    def _apply_camera_cfg_locked(self, cam: Dict[str, Any]):
        self._shutdown_camera()
        # allow libcamera to fully release resources before re-open
        time.sleep(0.25)

        self._cam_tuple = self._read_cam_tuple(cam)
        w, h, fps, rot, _ = self._cam_tuple
        self._picam = self._open_and_configure(w, h, fps, rot)

    def _reconfigure_locked(self, cam: Dict[str, Any]):
        self._apply_camera_cfg_locked(cam)

    def _shutdown_camera(self):
        if self._picam:
            try:
                self._picam.stop()
            except Exception:
                pass
            try:
                self._picam.close()
            except Exception:
                pass
            self._picam = None
