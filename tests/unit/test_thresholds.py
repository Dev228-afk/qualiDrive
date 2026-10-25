import pytest
from qualidrive.discovery.models import HealthSnapshot
from qualidrive.fio.parser import FioResult
from qualidrive.telemetry.diff import TelemetryDelta
from qualidrive.thresholds.rules import ThresholdRules
from qualidrive.thresholds.evaluator import evaluate_case_thresholds


def test_evaluate_thresholds_all_pass():
    rules = ThresholdRules(
        max_error_count_delta=0,
        max_temperature_c=75,
        max_p99_latency_ms=10.0,
        max_p99_9_latency_ms=25.0,
        min_iops=100.0,
        require_no_kernel_errors=True,
        require_no_pcie_downgrade=True
    )

    fio_res = FioResult(
        total_iops=25000.0,
        lat_p99_us=3500.0,      # 3.5 ms
        lat_p99_9_us=8200.0     # 8.2 ms
    )
    post_health = HealthSnapshot(timestamp="now", temperature_c=42)
    delta = TelemetryDelta(
        temperature_delta_c=5,
        media_errors_delta=0,
        error_log_delta=0,
        unsafe_shutdowns_delta=0,
        host_reads_gb_delta=1.2,
        host_writes_gb_delta=0.0,
        detected_kernel_signatures=[]
    )

    passed, checks = evaluate_case_thresholds(rules, fio_res, post_health, delta, pcie_downgraded=False)
    assert passed
    assert all(c.passed for c in checks)


def test_evaluate_thresholds_catches_media_errors():
    rules = ThresholdRules(max_error_count_delta=0)
    fio_res = FioResult(total_iops=1000.0, lat_p99_us=2000.0, lat_p99_9_us=5000.0)
    post_health = HealthSnapshot(timestamp="now", temperature_c=40)
    delta = TelemetryDelta(
        temperature_delta_c=2,
        media_errors_delta=3,   # 3 media errors!
        error_log_delta=0,
        unsafe_shutdowns_delta=0,
        host_reads_gb_delta=0.5,
        host_writes_gb_delta=0.0,
        detected_kernel_signatures=[]
    )

    passed, checks = evaluate_case_thresholds(rules, fio_res, post_health, delta, pcie_downgraded=False)
    assert not passed
    err_check = next(c for c in checks if c.metric == "error_count_delta")
    assert not err_check.passed
    assert err_check.observed == 3


def test_evaluate_thresholds_catches_kernel_reset_signature():
    rules = ThresholdRules(require_no_kernel_errors=True)
    fio_res = FioResult(total_iops=500.0, lat_p99_us=2000.0, lat_p99_9_us=4000.0)
    post_health = HealthSnapshot(timestamp="now", temperature_c=45)
    delta = TelemetryDelta(
        temperature_delta_c=1,
        media_errors_delta=0,
        error_log_delta=0,
        unsafe_shutdowns_delta=0,
        host_reads_gb_delta=0.1,
        host_writes_gb_delta=0.0,
        detected_kernel_signatures=["NVME_CONTROLLER_RESET"]
    )

    passed, checks = evaluate_case_thresholds(rules, fio_res, post_health, delta, pcie_downgraded=False)
    assert not passed
    k_check = next(c for c in checks if c.metric == "kernel_fault_signatures")
    assert not k_check.passed
