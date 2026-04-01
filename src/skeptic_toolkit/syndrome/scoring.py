"""Syndrome scoring -- compute violation vector from constraints."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import spearmanr

from .constraints import ConstraintModel


@dataclass
class SyndromeResult:
    """Dataset-level syndrome decomposition."""

    syndrome_score: float
    pairwise_violation_score: float
    stability_score: float
    noise_sensitivity: str  # "low" / "medium" / "high"
    top_violated_pairs: list[dict]
    n_constraints: int
    n_samples: int


def compute_syndrome_pairwise(
    X: np.ndarray,
    model: ConstraintModel,
) -> SyndromeResult:
    """Compute pairwise constraint violations on candidate data.

    No AE/torch required -- pure numpy/scipy.
    """
    n_samples = X.shape[0]
    constraints = model.pairwise

    if not constraints or n_samples < 5:
        return SyndromeResult(
            syndrome_score=0.0,
            pairwise_violation_score=0.0,
            stability_score=0.0,
            noise_sensitivity="high",
            top_violated_pairs=[],
            n_constraints=0,
            n_samples=n_samples,
        )

    violations = []
    details = []

    for feat_i, feat_j, expected_rho, stability in constraints:
        col_i = X[:, feat_i]
        col_j = X[:, feat_j]

        if col_i.std() < 1e-12 or col_j.std() < 1e-12:
            actual_rho = 0.0
        else:
            actual_rho, _ = spearmanr(col_i, col_j)
            if np.isnan(actual_rho):
                actual_rho = 0.0

        delta = abs(float(actual_rho) - expected_rho)
        weighted = delta * stability
        violations.append(weighted)

        name_i = model.feature_names[feat_i] if feat_i < len(model.feature_names) else f"f{feat_i}"
        name_j = model.feature_names[feat_j] if feat_j < len(model.feature_names) else f"f{feat_j}"

        details.append(
            {
                "feature_i": name_i,
                "feature_j": name_j,
                "expected_rho": round(expected_rho, 4),
                "actual_rho": round(float(actual_rho), 4),
                "delta": round(delta, 4),
                "stability": round(stability, 4),
                "violation_score": round(weighted, 4),
            }
        )

    pw_score = float(np.mean(violations))
    details.sort(key=lambda d: -d["violation_score"])

    n_constraints = len(constraints)
    stab = min(1.0, n_constraints / 100) * min(1.0, n_samples / 50)

    if n_samples < 20 or n_constraints < 20:
        noise = "high"
    elif n_samples < 50 or n_constraints < 50:
        noise = "medium"
    else:
        noise = "low"

    return SyndromeResult(
        syndrome_score=round(pw_score, 4),
        pairwise_violation_score=round(pw_score, 4),
        stability_score=round(stab, 4),
        noise_sensitivity=noise,
        top_violated_pairs=details[:10],
        n_constraints=n_constraints,
        n_samples=n_samples,
    )
