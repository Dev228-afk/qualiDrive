"""
JSON and CSV result exporter for qualification run artifacts.
"""

import csv
import json
import os
from typing import List, Dict, Any


def export_run_artifacts(
    results: List[Dict[str, Any]],
    run_id: str,
    output_dir: str
) -> Dict[str, str]:
    """Saves run_summary.json and summary.csv to output_dir."""
    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(output_dir, f"{run_id}_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "run_id": run_id,
            "total_cases": len(results),
            "passed": sum(1 for r in results if r["status"] == "PASS"),
            "failed": sum(1 for r in results if r["status"] == "FAIL"),
            "blocked": sum(1 for r in results if r["status"] == "BLOCKED_BY_SAFETY"),
            "results": results
        }, f, indent=2)

    csv_path = os.path.join(output_dir, f"{run_id}_summary.csv")
    fieldnames = [
        "case_id", "status", "block_size", "queue_depth", "read_percent", "access",
        "total_iops", "total_bw_mb", "p99_latency_ms", "temperature_c", "media_errors_delta", "error_log_delta"
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            wl = r.get("workload", {})
            fio = r.get("fio", {})
            deltas = r.get("deltas", {})
            post_h = r.get("post_health", {})
            writer.writerow({
                "case_id": r["case_id"],
                "status": r["status"],
                "block_size": wl.get("block_size", ""),
                "queue_depth": wl.get("queue_depth", 0),
                "read_percent": wl.get("read_percent", 0),
                "access": wl.get("access", ""),
                "total_iops": fio.get("total_iops", 0.0),
                "total_bw_mb": fio.get("total_bw_mb", 0.0),
                "p99_latency_ms": round(fio.get("lat_p99_us", 0.0) / 1000.0, 3),
                "temperature_c": post_h.get("temperature_c", 0),
                "media_errors_delta": deltas.get("media_errors_delta", 0),
                "error_log_delta": deltas.get("error_log_delta", 0),
            })

    return {"json": json_path, "csv": csv_path}
