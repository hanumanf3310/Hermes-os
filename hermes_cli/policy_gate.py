"""Merged policy gate helpers for startup enforcement.

This module provides a small hard gate that validates the merged policy file
before command surfaces start up.  It is intentionally separate from the
validator so CLI/gateway startup code can fail closed without duplicating the
rules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from tools.merged_policy_validator import PolicyValidationError, assert_policy_file_valid


DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[1] / "website" / "docs" / "reference" / "merged-hard-gate-policy.yaml"


def assert_merged_policy_gate(path: Optional[Path] = None) -> None:
    """Raise ``PolicyValidationError`` if the merged policy file is invalid."""
    assert_policy_file_valid(path or DEFAULT_POLICY_PATH)
