#!/usr/bin/env bash
set -euo pipefail

IMAGE_DIR="/tmp/qualidrive_qemu"
PID_FILE="${IMAGE_DIR}/qemu.pid"

if [ -f "${PID_FILE}" ]; then
    PID=$(cat "${PID_FILE}")
    if kill -0 "${PID}" 2>/dev/null; then
        echo "[INFO] Terminating QEMU NVMe instance (PID ${PID})..."
        kill -9 "${PID}" || true
    fi
    rm -f "${PID_FILE}"
fi

echo "[INFO] Cleaning up QEMU disk artifacts..."
rm -rf "${IMAGE_DIR}"
echo "[INFO] QEMU NVMe testbed successfully torn down."
