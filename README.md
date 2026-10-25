# QualiDrive

Automated NVMe SSD qualification and regression framework implemented in Python, Linux, Bash, fio, and nvme-cli.

## Key Capabilities
- **NVMe Topology & Controller Discovery**: Enumerates controllers, namespaces, PCIe link speeds/widths, and Identify Controller/Namespace descriptors.
- **Safety Engine**: Hardware whitelist, mount/swap/root guardrails, and non-destructive fallbacks.
- **Matrix Generator**: Generates 1,200+ multi-dimensional test combinations across block sizes, queue depths, R/W mixes, numjobs, and access patterns.
- **Workload Orchestration**: Direct integration with `fio` using structured JSON+ telemetry.
- **Telemetry & Health Lifecycle**: Pre-test and post-test SMART/health snapshots, error logs, and kernel message audits.
- **Threshold Engine**: Automated SLA verification on latency percentiles (p99/p99.9), IOPS, bandwidth, and zero media/SMART error delta invariants.
- **Reporting & Dashboards**: Standard JUnit XML, JSON run summaries, CSV exports, and interactive HTML qualification dashboards.
- **Regression Analysis**: Cross-firmware comparison (`qualidrive compare`) highlighting performance regressions and health delta changes.

## Quickstart
```bash
# Discover controllers and namespaces
python3 -m qualidrive.cli.main discover

# Plan test matrix (generates 1,200+ test cases)
python3 -m qualidrive.cli.main plan manifests/full_qualification.yaml

# Execute qualification run against QEMU or safe target
python3 -m qualidrive.cli.main run manifests/smoke.yaml --output-dir reports/smoke_run

# Compare two qualification runs
python3 -m qualidrive.cli.main compare reports/run_v1 reports/run_v2
```
