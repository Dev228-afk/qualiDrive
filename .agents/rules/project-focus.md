# PRIMARY GOAL:
Build a real NVMe qualification framework that substantiates the resume.

# SAFETY:
Never run destructive I/O against an unverified physical device.
Default to QEMU.
Never target root, mounted, swap, LVM, RAID, or boot devices.
Require explicit allow-destructive mode and device whitelist.

# QUALITY:
Every pass/fail result must point to raw evidence.
Never invent performance metrics.
Never hide a first failure by retrying it.
Preserve raw stdout/stderr for external tools.

# SCOPE:
Do not add unrelated infrastructure.
Do not build a large frontend before qualification execution works.
Do not claim emulation is equivalent to physical firmware validation.

# INTERVIEW:
Every major component must document:
- why it exists
- failure mode
- evidence
- tradeoff
- alternative
- scaling implications
