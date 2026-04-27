#!/usr/bin/env python3
"""Hermes Fact+* validator.

Validates Fact Store records against the current Draft 2020-12 contract
and enforces the Fact / Fact+ / Fact* / Fact+* rules used by Hermes OS.

This module is intentionally dependency-free so it can run anywhere Python 3
is available.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ALLOWED_FACT_TYPES = {"fact", "fact_plus", "fact_star", "fact_plus_star"}
ALLOWED_CATEGORIES = {
    "user_pref",
    "policy",
    "technical",
    "project",
    "learning",
    "tool",
    "other",
    "general",
}
ALLOWED_SOURCES = {
    "manual",
    "system",
    "imported",
    "learned",
    "inferred",
    "unknown",
}
ALLOWED_IMPORTANCE = {"normal", "important", "critical"}
ALLOWED_VERIFICATION = {"unverified", "verified", "needs_review", "rejected"}
ALLOWED_IMPACT_SCOPE = {
    "none",
    "user_pref",
    "learning",
    "dashboard",
    "workflow",
    "policy",
    "routing",
    "safety",
    "rollback",
    "tooling",
    "hermes_os",
    "thclaws",
    "omx",
    "upstream_core",
}

SCHEMA_PATH = Path(__file__).with_name("fact-record.schema.json")


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: List[str]

    def raise_for_errors(self) -> None:
        if not self.ok:
            raise ValueError("Fact record validation failed: " + "; ".join(self.errors))


def _is_bool(value: Any) -> bool:
    return isinstance(value, bool)


def _is_str(value: Any) -> bool:
    return isinstance(value, str)


def _is_nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_datetime(value: Any) -> bool:
    if not _is_str(value):
        return False
    candidates = [value, value.replace("Z", "+00:00")]
    for candidate in candidates:
        try:
            datetime.fromisoformat(candidate)
            return True
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            datetime.strptime(value, fmt)
            return True
        except ValueError:
            pass
    return False


def _ensure_list(value: Any) -> bool:
    return isinstance(value, list)


def _check_enum(name: str, value: Any, allowed: Iterable[str], errors: List[str]) -> None:
    if value not in allowed:
        errors.append(f"{name} must be one of {sorted(allowed)}, got {value!r}")


def normalize_fact_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Return a shallow copy with common implicit defaults filled in.

    This is optional convenience logic for callers that want to prepare a record
    before validation. Validation still applies after normalization.
    """
    normalized = dict(record)
    normalized.setdefault("tags", [])
    normalized.setdefault("source", "unknown")
    normalized.setdefault("impact_scope", ["none"])
    normalized.setdefault("rollback_required", False)
    normalized.setdefault("trust_score", 0.5)
    normalized.setdefault("confidence_score", 0.5)
    normalized.setdefault("verification_status", "unverified")
    return normalized


def classify_fact_type(record: Dict[str, Any]) -> str:
    """Infer a canonical fact_type from flags when one is missing.

    If fact_type already exists, it is returned as-is.
    """
    fact_type = record.get("fact_type")
    if fact_type in ALLOWED_FACT_TYPES:
        return fact_type
    fact_plus = record.get("fact_plus") is True
    fact_star = record.get("fact_star") is True
    if fact_plus and fact_star:
        return "fact_plus_star"
    if fact_plus:
        return "fact_plus"
    if fact_star:
        return "fact_star"
    return "fact"


