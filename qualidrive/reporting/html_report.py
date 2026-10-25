"""
HTML qualification report generator creating an interactive summary dashboard.
"""

from typing import List, Dict, Any


def generate_html_report(results: List[Dict[str, Any]], run_id: str, device_info: Dict[str, Any]) -> str:
    """Generates a standalone, beautiful HTML qualification report."""
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    blocked = sum(1 for r in results if r["status"] == "BLOCKED_BY_SAFETY")
    timed_out = sum(1 for r in results if r["status"] == "TIMEOUT")
    pass_rate = round((passed / total * 100.0) if total else 0.0, 1)

    table_rows = []
    for r in results:
        status = r["status"]
        status_color = "#10b981" if status == "PASS" else ("#ef4444" if status == "FAIL" else "#f59e0b")
        fio = r.get("fio", {})
        deltas = r.get("deltas", {})
        post_h = r.get("post_health", {})
        wl = r.get("workload", {})

        p99_ms = round(fio.get("lat_p99_us", 0.0) / 1000.0, 2)
        iops = fio.get("total_iops", 0.0)
        bw_mb = fio.get("total_bw_mb", 0.0)
        temp_c = post_h.get("temperature_c", "-")
        err_delta = deltas.get("media_errors_delta", 0) + deltas.get("error_log_delta", 0)

        table_rows.append(f"""
        <tr>
            <td style="font-family:monospace; font-weight:600;">{r['case_id']}</td>
            <td>{wl.get('block_size','-')}</td>
            <td>QD{wl.get('queue_depth','-')}</td>
            <td>{wl.get('read_percent','-')}% R</td>
            <td>{wl.get('access','-')}</td>
            <td><strong>{iops:,.0f}</strong></td>
            <td>{bw_mb:,.1f} MB/s</td>
            <td>{p99_ms} ms</td>
            <td>{temp_c}°C</td>
            <td>{err_delta}</td>
            <td><span style="background:{status_color}; color:#fff; padding:3px 8px; border-radius:4px; font-weight:600; font-size:12px;">{status}</span></td>
        </tr>
        """)

    rows_html = "\n".join(table_rows)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>QualiDrive Qualification Report - {run_id}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 24px; background: #0f172a; color: #f8fafc; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 16px; margin-bottom: 24px; }}
        .header h1 {{ margin: 0; font-size: 24px; color: #38bdf8; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .kpi-card {{ background: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid #334155; }}
        .kpi-label {{ font-size: 13px; color: #94a3b8; text-transform: uppercase; font-weight: 600; }}
        .kpi-value {{ font-size: 28px; font-weight: 700; margin-top: 6px; color: #f8fafc; }}
        .info-card {{ background: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid #334155; margin-bottom: 24px; }}
        table {{ width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 8px; overflow: hidden; border: 1px solid #334155; }}
        th, td {{ padding: 12px 14px; text-align: left; border-bottom: 1px solid #334155; font-size: 14px; }}
        th {{ background: #0f172a; color: #94a3b8; font-weight: 600; text-transform: uppercase; font-size: 12px; }}
        tr:hover {{ background: #24344d; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>QualiDrive: NVMe SSD Qualification Report</h1>
            <div style="color: #94a3b8; margin-top: 4px;">Run Identifier: <strong>{run_id}</strong></div>
        </div>
        <div style="text-align: right;">
            <span style="background: #0284c7; color: #fff; padding: 6px 14px; border-radius: 6px; font-weight: 600;">Status: COMPLETED</span>
        </div>
    </div>

    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-label">Total Cases</div>
            <div class="kpi-value">{total}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Pass Rate</div>
            <div class="kpi-value" style="color: {'#10b981' if pass_rate >= 90 else '#ef4444'};">{pass_rate}%</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Passed</div>
            <div class="kpi-value" style="color: #10b981;">{passed}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Failed</div>
            <div class="kpi-value" style="color: {'#ef4444' if failed > 0 else '#94a3b8'};">{failed}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Blocked / Safety</div>
            <div class="kpi-value" style="color: #f59e0b;">{blocked}</div>
        </div>
    </div>

    <div class="info-card">
        <h3 style="margin-top:0; color:#38bdf8; font-size:16px;">Device Topology & Identity</h3>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; font-size: 14px;">
            <div><strong>Model:</strong> {device_info.get('model', 'QEMU NVMe Controller')}</div>
            <div><strong>Serial:</strong> {device_info.get('serial', 'QEMU_NVME_0001')}</div>
            <div><strong>Firmware:</strong> {device_info.get('firmware_rev', '1.0')}</div>
            <div><strong>PCIe Link:</strong> {device_info.get('pcie_link', {}).get('speed', '8.0 GT/s')} ({device_info.get('pcie_link', {}).get('width', 'x4')})</div>
        </div>
    </div>

    <h3 style="color:#38bdf8; font-size:16px; margin-bottom: 12px;">Test Matrix Results</h3>
    <table>
        <thead>
            <tr>
                <th>Test Case ID</th>
                <th>Block Size</th>
                <th>QD</th>
                <th>R/W Mix</th>
                <th>Pattern</th>
                <th>IOPS</th>
                <th>Bandwidth</th>
                <th>p99 Latency</th>
                <th>Peak Temp</th>
                <th>Error Δ</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
</body>
</html>
"""
