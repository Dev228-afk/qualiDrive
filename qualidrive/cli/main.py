"""
Command Line Interface (CLI) for QualiDrive NVMe Qualification Framework.
"""

import argparse
import json
import os
import sys
import time
import uuid
from typing import List, Dict, Any

from qualidrive.discovery.scanner import DeviceScanner
from qualidrive.execution.matrix import load_manifest, generate_test_matrix
from qualidrive.execution.runner import QualificationRunner
from qualidrive.execution.compare import compare_runs
from qualidrive.reporting.html_report import generate_html_report
from qualidrive.reporting.junit import generate_junit_xml
from qualidrive.reporting.json_exporter import export_run_artifacts
from qualidrive.safety.guard import SafetyGuard
from qualidrive.thresholds.rules import ThresholdRules


def cmd_discover(args):
    scanner = DeviceScanner()
    controllers = scanner.scan()

    if not controllers:
        print("[INFO] No physical NVMe controllers detected via sysfs/nvme-cli.")
        print("[INFO] Displaying default QEMU emulated NVMe profile for qualification:")
        ctrl = scanner.get_synthetic_qemu_device()
        controllers = [ctrl]

    print("\n" + "=" * 65)
    print(" QUALIDRIVE NVME DISCOVERY REPORT")
    print("=" * 65)
    for c in controllers:
        print(f"Controller:   {c.controller_id} ({c.device_path})")
        print(f"  Model:      {c.model}")
        print(f"  Serial:     {c.serial}")
        print(f"  Firmware:   {c.firmware_rev}")
        print(f"  PCIe Link:  {c.pcie_link.speed} ({c.pcie_link.width}) [Max: {c.pcie_link.max_speed} {c.pcie_link.max_width}]")
        print(f"  Namespaces: ({len(c.namespaces)})")
        for ns in c.namespaces:
            size_gb = ns.size_bytes / (1024**3)
            print(f"    * {ns.device_path} (NSID {ns.nsid}): {size_gb:.1f} GiB, Sector: {ns.sector_size} B")
        print("-" * 65)
    print()


def cmd_plan(args):
    manifest = load_manifest(args.manifest)
    cases = generate_test_matrix(manifest)

    print("\n" + "=" * 65)
    print(f" QUALIDRIVE TEST MATRIX PLAN: {manifest.get('run', {}).get('name', 'Qualification Run')}")
    print("=" * 65)
    print(f"Backend Target:       {manifest.get('run', {}).get('backend', 'qemu')}")
    print(f"Total Planned Cases:  {len(cases)}")
    print("-" * 65)
    print("Sample Planned Cases (first 5):")
    for tc in cases[:5]:
        print(f"  * {tc.case_id}: BS={tc.block_size}, QD={tc.queue_depth}, R/W={tc.read_percent}% Read, {tc.access}, {tc.runtime_seconds}s")
    if len(cases) > 5:
        print(f"  ... and {len(cases) - 5} additional cases.")
    print("=" * 65 + "\n")