def validate_fact_record(record: Dict[str, Any], *, strict: bool = True) -> ValidationResult:
    errors: List[str] = []

    if not isinstance(record, dict):
        return ValidationResult(False, ["record must be an object/dict"])

    allowed_keys = {
        "fact_id",
        "content",
        "category",
        "tags",
        "source",
        "fact_type",
        "fact_star",
        "fact_plus",
        "verify_before_use",
        "importance_level",
        "star_reason",
        "learning_policy_id",
        "verified_by",
        "last_verified_at",
        "verification_status",
        "trust_score",
        "confidence_score",
        "impact_scope",
        "rollback_required",
        "related_entities",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "notes",
    }
    extra_keys = sorted(set(record) - allowed_keys)
    if extra_keys:
        errors.append(f"unexpected fields: {extra_keys}")
        if strict:
            return ValidationResult(False, errors)

    required = [
        "fact_id",
        "content",
        "category",
        "fact_type",
        "fact_star",
        "fact_plus",
        "verify_before_use",
        "importance_level",
        "verification_status",
        "trust_score",
        "confidence_score",
        "created_at",
        "updated_at",
    ]
    missing = [field for field in required if field not in record]
    if missing:
        errors.append(f"missing required fields: {missing}")

    # Type checks
    if "fact_id" in record and not _is_int(record["fact_id"]):
        errors.append("fact_id must be an integer")
    if "content" in record and not _is_nonempty_str(record["content"]):
        errors.append("content must be a non-empty string")
    if "category" in record:
        if not _is_nonempty_str(record["category"]):
            errors.append("category must be a non-empty string")
        elif record["category"] not in ALLOWED_CATEGORIES:
            errors.append(f"category must be one of {sorted(ALLOWED_CATEGORIES)}, got {record['category']!r}")
    if "tags" in record:
        if not _ensure_list(record["tags"]):
            errors.append("tags must be an array/list")
        else:
            for idx, tag in enumerate(record["tags"]):
                if not _is_nonempty_str(tag):
                    errors.append(f"tags[{idx}] must be a non-empty string")
    if "source" in record:
        if not _is_nonempty_str(record["source"]):
            errors.append("source must be a non-empty string")
        elif record["source"] not in ALLOWED_SOURCES:
            errors.append(f"source must be one of {sorted(ALLOWED_SOURCES)}, got {record['source']!r}")
    if "fact_type" in record:
        if not _is_nonempty_str(record["fact_type"]):
            errors.append("fact_type must be a non-empty string")
        elif record["fact_type"] not in ALLOWED_FACT_TYPES:
            errors.append(f"fact_type must be one of {sorted(ALLOWED_FACT_TYPES)}, got {record['fact_type']!r}")
    for field in ("fact_star", "fact_plus", "verify_before_use", "rollback_required"):
        if field in record and not _is_bool(record[field]):
            errors.append(f"{field} must be a boolean")
    if "importance_level" in record:
        if not _is_nonempty_str(record["importance_level"]):
            errors.append("importance_level must be a non-empty string")
        elif record["importance_level"] not in ALLOWED_IMPORTANCE:
            errors.append(f"importance_level must be one of {sorted(ALLOWED_IMPORTANCE)}, got {record['importance_level']!r}")
    for field in ("star_reason", "learning_policy_id", "verified_by", "created_by", "updated_by", "notes"):
        if field in record and record[field] is not None and not _is_str(record[field]):
            errors.append(f"{field} must be a string or null")
    if "last_verified_at" in record and record["last_verified_at"] is not None and not _is_datetime(record["last_verified_at"]):
        errors.append("last_verified_at must be RFC3339/ISO-8601 datetime or null")
    if "verification_status" in record:
        if not _is_nonempty_str(record["verification_status"]):
            errors.append("verification_status must be a non-empty string")
        elif record["verification_status"] not in ALLOWED_VERIFICATION:
            errors.append(
                f"verification_status must be one of {sorted(ALLOWED_VERIFICATION)}, got {record['verification_status']!r}"
            )
    for field in ("trust_score", "confidence_score"):
        if field in record:
            if not _is_number(record[field]):
                errors.append(f"{field} must be a number")
            elif not (0 <= float(record[field]) <= 1):
                errors.append(f"{field} must be between 0 and 1")
    if "impact_scope" in record:
        if not _ensure_list(record["impact_scope"]):
            errors.append("impact_scope must be an array/list")
        else:
            for idx, scope in enumerate(record["impact_scope"]):
                if not _is_nonempty_str(scope):
                    errors.append(f"impact_scope[{idx}] must be a non-empty string")
                elif scope not in ALLOWED_IMPACT_SCOPE:
                    errors.append(f"impact_scope[{idx}] must be one of {sorted(ALLOWED_IMPACT_SCOPE)}, got {scope!r}")
    for field in ("created_at", "updated_at"):
        if field in record and not _is_datetime(record[field]):
            errors.append(f"{field} must be RFC3339/ISO-8601 datetime")

    # Cross-field rules
    fact_type = record.get("fact_type")
    fact_plus = record.get("fact_plus")
    fact_star = record.get("fact_star")
    verify_before_use = record.get("verify_before_use")
    importance_level = record.get("importance_level")
    verification_status = record.get("verification_status")

    if fact_type in ALLOWED_FACT_TYPES:
        inferred = classify_fact_type(record)
        if fact_type != inferred and ("fact_plus" in record or "fact_star" in record):
            errors.append(f"fact_type {fact_type!r} does not match flag combination {inferred!r}")

    if fact_type == "fact":
        if fact_plus is not False:
            errors.append("fact records must set fact_plus=false")
        if fact_star is not False:
            errors.append("fact records must set fact_star=false")
        if verify_before_use is not False:
            errors.append("fact records must set verify_before_use=false")
        if importance_level is not None and importance_level != "normal":
            errors.append("fact records must set importance_level='normal'")

    elif fact_type == "fact_plus":
        if fact_plus is not True:
            errors.append("fact_plus records must set fact_plus=true")
        if fact_star is not False:
            errors.append("fact_plus records must set fact_star=false")
        if verify_before_use is not False:
            errors.append("fact_plus records must set verify_before_use=false")
        if not _is_nonempty_str(record.get("learning_policy_id")):
            errors.append("fact_plus records require learning_policy_id")

    elif fact_type == "fact_star":
        if fact_star is not True:
            errors.append("fact_star records must set fact_star=true")
        if verify_before_use is not True:
            errors.append("fact_star records must set verify_before_use=true")
        if importance_level != "critical":
            errors.append("fact_star records must set importance_level='critical'")
        if not _is_nonempty_str(record.get("star_reason")):
            errors.append("fact_star records require star_reason")

    elif fact_type == "fact_plus_star":
        if fact_plus is not True:
            errors.append("fact_plus_star records must set fact_plus=true")
        if fact_star is not True:
            errors.append("fact_plus_star records must set fact_star=true")
        if verify_before_use is not True:
            errors.append("fact_plus_star records must set verify_before_use=true")
        if importance_level != "critical":
            errors.append("fact_plus_star records must set importance_level='critical'")
        if not _is_nonempty_str(record.get("learning_policy_id")):
            errors.append("fact_plus_star records require learning_policy_id")
        if not _is_nonempty_str(record.get("star_reason")):
            errors.append("fact_plus_star records require star_reason")

    if fact_star is True and verify_before_use is not True:
        errors.append("fact_star=true requires verify_before_use=true")

    if verification_status == "verified" and fact_star is True and not _is_datetime(record.get("last_verified_at")):
        errors.append("verified star facts should include last_verified_at")

    return ValidationResult(ok=not errors, errors=errors)


def should_feed_learning(record: Dict[str, Any]) -> bool:
    return record.get("fact_plus") is True or record.get("fact_type") in {"fact_plus", "fact_plus_star"}


def can_use_operationally(record: Dict[str, Any]) -> bool:
    if record.get("fact_star") is True:
        return record.get("verification_status") == "verified"
    return True


def load_json_file(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _cli(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Hermes Fact records, including Fact+*")
    parser.add_argument("path", nargs="?", help="Path to a JSON file containing a fact record; reads stdin if omitted")
    parser.add_argument("--loose", action="store_true", help="Report errors without failing on unexpected extra fields")
    parser.add_argument("--show-normalized", action="store_true", help="Print normalized JSON when validation succeeds")
    args = parser.parse_args(argv)

    try:
        if args.path:
            record = load_json_file(Path(args.path))
        else:
            record = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"INVALID JSON: {exc}", file=sys.stderr)
        return 2

    normalized = normalize_fact_record(record)
    result = validate_fact_record(normalized, strict=not args.loose)
    if result.ok:
        print("OK")
        if args.show_normalized:
            print(json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    for error in result.errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(_cli())
