#!/usr/bin/env python3
"""Validate release-facing Skeptic Engine claim contracts.

The validator is intentionally small and fail-closed:
- every referenced file must exist
- every claim check must pass
- matrix summary counts must match claim statuses
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = Path("claims/publication_canonical_index.v0.2.0.json")
MATRIX_PATH = Path("claims/publication_claim_matrix.v0.2.0.json")


def fail(message: str) -> None:
    raise AssertionError(message)


def load_json(rel_path: str | Path) -> Any:
    path = REPO_ROOT / rel_path
    if not path.exists():
        fail(f"Missing JSON artifact: {rel_path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_text(rel_path: str | Path) -> str:
    path = REPO_ROOT / rel_path
    if not path.exists():
        fail(f"Missing text artifact: {rel_path}")
    return path.read_text(encoding="utf-8")


def rel_exists(rel_path: str | Path) -> None:
    if not (REPO_ROOT / rel_path).exists():
        fail(f"Missing referenced artifact: {rel_path}")


def json_path_get(data: Any, dotted_path: str) -> Any:
    current = data
    for part in dotted_path.split("."):
        if isinstance(current, dict):
            if part not in current:
                fail(f"JSON path missing key '{part}' in '{dotted_path}'")
            current = current[part]
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError) as exc:
                fail(f"JSON path invalid list index '{part}' in '{dotted_path}': {exc}")
        else:
            fail(f"JSON path cannot descend into {type(current).__name__} at '{part}'")
    return current


def values_equal(actual: Any, expected: Any, tolerance: float | None = None) -> bool:
    if isinstance(expected, bool):
        return actual is expected
    if isinstance(expected, int) and not isinstance(expected, bool):
        return actual == expected
    if isinstance(expected, float):
        if not isinstance(actual, int | float):
            return False
        tol = 0.0 if tolerance is None else tolerance
        return math.isclose(float(actual), expected, rel_tol=0.0, abs_tol=tol)
    return actual == expected


def validate_index(index: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "generated_for",
        "scope",
        "release_surface",
        "governance",
        "source_of_truth",
        "note",
    }
    if not required.issubset(index):
        fail(f"Canonical index missing keys: {sorted(required - set(index))}")

    for rel_path in index["release_surface"]:
        rel_exists(rel_path)

    for rel_path in index["governance"].values():
        rel_exists(rel_path)

    for group, paths in index["source_of_truth"].items():
        if not isinstance(paths, list) or not paths:
            fail(f"source_of_truth.{group} must be a non-empty list")
        for rel_path in paths:
            rel_exists(rel_path)


def run_check(check: dict[str, Any]) -> None:
    check_type = check.get("type")
    rel_path = check.get("path")
    if not check_type or not rel_path:
        fail(f"Invalid check object: {check}")

    if check_type == "file_contains":
        text = read_text(rel_path)
        expected_text = check["text"]
        if expected_text not in text:
            fail(f"{rel_path} does not contain required text: {expected_text!r}")
        return

    if check_type == "file_not_contains":
        text = read_text(rel_path)
        forbidden_text = check["text"]
        if forbidden_text in text:
            fail(f"{rel_path} contains retired/forbidden text: {forbidden_text!r}")
        return

    if check_type == "json_value":
        data = load_json(rel_path)
        actual = json_path_get(data, check["json_path"])
        expected = check["expected"]
        tolerance = check.get("tolerance")
        if not values_equal(actual, expected, tolerance):
            fail(
                f"{rel_path}:{check['json_path']} expected {expected!r}, "
                f"got {actual!r}"
            )
        return

    fail(f"Unsupported check type: {check_type}")


def validate_claim_matrix(matrix: dict[str, Any]) -> None:
    required = {"schema_version", "generated_for", "governance_source", "claims", "summary"}
    if not required.issubset(matrix):
        fail(f"Claim matrix missing keys: {sorted(required - set(matrix))}")

    rel_exists(matrix["governance_source"])

    claims = matrix["claims"]
    if not isinstance(claims, list) or not claims:
        fail("Claim matrix must contain a non-empty claims list")

    seen_ids: set[str] = set()
    status_counts: dict[str, int] = {}

    for claim in claims:
        for key in (
            "id",
            "surface",
            "claim_text",
            "status",
            "evidence",
            "checks",
            "required_wording",
            "caveats",
        ):
            if key not in claim:
                fail(f"Claim missing key {key}: {claim}")

        claim_id = claim["id"]
        if claim_id in seen_ids:
            fail(f"Duplicate claim id: {claim_id}")
        seen_ids.add(claim_id)

        status = str(claim["status"]).lower()
        status_counts[status] = status_counts.get(status, 0) + 1

        rel_exists(claim["surface"])
        for rel_path in claim["evidence"]:
            rel_exists(rel_path)
        for check in claim["checks"]:
            try:
                run_check(check)
            except AssertionError as exc:
                fail(f"{claim_id} failed: {exc}")

    summary = matrix["summary"]
    if summary.get("total_claims") != len(claims):
        fail("summary.total_claims does not match claims length")

    for key in ("verified", "partial", "retired", "unverified"):
        expected_count = status_counts.get(key, 0)
        if summary.get(key, 0) != expected_count:
            fail(f"summary.{key} expected {expected_count}, got {summary.get(key, 0)}")


def main() -> int:
    try:
        index = load_json(INDEX_PATH)
        matrix = load_json(MATRIX_PATH)
        validate_index(index)
        validate_claim_matrix(matrix)
    except AssertionError as exc:
        print(f"PUBLICATION CLAIMS FAILED: {exc}")
        return 1
    except Exception as exc:  # pragma: no cover - fail closed for governance tooling
        print(f"PUBLICATION CLAIMS ERROR: {exc}")
        return 1

    print("PUBLICATION CLAIMS PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
