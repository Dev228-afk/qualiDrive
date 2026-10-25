import json
import pytest
from qualidrive.nvme.parsers import parse_nvme_list, parse_smart_log, parse_id_ctrl, parse_pcie_link
from qualidrive.fio.parser import parse_fio_json


def test_parse_nvme_list_json():
    sample = json.dumps({
        "Devices": [
            {
                "DevicePath": "/dev/nvme0n1",
                "SerialNumber": "SN12345678",
                "ModelNumber": "KIOXIA_EXCELERATOR",
                "Firmware": "1.00A"
            }
        ]
    })
    devs = parse_nvme_list(sample)
    assert len(devs) == 1
    assert devs[0]["SerialNumber"] == "SN12345678"
    assert devs[0]["ModelNumber"] == "KIOXIA_EXCELERATOR"


def test_parse_smart_log_json():
    sample = json.dumps({
        "temperature": 312,  # 312 Kelvin = 39 C
        "critical_warning": 0,
        "avail_spare": 98,
        "percent_used": 2,
        "media_errors": 0,
        "num_err_log_entries": 0,
        "power_on_hours": 1500,
        "unsafe_shutdowns": 4,
        "data_units_read": 204800,
        "data_units_written": 102400,
        "controller_busy_time": 45
    })
    snap = parse_smart_log(sample, timestamp="2026-10-10T00:00:00Z")
    assert snap.temperature_c == 39
    assert snap.critical_warning == 0
    assert snap.available_spare_percent == 98
    assert snap.percentage_used == 2
    assert snap.media_errors == 0
    assert snap.unsafe_shutdowns == 4
    assert snap.host_reads_gb == 97.66
    assert snap.host_writes_gb == 48.83


def test_parse_pcie_link_lspci():
    sample = """
        LnkCap: Port #0, Speed 16.0GT/s, Width x4, ASPM L1, Exit Latency L1 <64us
        LnkSta: Speed 16.0GT/s (ok), Width x4 (ok)
    """
    link = parse_pcie_link(sample)
    assert link.speed == "16.0GT/s"
    assert link.width == "x4"
    assert link.max_speed == "16.0GT/s"
    assert link.max_width == "x4"
    assert not link.downgraded


def test_parse_pcie_link_downgraded():
    sample = """
        LnkCap: Port #0, Speed 16.0GT/s, Width x4, ASPM L1, Exit Latency L1 <64us
        LnkSta: Speed 8.0GT/s (ok), Width x2 (downgraded)
    """
    link = parse_pcie_link(sample)
    assert link.width == "x2"
    assert link.max_width == "x4"
    assert link.downgraded


def test_parse_fio_json_standard():
    sample = json.dumps({
        "jobs": [
            {
                "jobname": "test_job",
                "read": {
                    "iops": 50000.0,
                    "bw_bytes": 204800000,
                    "clat_ns": {
                        "percentile": {
                            "50.000000": 18000,
                            "90.000000": 35000,
                            "95.000000": 50000,
                            "99.000000": 120000,
                            "99.900000": 250000
                        },
                        "mean": 22000
                    },
                    "total_err": 0
                },
                "write": {"iops": 0, "bw_bytes": 0, "total_err": 0},
                "usr_cpu": 12.0,
                "sys_cpu": 35.0
            }
        ],
        "disk_util": [{"util": 88.5}]
    })
    res = parse_fio_json(sample)
    assert res.total_iops == 50000.0
    assert res.read_bw_mb == 195.31
    assert res.lat_p50_us == 18.0
    assert res.lat_p99_us == 120.0
    assert res.lat_p99_9_us == 250.0
    assert res.disk_util_percent == 88.5
    assert res.total_errors == 0
