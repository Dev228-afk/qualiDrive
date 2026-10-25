import pytest
from qualidrive.safety.guard import SafetyGuard


def test_safety_guard_blocks_unwhitelisted_device():
    guard = SafetyGuard(whitelist=["/dev/nvme0n1", "/dev/qemu-nvme"])
    safe, reason = guard.validate_target(
        device_path="/dev/nvme1n1",
        is_destructive=True,
        allow_destructive_flag=True
    )
    assert not safe
    assert "BLOCKED_BY_SAFETY" in reason
    assert "whitelist" in reason


def test_safety_guard_requires_allow_destructive_flag():
    guard = SafetyGuard(whitelist=["/dev/nvme0n1"])
    safe, reason = guard.validate_target(
        device_path="/dev/nvme0n1",
        is_destructive=True,
        allow_destructive_flag=False
    )
    assert not safe
    assert "BLOCKED_BY_SAFETY" in reason
    assert "--allow-destructive" in reason


def test_safety_guard_validates_confirmation_token():
    guard = SafetyGuard(whitelist=["/dev/nvme0n1"])
    safe, reason = guard.validate_target(
        device_path="/dev/nvme0n1",
        is_destructive=True,
        allow_destructive_flag=True,
        confirmation_token="WRONG_TOKEN",
        expected_token="CONFIRM_ERASE_123"
    )
    assert not safe
    assert "BLOCKED_BY_SAFETY" in reason
    assert "Confirmation token mismatch" in reason


def test_safety_guard_permits_safe_file_target():
    guard = SafetyGuard()
    safe, reason = guard.validate_target(
        device_path="/tmp/qualidrive_test_dir",
        is_destructive=False
    )
    assert safe
    assert reason == "SAFE_FILE_TARGET"


def test_safety_guard_permits_whitelisted_with_correct_token():
    guard = SafetyGuard(whitelist=["/dev/nvme0n1"])
    safe, reason = guard.validate_target(
        device_path="/dev/nvme0n1",
        is_destructive=True,
        allow_destructive_flag=True,
        confirmation_token="CONFIRM_ERASE_123",
        expected_token="CONFIRM_ERASE_123"
    )
    # Target is not mounted in unit test environment
    assert safe or "mounted" in reason
