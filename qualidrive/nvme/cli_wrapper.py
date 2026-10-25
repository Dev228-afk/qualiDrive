"""
Subprocess wrapper for nvme-cli and smartctl with version auto-detection and timeouts.
"""

import subprocess
import shutil
import time
from typing import Tuple, Dict, Any, Optional


class NvmeCli:
    def __init__(self, nvme_path: Optional[str] = None):
        self.nvme_bin = nvme_path or shutil.which("nvme")
        self.version = self._detect_version() if self.nvme_bin else "not_installed"

    def _detect_version(self) -> str:
        try:
            res = subprocess.run([self.nvme_bin, "version"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                first_line = res.stdout.strip().splitlines()[0]
                return first_line
        except Exception:
            pass
        return "unknown"

    def is_available(self) -> bool:
        return self.nvme_bin is not None

    def _run_cmd(self, args: list, timeout: int = 10) -> Tuple[int, str, str]:
        if not self.nvme_bin:
            return 127, "", "nvme command not found"
        start = time.time()
        try:
            res = subprocess.run([self.nvme_bin] + args, capture_output=True, text=True, timeout=timeout)
            return res.returncode, res.stdout, res.stderr
        except subprocess.TimeoutExpired:
            return 124, "", f"Command timed out after {timeout}s: nvme {' '.join(args)}"
        except Exception as e:
            return 1, "", str(e)

    def list_devices(self, timeout: int = 10) -> Tuple[int, str, str]:
        return self._run_cmd(["list", "-o", "json"], timeout=timeout)

    def id_ctrl(self, device_path: str, timeout: int = 10) -> Tuple[int, str, str]:
        # Try modern syntax first
        rc, out, err = self._run_cmd(["id-ctrl", device_path, "-o", "json"], timeout=timeout)
        if rc != 0 and "Invalid sub-command" in err:
            rc, out, err = self._run_cmd(["id", "ctrl", device_path, "-o", "json"], timeout=timeout)
        return rc, out, err

    def id_ns(self, device_path: str, timeout: int = 10) -> Tuple[int, str, str]:
        rc, out, err = self._run_cmd(["id-ns", device_path, "-o", "json"], timeout=timeout)
        if rc != 0 and "Invalid sub-command" in err:
            rc, out, err = self._run_cmd(["id", "ns", device_path, "-o", "json"], timeout=timeout)
        return rc, out, err

    def smart_log(self, device_path: str, timeout: int = 10) -> Tuple[int, str, str]:
        rc, out, err = self._run_cmd(["smart-log", device_path, "-o", "json"], timeout=timeout)
        if rc != 0 and "Invalid sub-command" in err:
            rc, out, err = self._run_cmd(["log", "smart", device_path, "-o", "json"], timeout=timeout)
        return rc, out, err

    def error_log(self, device_path: str, timeout: int = 10) -> Tuple[int, str, str]:
        rc, out, err = self._run_cmd(["error-log", device_path, "-o", "json"], timeout=timeout)
        if rc != 0 and "Invalid sub-command" in err:
            rc, out, err = self._run_cmd(["log", "error", device_path, "-o", "json"], timeout=timeout)
        return rc, out, err
