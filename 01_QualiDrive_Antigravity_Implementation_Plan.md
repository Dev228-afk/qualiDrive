# QualiDrive — AI-Agent Implementation Plan

## 1. Project Mission

Build **QualiDrive** as a production-style NVMe SSD qualification and regression framework that substantiates the resume claims for storage qualification, Linux automation, workload generation, NVMe health/telemetry capture, reproducible test matrices, and structured evidence.

This project is based on the resume claim:

> QualiDrive – Automated NVMe SSD qualification and regression framework (Python, Bash, Linux, fio, nvme-cli, Pytest)

The priority order is:

1. **Reproduce the technical claims on the resume with working code.**
2. **Create evidence that can survive technical interview follow-ups.**
3. **Make the qualification process safe, deterministic, and reproducible.**
4. **Create a concise reviewer-facing qualification report/dashboard.**

Do not optimize primarily for UI.

The most important end product is a real test framework that can run against:
- QEMU-emulated NVMe hardware,
- an explicitly whitelisted physical NVMe test device,
- and an optional cloud NVMe profile where useful.

---

# 2. Resume Claims This Project Must Support

The implementation must substantiate these capabilities:

- discover NVMe controllers and namespaces
- validate prerequisites before a test run
- execute configurable test matrices
- vary:
  - block size
  - queue depth
  - read/write mix
  - job count
  - runtime
  - sequential/random access
- capture:
  - Identify Controller
  - Identify Namespace
  - SMART/health information
  - NVMe error logs
  - firmware revision
  - PCIe link state
  - kernel messages
  - temperature
  - IOPS
  - bandwidth
  - latency percentiles
- produce timestamped JSON/CSV evidence
- support 1,200+ generated test cases
- pre-checks
- post-checks
- timeout handling
- retries
- cleanup
- pass/fail thresholds
- JUnit and HTML summaries
- reproducible runs from one manifest

The resume states historical outcomes such as a reduction in hands-on execution time. The recreated project must not invent matching percentages. It should measure its own automation overhead and record the reproduction result separately.

---

# 3. Safety Is a Hard Requirement

This project can issue destructive I/O.

The framework MUST NOT default to a real block device.

Default backend:

```text
QEMU NVMe emulation
```

Real-device execution requires all of:

```text
--backend physical
--device /dev/nvmeXnY
--allow-destructive
--confirmation-token <generated-token>
```

and a device whitelist.

The framework must refuse to run destructive workloads if:

- the target is the root filesystem
- the target is mounted
- the target backs swap
- the target is used by LVM/RAID
- the target is part of the host boot path
- the device was not explicitly whitelisted
- the user did not enable destructive mode

Never issue:

```text
nvme format
nvme sanitize
namespace deletion
firmware activation
destructive fio write workloads
```

against an unverified physical device.

For development and CI, use disk-image-backed QEMU NVMe devices.

---

# 4. Hardware-Independent Development Strategy

The earlier machine limitation must not block this project.

Use three execution backends.

## 4.1 QEMU NVMe backend — default

QEMU supports emulated NVMe controllers and namespaces.

Build a reusable VM profile that exposes:

```text
/dev/nvme0
/dev/nvme0n1
```

and optionally multiple namespaces.

Use this backend for:

- controller discovery
- namespace discovery
- `nvme id ctrl`
- `nvme id ns`
- SMART/log parsing where supported
- fio workload orchestration
- multi-namespace logic
- regression automation
- CI smoke testing

Repository:

```text
infra/qemu/
```

Required command:

```bash
make nvme-lab-up
make nvme-lab-down
```

---

# 5. Optional Physical NVMe Backend

A Linux system with a spare NVMe SSD can run the same harness.

Requirements:

```text
Ubuntu 22.04+ or comparable Linux
nvme-cli
fio
smartmontools
Python 3.11+
root/sudo for selected diagnostics
```

The harness must collect:

```text
lsblk
lspci
nvme list
nvme id ctrl
nvme id ns
nvme log smart
nvme log error
smartctl where supported
dmesg snapshots
sysfs PCIe state
```

Current `nvme-cli` has moved many older command names into grouped commands; for example `nvme id ctrl` and `nvme log smart`, while older forms remain deprecated aliases. Write wrappers that detect the installed CLI version rather than hard-coding only the legacy syntax.

---

# 6. Optional AWS Profile

AWS is optional for QualiDrive.

Useful use cases:

- Linux automation on EC2
- artifact upload to S3
- remote test-agent execution
- CI-triggered qualification runs
- testing NVMe enumeration on instance-store-backed instance types

EC2 instance-store NVMe devices are available on supported instance families and are automatically attached at instance launch.

