"""Syndrome report generation -- JSON, Markdown, and CSV."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from .scoring import SyndromeResult


def syndrome_to_json(result: SyndromeResult, path: Path) -> None:
    """Write full syndrome result to JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")


def syndrome_to_csv(result: SyndromeResult, path: Path) -> None:
    """Write top violations (pairs + modules + residuals) to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["type", "item_a", "item_b", "expected", "actual", "delta", "severity"])
        for p in result.top_violated_pairs:
            sev = (
                "HIGH"
                if p["violation_score"] > 0.5
                else "MEDIUM"
                if p["violation_score"] > 0.2
                else "LOW"
            )
            w.writerow(
                [
                    "pairwise",
                    p["feature_i"],
                    p["feature_j"],
                    p["expected_rho"],
                    p["actual_rho"],
                    p["delta"],
                    sev,
                ]
            )
        for m in result.top_violated_modules:
            sev = "HIGH" if m["delta"] > 0.3 else "MEDIUM" if m["delta"] > 0.1 else "LOW"
            w.writerow(
                [
                    "module",
                    f"module_{m['module_id']}",
                    "; ".join(m["top_genes"]),
                    m["expected_internal_rho"],
                    m["actual_internal_rho"],
                    m["delta"],
                    sev,
                ]
            )
        for r in result.top_violated_features:
            sev = "HIGH" if r["z_score"] > 5 else "MEDIUM" if r["z_score"] > 2 else "LOW"
            w.writerow(
                ["residual", r["feature"], "", r["ref_mean"], r["test_residual"], r["z_score"], sev]
            )


def syndrome_to_markdown(result: SyndromeResult) -> str:
    """Format full syndrome result as Markdown report."""
    assessments = {
        "clean": "Structural dependencies are preserved. No anomalies detected.",
        "technical_noise": "Minor scattered violations consistent with technical noise.",
        "local_break": "Localized dependency break in specific modules. Expert review recommended.",
        "structural_anomaly": "Broad structural violations across multiple modules. Escalate for review.",
    }

    lines = [
        "# Syndrome Analysis Report",
        "",
        f"**Syndrome score:** {result.syndrome_score:.4f}",
        f"**Pairwise violation:** {result.pairwise_violation_score:.4f}",
        f"**Module violation:** {result.module_violation_score:.4f}",
        f"**Residual violation:** {result.residual_violation_score:.4f}",
        f"**Stability:** {result.stability_score:.4f}",
        f"**Noise sensitivity:** {result.noise_sensitivity}",
        f"**Violation class:** {result.violation_class}",
        f"**Review required:** {'Yes' if result.review_required else 'No'}",
        f"**Constraints:** {result.n_constraints} pairwise, {result.n_modules} modules",
        f"**Samples:** {result.n_samples}",
        "",
        f"**Assessment:** {assessments.get(result.violation_class, 'Unknown')}",
        "",
    ]

    if result.top_violated_pairs:
        lines.append("## Top Violated Pairwise Dependencies")
        lines.append("")
        lines.append("| Feature A | Feature B | Expected | Actual | Delta | Severity |")
        lines.append("|-----------|-----------|----------|--------|-------|----------|")
        for p in result.top_violated_pairs:
            sev = (
                "HIGH"
                if p["violation_score"] > 0.5
                else "MEDIUM"
                if p["violation_score"] > 0.2
                else "LOW"
            )
            lines.append(
                f"| {p['feature_i']} | {p['feature_j']} | "
                f"{p['expected_rho']:.3f} | {p['actual_rho']:.3f} | {p['delta']:.3f} | {sev} |"
            )
        lines.append("")

    if result.top_violated_modules:
        lines.append("## Top Violated Modules")
        lines.append("")
        lines.append("| Module genes | Size | Expected | Actual | Delta | Broken |")
        lines.append("|-------------|------|----------|--------|-------|--------|")
        for m in result.top_violated_modules:
            genes = ", ".join(m["top_genes"][:3])
            lines.append(
                f"| {genes}... | {m['module_size']} | "
                f"{m['expected_internal_rho']:.3f} | {m['actual_internal_rho']:.3f} | "
                f"{m['delta']:.3f} | {m['n_broken_pairs']}/{m['n_total_pairs']} |"
            )
        lines.append("")

    if result.module_violation_counts:
        broken = {k: v for k, v in result.module_violation_counts.items() if v > 0}
        if broken:
            lines.append("## Module Violation Histogram")
            lines.append("")
            for name, count in sorted(broken.items(), key=lambda x: -x[1]):
                bar = "#" * min(count, 40)
                lines.append(f"  {name}: {bar} ({count})")
            lines.append("")

    if result.top_violated_features:
        lines.append("## Top Residual Violations (AE)")
        lines.append("")
        lines.append("| Feature | Z-score | Test residual | Ref mean |")
        lines.append("|---------|---------|--------------|----------|")
        for r in result.top_violated_features:
            lines.append(
                f"| {r['feature']} | {r['z_score']:.2f} | {r['test_residual']:.4f} | {r['ref_mean']:.4f} |"
            )
        lines.append("")

    lines.append("---")
    lines.append(
        "*Generated by Skeptic Engine. Violations indicate structural breaks, not fraud. "
        "Expert review required before conclusions about intent.*"
    )
    return "\n".join(lines)
