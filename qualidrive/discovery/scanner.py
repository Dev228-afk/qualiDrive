"""
NVMe hardware and namespace scanner with sysfs, lsblk, and nvme-cli integration.
"""

import json
import os
import re
import shutil
import subprocess
from typing import List, Dict, Any, Optional

from qualidrive.discovery.models import NvmeController, NvmeNamespace, PcieLink
from qualidrive.nvme.cli_wrapper import NvmeCli
from qualidrive.nvme.parsers import parse_nvme_list, parse_id_ctrl, parse_id_ns, parse_pcie_link


class DeviceScanner:
    def __init__(self, nvme_cli: Optional[NvmeCli] = None):
        self.cli = nvme_cli or NvmeCli()

    def scan(self) -> List[NvmeController]:
        """Scans the host system for NVMe controllers and attached namespaces."""
        controllers: Dict[str, NvmeController] = {}

        # 1. Check sysfs /sys/class/nvme
        sysfs_nvme = "/sys/class/nvme"
        if os.path.isdir(sysfs_nvme):
            for entry in os.listdir(sysfs_nvme):
                ctrl_path = os.path.join(sysfs_nvme, entry)
                ctrl_id = entry  # e.g. "nvme0"
                dev_path = f"/dev/{ctrl_id}"

                model = self._read_sysfs(os.path.join(ctrl_path, "model")) or "Unknown NVMe Model"
                serial = self._read_sysfs(os.path.join(ctrl_path, "serial")) or "Unknown Serial"
                firmware = self._read_sysfs(os.path.join(ctrl_path, "firmware_rev")) or "Unknown FW"

                # Check PCI link
                bdf = self._read_sysfs_symlink(os.path.join(ctrl_path, "device"))
                pcie = self._get_pcie_link(bdf) if bdf else PcieLink()

                controllers[ctrl_id] = NvmeController(
                    controller_id=ctrl_id,
                    device_path=dev_path,
                    model=model.strip(),
                    serial=serial.strip(),
                    firmware_rev=firmware.strip(),
                    pci_bdf=bdf,
                    pcie_link=pcie,
                    namespaces=[]
                )

        # 2. Check nvme-cli list if sysfs was empty or to complement
        if self.cli.is_available():
            rc, out, _ = self.cli.list_devices()
            if rc == 0:
                devs = parse_nvme_list(out)
                for d in devs:
                    dp = d.get("DevicePath", "")
                    # Match /dev/nvme0n1 -> ctrl_id "nvme0", nsid 1
                    m = re.match(r"/dev/(nvme\d+)n(\d+)", dp)
                    if m:
                        ctrl_id = m.group(1)
                        nsid = int(m.group(2))
                        if ctrl_id not in controllers:
                            controllers[ctrl_id] = NvmeController(
                                controller_id=ctrl_id,
                                device_path=f"/dev/{ctrl_id}",
                                model=d.get("ModelNumber", "Unknown Model").strip(),
                                serial=d.get("SerialNumber", "Unknown Serial").strip(),
                                firmware_rev=d.get("Firmware", "Unknown FW").strip(),
                                namespaces=[]
                            )

        # 3. Discover namespaces for each controller via /sys/class/block
        sysfs_block = "/sys/class/block"
        if os.path.isdir(sysfs_block):
            for b_entry in os.listdir(sysfs_block):
                m = re.match(r"(nvme\d+)n(\d+)", b_entry)
                if m:
                    ctrl_id = m.group(1)
                    nsid = int(m.group(2))
                    dev_path = f"/dev/{b_entry}"
                    size_sectors = int(self._read_sysfs(os.path.join(sysfs_block, b_entry, "size")) or "0")
                    sector_size = int(self._read_sysfs(os.path.join(sysfs_block, b_entry, "queue/hw_sector_size")) or "512")
                    size_bytes = size_sectors * sector_size

                    ns = NvmeNamespace(
                        nsid=nsid,
                        device_path=dev_path,
                        size_bytes=size_bytes,
                        sector_size=sector_size,
                        sector_count=size_sectors
                    )
                    if ctrl_id in controllers:
                        # Avoid duplicates
                        if not any(x.nsid == nsid for x in controllers[ctrl_id].namespaces):
                            controllers[ctrl_id].namespaces.append(ns)

        # 4. If no physical controllers exist (e.g. running in testing / CI container),
        # return synthetic QEMU profile if requested or empty list
        return list(controllers.values())

    @staticmethod
    def get_synthetic_qemu_device() -> NvmeController:
        """Returns a standardized QEMU NVMe device model for emulation/testing."""
        return NvmeController(
            controller_id="nvme0",
            device_path="/dev/nvme0",
            model="QEMU NVMe Controller",
            serial="QEMU_NVME_0001",
            firmware_rev="1.0",
            pci_bdf="0000:00:04.0",
            pcie_link=PcieLink(speed="8.0 GT/s", width="x4", max_speed="8.0 GT/s", max_width="x4", downgraded=False),
            namespaces=[
                NvmeNamespace(
                    nsid=1,
                    device_path="/dev/nvme0n1",
                    size_bytes=10737418240,  # 10 GiB
                    sector_size=512,
                    sector_count=20971520
                )
            ]
        )

    def _read_sysfs(self, path: str) -> Optional[str]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception:
                pass
        return None

    def _read_sysfs_symlink(self, path: str) -> str:
        if os.path.islink(path):
            try:
                target = os.readlink(path)
                return os.path.basename(target)
            except Exception:
                pass
        return ""

    def _get_pcie_link(self, bdf: str) -> PcieLink:
        if not shutil.which("lspci") or not bdf:
            return PcieLink()
        try:
            res = subprocess.run(["lspci", "-s", bdf, "-vvv"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                return parse_pcie_link(res.stdout)
        except Exception:
            pass
        return PcieLink()
