"""
Cross-run regression comparison engine (e.g. Firmware A vs Firmware B).
"""

import json
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional


@dataclass
class CaseRegressionDiff:
    case_id: str
    status_a: str
    status_b: str
    iops_a: float
    iops_b: float
    iops_delta_percent: float
    bw_a_mb: float
    bw_b_mb: float
    bw_delta_percent: float
    p99_a_ms: float
    p99_b_ms: float
    p99_delta_percent: float
    error_delta_a: int
    error_delta_b: int
    regressed: bool
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compare_runs(
    run_a_results: List[Dict[str, Any]],
    run_b_results: List[Dict[str, Any]],
    iops_regression_threshold_pct: float = -10.0,
    latency_regression_threshold_pct: float = 15.0
) -> Dict[str, Any]:
    """Compares two qualification runs and detects performance/reliability regressions."""
    map_a = {r["case_id"]: r for r in run_a_results}
    map_b = {r["case_id"]: r for r in run_b_results}

    all_cases = sorted(list(set(map_a.keys()) | set(map_b.keys())))
    diffs: List[CaseRegressionDiff] = []
    regressions_count = 0

    for cid in all_cases:
        ra = map_a.get(cid)
        rb = map_b.get(cid)

        if not ra or not rb:
            diffs.append(CaseRegressionDiff(
                case_id=cid,
                status_a=ra["status"] if ra else "MISSING",
                status_b=rb["status"] if rb else "MISSING",
                iops_a=ra.get("fio", {}).get("total_iops", 0.0) if ra else 0.0,
                iops_b=rb.get("fio", {}).get("total_iops", 0.0) if rb else 0.0,
                iops_delta_percent=0.0,
                bw_a_mb=ra.get("fio", {}).get("total_bw_mb", 0.0) if ra else 0.0,
                bw_b_mb=rb.get("fio", {}).get("total_bw_mb", 0.0) if rb else 0.0,
                bw_delta_percent=0.0,
                p99_a_ms=round(ra.get("fio", {}).get("lat_p99_us", 0.0) / 1000.0, 3) if ra else 0.0,
                p99_b_ms=round(rb.get("fio", {}).get("lat_p99_us", 0.0) / 1000.0, 3) if rb else 0.0,
                p99_delta_percent=0.0,
                error_delta_a=0,
                error_delta_b=0,
                regressed=True,
                notes="Case missing in one of the runs"
            ))
            regressions_count += 1
            continue

        fio_a = ra.get("fio", {})
        fio_b = rb.get("fio", {})

        iops_a = fio_a.get("total_iops", 0.0)
        iops_b = fio_b.get("total_iops", 0.0)
        iops_pct = round(((iops_b - iops_a) / iops_a * 100.0) if iops_a > 0 else 0.0, 2)

        bw_a = fio_a.get("total_bw_mb", 0.0)
        bw_b = fio_b.get("total_bw_mb", 0.0)
        bw_pct = round(((bw_b - bw_a) / bw_a * 100.0) if bw_a > 0 else 0.0, 2)

        p99_a = round(fio_a.get("lat_p99_us", 0.0) / 1000.0, 3)
        p99_b = round(fio_b.get("lat_p99_us", 0.0) / 1000.0, 3)
        p99_pct = round(((p99_b - p99_a) / p99_a * 100.0) if p99_a > 0 else 0.0, 2)

        err_a = ra.get("deltas", {}).get("media_errors_delta", 0) + ra.get("deltas", {}).get("error_log_delta", 0)
        err_b = rb.get("deltas", {}).get("media_errors_delta", 0) + rb.get("deltas", {}).get("error_log_delta", 0)

        is_regressed = False
        reasons = []

        if ra["status"] == "PASS" and rb["status"] != "PASS":
            is_regressed = True
            reasons.append(f"Status regressed from {ra['status']} to {rb['status']}")
        if iops_pct < iops_regression_threshold_pct:
            is_regressed = True
            reasons.append(f"IOPS dropped by {abs(iops_pct)}%")
        if p99_pct > latency_regression_threshold_pct:
            is_regressed = True
            reasons.append(f"p99 latency increased by {p99_pct}%")
        if err_b > err_a:
            is_regressed = True
            reasons.append(f"Errors increased from {err_a} to {err_b}")

        if is_regressed:
            regressions_count += 1

        diffs.append(CaseRegressionDiff(
            case_id=cid,
            status_a=ra["status"],
            status_b=rb["status"],
            iops_a=iops_a,
            iops_b=iops_b,
            iops_delta_percent=iops_pct,
            bw_a_mb=bw_a,
            bw_b_mb=bw_b,
            bw_delta_percent=bw_pct,
            p99_a_ms=p99_a,
            p99_b_ms=p99_b,
            p99_delta_percent=p99_pct,
            error_delta_a=err_a,
            error_delta_b=err_b,
            regressed=is_regressed,
            notes="; ".join(reasons) if reasons else "Nominal"
        ))

    return {
        "total_cases_compared": len(all_cases),
        "regressions_detected": regressions_count,
        "regression_rate_percent": round((regressions_count / len(all_cases) * 100.0) if all_cases else 0.0, 2),
        "case_diffs": [d.to_dict() for d in diffs]
    }
