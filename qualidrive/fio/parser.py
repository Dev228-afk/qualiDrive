"""
Parser for fio JSON and JSON+ execution output.
"""

import json
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional


@dataclass
class FioResult:
    read_iops: float = 0.0
    write_iops: float = 0.0
    total_iops: float = 0.0
    read_bw_mb: float = 0.0
    write_bw_mb: float = 0.0
    total_bw_mb: float = 0.0
    lat_p50_us: float = 0.0
    lat_p90_us: float = 0.0
    lat_p95_us: float = 0.0
    lat_p99_us: float = 0.0
    lat_p99_9_us: float = 0.0
    lat_mean_us: float = 0.0
    cpu_usr_percent: float = 0.0
    cpu_sys_percent: float = 0.0
    disk_util_percent: float = 0.0
    total_errors: int = 0
    raw_json: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("raw_json", None)
        return d


def parse_fio_json(raw_json_str: str) -> FioResult:
    """Parses standard fio JSON / JSON+ string into FioResult."""
    result = FioResult()
    if not raw_json_str.strip():
        return result

    try:
        data = json.loads(raw_json_str)
        result.raw_json = data
    except Exception:
        # Sometimes fio prints non-JSON warnings before the opening brace '{'
        brace_idx = raw_json_str.find("{")
        if brace_idx >= 0:
            try:
                data = json.loads(raw_json_str[brace_idx:])
                result.raw_json = data
            except Exception:
                return result
        else:
            return result

    jobs = data.get("jobs", [])
    if not jobs:
        return result

    # Aggregate across reported jobs
    r_iops, w_iops = 0.0, 0.0
    r_bw, w_bw = 0.0, 0.0
    errors = 0
    cpu_usr, cpu_sys = 0.0, 0.0
    p50_list, p90_list, p95_list, p99_list, p99_9_list, mean_lat_list = [], [], [], [], [], []

    for job in jobs:
        read_obj = job.get("read", {})
        write_obj = job.get("write", {})

        r_iops += float(read_obj.get("iops", 0.0))
        w_iops += float(write_obj.get("iops", 0.0))

        # fio bw_bytes is in bytes/sec
        r_bw += float(read_obj.get("bw_bytes", 0.0)) / (1024 * 1024)
        w_bw += float(write_obj.get("bw_bytes", 0.0)) / (1024 * 1024)

        errors += int(read_obj.get("total_err", 0)) + int(write_obj.get("total_err", 0))

        cpu_usr += float(job.get("usr_cpu", 0.0))
        cpu_sys += float(job.get("sys_cpu", 0.0))

        # Extract latencies (clat_ns or clat)
        for sub in (read_obj, write_obj):
            if sub.get("iops", 0) > 0:
                clat_ns = sub.get("clat_ns", {})
                clat_us = sub.get("clat", {})  # older fio
                pcts = clat_ns.get("percentile") or clat_us.get("percentile", {})
                factor = 0.001 if clat_ns.get("percentile") else 1.0  # ns to us

                if pcts:
                    p50_list.append(float(pcts.get("50.000000", 0.0)) * factor)
                    p90_list.append(float(pcts.get("90.000000", 0.0)) * factor)
                    p95_list.append(float(pcts.get("95.000000", 0.0)) * factor)
                    p99_list.append(float(pcts.get("99.000000", 0.0)) * factor)
                    p99_9_list.append(float(pcts.get("99.900000", 0.0)) * factor)

                mean_val = clat_ns.get("mean") or clat_us.get("mean", 0.0)
                if mean_val:
                    mean_lat_list.append(float(mean_val) * factor)

    result.read_iops = round(r_iops, 2)
    result.write_iops = round(w_iops, 2)
    result.total_iops = round(r_iops + w_iops, 2)

    result.read_bw_mb = round(r_bw, 2)
    result.write_bw_mb = round(w_bw, 2)
    result.total_bw_mb = round(r_bw + w_bw, 2)

    result.total_errors = errors
    result.cpu_usr_percent = round(cpu_usr / len(jobs), 2)
    result.cpu_sys_percent = round(cpu_sys / len(jobs), 2)

    if p50_list:
        result.lat_p50_us = round(max(p50_list), 2)
        result.lat_p90_us = round(max(p90_list), 2)
        result.lat_p95_us = round(max(p95_list), 2)
        result.lat_p99_us = round(max(p99_list), 2)
        result.lat_p99_9_us = round(max(p99_9_list), 2)
    if mean_lat_list:
        result.lat_mean_us = round(sum(mean_lat_list) / len(mean_lat_list), 2)

    # Disk utilization
    disk_util = data.get("disk_util", [])
    if disk_util:
        result.disk_util_percent = round(float(disk_util[0].get("util", 0.0)), 2)

    return result
