"""
Qualification test suite runner executing test matrix with safety, telemetry, and cleanup.
"""

import datetime
import os
import time
from typing import Dict, Any, List, Optional

from qualidrive.discovery.models import NvmeController, HealthSnapshot
from qualidrive.discovery.scanner import DeviceScanner
from qualidrive.execution.matrix import TestCase
from qualidrive.fio.job_generator import generate_fio_args
from qualidrive.fio.runner import FioRunner
from qualidrive.fio.parser import FioResult
from qualidrive.prerequisites.validator import PrerequisiteValidator
from qualidrive.safety.guard import SafetyGuard
from qualidrive.telemetry.collector import TelemetryCollector
from qualidrive.telemetry.diff import compute_telemetry_delta
from qualidrive.thresholds.evaluator import evaluate_case_thresholds
from qualidrive.thresholds.rules import ThresholdRules


class QualificationRunner:
    def __init__(
        self,
        guard: Optional[SafetyGuard] = None,
        scanner: Optional[DeviceScanner] = None,
        telemetry: Optional[TelemetryCollector] = None,
        fio_runner: Optional[FioRunner] = None
    ):
        self.guard = guard or SafetyGuard()
        self.scanner = scanner or DeviceScanner()
        self.telemetry = telemetry or TelemetryCollector()
        self.fio_runner = fio_runner or FioRunner()
        self.validator = PrerequisiteValidator(self.guard)

    def execute_case(
        self,
        run_id: str,
        test_case: TestCase,
        target_path: str,
        controller: NvmeController,
        threshold_rules: ThresholdRules,
        allow_destructive: bool = False,
        confirmation_token: str = "",
        artifacts_dir: str = "./artifacts"
    ) -> Dict[str, Any]:
        """Executes a single qualification test case through the complete safety & telemetry lifecycle."""
        is_destructive = (test_case.read_percent < 100) and target_path.startswith("/dev/")
        case_start = time.time()

        result_record: Dict[str, Any] = {
            "run_id": run_id,
            "case_id": test_case.case_id,
            "status": "UNKNOWN",
            "device": controller.to_dict(),
            "workload": test_case.to_dict(),
            "pre_health": {},
            "fio": {},
            "post_health": {},
            "deltas": {},
            "thresholds": [],
            "artifacts": [],
            "duration_sec": 0.0,
            "error_message": ""
        }

        # 1. Pre-flight & Safety check
        val_rep = self.validator.validate(
            target_path=target_path,
            is_destructive=is_destructive,
            allow_destructive=allow_destructive,
            confirmation_token=confirmation_token
        )
        if val_rep["blocked_by_safety"]:
            result_record["status"] = "BLOCKED_BY_SAFETY"
            result_record["error_message"] = "Execution blocked by safety policy"
            result_record["duration_sec"] = round(time.time() - case_start, 2)
            return result_record
        elif not val_rep["passed"]:
            result_record["status"] = "BLOCKED_BY_SAFETY"
            result_record["error_message"] = f"Prerequisite checks failed: {val_rep['checks']}"
            result_record["duration_sec"] = round(time.time() - case_start, 2)
            return result_record

        pre_health = HealthSnapshot(timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat())
        post_health = pre_health

        try:
            # 2. Pre-test health snapshot
            pre_health = self.telemetry.capture_snapshot(target_path)
            result_record["pre_health"] = pre_health.to_dict()

            # 3. Generate fio arguments
            fio_args = generate_fio_args(
                target_path=target_path,
                block_size=test_case.block_size,
                queue_depth=test_case.queue_depth,
                read_percent=test_case.read_percent,
                numjobs=test_case.jobs,
                access=test_case.access,
                runtime_seconds=test_case.runtime_seconds,
                direct=test_case.direct,
                ioengine=test_case.ioengine
            )

            # 4. Execute fio workload
            rc, fio_res, stdout, stderr, elapsed = self.fio_runner.run(
                fio_args, expected_runtime_sec=test_case.runtime_seconds
            )
            result_record["fio"] = fio_res.to_dict()

            # Save raw fio artifact
            os.makedirs(artifacts_dir, exist_ok=True)
            fio_art_path = os.path.join(artifacts_dir, f"{test_case.case_id}_fio.json")
            try:
                with open(fio_art_path, "w", encoding="utf-8") as f:
                    f.write(stdout if stdout else stderr)
                result_record["artifacts"].append(fio_art_path)
            except Exception:
                pass

            # 5. Post-test health snapshot & kernel telemetry
            post_health = self.telemetry.capture_snapshot(target_path)
            result_record["post_health"] = post_health.to_dict()
            kernel_log = self.telemetry.capture_kernel_messages()

            # 6. Compute deltas
            delta = compute_telemetry_delta(pre_health, post_health, kernel_log)
            result_record["deltas"] = delta.to_dict()

            # 7. Evaluate status
            if rc == 124:
                result_record["status"] = "TIMEOUT"
                result_record["error_message"] = stderr
            elif rc != 0:
                result_record["status"] = "FAIL"
                result_record["error_message"] = f"fio exited with return code {rc}: {stderr}"
            else:
                passed, th_checks = evaluate_case_thresholds(
                    rules=threshold_rules,
                    fio_res=fio_res,
                    post_health=post_health,
                    delta=delta,
                    pcie_downgraded=controller.pcie_link.downgraded
                )
                result_record["thresholds"] = [c.to_dict() for c in th_checks]
                result_record["status"] = "PASS" if passed else "FAIL"

        except Exception as e:
            result_record["status"] = "ERROR"
            result_record["error_message"] = str(e)
        finally:
            # Enforce cleanup
            result_record["duration_sec"] = round(time.time() - case_start, 2)

        return result_record