def cmd_run(args):
    manifest = load_manifest(args.manifest)
    run_cfg = manifest.get("run", {})
    run_name = run_cfg.get("name", "qual_run")
    run_id = f"{run_name}_{int(time.time())}"
    output_dir = args.output_dir or f"./reports/{run_id}"
    os.makedirs(output_dir, exist_ok=True)

    scanner = DeviceScanner()
    controllers = scanner.scan()
    ctrl = controllers[0] if controllers else scanner.get_synthetic_qemu_device()

    target_path = args.device or run_cfg.get("device_path")
    if not target_path:
        # Default to a safe file-based scratch directory in output_dir
        scratch_dir = os.path.join(output_dir, "scratch_target")
        os.makedirs(scratch_dir, exist_ok=True)
        target_path = scratch_dir

    threshold_rules = ThresholdRules.from_dict(manifest.get("thresholds", {}))
    guard = SafetyGuard(whitelist=run_cfg.get("device_whitelist", ["/dev/nvme0n1", "/dev/qemu-nvme"]))

    runner = QualificationRunner(guard=guard, scanner=scanner)
    cases = generate_test_matrix(manifest)

    if args.max_cases and args.max_cases > 0:
        cases = cases[:args.max_cases]

    print("\n" + "=" * 65)
    print(f" EXECUTING QUALIDRIVE SUITE: {run_id}")
    print(f" Target: {target_path} | Cases: {len(cases)}")
    print("=" * 65)

    results: List[Dict[str, Any]] = []
    artifacts_dir = os.path.join(output_dir, "artifacts")

    for idx, tc in enumerate(cases, 1):
        print(f"[{idx}/{len(cases)}] Executing {tc.case_id}...", end=" ", flush=True)
        res = runner.execute_case(
            run_id=run_id,
            test_case=tc,
            target_path=target_path,
            controller=ctrl,
            threshold_rules=threshold_rules,
            allow_destructive=args.allow_destructive,
            confirmation_token=args.confirmation_token or "",
            artifacts_dir=artifacts_dir
        )
        results.append(res)
        status = res["status"]
        iops = res.get("fio", {}).get("total_iops", 0)
        p99_ms = round(res.get("fio", {}).get("lat_p99_us", 0) / 1000.0, 2)
        print(f"[{status}] (IOPS: {iops:,.0f}, p99: {p99_ms} ms)")

    # Export artifacts
    arts = export_run_artifacts(results, run_id, output_dir)
    junit_str = generate_junit_xml(results, run_id)
    junit_path = os.path.join(output_dir, f"{run_id}_junit.xml")
    with open(junit_path, "w", encoding="utf-8") as f:
        f.write(junit_str)

    html_str = generate_html_report(results, run_id, ctrl.to_dict())
    html_path = os.path.join(output_dir, f"{run_id}_report.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_str)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    blocked = sum(1 for r in results if r["status"] == "BLOCKED_BY_SAFETY")

    print("\n" + "=" * 65)
    print(f" QUALIFICATION COMPLETED: {run_id}")
    print(f" Passed: {passed} | Failed: {failed} | Blocked: {blocked} | Total: {len(results)}")
    print(f" HTML Report:  {html_path}")
    print(f" JUnit XML:    {junit_path}")
    print(f" JSON Summary: {arts['json']}")
    print(f" CSV Summary:  {arts['csv']}")
    print("=" * 65 + "\n")


def cmd_compare(args):
    with open(args.run_a, "r", encoding="utf-8") as f:
        data_a = json.load(f)
    with open(args.run_b, "r", encoding="utf-8") as f:
        data_b = json.load(f)

    results_a = data_a.get("results", [])
    results_b = data_b.get("results", [])

    diff_report = compare_runs(results_a, results_b)

    print("\n" + "=" * 75)
    print(" QUALIDRIVE REGRESSION COMPARISON REPORT")
    print("=" * 75)
    print(f"Run A: {data_a.get('run_id')} | Run B: {data_b.get('run_id')}")
    print(f"Cases Compared: {diff_report['total_cases_compared']}")
    print(f"Regressions:    {diff_report['regressions_detected']} ({diff_report['regression_rate_percent']}%)")
    print("-" * 75)
    print(f"{'Case ID':<30} | {'IOPS Δ %':<10} | {'p99 Lat Δ %':<12} | {'Regressed?':<10} | Notes")
    print("-" * 75)
    for d in diff_report["case_diffs"][:15]:
        reg_str = "YES" if d["regressed"] else "NO"
        print(f"{d['case_id']:<30} | {d['iops_delta_percent']:>8.1f}% | {d['p99_delta_percent']:>10.1f}% | {reg_str:<10} | {d['notes']}")
    print("=" * 75 + "\n")


def main():
    parser = argparse.ArgumentParser(description="QualiDrive: NVMe SSD Qualification Framework")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # discover
    p_disc = subparsers.add_parser("discover", help="Discover NVMe controllers and namespaces")
    p_disc.set_defaults(func=cmd_discover)

    # plan
    p_plan = subparsers.add_parser("plan", help="Generate and display test matrix plan")
    p_plan.add_argument("manifest", help="Path to manifest YAML")
    p_plan.set_defaults(func=cmd_plan)

    # run
    p_run = subparsers.add_parser("run", help="Execute qualification matrix")
    p_run.add_argument("manifest", help="Path to manifest YAML")
    p_run.add_argument("--device", help="Target NVMe block device or scratch directory")
    p_run.add_argument("--allow-destructive", action="store_true", help="Allow destructive write tests")
    p_run.add_argument("--confirmation-token", help="Confirmation token for destructive tests")
    p_run.add_argument("--max-cases", type=int, default=0, help="Limit number of test cases to execute")
    p_run.add_argument("--output-dir", help="Directory to store reports and artifacts")
    p_run.set_defaults(func=cmd_run)

    # compare
    p_comp = subparsers.add_parser("compare", help="Compare two qualification runs for regression analysis")
    p_comp.add_argument("run_a", help="Path to run A summary JSON")
    p_comp.add_argument("run_b", help="Path to run B summary JSON")
    p_comp.set_defaults(func=cmd_compare)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
