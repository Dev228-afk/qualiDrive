import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
import pytest

from qualidrive.discovery.scanner import DeviceScanner
from qualidrive.execution.matrix import load_manifest, generate_test_matrix
from qualidrive.execution.runner import QualificationRunner
from qualidrive.execution.compare import compare_runs
from qualidrive.reporting.html_report import generate_html_report
from qualidrive.reporting.junit import generate_junit_xml
from qualidrive.reporting.json_exporter import export_run_artifacts
from qualidrive.safety.guard import SafetyGuard
from qualidrive.thresholds.rules import ThresholdRules


def test_end_to_end_smoke_execution():
    temp_dir = tempfile.mkdtemp(prefix="qualidrive_test_")
    try:
        manifest_path = os.path.join(os.path.dirname(__file__), "../../manifests/smoke.yaml")
        manifest = load_manifest(manifest_path)
        cases = generate_test_matrix(manifest)
        assert len(cases) == 4

        scanner = DeviceScanner()
        ctrl = scanner.get_synthetic_qemu_device()
        guard = SafetyGuard()
        runner = QualificationRunner(guard=guard, scanner=scanner)
        threshold_rules = ThresholdRules.from_dict(manifest.get("thresholds", {}))

        run_id = "test_smoke_run_001"
        artifacts_dir = os.path.join(temp_dir, "artifacts")
        results = []

        # Run the 4 smoke cases against the safe temp directory
        for tc in cases:
            res = runner.execute_case(
                run_id=run_id,
                test_case=tc,
                target_path=temp_dir,
                controller=ctrl,
                threshold_rules=threshold_rules,
                artifacts_dir=artifacts_dir
            )
            results.append(res)
            assert res["status"] in ("PASS", "FAIL", "BLOCKED_BY_SAFETY")

        # 1. Export JSON and CSV
        arts = export_run_artifacts(results, run_id, temp_dir)
        assert os.path.exists(arts["json"])
        assert os.path.exists(arts["csv"])

        # 2. Generate and verify JUnit XML
        junit_str = generate_junit_xml(results, run_id)
        junit_path = os.path.join(temp_dir, f"{run_id}_junit.xml")
        with open(junit_path, "w", encoding="utf-8") as f:
            f.write(junit_str)
        # Parse XML
        root = ET.fromstring(junit_str)
        assert root.tag == "testsuites"
        suite = root.find("testsuite")
        assert suite is not None
        assert suite.attrib["tests"] == "4"

        # 3. Generate and verify HTML report
        html_str = generate_html_report(results, run_id, ctrl.to_dict())
        html_path = os.path.join(temp_dir, f"{run_id}_report.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_str)
        assert "<html" in html_str
        assert "tc_bs4k_qd1_rm100_j1_rand_t3" in html_str

        # 4. Verify compare_runs functionality
        comp = compare_runs(results, results)
        assert comp["total_cases_compared"] == 4
        assert comp["regressions_detected"] == 0

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
