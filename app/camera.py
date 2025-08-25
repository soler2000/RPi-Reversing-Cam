import threading, time, io, cv2, numpy as np
from picamera2 import Picamera2
from . import settings
from .sensors import get_state
from .motion import MotionDetector

class Camera:
    def __init__(self):
        self.picam = Picamera2()
        self.frame_lock = threading.Lock()
        self.frame = None
        self.motion = MotionDetector()
        self.running = False

    def start(self):
        if self.running: return
        w,h = [int(x) for x in settings.get("camera.resolution","1280x720").split('x')]
        fps = int(settings.get("camera.framerate","30"))
        config = self.picam.create_video_configuration(main={"size":(w,h)}, controls={"FrameRate": fps})
        self.picam.configure(config)
        self.picam.start()
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        try:
            self.picam.stop()
        except: pass
        self.running = False

    def latest(self):
        with self.frame_lock:
            return None if self.frame is None else self.frame.copy()

    def _draw_guidelines(self, img):
        for i in (1,2):
            color = settings.get(f"guideline{i}.color","#00FF00").lstrip('#')
            r = int(color[0:2], 16); g = int(color[2:4], 16); b = int(color[4:6], 16)
            alpha = float(settings.get(f"guideline{i}.alpha","0.6"))
            thick = int(settings.get(f"guideline{i}.width","4"))
            sx,sy = [float(x) for x in settings.get(f"guideline{i}.start","0.25,0.8").split(',')]
            ex,ey = [float(x) for x in settings.get(f"guideline{i}.end","0.25,0.95").split(',')]
            h,w = img.shape[:2]
            p1 = (int(sx*w), int(sy*h))
            p2 = (int(ex*w), int(ey*h))
            overlay = img.copy()
            cv2.line(overlay, p1, p2, (b,g,r), thickness=thick, lineType=cv2.LINE_AA)
            cv2.addWeighted(overlay, alpha, img, 1-alpha, 0, img)

    def _overlay_texts(self, img):
        st = get_state()
        if settings.get("overlay.enabled","1") != "1": return
        xnorm, ynorm = [float(x) for x in settings.get("overlay.text_pos","0.02,0.10").split(',')]
        scale = float(settings.get("overlay.text_scale","1.0"))
        x = int(xnorm*img.shape[1]); y = int(ynorm*img.shape[0])
        lines = []
        if settings.get("overlay.show_distance","1")=="1" and st.distance_m is not None:
            lines.append(f"Dist: {st.distance_m:.1f} m")
        if settings.get("overlay.show_battery","1")=="1" and st.batt_pct is not None:
            lines.append(f"Batt: {st.batt_pct:.0f}% ({(st.voltage or 0):.2f}V)")
        if settings.get("overlay.show_cpu","1")=="1" and st.cpu_temp_c is not None:
            lines.append(f"CPU: {st.cpu_temp_c:.1f}C load {st.cpu_load:.2f}")

        for i,txt in enumerate(lines):
            cv2.putText(img, txt, (x, y + i*int(28*scale)), cv2.FONT_HERSHEY_SIMPLEX,
                        scale, (0,0,0), thickness=3, lineType=cv2.LINE_AA)
            cv2.putText(img, txt, (x, y + i*int(28*scale)), cv2.FONT_HERSHEY_SIMPLEX,
                        scale, (255,255,255), thickness=1, lineType=cv2.LINE_AA)

    def _maybe_rotate(self, img):
        rot = int(settings.get("camera.rotation","0"))
        if rot % 360 == 180:
            return cv2.rotate(img, cv2.ROTATE_180)
        return img

    def _loop(self):
        last_motion_log = 0
        while self.running:
            frame = self.picam.capture_array("main")
            frame = self._maybe_rotate(frame)
            # motion score + log occasionally
            mscore = self.motion.tick(frame)
            now = int(time.time())
            if now - last_motion_log >= 5:  # sample coarsely
                from .settings import log_motion
                log_motion(now, float(mscore))
                last_motion_log = now
            self._draw_guidelines(frame)
            self._overlay_texts(frame)
            with self.frame_lock:
                self.frame = frame

    def mjpeg_generator(self, quality=80):
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        while True:
            frame = self.latest()
            if frame is None:
                time.sleep(0.01); continue
            ok, jpg = cv2.imencode('.jpg', frame, encode_param)
            if not ok:
                continue
            b = jpg.tobytes()
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n"
                   b"Content-Length: " + str(len(b)).encode() + b"\r\n\r\n" +
                   b + b"\r\n")
