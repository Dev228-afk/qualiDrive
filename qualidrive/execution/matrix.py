"""
Test matrix generator expanding manifest dimensions into qualification test cases.
"""

import itertools
import yaml
from dataclasses import dataclass, asdict
from typing import List, Dict, Any


@dataclass
class TestCase:
    case_id: str
    block_size: str
    queue_depth: int
    read_percent: int
    jobs: int
    access: str
    runtime_seconds: int
    direct: int = 1
    ioengine: str = "libaio"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_manifest(manifest_path: str) -> Dict[str, Any]:
    with open(manifest_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def generate_test_matrix(manifest: Dict[str, Any]) -> List[TestCase]:
    """Expands matrix dimensions from manifest into a list of explicit TestCases."""
    matrix_cfg = manifest.get("matrix", {})

    block_sizes = matrix_cfg.get("block_size", ["4k"])
    queue_depths = matrix_cfg.get("queue_depth", [32])
    read_percents = matrix_cfg.get("read_percent", [100])
    job_counts = matrix_cfg.get("jobs", [1])
    access_patterns = matrix_cfg.get("access", ["random"])
    runtimes = matrix_cfg.get("runtime_seconds", [10])

    cases: List[TestCase] = []

    for bs, qd, rm, j, acc, rt in itertools.product(
        block_sizes, queue_depths, read_percents, job_counts, access_patterns, runtimes
    ):
        cid = f"tc_bs{bs}_qd{qd}_rm{rm}_j{j}_{acc[:4]}_t{rt}"
        cases.append(TestCase(
            case_id=cid,
            block_size=str(bs),
            queue_depth=int(qd),
            read_percent=int(rm),
            jobs=int(j),
            access=str(acc),
            runtime_seconds=int(rt)
        ))

    return cases