Do NOT treat EC2 instance-store NVMe as a substitute for physical SSD firmware qualification.

Cloud profile:

```text
EC2 test host
S3 evidence bucket
CloudWatch logs
Systems Manager optional
Terraform
```

Do not add EKS unless there is a real benefit.

---

# 7. Repository Structure

```text
qualidrive/
├── README.md
├── PROJECT_CONSTITUTION.md
├── Makefile
├── pyproject.toml
├── .agents/
│   ├── rules/
│   ├── skills/
│   └── agents/
├── qualidrive/
│   ├── cli/
│   ├── discovery/
│   ├── prerequisites/
│   ├── nvme/
│   ├── fio/
│   ├── telemetry/
│   ├── execution/
│   ├── thresholds/
│   ├── reporting/
│   └── safety/
├── manifests/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── hardware/
├── infra/
│   ├── qemu/
│   └── aws/
├── scripts/
├── evidence/
├── reports/
├── dashboard/
└── interview/
```

---

# 8. First Vertical Slice

Before building a large matrix, make this work:

```text
start QEMU NVMe lab
      |
discover controller and namespace
      |
run one read-only fio workload
      |
capture pre-test telemetry
      |
capture fio JSON+
      |
capture post-test telemetry
      |
evaluate thresholds
      |
write JSON result
      |
generate JUnit + HTML report
```

Only after this succeeds should the agent expand to 1,200+ matrix cases.

---

# 9. Device Discovery

Implement Python models:

```text
NvmeController
NvmeNamespace
PcieLink
DeviceIdentity
HealthSnapshot
```

Discovery sources:

```text
nvme list
nvme id ctrl
nvme id ns
lsblk --json
lspci
sysfs
```

Capture:

```text
model
serial
firmware revision
PCI BDF
namespace ID
namespace size
LBA format
logical block size
controller capabilities
PCIe negotiated speed
PCIe negotiated width
```

Store raw command output and parsed data.

Every parsed field must be traceable to the raw artifact.

---

# 10. Prerequisite Validation

Before a run:

```text
device exists
NVMe driver loaded
required commands installed
sufficient privilege
device not root
device not mounted
device not swap
test directory exists
free space sufficient for file-based test
fio version supported
nvme-cli version supported
time sync reasonable
temperature below pre-test threshold
no critical health flags
```

Generate a machine-readable prerequisite report.

If a destructive test cannot safely run, mark:

```text
BLOCKED_BY_SAFETY
```

not:

```text
FAILED
```

---

# 11. Manifest Format

Use YAML.

Example:

```yaml
run:
  name: nightly_nvme_regression
  backend: qemu
  device_selector:
    model_regex: "QEMU NVMe"
  destructive: false

matrix:
  block_size: [4k, 16k, 128k]
  queue_depth: [1, 8, 32, 64]
  read_percent: [0, 50, 70, 100]
  jobs: [1, 4]
  access: [sequential, random]
  runtime_seconds: [30]

thresholds:
  max_error_count_delta: 0
  max_temperature_c: 80
  max_p99_latency_ms: 50
```

The matrix generator must turn manifest dimensions into explicit test case IDs.

---

# 12. 1,200+ Test Case Requirement

Generate enough combinations to exceed 1,200 cases without creating meaningless permutations.

Dimensions may include:

```text
block size
queue depth
read/write mix
job count
access pattern
runtime
iodepth batching
direct/buffered mode where safe
numa/cpu affinity profile
namespace
```

Create:

```bash
qualidrive plan manifests/full_qualification.yaml
```

Output:

```text
planned_cases: 1344
```

The project only needs to *support* executing the full matrix.

CI should use a smaller smoke matrix.

---

# 13. fio Integration

Use `fio` with JSON or JSON+ output.

Capture:

```text
read IOPS
write IOPS
read bandwidth
write bandwidth
completion latency
total latency
p50
p90
p95
p99
p99.9
CPU usage
disk utilization
error count
```

`fio` supports JSON output and JSON+ latency bins, which is ideal for deterministic parser tests and percentile visualization.

Workload classes:

```text
seq_read
seq_write
rand_read
rand_write
mixed_70_30
mixed_50_50
latency_sensitive
queue_depth_sweep
block_size_sweep
```

All write-heavy physical-device profiles require destructive safety gating.

---

# 14. Pre/Post Health Capture

For every test case:

```text
PRE
---
Identify Controller
Identify Namespace
SMART/Health
NVMe Error Log
PCIe link state
kernel message cursor/offset
temperature
unsafe shutdown count
media/data integrity error count
critical warning
```

Then execute workload.

