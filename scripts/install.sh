#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.."; pwd)"
cd "$APP_DIR"

echo "[+] Updating apt and installing system deps..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip python3-opencv python3-libcamera python3-picamera2 \
                        network-manager dnsmasq-base i2c-tools git

echo "[+] Enabling camera & I2C..."
sudo raspi-config nonint do_i2c 0 || true
sudo raspi-config nonint do_camera 0 || true

echo "[+] Python venv & deps..."
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip wheel
pip install -r requirements.txt

echo "[+] Set permissions (NeoPixel requires root via PWM/DMA)"
sudo usermod -aG video,i2c,gpio pi || true

echo "[+] Initialize DB..."
. .venv/bin/activate
python -m db.migrations
deactivate

echo "[+] Install systemd service..."
sudo install -m 0644 -o root -g root systemd/motion_wide.service /etc/systemd/system/motion_wide.service
sudo systemctl daemon-reload
sudo systemctl enable motion_wide.service

echo "[+] Install Wi‑Fi fallback service (rc-local style via systemd)"
sudo install -m 0755 -o root -g root scripts/wifi_fallback.sh /usr/local/bin/rpi_wifi_fallback.sh

echo "[+] Cleanup old files (if any)..."
# (Example: remove obsolete configs)
sudo rm -f /etc/systemd/system/old_motion.service 2>/dev/null || true

echo "[+] Done. Start service:"
echo "    sudo systemctl start motion_wide.service"
