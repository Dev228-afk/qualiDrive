# PROJECT CONSTITUTION: QualiDrive

## Mission Statement
QualiDrive is an automated NVMe SSD qualification and regression framework built to validate SSD firmware and hardware across performance, reliability, telemetry, and error-handling criteria.

## Absolute Safety Directives
1. **Host Storage Protection**: Under NO circumstances shall destructive workloads (formatting, sanitization, raw block writes) be executed against unverified or active host devices.
2. **Mandatory Device Whitelist**: Any target device for destructive tests must be explicitly declared in an isolated whitelist.
3. **Mount & System Guards**: Devices containing root (`/`), boot (`/boot`), swap, LVM, RAID, or active mounts are strictly prohibited from destructive execution.
4. **Safety Over Failure**: If safety prerequisites fail, the framework marks tests as `BLOCKED_BY_SAFETY` rather than `FAILED`.
5. **Safe Default**: Development and continuous integration default to QEMU-emulated NVMe devices or non-destructive synthetic workloads.

## Engineering Principles
1. **Traceable Evidence**: Every qualification metric (IOPS, latency, SMART deltas) must link directly to raw stdout/stderr artifacts.
2. **Zero Metric Fabrication**: Never manufacture or hallucinate performance numbers or improvement percentages.
3. **First-Failure Preservation**: Do not mask true hardware/firmware defects with blind retries.
4. **Structured Lifecycle**: Enforce Pre-check -> Pre-telemetry -> Workload -> Post-telemetry -> Deltas -> Thresholds -> Cleanup.