Then collect the same POST snapshot.

Compute deltas.

Example:

```text
temperature_delta
media_error_delta
error_log_delta
unsafe_shutdown_delta
kernel_error_signatures
PCIe link change
```

---

# 15. Kernel and System Telemetry

Collect:

```text
dmesg
journalctl -k
iostat
vmstat
optional blktrace
optional perf
```

Associate telemetry with:

```text
run_id
case_id
device_id
firmware
start_time
end_time
```

Never mix host-wide logs with a test result without timestamps.

---

# 16. Retry Policy

Retries should be deliberate.

Retryable:

```text
temporary harness SSH/session failure
transient telemetry command timeout
known setup race
```

Do not blindly retry:

```text
media error
I/O timeout
controller reset
data corruption
unexpected SMART delta
```

Those may be the failure being qualified.

Preserve the first failure before any retry.

---

# 17. Timeout Model

Each external command must have:

```text
timeout
stdout capture
stderr capture
exit code
start/end time
```

fio cases must have:

```text
expected runtime
grace period
hard timeout
```

If the test times out:

```text
case status = TIMEOUT
```

and collect emergency evidence before cleanup.

---

# 18. Cleanup

After each case:

- stop background telemetry
- terminate fio if needed
- flush buffers if applicable
- unmount temporary test filesystem if created
- restore test-specific system tuning
- capture final logs
- leave device in known state

Cleanup must run even after failure.

Use `try/finally`.

---

# 19. Pass/Fail Threshold Engine

Thresholds may include:

```text
fio exit status
no media/data integrity error delta
no unexpected NVMe error entries
max temperature
min IOPS
min bandwidth
max p99 latency
max p99.9 latency
no controller reset signature
no PCIe downgrade
no kernel I/O error
```

Threshold definitions belong in YAML.

Result must show:

```text
metric
observed
operator
threshold
status
```

---

# 20. Result Schema

Every case writes:

```json
{
  "run_id": "...",
  "case_id": "...",
  "device": {},
  "workload": {},
  "pre_health": {},
  "fio": {},
  "post_health": {},
  "deltas": {},
  "thresholds": [],
  "artifacts": [],
  "status": "PASS"
}
```

Also export normalized CSV rows.

---

# 21. Reports

Required:

```text
JUnit XML
HTML report
JSON run summary
CSV summary
```

Summary:

```text
planned
executed
passed
failed
blocked
timed_out
retried
duration
```

HTML report should link failures to raw evidence.

---

# 22. Regression Comparison

Support comparison:

```bash
qualidrive compare run_A run_B
```

Dimensions:

```text
firmware A vs firmware B
same workload
same block size
same QD
same device class
```

Report:

```text
IOPS delta
bandwidth delta
latency delta
temperature delta
error-count differences
new failure signatures
```

Require a configurable regression threshold.

---

# 23. Fault Injection

QEMU/simulation profile may inject controlled faults.

Safe examples:

```text
command timeout simulation
telemetry parser failure
synthetic controller-reset kernel log
synthetic media-error log
threshold breach
runner process interruption
```

Do not claim QEMU reproduces real NAND/media physics.

The distinction between emulation, simulation, and physical-device evidence must remain explicit.

---

# 24. CI/CD

Required pipeline:

```text
lint
type check
unit tests
parser fixture tests
manifest validation
QEMU lab boot
NVMe discovery smoke test
read-only fio smoke workload
report generation
artifact upload
```

Nightly or manual extended pipeline:

```text
larger matrix
fault injection
regression comparison
```

Hardware-tagged tests must not run on ordinary CI agents.

---

# 25. AWS Integration

Optional remote runner:

```text
GitHub Actions/Jenkins
       |
       v
launch EC2 test host
       |
       v
run safe NVMe profile
       |
       v
upload evidence to S3
       |
       v
terminate host
```

Store:

```text
run manifests
logs
JUnit
HTML
JSON
```

in S3.

Cloud resources must auto-teardown.

---

# 26. Reviewer Surface

Secondary priority.

Build a simple report viewer/dashboard.

Pages:

```text
Qualification Summary
Test Matrix
Device Identity
SMART/Health
Performance
Failures
Firmware Comparison
Artifacts
```

The dashboard should consume recorded run artifacts.

Do not require a live NVMe device.

---

# 27. Antigravity Agent Structure

Lead:

```text
qualidrive-lead
```

Subagents:

```text
nvme-discovery-agent
fio-matrix-agent
safety-runner-agent
reporting-agent
qemu-infra-agent
verification-interview-agent
dashboard-agent
```

Do not parallelize until the first end-to-end case succeeds.

---

