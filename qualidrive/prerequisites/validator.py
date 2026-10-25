"""
Prerequisite validation prior to qualification execution.
"""

import os
import shutil
import subprocess
from typing import Dict, Any, List
from qualidrive.discovery.models import NvmeController
from qualidrive.safety.guard import SafetyGuard


class PrerequisiteValidator:
    def __init__(self, guard: SafetyGuard):
        self.guard = guard

    def validate(
        self,
        target_path: str,
        is_destructive: bool = False,
        allow_destructive: bool = False,
        confirmation_token: str = "",
        max_pretest_temp_c: int = 70
    ) -> Dict[str, Any]:
        """Runs pre-flight qualification checks and returns a structured validation report."""
        checks: List[Dict[str, Any]] = []
        overall_passed = True
        blocked_by_safety = False

        # 1. Check fio availability
        fio_path = shutil.which("fio")
        fio_ver = "unknown"
        if fio_path:
            try:
                res = subprocess.run([fio_path, "--version"], capture_output=True, text=True, timeout=5)
                fio_ver = res.stdout.strip()
            except Exception:
                pass
        checks.append({
            "name": "fio_installed",
            "passed": fio_path is not None,
            "details": f"Path: {fio_path}, Version: {fio_ver}"
        })
        if not fio_path:
            overall_passed = False

        # 2. Check nvme-cli availability
        nvme_path = shutil.which("nvme")
        checks.append({
            "name": "nvme_cli_installed",
            "passed": nvme_path is not None,
            "details": f"Path: {nvme_path}"
        })

        # 3. Target existence
        target_exists = os.path.exists(target_path)
        checks.append({
            "name": "target_exists",
            "passed": target_exists,
            "details": f"Target: {target_path}"
        })
        if not target_exists:
            overall_passed = False

        # 4. Safety validation
        safe, reason = self.guard.validate_target(
            device_path=target_path,
            is_destructive=is_destructive,
            allow_destructive_flag=allow_destructive,
            confirmation_token=confirmation_token
        )
        checks.append({
            "name": "safety_guard",
            "passed": safe,
            "details": reason
        })
        if not safe:
            overall_passed = False
            if "BLOCKED_BY_SAFETY" in reason:
                blocked_by_safety = True

        # 5. Free disk space if file-based target
        if not target_path.startswith("/dev/") and os.path.isdir(target_path):
            total, used, free = shutil.disk_usage(target_path)
            free_gb = free / (1024**3)
            has_space = free_gb >= 1.0  # At least 1 GiB free
            checks.append({
                "name": "free_space_adequate",
                "passed": has_space,
                "details": f"Free: {free_gb:.2f} GiB (minimum 1.0 GiB)"
            })
            if not has_space:
                overall_passed = False

        return {
            "passed": overall_passed,
            "blocked_by_safety": blocked_by_safety,
            "target": target_path,
            "checks": checks
        }
