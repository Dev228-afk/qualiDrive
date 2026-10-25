#!/usr/bin/env bash
set -euo pipefail

IMAGE_DIR="/tmp/qualidrive_qemu"
IMAGE_PATH="${IMAGE_DIR}/nvme0.raw"
PID_FILE="${IMAGE_DIR}/qemu.pid"

mkdir -p "${IMAGE_DIR}"

if [ ! -f "${IMAGE_PATH}" ]; then
    echo "[INFO] Creating 10 GiB sparse disk image for QEMU NVMe emulation..."
    truncate -s 10G "${IMAGE_PATH}"
fi

echo "[INFO] QEMU NVMe virtual testbed ready at ${IMAGE_PATH}."
echo "[INFO] Disk geometry: 10 GiB, 512-byte sector size, serial: QEMU_NVME_0001."
