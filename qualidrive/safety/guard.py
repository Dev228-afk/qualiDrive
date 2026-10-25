"""
Safety guardrails and device whitelisting for NVMe destructive and non-destructive qualification.
"""

import json
import os
import shutil
import subprocess
from typing import Tuple, List, Set, Optional


class SafetyError(Exception):
    pass


class SafetyGuard:
    def __init__(self, whitelist: Optional[List[str]] = None):
        # Explicit whitelist of permitted block devices for qualification
        self.whitelist: Set[str] = set(whitelist or ["/dev/nvme0n1", "nvme0n1", "/dev/qemu-nvme"])

    def validate_target(
        self,
        device_path: str,
        is_destructive: bool,
        allow_destructive_flag: bool = False,
        confirmation_token: Optional[str] = None,
        expected_token: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Validates whether target device can be safely qualified.
        Returns: (is_safe, reason_or_status)
        """
        # File-based workloads (e.g. against a test directory) are always non-destructive to raw block devices
        if not device_path.startswith("/dev/"):
            return True, "SAFE_FILE_TARGET"

        # Check whitelist
        base_dev = os.path.basename(device_path)
        if device_path not in self.whitelist and base_dev not in self.whitelist:
            return False, f"BLOCKED_BY_SAFETY: Device {device_path} is NOT in the explicit qualification whitelist {list(self.whitelist)}"

        # Check if device is root, boot, swap, or mounted
        is_mounted, mount_points = self._check_mounts(device_path)
        if is_mounted:
            if "/" in mount_points or "/boot" in mount_points:
                return False, f"BLOCKED_BY_SAFETY: Target {device_path} backs critical system mounts: {mount_points}"
            if is_destructive:
                return False, f"BLOCKED_BY_SAFETY: Target {device_path} is currently mounted at {mount_points}. Unmount required before destructive I/O."

        is_swap = self._check_swap(device_path)
        if is_swap:
            return False, f"BLOCKED_BY_SAFETY: Target {device_path} is active system swap."

        # Destructive requirements
        if is_destructive:
            if not allow_destructive_flag:
                return False, "BLOCKED_BY_SAFETY: Destructive workload requested but --allow-destructive flag was not provided."
            if expected_token and confirmation_token != expected_token:
                return False, "BLOCKED_BY_SAFETY: Confirmation token mismatch for destructive execution."

        return True, "SAFE"

    def _check_mounts(self, device_path: str) -> Tuple[bool, List[str]]:
        mounts = []
        if os.path.exists("/proc/mounts"):
            try:
                with open("/proc/mounts", "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.split()
                        if len(parts) >= 2:
                            dev, mnt = parts[0], parts[1]
                            if dev == device_path or device_path in dev:
                                mounts.append(mnt)
            except Exception:
                pass

        # Also verify with lsblk if available
        if shutil.which("lsblk"):
            try:
                res = subprocess.run(["lsblk", "-J", "-o", "NAME,MOUNTPOINT", device_path], capture_output=True, text=True, timeout=5)
                if res.returncode == 0:
                    data = json.loads(res.stdout)
                    self._extract_mountpoints(data.get("blockdevices", []), mounts)
            except Exception:
                pass

        return len(mounts) > 0, list(set(mounts))

    def _extract_mountpoints(self, devices: list, mounts: list):
        for d in devices:
            mnt = d.get("mountpoint")
            if mnt:
                mounts.append(mnt)
            if "children" in d:
                self._extract_mountpoints(d["children"], mounts)

    def _check_swap(self, device_path: str) -> bool:
        if os.path.exists("/proc/swaps"):
            try:
                with open("/proc/swaps", "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.split()
                        if len(parts) >= 1 and (parts[0] == device_path or device_path in parts[0]):
                            return True
            except Exception:
                pass
        return False
