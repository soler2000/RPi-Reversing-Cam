from __future__ import annotations
boundary = b"--frame"
while not self._stop.is_set():
frame = self.latest_jpeg()
if frame is not None:
yield boundary + b"\r\n" + b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
time.sleep(max(0.001, 1.0 / max(1, self._fps)))


def _run(self) -> None:
pc = Picamera2()
transform = Transform(hflip=False, vflip=False)
config = pc.create_video_configuration(
main={"size": (self._w, self._h), "format": "RGB888"},
transform=transform,
)
pc.configure(config)
pc.start()


# Timing
target_dt = 1.0 / float(max(1, self._fps))
next_t = time.time()


try:
while not self._stop.is_set():
frame = pc.capture_array()
if frame is None:
continue


# Rotate if requested (180° increments for MVP)
if self._rot == 180:
frame = np.ascontiguousarray(np.rot90(frame, 2))


# Simple luma for lux estimation
# Convert RGB -> luma 0..255 (Rec.601)
luma = (0.299 * frame[:, :, 0] + 0.587 * frame[:, :, 1] + 0.114 * frame[:, :, 2]).mean()
lux = approx_lux_from_frame_mean(float(luma))


# Stats overlay text (optional)
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