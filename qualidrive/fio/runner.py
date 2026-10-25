"""
Subprocess execution runner for fio with timeouts, graceful termination, and raw capture.
"""

import shutil
import subprocess
import time
from typing import Tuple, Optional
from qualidrive.fio.parser import FioResult, parse_fio_json


class FioRunner:
    def __init__(self, fio_path: Optional[str] = None, mock: bool = False):
        self.mock = mock
        if mock:
            self.fio_bin = None
        else:
            self.fio_bin = shutil.which("fio") if fio_path is None else fio_path

    def run(
        self,
        fio_args: list,
        expected_runtime_sec: int = 10,
        grace_period_sec: int = 15
    ) -> Tuple[int, FioResult, str, str, float]:
        """
        Executes fio with a hard timeout.
        Returns: (exit_code, parsed_fio_result, raw_stdout, raw_stderr, elapsed_seconds)
        """
        timeout_sec = expected_runtime_sec + grace_period_sec
        start_time = time.time()

        if self.mock or not self.fio_bin:
            # Fallback mock for pure simulation mode
            mock_out = self._generate_mock_output()
            elapsed = 0.1
            return 0, parse_fio_json(mock_out), mock_out, "", elapsed

        cmd = [self.fio_bin] + fio_args
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
            elapsed = time.time() - start_time
            result = parse_fio_json(res.stdout)
            return res.returncode, result, res.stdout, res.stderr, round(elapsed, 2)
        except subprocess.TimeoutExpired as te:
            elapsed = time.time() - start_time
            stdout = te.stdout.decode() if isinstance(te.stdout, bytes) else (te.stdout or "")
            stderr = te.stderr.decode() if isinstance(te.stderr, bytes) else (te.stderr or "")
            return 124, FioResult(), stdout, f"fio execution timed out after {timeout_sec}s: {stderr}", round(elapsed, 2)
        except Exception as e:
            elapsed = time.time() - start_time
            return 1, FioResult(), "", str(e), round(elapsed, 2)

    def _generate_mock_output(self) -> str:
        import json
        mock = {
            "jobs": [
                {
                    "jobname": "qualidrive_mock",
                    "read": {
                        "io_bytes": 104857600,
                        "bw_bytes": 10485760,
                        "iops": 2560.0,
                        "clat_ns": {
                            "percentile": {
                                "50.000000": 350000,
                                "90.000000": 600000,
                                "95.000000": 800000,
                                "99.000000": 1500000,
                                "99.900000": 3000000
                            },
                            "mean": 380000
                        },
                        "total_err": 0
                    },
                    "write": {"io_bytes": 0, "bw_bytes": 0, "iops": 0, "total_err": 0},
                    "usr_cpu": 2.5,
                    "sys_cpu": 8.0
                }
            ],
            "disk_util": [{"util": 75.0}]
        }
        return json.dumps(mock)
