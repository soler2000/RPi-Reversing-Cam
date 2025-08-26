# RPi-Reversing-Cam (MVP) — dev1


Low-latency reversing camera web app for Raspberry Pi Zero 2 W on Raspberry Pi OS **Bookworm**.


**MVP focus:**
- Live MJPEG stream with **server-side overlays** (text + configurable reversing guide lines)
- Configurable: resolution, FPS, 180° rotation, overlay text size/position, 2 lines (start/end, width, color, alpha)
- Mobile-first Flask UI (dark mode) for iPhone/iPad
- Dashboard: CPU temp & load, Wi‑Fi SSID/signal, **approx. lux** from camera
- Settings saved in **YAML** (no sqlite)
- Python venv, `systemd` service, idempotent `install.sh`


> Later milestones (scaffolded): Wi‑Fi AP fallback if no network in 30s, Wi‑Fi manager UI, battery-voltage shutdown.


## Quick start


```bash
# On the Pi (Bookworm). Clone this repo then run installer:
sudo apt update
sudo apt install -y git


git clone https://github.com/soler2000/RPi-Reversing-Cam.git
cd RPi-Reversing-Cam
# (Optionally checkout dev branch)
# git checkout dev1


sudo ./install.sh