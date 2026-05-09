#!/usr/bin/env python3
"""Scan release-facing surfaces for Skeptic Engine overclaiming red flags."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SURFACES = [
    Path("README.md"),
    Path("REPORT.md"),
    Path("RELEASE_CHECKLIST.md"),
    Path("manuscript/manuscript.tex"),
    Path("manuscript/PREPRINT_v01.md"),
    Path("manuscript/PREPRINT_STRUCTURE.md"),
]


@dataclass
class Finding:
    code: str
    severity: str
    path: Path
    line: int
    message: str
    text: str


def iter_lines() -> list[tuple[Path, int, str]]:
    rows: list[tuple[Path, int, str]] = []
    for rel_path in SURFACES:
        path = REPO_ROOT / rel_path
        if not path.exists():
            rows.append((rel_path, 0, "<missing release surface>"))
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            rows.append((rel_path, line_no, line))
    return rows


def has_nearby_caveat(lines: list[str], index: int, patterns: list[str], window: int = 4) -> bool:
    start = max(0, index - window)
    end = min(len(lines), index + window + 1)
    context = "\n".join(lines[start:end]).lower()
    return any(re.search(pattern, context, re.IGNORECASE) for pattern in patterns)


def add_finding(
    findings: list[Finding],
    code: str,
    severity: str,
    rel_path: Path,
    line_no: int,
    message: str,
    line: str,
) -> None:
    findings.append(Finding(code, severity, rel_path, line_no, message, line))


def is_method_origin_fraud_language(lower: str) -> bool:
    return any(
        phrase in lower
        for phrase in (
            "banking fraud",
            "fraud detection expertise",
            "fraud expertise",
            "fraud-style",
            "fraud methods",
            "no real fraud ground truth",
        )
    )


def is_accusatory_fraud_language(lower: str) -> bool:
    return bool(
        re.search(r"\b(detects?|proves?|identif(?:y|ies)|flags?)\s+fraud\b", lower)
        or re.search(r"\bfraud\s+(accusation|intent|misconduct)\b", lower)
    )


def scan() -> list[Finding]:
    findings: list[Finding] = []
    by_file: dict[Path, list[str]] = {}
    for path, _line_no, text in iter_lines():
        by_file.setdefault(path, []).append(text)

    for rel_path, lines in by_file.items():
        if lines == ["<missing release surface>"]:
            add_finding(findings, "MISSING_SURFACE", "ERROR", rel_path, 0, "Release surface is missing", "")
            continue

        for idx, line in enumerate(lines):
            line_no = idx + 1
            lower = line.lower()
            stripped = lower.strip()

            if "ready for publishing" in lower:
                add_finding(
                    findings,
                    "OPTIMISTIC_RELEASE_STATUS",
                    "ERROR",
                    rel_path,
                    line_no,
                    "Release status must be fail-closed and based on current gates",
                    line,
                )

            if "ruff + mypy green" in lower or "302 tests passing" in lower:
                add_finding(
                    findings,
                    "STALE_GATE_CLAIM",
                    "ERROR",
                    rel_path,
                    line_no,
                    "Gate/test-count claims must cite current command output",
                    line,
                )

            has_perfect_metric = bool(
                re.search(r"\b(auc|f1)\s*[=:]?\s*1\.000\b", line, re.IGNORECASE)
            )
            perfect_metric_is_scoped = has_nearby_caveat(
                lines,
                idx,
                [
                    r"synthetic",
                    r"simulated",
                    r"fabricat",
                    r"within-dataset",
                    r"trivial",
                    r"small",
                    r"limited",
                    r"not.*real-world",
                ],
            )
            if has_perfect_metric and not perfect_metric_is_scoped:
                add_finding(
                    findings,
                    "PERFECT_METRIC_WITHOUT_SCOPE",
                    "ERROR",
                    rel_path,
                    line_no,
                    "Perfect AUC/F1 requires synthetic/limited-scope caveat nearby",
                    line,
                )

            if (
                rel_path != Path("RELEASE_CHECKLIST.md")
                and "validated" in lower
                and re.search(r"synthetic|simulated", lower)
            ):
                add_finding(
                    findings,
                    "VALIDATED_SYNTHETIC_LANGUAGE",
                    "WARN",
                    rel_path,
                    line_no,
                    "Avoid unqualified validated language for synthetic-only evidence",
                    line,
                )

            has_fraud = bool(re.search(r"\bfraud\b", lower))
            fraud_needs_caveat = has_fraud and (
                is_accusatory_fraud_language(lower) or not is_method_origin_fraud_language(lower)
            )
            fraud_has_caveat = has_nearby_caveat(
                lines,
                idx,
                [
                    r"not.*fraud",
                    r"not.*intent",
                    r"not.*misconduct",
                    r"artifact",
                    r"anomal",
                    r"expert review",
                ],
            )
            if fraud_needs_caveat and not fraud_has_caveat:
                add_finding(
                    findings,
                    "FRAUD_WITHOUT_CAVEAT",
                    "ERROR",
                    rel_path,
                    line_no,
                    "Fraud language must be clearly framed as no intent attribution",
                    line,
                )

            has_generalization_claim = bool(
                re.search(r"generaliz(es|e)|general-purpose|universal detector", lower)
            )
            generalization_is_bounded = (
                "fails" in lower
                or "failure" in lower
                or "degrades" in lower
                or "limitation" in lower
                or stripped.startswith("#")
                or "run_cross" in lower
                or "heatmap" in lower
            )
            if has_generalization_claim and not generalization_is_bounded:
                add_finding(
                    findings,
                    "GENERALIZATION_LANGUAGE",
                    "WARN",
                    rel_path,
                    line_no,
                    "Generalization claims need explicit boundary because failures are documented",
                    line,
                )

    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        add_finding(
            findings,
            "ENV_FILE_PRESENT",
            "WARN",
            Path(".env"),
            0,
            "A local .env exists; confirm it is ignored and never published",
            "",
        )

    return findings


def main() -> int:
    findings = scan()
    error_count = sum(1 for finding in findings if finding.severity == "ERROR")
    warn_count = sum(1 for finding in findings if finding.severity == "WARN")

    print("SKEPTIC ENGINE RED-FLAG SCAN")
    print(f"ERRORS: {error_count}")
    print(f"WARNINGS: {warn_count}")

    for finding in findings:
        location = f"{finding.path}:{finding.line}" if finding.line else str(finding.path)
        print(f"{finding.severity} {finding.code} {location} - {finding.message}")
        if finding.text:
            print(f"  {finding.text.strip()}")

    return 1 if error_count else 0


if __name__ == "__main__":
    sys.exit(main())
