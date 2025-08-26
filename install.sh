#!/usr/bin/env bash
set -euo pipefail

APP_NAME="${APP_NAME:-rpi-reversing-cam}"
APP_DIR="${APP_DIR:-/opt/${APP_NAME}}"
VENV_DIR="${VENV_DIR:-${APP_DIR}/venv}"
SYSTEMD_DIR="/etc/systemd/system"

say(){ echo -e "\033[1;32m==>\033[0m $*"; }
warn(){ echo -e "\033[1;33m==>\033[0m $*"; }
err(){ echo -e "\033[1;31m==>\033[0m $*"; }

[[ $(id -u) -eq 0 ]] || { err "Run as root: sudo ./install.sh"; exit 1; }

# Safety guards
[[ -n "${APP_DIR}" ]] || { err "APP_DIR is empty"; exit 1; }
[[ "${APP_DIR}" != "/" ]] || { err "APP_DIR cannot be /"; exit 1; }
[[ "${APP_DIR}" == /* ]] || { err "APP_DIR must be absolute"; exit 1; }

install_apt_deps() {
  say "Installing APT dependencies..."
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3-picamera2 libcamera-tools python3-pil python3-numpy \
    network-manager fonts-dejavu python3-venv rsync
}

sync_project() {
  say "Syncing project to ${APP_DIR} (clean)..."
  mkdir -p "${APP_DIR}"
  local SRC_DIR; SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  [[ -d "${APP_DIR}" && "${APP_DIR}" == /opt/* ]] || { err "Refusing to sync to ${APP_DIR}"; exit 1; }
  rsync -a --delete --exclude venv --exclude .git --exclude .github \
    "${SRC_DIR}/" "${APP_DIR}/"
}

detect_module() {
  if [[ -f "${APP_DIR}/rpi_reversing_cam/app.py" ]]; then
    echo "rpi_reversing_cam.app:create_app"
  elif [[ -f "${APP_DIR}/RPi_Reversing_Cam/rpi_reversing_cam/app.py" ]]; then
    echo "RPi_Reversing_Cam.rpi_reversing_cam.app:create_app"
  else
    err "Cannot find app.py in expected paths"; exit 1
  fi
}

install_systemd() {
  say "Installing systemd unit..."
  local MODULE; MODULE="$(detect_module)"
  cat >"${SYSTEMD_DIR}/motion_wide.service" <<UNIT
[Unit]
Description=RPi Reversing Cam Web App (motion_wide)
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
User=root
Group=video
Environment=PYTHONUNBUFFERED=1
WorkingDirectory=${APP_DIR}
ExecStart=${VENV_DIR}/bin/waitress-serve --host=0.0.0.0 --port=8000 ${MODULE}
Restart=on-failure
[Install]
WantedBy=multi-user.target
UNIT
  systemctl daemon-reload
  systemctl enable motion_wide.service
}

setup_venv() {
  say "Setting up venv at ${VENV_DIR} (with system site-packages for picamera2)..."
  python3 -m venv --system-site-packages "${VENV_DIR}" || true
  "${VENV_DIR}/bin/pip" install --upgrade pip
  "${VENV_DIR}/bin/pip" install -r "${APP_DIR}/requirements.txt"
}

ensure_config() {
  if [[ ! -f "${APP_DIR}/config.yaml" ]]; then
    say "Creating default config.yaml..."
    cp "${APP_DIR}/config.example.yaml" "${APP_DIR}/config.yaml"
  else
    warn "config.yaml exists; leaving as-is."
  fi
}

restart_service() {
  say "(Re)starting motion_wide.service..."
  systemctl stop motion_wide.service || true
  systemctl start motion_wide.service
  systemctl status motion_wide.service --no-pager --full || true
}

main() {
  install_apt_deps
  sync_project
  setup_venv
  ensure_config
  install_systemd
  restart_service
  say "Done. Open http://<pi-ip>:8000/"
}
main "$@"