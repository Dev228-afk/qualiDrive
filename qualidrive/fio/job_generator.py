"""
fio job configuration and command line argument generator.
"""

from typing import Dict, Any, List


def determine_fio_rw(access: str, read_percent: int) -> str:
    """Maps access pattern and read percentage to fio 'rw' parameter."""
    access_lower = access.lower()
    is_rand = "rand" in access_lower

    if read_percent == 100:
        return "randread" if is_rand else "read"
    elif read_percent == 0:
        return "randwrite" if is_rand else "write"
    else:
        return "randrw" if is_rand else "rw"


def generate_fio_args(
    target_path: str,
    block_size: str = "4k",
    queue_depth: int = 32,
    read_percent: int = 100,
    numjobs: int = 1,
    access: str = "random",
    runtime_seconds: int = 10,
    direct: int = 1,
    ioengine: str = "libaio",
    size_mb: int = 100
) -> List[str]:
    """Generates CLI arguments for fio command."""
    rw = determine_fio_rw(access, read_percent)
    args = [
        f"--name=qualidrive_job",
        f"--rw={rw}",
        f"--bs={block_size}",
        f"--iodepth={queue_depth}",
        f"--numjobs={numjobs}",
        f"--runtime={runtime_seconds}",
        f"--time_based=1",
        f"--ioengine={ioengine}",
        f"--direct={direct}",
        f"--group_reporting=1",
        f"--output-format=json+",
    ]

    if read_percent not in (0, 100):
        args.append(f"--rwmixread={read_percent}")

    if target_path.startswith("/dev/"):
        args.append(f"--filename={target_path}")
    else:
        # File-based path in directory
        args.append(f"--directory={target_path}")
        args.append(f"--size={size_mb}M")

    return args
