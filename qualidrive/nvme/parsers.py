"""
Parsers for nvme-cli, smartctl, lsblk, and sysfs command outputs.
"""

import json
import re
from typing import Dict, Any, List, Optional
from qualidrive.discovery.models import NvmeController, NvmeNamespace, PcieLink, HealthSnapshot


def parse_nvme_list(json_or_text: str) -> List[Dict[str, Any]]:
    """Parses `nvme list -o json` or tabular text."""
    if not json_or_text.strip():
        return []
    try:
        data = json.loads(json_or_text)
        if "Devices" in data:
            return data["Devices"]
        elif isinstance(data, list):
            return data
    except Exception:
        pass

    # Text fallback
    results = []
    lines = json_or_text.strip().splitlines()
    for line in lines:
        if line.startswith("/dev/nvme"):
            parts = line.split()
            if len(parts) >= 6:
                results.append({
                    "DevicePath": parts[0],
                    "SerialNumber": parts[1],
                    "ModelNumber": parts[2],
                    "Firmware": parts[len(parts) - 1],
                })
    return results


def parse_id_ctrl(raw_json_or_text: str) -> Dict[str, Any]:
    """Parses `nvme id-ctrl -o json`."""
    if not raw_json_or_text.strip():
        return {}
    try:
        return json.loads(raw_json_or_text)
    except Exception:
        pass

    out: Dict[str, Any] = {}
    for line in raw_json_or_text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def parse_id_ns(raw_json_or_text: str) -> Dict[str, Any]:
    """Parses `nvme id-ns -o json`."""
    if not raw_json_or_text.strip():
        return {}
    try:
        return json.loads(raw_json_or_text)
    except Exception:
        pass

    out: Dict[str, Any] = {}
    for line in raw_json_or_text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def parse_smart_log(raw_json_or_text: str, timestamp: str = "") -> HealthSnapshot:
    """Parses `nvme smart-log -o json` or smartctl output into a HealthSnapshot."""
    snapshot = HealthSnapshot(timestamp=timestamp)
    if not raw_json_or_text.strip():
        return snapshot

    try:
        data = json.loads(raw_json_or_text)
        snapshot.raw_smart = data

        # nvme-cli JSON fields (in Celsius or Kelvin depending on version, standard is Kelvin - 273 or integer C)
        raw_temp = data.get("temperature", 0)
        # nvme-cli often reports temperature in Kelvin (e.g. 310 K = 37 C)
        if raw_temp > 200:
            snapshot.temperature_c = raw_temp - 273
        else:
            snapshot.temperature_c = raw_temp

        snapshot.critical_warning = int(data.get("critical_warning", 0))
        snapshot.available_spare_percent = int(data.get("avail_spare", 100))
        snapshot.percentage_used = int(data.get("percent_used", 0))
        snapshot.media_errors = int(data.get("media_errors", 0))
        snapshot.num_err_log_entries = int(data.get("num_err_log_entries", 0))
        snapshot.power_on_hours = int(data.get("power_on_hours", 0))
        snapshot.unsafe_shutdowns = int(data.get("unsafe_shutdowns", 0))

        # Data units are 1000 sectors of 512 bytes = ~512,000 bytes
        reads_units = int(data.get("data_units_read", 0))
        writes_units = int(data.get("data_units_written", 0))
        snapshot.host_reads_gb = round((reads_units * 512000.0) / (1024**3), 2)
        snapshot.host_writes_gb = round((writes_units * 512000.0) / (1024**3), 2)
        snapshot.controller_busy_time_minutes = int(data.get("controller_busy_time", 0))
        return snapshot
    except Exception:
        pass

    # Regex fallback for text output
    lines = raw_json_or_text.splitlines()
    for line in lines:
        lower = line.lower()
        if "temperature" in lower and ":" in line:
            m = re.search(r"(\d+)\s*(?:c|k)?", line.split(":")[1], re.IGNORECASE)
            if m:
                t = int(m.group(1))
                snapshot.temperature_c = (t - 273) if t > 200 else t
        elif "critical warning" in lower and ":" in line:
            m = re.search(r"0x([0-9a-fA-F]+)|\b(\d+)\b", line.split(":")[1])
            if m:
                snapshot.critical_warning = int(m.group(1) or m.group(2), 16 if m.group(1) else 10)
        elif "media and data integrity errors" in lower and ":" in line:
            m = re.search(r"(\d+)", line.split(":")[1])
            if m:
                snapshot.media_errors = int(m.group(1))
        elif "error information log entries" in lower and ":" in line:
            m = re.search(r"(\d+)", line.split(":")[1])
            if m:
                snapshot.num_err_log_entries = int(m.group(1))
        elif "unsafe shutdowns" in lower and ":" in line:
            m = re.search(r"(\d+)", line.split(":")[1])
            if m:
                snapshot.unsafe_shutdowns = int(m.group(1))
    return snapshot


def parse_pcie_link(lspci_text: str) -> PcieLink:
    """Parses lspci -vvv output for LnkCap and LnkSta."""
    link = PcieLink()
    if not lspci_text:
        return link

    # LnkCap: Port #0, Speed 8GT/s, Width x4, ASPM L1, Exit Latency L1 <64us
    cap_match = re.search(r"LnkCap:.*?Speed\s+([0-9\.]+GT/s).*?Width\s+(x\d+)", lspci_text)
    if cap_match:
        link.max_speed = cap_match.group(1)
        link.max_width = cap_match.group(2)

    # LnkSta: Speed 8GT/s (ok), Width x4 (ok)
    sta_match = re.search(r"LnkSta:.*?Speed\s+([0-9\.]+GT/s).*?Width\s+(x\d+)", lspci_text)
    if sta_match:
        link.speed = sta_match.group(1)
        link.width = sta_match.group(2)

    if link.max_width != "Unknown" and link.width != "Unknown":
        try:
            curr_w = int(link.width.replace("x", ""))
            max_w = int(link.max_width.replace("x", ""))
            if curr_w < max_w:
                link.downgraded = True
        except ValueError:
            pass

    return link
