"""Syndrome vector computation from constraint violations.

For each sample, compute HOW MUCH each constraint is violated,
producing a syndrome vector that decomposes the overall anomaly score.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import spearmanr

from constraint_builder import ConstraintModel


@dataclass
class SyndromeResult:
    """Per-sample syndrome decomposition."""

    global_anomaly_score: float  # overall anomaly (0-1)
    syndrome_score: float  # aggregated constraint violation (0-1)
    pairwise_violation_score: float  # from rank-correlation violations
    residual_violation_score: float  # from AE residual violations
    stability_score: float  # how robust is this assessment (0-1)
    top_violated_pairs: list[dict]  # top constraint violations with details
    noise_sensitivity: str  # "low" / "medium" / "high"


def compute_pairwise_violations(
    X: np.ndarray,
    constraints: list[tuple[int, int, float, float]],
) -> tuple[np.ndarray, list[dict]]:
    """Compute per-constraint violation scores for a set of samples.

    For each constraint (i, j, expected_rho, stability):
    - Compute actual rho(i,j) on the test samples
    - Violation = |actual_rho - expected_rho| weighted by stability

    Returns:
        violation_vector: (n_constraints,) violation scores
        violation_details: list of dicts with constraint info
    """
    if not constraints or X.shape[0] < 5:
        return np.zeros(0), []

    violations = []
    details = []

    for feat_i, feat_j, expected_rho, stability in constraints:
        col_i = X[:, feat_i]
        col_j = X[:, feat_j]

        # Compute actual correlation on test data
        if col_i.std() < 1e-12 or col_j.std() < 1e-12:
            actual_rho = 0.0
        else:
            actual_rho, _ = spearmanr(col_i, col_j)
            if np.isnan(actual_rho):
                actual_rho = 0.0

        delta = abs(float(actual_rho) - expected_rho)
        weighted_violation = delta * stability

        violations.append(weighted_violation)
        details.append({
            "feature_i": int(feat_i),
            "feature_j": int(feat_j),
            "expected_rho": round(expected_rho, 4),
            "actual_rho": round(float(actual_rho), 4),
            "delta": round(delta, 4),
            "stability": round(stability, 4),
            "violation_score": round(weighted_violation, 4),
        })

    return np.array(violations), details


def compute_residual_violations(
    X: np.ndarray,
    model: ConstraintModel,
    ae_model=None,
    scaler=None,
) -> tuple[float, list[dict]]:
    """Compute per-feature residual violation scores.

    Compare test residuals against reference residual norms.
    Features where test residuals >> reference residuals are flagged.
    """
    if model.residual_means is None or ae_model is None or scaler is None:
        return 0.0, []

    import torch

    with torch.no_grad():
        X_scaled = scaler.transform(X)
        X_tensor = torch.tensor(X_scaled, dtype=torch.float32)
        recon = ae_model(X_tensor).numpy()
        test_residuals = np.abs(X_scaled - recon).mean(axis=0)

    # Z-score each feature's residual against reference distribution
    z_scores = np.zeros_like(test_residuals)
    safe_std = np.maximum(model.residual_stds, 1e-10)
    z_scores = (test_residuals - model.residual_means) / safe_std

    # Top violated features
    top_idx = np.argsort(z_scores)[::-1][:20]
    details = []
    for idx in top_idx:
        if z_scores[idx] > 1.0:  # only report if > 1 std above reference
            details.append({
                "feature": model.feature_names[idx] if idx < len(model.feature_names) else f"f{idx}",
                "feature_idx": int(idx),
                "z_score": round(float(z_scores[idx]), 3),
                "test_residual": round(float(test_residuals[idx]), 4),
                "ref_mean": round(float(model.residual_means[idx]), 4),
                "ref_std": round(float(safe_std[idx]), 4),
            })

    # Aggregate: fraction of features with z > 2
    violation_frac = float((z_scores > 2.0).mean())
    return violation_frac, details


def compute_syndrome(
    X: np.ndarray,
    model: ConstraintModel,
    ae_model=None,
    scaler=None,
) -> SyndromeResult:
    """Full syndrome analysis for a set of samples."""

    # Pairwise violations
    pw_violations, pw_details = compute_pairwise_violations(X, model.pairwise)
    pw_score = float(pw_violations.mean()) if len(pw_violations) > 0 else 0.0

    # Residual violations
    res_score, res_details = compute_residual_violations(X, model, ae_model, scaler)

    # Aggregate syndrome score (weighted combination)
    # WHY: pairwise captures correlation structure breaks,
    # residual captures reconstruction anomalies. Both matter.
    syndrome_score = 0.6 * pw_score + 0.4 * res_score

    # Global anomaly = max of both signals
    global_score = max(pw_score, res_score, syndrome_score)

    # Stability: based on number of constraints and sample size
    n_constraints = len(model.pairwise)
    stability = min(1.0, n_constraints / 100) * min(1.0, X.shape[0] / 50)

    # Noise sensitivity
    if X.shape[0] < 20 or n_constraints < 20:
        noise_flag = "high"
    elif X.shape[0] < 50 or n_constraints < 50:
        noise_flag = "medium"
    else:
        noise_flag = "low"

    # Top violated pairs
    pw_details.sort(key=lambda d: -d["violation_score"])
    top_pairs = pw_details[:10]

    return SyndromeResult(
        global_anomaly_score=round(global_score, 4),
        syndrome_score=round(syndrome_score, 4),
        pairwise_violation_score=round(pw_score, 4),
        residual_violation_score=round(res_score, 4),
        stability_score=round(stability, 4),
        top_violated_pairs=top_pairs,
        noise_sensitivity=noise_flag,
    )
