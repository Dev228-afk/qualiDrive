"""
Threshold criteria configurations for qualification test evaluation.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class ThresholdRules:
    max_error_count_delta: int = 0
    max_temperature_c: int = 80
    max_p99_latency_ms: float = 50.0
    max_p99_9_latency_ms: float = 100.0
    min_iops: float = 0.0
    min_bandwidth_mb: float = 0.0
    require_no_kernel_errors: bool = True
    require_no_pcie_downgrade: bool = True

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ThresholdRules":
        return cls(
            max_error_count_delta=int(d.get("max_error_count_delta", 0)),
            max_temperature_c=int(d.get("max_temperature_c", 80)),
            max_p99_latency_ms=float(d.get("max_p99_latency_ms", 50.0)),
            max_p99_9_latency_ms=float(d.get("max_p99_9_latency_ms", 100.0)),
            min_iops=float(d.get("min_iops", 0.0)),
            min_bandwidth_mb=float(d.get("min_bandwidth_mb", 0.0)),
            require_no_kernel_errors=bool(d.get("require_no_kernel_errors", True)),
            require_no_pcie_downgrade=bool(d.get("require_no_pcie_downgrade", True))
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
