"""
Telemetry diff engine computing delta metrics between pre and post execution snapshots.
"""

import re
from dataclasses import dataclass, asdict
from typing import Dict, Any, List
from qualidrive.discovery.models import HealthSnapshot


@dataclass
class TelemetryDelta:
    temperature_delta_c: int
    media_errors_delta: int
    error_log_delta: int
    unsafe_shutdowns_delta: int
    host_reads_gb_delta: float
    host_writes_gb_delta: float
    detected_kernel_signatures: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_telemetry_delta(
    pre: HealthSnapshot,
    post: HealthSnapshot,
    kernel_log: str = ""
) -> TelemetryDelta:
    """Computes differences between pre and post health snapshots and scans kernel logs for signatures."""
    temp_delta = post.temperature_c - pre.temperature_c
    media_delta = max(0, post.media_errors - pre.media_errors)
    err_delta = max(0, post.num_err_log_entries - pre.num_err_log_entries)
    shutdown_delta = max(0, post.unsafe_shutdowns - pre.unsafe_shutdowns)
    reads_delta = round(max(0.0, post.host_reads_gb - pre.host_reads_gb), 2)
    writes_delta = round(max(0.0, post.host_writes_gb - pre.host_writes_gb), 2)

    # Scan kernel logs for critical NVMe failure signatures
    signatures = []
    fault_patterns = [
        (r"nvme\d+:.*(?:reset|controller reset)", "NVME_CONTROLLER_RESET"),
        (r"nvme\d+:.*(?:timeout|I/O timeout|abort)", "NVME_IO_TIMEOUT"),
        (r"I/O error.*dev nvme", "NVME_KERNEL_IO_ERROR"),
        (r"Controller Fatal Status", "NVME_CONTROLLER_FATAL_STATUS"),
        (r"PCIe link down|aer_status", "PCIE_LINK_DOWN_OR_AER"),
        (r"nvme\d+:.*status: 0x[0-9a-fA-F]+", "NVME_COMMAND_STATUS_ERROR")
    ]

    for pat, label in fault_patterns:
        if re.search(pat, kernel_log, re.IGNORECASE):
            signatures.append(label)

    return TelemetryDelta(
        temperature_delta_c=temp_delta,
        media_errors_delta=media_delta,
        error_log_delta=err_delta,
        unsafe_shutdowns_delta=shutdown_delta,
        host_reads_gb_delta=reads_delta,
        host_writes_gb_delta=writes_delta,
        detected_kernel_signatures=signatures
    )
