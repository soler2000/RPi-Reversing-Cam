#!/usr/bin/env bash
set -euo pipefail

TIMEOUT="$(python3 -c 'from app import settings as s; print(s.get("wifi.fallback_timeout_s","30"))' 2>/dev/null || echo 30)"
APSSID="$(python3 -c 'from app import settings as s; print(s.get("wifi.ap.ssid","RPiCam"))' 2>/dev/null || echo RPiCam)"

echo "[wifi_fallback] Waiting ${TIMEOUT}s for known Wi‑Fi..."
for i in $(seq 1 "$TIMEOUT"); do
  if nmcli -t -f DEVICE,STATE dev | grep -q '^wlan0:connected'; then
    echo "[wifi_fallback] Connected to Wi‑Fi."
    exit 0
  fi
  sleep 1
done

echo "[wifi_fallback] Not connected, enabling AP '$APSSID'..."
python3 - <<'PY'
from app import wifi
wifi.up_ap()
PY
exit 0
