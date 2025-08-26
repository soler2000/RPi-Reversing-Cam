#!/usr/bin/env bash
VENV_DIR="${APP_DIR}/venv"
SYSTEMD_DIR="/etc/systemd/system"


# Colors
Y="\033[1;33m"; G="\033[1;32m"; R="\033[1;31m"; Z="\033[0m"


say() { echo -e "${G}==>${Z} $*"; }
warn() { echo -e "${Y}==>${Z} $*"; }
err() { echo -e "${R}==>${Z} $*"; }


require_root() {
if [[ $(id -u) -ne 0 ]]; then
err "Please run as root: sudo ./install.sh"; exit 1
fi
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
rsync -a --delete --exclude venv ./ "${APP_DIR}/"
}


setup_venv() {
say "Setting up venv at ${VENV_DIR}..."
python3 -m venv "${VENV_DIR}" || true
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install -r requirements.txt
}


install_systemd() {
say "Installing systemd units..."
install -m 0644 systemd/motion_wide.service "${SYSTEMD_DIR}/motion_wide.service"
# Optional AP fallback (disabled by default)
install -m 0644 systemd/ap_fallback.service "${SYSTEMD_DIR}/ap_fallback.service" || true
systemctl daemon-reload
systemctl enable motion_wide.service
}


create_config() {
if [[ ! -f "${APP_DIR}/config.yaml" ]]; then
say "Creating default config.yaml..."
cp config.example.yaml "${APP_DIR}/config.yaml"
else
warn "config.yaml exists; leaving as-is."
fi
}


restart_service() {
say "(Re)starting service motion_wide.service..."
systemctl stop motion_wide.service || true
systemctl start motion_wide.service
systemctl status motion_wide.service --no-pager --full || true
}


main() {
require_root
install_apt_deps
sync_project
pushd "${APP_DIR}" >/dev/null
setup_venv
create_config
install_systemd
restart_service
popd >/dev/null
say "Done. Open http://<pi-ip>:8000/"
}


main "$@"