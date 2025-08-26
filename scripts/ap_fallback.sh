#!/usr/bin/env bash
set -euo pipefail
# Simple connectivity probe; if offline for >30s, create a hotspot via NetworkManager.
# NOTE: This is a stub; refine for your environment before enabling the service.


IFACE="wlan0"
SSID="RPi-Cam"
PASS="reverse1234"
TIMEOUT=30


ping -c1 -W1 1.1.1.1 >/dev/null 2>&1 && exit 0
sleep "${TIMEOUT}"
ping -c1 -W1 1.1.1.1 >/dev/null 2>&1 && exit 0


# Bring up hotspot (requires NetworkManager)
if command -v nmcli >/dev/null 2>&1; then
nmcli dev wifi hotspot ifname "${IFACE}" ssid "${SSID}" password "${PASS}" || true
fi