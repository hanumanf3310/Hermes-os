"""Validation helpers for the merged hard-gate policy.

This module validates the machine-readable policy file at
``website/docs/reference/merged-hard-gate-policy.yaml`` and returns either a
structured validation result or raises a clear error with the missing gates.

The validator is intentionally small and dependency-light so it can be reused
from tests, docs tooling, or future CLI enforcement code.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import sys

import yaml

DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[1] / "website" / "docs" / "reference" / "merged-hard-gate-policy.yaml"

_REQUIRED_POLICY_LAYERS = ("identity", "evidence", "terminal", "memory", "skills", "conflicts", "checkpoints")
_REQUIRED_LABELS = ("Verified", "Inferred", "Blocked", "Needs confirmation")


class PolicyValidationError(ValueError):
    """Raised when the merged policy file is malformed or incomplete."""

    def __init__(self, errors: List[str]):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


@dataclass(frozen=True)
class PolicyValidationResult:
    valid: bool
    errors: List[str]
    policy: Optional[Dict[str, Any]]


def load_policy_file(path: Path = DEFAULT_POLICY_PATH) -> Dict[str, Any]:
    """Load and parse the policy YAML file."""
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except yaml.YAMLError as exc:
        raise PolicyValidationError([f"Invalid YAML in {path}: {exc}"]) from exc
    except OSError as exc:
        raise PolicyValidationError([f"Failed to read policy file {path}: {exc}"]) from exc

    if not isinstance(data, dict):
        raise PolicyValidationError(["policy root must be a mapping"])
    return data


def _require_mapping(errors: List[str], policy: Dict[str, Any], key: str, parent: str = "") -> Dict[str, Any]:
    full_key = f"{parent}.{key}" if parent else key
    value = policy.get(key)
    if not isinstance(value, dict):
        errors.append(f"{full_key} is required and must be a mapping")
        return {}
    return value


def _require_list(errors: List[str], policy: Dict[str, Any], key: str, parent: str = "") -> List[Any]:
    full_key = f"{parent}.{key}" if parent else key
    value = policy.get(key)
    if not isinstance(value, list):
        errors.append(f"{full_key} is required and must be a list")
        return []
    return value


def _require_bool(errors: List[str], policy: Dict[str, Any], key: str, expected: Optional[bool] = None, parent: str = "") -> None:
    full_key = f"{parent}.{key}" if parent else key
    value = policy.get(key)
    if not isinstance(value, bool):
        errors.append(f"{full_key} is required and must be a boolean")
        return
    if expected is not None and value is not expected:
        errors.append(f"{full_key} must be {expected}")


def validate_policy(policy: Dict[str, Any]) -> List[str]:
    """Return a list of validation errors for *policy*."""
    errors: List[str] = []

    if policy.get("version") != 1:
        errors.append("version must be 1")
    if not isinstance(policy.get("name"), str) or not policy["name"].strip():
        errors.append("name is required and must be a non-empty string")
    if not isinstance(policy.get("purpose"), str) or not policy["purpose"].strip():
        errors.append("purpose is required and must be a non-empty string")
    _require_bool(errors, policy, "source_of_truth", expected=True)

    owner = _require_mapping(errors, policy, "owner")
    if owner:
        if not isinstance(owner.get("user_label"), str) or owner["user_label"].strip() != "Boss":
            errors.append("owner.user_label must be 'Boss'")
        if not isinstance(owner.get("assistant_label"), str) or owner["assistant_label"].strip() != "น้องเมส":
            errors.append("owner.assistant_label must be 'น้องเมส'")

    policy_layers = _require_mapping(errors, policy, "policy_layers")
    if policy_layers:
        for key in _REQUIRED_POLICY_LAYERS:
            value = policy_layers.get(key)
            if not isinstance(value, list) or not value:
                errors.append(f"policy_layers.{key} is required and must be a non-empty list")

    labels = _require_mapping(errors, policy, "labels")
    if labels:
        required_outputs = _require_list(errors, labels, "required_for_outputs", parent="labels")
        if required_outputs and [str(item) for item in required_outputs] != list(_REQUIRED_LABELS):
            errors.append(
                "labels.required_for_outputs must be exactly [Verified, Inferred, Blocked, Needs confirmation]"
            )

    enforcement = _require_mapping(errors, policy, "enforcement")
    if enforcement:
        claims = _require_mapping(errors, enforcement, "claims", parent="enforcement")
        if claims:
            _require_bool(errors, claims, "verified_only_when_evidenced", expected=True, parent="enforcement.claims")

        terminal = _require_mapping(errors, enforcement, "terminal", parent="enforcement")
        if terminal:
            _require_bool(errors, terminal, "require_rtk_wrapper", expected=True, parent="enforcement.terminal")

        memory = _require_mapping(errors, enforcement, "memory", parent="enforcement")
        if memory:
            _require_bool(errors, memory, "require_two_round_confirmation", expected=True, parent="enforcement.memory")

        skills = _require_mapping(errors, enforcement, "skills", parent="enforcement")
        if skills:
            _require_bool(errors, skills, "require_reuse_then_patch_before_create", expected=True, parent="enforcement.skills")
            _require_bool(errors, skills, "require_registry_and_category", expected=True, parent="enforcement.skills")

        conflicts = _require_mapping(errors, enforcement, "conflicts", parent="enforcement")
        if conflicts:
            _require_bool(errors, conflicts, "require_stop_explain_confirm", expected=True, parent="enforcement.conflicts")

    return errors


def validate_policy_file(path: Path = DEFAULT_POLICY_PATH) -> PolicyValidationResult:
    """Load *path* and return a structured validation result."""
    policy = load_policy_file(path)
    errors = validate_policy(policy)
    return PolicyValidationResult(valid=not errors, errors=errors, policy=policy)


def assert_policy_file_valid(path: Path = DEFAULT_POLICY_PATH) -> Dict[str, Any]:
    """Return the policy mapping if valid, otherwise raise PolicyValidationError."""
    result = validate_policy_file(path)
    if not result.valid:
        raise PolicyValidationError(result.errors)
    return result.policy or {}


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point for policy validation."""
    args = list(argv if argv is not None else sys.argv[1:])
    path = Path(args[0]).expanduser() if args else DEFAULT_POLICY_PATH
    result = validate_policy_file(path)
    if result.valid:
        print(f"VALID: {path}")
        return 0

    print(f"INVALID: {path}")
    for error in result.errors:
        print(f"- {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
