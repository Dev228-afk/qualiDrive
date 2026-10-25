import pytest
from qualidrive.fio.job_generator import generate_fio_args, determine_fio_rw
from qualidrive.fio.runner import FioRunner


def test_fio_rw_mapping():
    assert determine_fio_rw("sequential", 100) == "read"
    assert determine_fio_rw("sequential", 0) == "write"
    assert determine_fio_rw("sequential", 70) == "rw"
    assert determine_fio_rw("random", 100) == "randread"
    assert determine_fio_rw("random", 0) == "randwrite"
    assert determine_fio_rw("random", 70) == "randrw"


def test_generate_fio_args_structure():
    args = generate_fio_args(
        target_path="/tmp/test_dir",
        block_size="16k",
        queue_depth=16,
        read_percent=70,
        numjobs=2,
        access="random",
        runtime_seconds=5
    )
    args_str = " ".join(args)
    assert "--rw=randrw" in args_str
    assert "--bs=16k" in args_str
    assert "--iodepth=16" in args_str
    assert "--numjobs=2" in args_str
    assert "--runtime=5" in args_str
    assert "--rwmixread=70" in args_str
    assert "--output-format=json+" in args_str


def test_fio_runner_mock_execution():
    runner = FioRunner(mock=True)  # Explicit mock mode
    rc, result, stdout, stderr, elapsed = runner.run(["--name=mock"])
    assert rc == 0
    assert result.total_iops == 2560.0
    assert result.lat_p99_us == 1500.0
