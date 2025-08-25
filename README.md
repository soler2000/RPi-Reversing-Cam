# RPi-Reversing-Cam

Low-latency reversing camera for **Raspberry Pi Zero 2 W (Bookworm)** with:
- Live MJPEG video with **server-side overlays** (distance, battery, CPU, 2 adjustable guide lines)
- **VL53L1X** TOF (0x29) distance displayed (m, 1 decimal) on video and dashboard
- **INA219** (0x43) voltage/current/power + % estimate
- 16x **NeoPixel ring** on GPIO18 (pin 12): white illumination and distance-warning alternating **white ↔ red** with frequency mapping **0.1–20 Hz** (configurable)
- Flask web UI (dark, mobile-first), dashboard updates every 2s
- **Wi‑Fi fallback** AP if not connected within 30s
- Auto-start via systemd (`motion_wide.service`)

## Quick start
```bash
git clone https://github.com/solder2000/RPi-Reversing-Cam.git
cd RPi-Reversing-Cam
bash scripts/install.sh
sudo systemctl start motion_wide.service
