#!/usr/bin/env bash
set -euo pipefail

APP_NAME="${APP_NAME:-rpi-reversing-cam}"
APP_DIR="${APP_DIR:-/opt/${APP_NAME}}"
VENV_DIR="${VENV_DIR:-${APP_DIR}/venv}"
SYSTEMD_DIR="/etc/systemd/system"

say()  { echo -e "\033[1;32m==>\033[0m $*"; }
warn() { echo -e "\033[1;33m==>\033[0m $*"; }
err()  { echo -e "\033[1;31m==>\033[0m $*"; }

require_root() { [[ $(id -u) -eq 0 ]] || { err "Run as root: sudo ./install.sh"; exit 1; }; }

validate_paths() {
  if [[ -z "${APP_DIR}" ]]; then err "APP_DIR is empty. Aborting."; exit 1; fi
  if [[ "${APP_DIR}" == "/" ]]; then err "APP_DIR cannot be '/'. Aborting."; exit 1; fi
  if [[ "${APP_DIR}" != /* ]]; then err "APP_DIR must be an absolute path. Aborting."; exit 1; fi
}

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
  # resolve script dir safely
  local SRC_DIR; SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  # write-protect against accidental '/' by verifying destination
  [[ -d "${APP_DIR}" && "${APP_DIR}" == /opt/* ]] || { err "Refusing to sync to ${APP_DIR}"; exit 1; }
  rsync -a --delete --exclude venv --exclude .git --exclude .github \
    "${SRC_DIR}/" "${APP_DIR}/"
}

detect_module_path() {
  local ROOT="${APP_DIR}"
  if [[ -f "${ROOT}/rpi_reversing_cam/app.py" ]]; then
    echo "rpi_reversing_cam.app:create_app"
  elif [[ -f "${ROOT}/RPi_Reversing_Cam/rpi_reversing_cam/app.py" ]]; then
    echo "RPi_Reversing_Cam.rpi_reversing_cam.app:create_app"
  else
    err "Could not find app.py under expected paths."; exit 1
  fi
}

install_systemd() {
  say "Installing systemd unit..."
  local MODULE; MODULE="$(detect_module_path)"
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
  say "Setting up venv at ${VENV_DIR}..."
  python3 -m venv "${VENV_DIR}" || true
  "${VENV_DIR}/bin/pip" install --upgrade pip
  "${VENV_DIR}/bin/pip" install -r requirements.txt
}

create_config() {
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
  require_root
  validate_paths
  install_apt_deps
  sync_project
  ( cd "${APP_DIR}" && setup_venv )
  create_config
  install_systemd
  restart_service
  say "Done. Open http://<pi-ip>:8000/"
}
main "$@"