# 28. Antigravity Workspace Rules

Create `.agents/rules/project-focus.md`.

Required contents:

```text
PRIMARY GOAL:
Build a real NVMe qualification framework that substantiates the resume.

SAFETY:
Never run destructive I/O against an unverified physical device.
Default to QEMU.
Never target root, mounted, swap, LVM, RAID, or boot devices.
Require explicit allow-destructive mode and device whitelist.

QUALITY:
Every pass/fail result must point to raw evidence.
Never invent performance metrics.
Never hide a first failure by retrying it.
Preserve raw stdout/stderr for external tools.

SCOPE:
Do not add unrelated infrastructure.
Do not build a large frontend before qualification execution works.
Do not claim emulation is equivalent to physical firmware validation.

INTERVIEW:
Every major component must document:
- why it exists
- failure mode
- evidence
- tradeoff
- alternative
- scaling implications
```

---

# 29. Master Antigravity Prompt

```text
/goal

Implement QualiDrive according to PROJECT_CONSTITUTION.md.

Primary objective:
Substantiate the resume's NVMe qualification claims with a working, safe, reproducible framework.

Default all development to QEMU NVMe emulation.

First complete one vertical slice:
QEMU NVMe -> discovery -> pre-health snapshot -> fio workload -> post-health snapshot -> thresholds -> JSON/JUnit/HTML evidence.

Only then implement the full test-matrix generator.

Priority:
1. safety
2. discovery
3. fio orchestration
4. pre/post telemetry
5. result schema
6. threshold evaluation
7. 1,200+ case matrix generation
8. retry/timeout/cleanup
9. regression comparison
10. CI/QEMU automation
11. optional AWS runner
12. dashboard

Do not fabricate the resume's historical efficiency percentages.
Measure the recreated project independently.

At completion generate interview/QUALIDRIVE_INTERVIEW_GUIDE.md from the implemented code, command output, and test evidence.
```

---

# 30. Interview Guide

Generate:

```text
interview/QUALIDRIVE_INTERVIEW_GUIDE.md
```

For each question include:

```text
30-second answer
90-second answer
deep dive
actual source file
actual command
actual evidence
failure mode
tradeoffs
alternative
follow-up questions
```

Minimum categories:

## NVMe

- controller vs namespace
- submission/completion queues
- queue depth
- namespaces
- SMART/health
- error logs
- critical warnings
- firmware revision
- LBA format
- TRIM/DSM
- PCIe link width/speed

## fio

- IOPS vs bandwidth
- block size
- QD
- job count
- random vs sequential
- direct I/O
- read/write mix
- p99/p99.9
- warmup
- steady state
- reproducibility

## Qualification

- functional
- regression
- stress
- endurance
- negative
- boundary
- fault injection
- qualification matrix
- release criteria

## Linux/debug

- dmesg
- journalctl
- lspci
- lsblk
- iostat
- vmstat
- blktrace
- perf
- sysfs

## Reliability

- controller reset
- I/O timeout
- media error
- thermal throttling
- PCIe downgrade
- unexpected SMART deltas
- flaky test vs product defect

Minimum:

```text
50 primary questions
100 follow-ups
20 failure-diagnosis scenarios
5 test-plan/system-design questions
```

---

# 31. Mandatory Interview Scenarios

The final guide must answer:

1. Why did IOPS stop scaling beyond QD32?
2. Why is p99 latency important when average latency is stable?
3. How do you distinguish a controller reset from a host-side fio error?
4. What evidence would indicate thermal throttling?
5. What if bandwidth drops but no SMART error appears?
6. What if PCIe link width changes from x4 to x2?
7. How do you make fio runs comparable?
8. Why are pre/post SMART snapshots important?
9. What is the difference between qualification failure and harness failure?
10. How would you handle a flaky timeout?
11. Why shouldn't failures always be retried?
12. What test dimensions belong in an SSD qualification matrix?
13. What can QEMU validate and what can it not validate?
14. How would you qualify a new firmware release?
15. How do you prevent destructive test automation from damaging the host?

---

# 32. Definition of Done

QualiDrive is complete only when:

- NVMe controller discovery works
- namespace discovery works
- QEMU backend works
- pre/post telemetry works
- fio JSON parsing works
- latency percentiles work
- matrix generation exceeds 1,200 meaningful cases
- prerequisite safety checks work
- destructive-device protection works
- timeouts work
- retries work
- cleanup works
- thresholds work
- JUnit works
- HTML report works
- JSON/CSV artifacts work
- regression comparison works
- CI smoke tests work
- failure evidence exists
- interview guide exists
- reviewer dashboard/report viewer exists
