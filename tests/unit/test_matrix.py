import os
import pytest
from qualidrive.execution.matrix import load_manifest, generate_test_matrix


def test_matrix_generation_smoke_manifest():
    manifest_path = os.path.join(os.path.dirname(__file__), "../../manifests/smoke.yaml")
    manifest = load_manifest(manifest_path)
    cases = generate_test_matrix(manifest)

    # Smoke matrix: 2 block sizes * 2 queue depths * 1 read_pct * 1 jobs * 1 access * 1 runtime = 4 cases
    assert len(cases) == 4
    case_ids = [c.case_id for c in cases]
    assert len(set(case_ids)) == 4  # All case IDs must be unique
    assert "tc_bs4k_qd1_rm100_j1_rand_t3" in case_ids
    assert "tc_bs128k_qd32_rm100_j1_rand_t3" in case_ids


def test_matrix_generation_exceeds_1200_cases():
    manifest_path = os.path.join(os.path.dirname(__file__), "../../manifests/full_qualification.yaml")
    manifest = load_manifest(manifest_path)
    cases = generate_test_matrix(manifest)

    # Full qualification matrix: 8 block sizes * 7 QD * 4 read_pct * 3 jobs * 2 access * 1 runtime = 1,344 cases
    assert len(cases) == 1344
    assert len(cases) > 1200

    # Ensure deterministic uniqueness
    case_ids = {c.case_id for c in cases}
    assert len(case_ids) == len(cases)
