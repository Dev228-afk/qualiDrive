"""
Threshold evaluator checking observed qualification performance and health against criteria.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple
from qualidrive.discovery.models import HealthSnapshot
from qualidrive.fio.parser import FioResult
from qualidrive.telemetry.diff import TelemetryDelta
from qualidrive.thresholds.rules import ThresholdRules


@dataclass
class ThresholdCheckResult:
    metric: str
    observed: Any
    operator: str
    threshold: Any
    passed: bool
    details: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_case_thresholds(
    rules: ThresholdRules,
    fio_res: FioResult,
    post_health: HealthSnapshot,
    delta: TelemetryDelta,
    pcie_downgraded: bool = False
) -> Tuple[bool, List[ThresholdCheckResult]]:
    """Evaluates all rules against the observed case metrics."""
    checks: List[ThresholdCheckResult] = []
    all_passed = True

    # 1. Error delta
    err_delta = delta.media_errors_delta + delta.error_log_delta
    c1 = ThresholdCheckResult(
        metric="error_count_delta",
        observed=err_delta,
        operator="<=",
        threshold=rules.max_error_count_delta,
        passed=(err_delta <= rules.max_error_count_delta),
        details=f"Media errors delta: {delta.media_errors_delta}, Error log delta: {delta.error_log_delta}"
    )
    checks.append(c1)
    if not c1.passed:
        all_passed = False

    # 2. Temperature
    c2 = ThresholdCheckResult(
        metric="temperature_c",
        observed=post_health.temperature_c,
        operator="<=",
        threshold=rules.max_temperature_c,
        passed=(post_health.temperature_c <= rules.max_temperature_c),
        details=f"Peak temperature: {post_health.temperature_c}°C (limit {rules.max_temperature_c}°C)"
    )
    checks.append(c2)
    if not c2.passed:
        all_passed = False

    # 3. p99 Latency (in ms)
    p99_ms = round(fio_res.lat_p99_us / 1000.0, 3)
    c3 = ThresholdCheckResult(
        metric="p99_latency_ms",
        observed=p99_ms,
        operator="<=",
        threshold=rules.max_p99_latency_ms,
        passed=(p99_ms <= rules.max_p99_latency_ms),
        details=f"Observed p99: {p99_ms} ms (limit {rules.max_p99_latency_ms} ms)"
    )
    checks.append(c3)
    if not c3.passed:
        all_passed = False

    # 4. p99.9 Latency (in ms)
    p99_9_ms = round(fio_res.lat_p99_9_us / 1000.0, 3)
    c4 = ThresholdCheckResult(
        metric="p99_9_latency_ms",
        observed=p99_9_ms,
        operator="<=",
        threshold=rules.max_p99_9_latency_ms,
        passed=(p99_9_ms <= rules.max_p99_9_latency_ms),
        details=f"Observed p99.9: {p99_9_ms} ms (limit {rules.max_p99_9_latency_ms} ms)"
    )
    checks.append(c4)
    if not c4.passed:
        all_passed = False

    # 5. IOPS threshold if configured
    if rules.min_iops > 0:
        c5 = ThresholdCheckResult(
            metric="total_iops",
            observed=fio_res.total_iops,
            operator=">=",
            threshold=rules.min_iops,
            passed=(fio_res.total_iops >= rules.min_iops),
            details=f"Observed IOPS: {fio_res.total_iops} (min {rules.min_iops})"
        )
        checks.append(c5)
        if not c5.passed:
            all_passed = False

    # 6. Kernel error signatures
    if rules.require_no_kernel_errors:
        has_signatures = len(delta.detected_kernel_signatures) > 0
        c6 = ThresholdCheckResult(
            metric="kernel_fault_signatures",
            observed=delta.detected_kernel_signatures,
            operator="==",
            threshold=[],
            passed=not has_signatures,
            details=f"Detected signatures: {delta.detected_kernel_signatures}" if has_signatures else "None detected"
        )
        checks.append(c6)
        if not c6.passed:
            all_passed = False

    # 7. PCIe downgrade
    if rules.require_no_pcie_downgrade:
        c7 = ThresholdCheckResult(
            metric="pcie_link_downgrade",
            observed=pcie_downgraded,
            operator="==",
            threshold=False,
            passed=not pcie_downgraded,
            details="PCIe link retained nominal width" if not pcie_downgraded else "PCIe width/speed downgraded"
        )
        checks.append(c7)
        if not c7.passed:
            all_passed = False

    return all_passed, checks
