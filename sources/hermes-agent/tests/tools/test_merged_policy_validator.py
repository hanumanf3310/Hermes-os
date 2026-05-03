from pathlib import Path

import pytest

from tools.merged_policy_validator import (
    PolicyValidationError,
    PolicyValidationResult,
    assert_policy_file_valid,
    main,
    validate_policy_file,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_DIR = REPO_ROOT / "website" / "docs" / "reference"
POLICY_PATH = REFERENCE_DIR / "merged-hard-gate-policy.yaml"
SCHEMA_PATH = REFERENCE_DIR / "merged-hard-gate-policy.schema.json"
CARD_PATH = REFERENCE_DIR / "merged-hard-gate-policy-card.md"


def test_validate_policy_file_reports_valid_source_of_truth():
    result = validate_policy_file(POLICY_PATH)

    assert isinstance(result, PolicyValidationResult)
    assert result.valid is True
    assert result.errors == []
    assert result.policy["source_of_truth"] is True
    assert result.policy["enforcement"]["terminal"]["require_rtk_wrapper"] is True
    assert result.policy["enforcement"]["memory"]["require_two_round_confirmation"] is True


def test_assert_policy_file_valid_returns_policy_mapping():
    policy = assert_policy_file_valid(POLICY_PATH)

    assert policy["owner"]["user_label"] == "Boss"
    assert policy["owner"]["assistant_label"] == "น้องเมส"
    assert "skills" in policy["policy_layers"]


def test_policy_artifacts_exist():
    assert POLICY_PATH.exists()
    assert SCHEMA_PATH.exists()
    assert CARD_PATH.exists()


def test_assert_policy_file_valid_raises_for_missing_required_gate(tmp_path):
    invalid_path = tmp_path / "broken-policy.yaml"
    invalid_path.write_text(
        """version: 1
name: broken-policy
source_of_truth: true
owner:
  user_label: Boss
  assistant_label: น้องเมส
policy_layers:
  identity:
    - call_user: Boss
enforcement:
  claims:
    verified_only_when_evidenced: true
  terminal:
    require_rtk_wrapper: true
  memory:
    require_two_round_confirmation: true
  skills:
    require_reuse_then_patch_before_create: true
    require_registry_and_category: true
  conflicts:
    require_stop_explain_confirm: true
""",
        encoding="utf-8",
    )

    with pytest.raises(PolicyValidationError, match="policy_layers\\.evidence is required"):
        assert_policy_file_valid(invalid_path)


def test_validator_cli_returns_zero_for_valid_policy(capsys):
    exit_code = main([str(POLICY_PATH)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "VALID:" in captured.out
    assert str(POLICY_PATH) in captured.out
