"""
Data models for NVMe controllers, namespaces, PCIe topology, and health state.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


@dataclass
class PcieLink:
    speed: str = "Unknown"          # e.g. "8.0 GT/s" (Gen3) or "16.0 GT/s" (Gen4)
    width: str = "Unknown"          # e.g. "x4"
    max_speed: str = "Unknown"
    max_width: str = "Unknown"
    downgraded: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NvmeNamespace:
    nsid: int
    device_path: str               # e.g. "/dev/nvme0n1"
    size_bytes: int
    sector_size: int = 512         # 512 or 4096 bytes
    sector_count: int = 0
    utilization_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NvmeController:
    controller_id: str             # e.g. "nvme0"
    device_path: str               # e.g. "/dev/nvme0"
    model: str
    serial: str
    firmware_rev: str
    pci_bdf: str = ""              # e.g. "0000:01:00.0"
    pcie_link: PcieLink = field(default_factory=PcieLink)
    namespaces: List[NvmeNamespace] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["pcie_link"] = self.pcie_link.to_dict()
        d["namespaces"] = [ns.to_dict() for ns in self.namespaces]
        return d


@dataclass
class HealthSnapshot:
    timestamp: str
    temperature_c: int = 0
    critical_warning: int = 0
    available_spare_percent: int = 100
    percentage_used: int = 0
    media_errors: int = 0
    num_err_log_entries: int = 0
    power_on_hours: int = 0
    unsafe_shutdowns: int = 0
    host_reads_gb: float = 0.0
    host_writes_gb: float = 0.0
    controller_busy_time_minutes: int = 0
    raw_smart: Dict[str, Any] = field(default_factory=dict)
    raw_error_log: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
