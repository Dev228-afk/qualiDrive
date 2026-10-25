"""
Pre and post telemetry collection for NVMe devices and host kernel state.
"""

import datetime
import os
import shutil
import subprocess
from typing import Dict, Any, Optional

from qualidrive.discovery.models import HealthSnapshot, PcieLink
from qualidrive.nvme.cli_wrapper import NvmeCli
from qualidrive.nvme.parsers import parse_smart_log, parse_pcie_link


class TelemetryCollector:
    def __init__(self, nvme_cli: Optional[NvmeCli] = None):
        self.cli = nvme_cli or NvmeCli()

    def capture_snapshot(self, device_path: str) -> HealthSnapshot:
        """Captures NVMe SMART, error logs, and temperature."""
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # If not an NVMe block device (e.g. simulated QEMU or directory path), return synthetic snapshot
        if not device_path.startswith("/dev/nvme"):
            return HealthSnapshot(
                timestamp=now_iso,
                temperature_c=35,
                critical_warning=0,
                available_spare_percent=100,
                percentage_used=0,
                media_errors=0,
                num_err_log_entries=0,
                power_on_hours=10,
                unsafe_shutdowns=0,
                host_reads_gb=0.0,
                host_writes_gb=0.0
            )

        # Query nvme-cli
        rc, out, _ = self.cli.smart_log(device_path)
        if rc == 0:
            snapshot = parse_smart_log(out, timestamp=now_iso)
        else:
            snapshot = HealthSnapshot(timestamp=now_iso)

        # Query error log
        rc_err, out_err, _ = self.cli.error_log(device_path)
        if rc_err == 0 and out_err.strip():
            try:
                import json
                err_data = json.loads(out_err)
                if isinstance(err_data, list):
                    snapshot.raw_error_log = err_data
                elif isinstance(err_data, dict):
                    snapshot.raw_error_log = err_data.get("Errors", [])
            except Exception:
                pass

        return snapshot

    def capture_kernel_messages(self, since_cursor: Optional[str] = None) -> str:
        """Captures recent kernel dmesg messages."""
        if not shutil.which("dmesg"):
            return ""
        try:
            res = subprocess.run(["dmesg", "-T"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                lines = res.stdout.strip().splitlines()
                # Return last 100 lines
                return "\n".join(lines[-100:])
        except Exception:
            pass
        return ""
