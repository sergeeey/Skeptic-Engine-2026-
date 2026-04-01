"""Syndrome scoring -- pairwise + module + residual violation vectors."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.stats import spearmanr

from .constraints import ConstraintModel


@dataclass
class SyndromeResult:
    """Full syndrome decomposition."""

    syndrome_score: float
    pairwise_violation_score: float
    module_violation_score: float
    residual_violation_score: float
    stability_score: float
    noise_sensitivity: str  # "low" / "medium" / "high"
    violation_class: str  # "clean" / "technical_noise" / "local_break" / "structural_anomaly"
    review_required: bool
    top_violated_pairs: list[dict]
    top_violated_modules: list[dict]
    top_violated_features: list[dict]  # from residual analysis
    module_violation_counts: dict[str, int]  # per-module count of violated pairs
    n_constraints: int
    n_modules: int
    n_samples: int


def _compute_pairwise_violations(
    X: np.ndarray,
    model: ConstraintModel,
) -> tuple[float, list[dict]]:
    """Pairwise rank-correlation violations."""
    if not model.pairwise or X.shape[0] < 5:
        return 0.0, []

    violations = []
    details = []

    for feat_i, feat_j, expected_rho, stability in model.pairwise:
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

    score = float(np.mean(violations)) if violations else 0.0
    details.sort(key=lambda d: -d["violation_score"])
    return score, details


def _compute_module_violations(
    X: np.ndarray,
    model: ConstraintModel,
) -> tuple[float, list[dict], dict[str, int]]:
    """Per-module internal consistency violations."""
    if not model.modules or X.shape[0] < 5:
        return 0.0, [], {}

    module_scores = []
    module_details = []
    module_counts: dict[str, int] = {}

    for mod in model.modules:
        indices = mod.feature_indices
        if len(indices) < 2:
            continue

        # Compute current internal rho
        internal_rhos = []
        for ii in range(len(indices)):
            for jj in range(ii + 1, len(indices)):
                ci = X[:, indices[ii]]
                cj = X[:, indices[jj]]
                if ci.std() < 1e-12 or cj.std() < 1e-12:
                    r = 0.0
                else:
                    r, _ = spearmanr(ci, cj)
                    if np.isnan(r):
                        r = 0.0
                internal_rhos.append(abs(float(r)))

        current_mean_rho = float(np.mean(internal_rhos)) if internal_rhos else 0.0
        delta = max(0.0, mod.mean_internal_rho - current_mean_rho)

        # Count how many pairs dropped below 50% of expected
        n_broken = sum(1 for r in internal_rhos if r < mod.mean_internal_rho * 0.5)
        mod_label = f"module_{mod.module_id}"
        module_counts[mod_label] = n_broken

        module_scores.append(delta)
        module_details.append(
            {
                "module_id": mod.module_id,
                "module_size": len(indices),
                "top_genes": mod.feature_names[:5],
                "expected_internal_rho": round(mod.mean_internal_rho, 4),
                "actual_internal_rho": round(current_mean_rho, 4),
                "delta": round(delta, 4),
                "n_broken_pairs": n_broken,
                "n_total_pairs": len(internal_rhos),
            }
        )

    score = float(np.mean(module_scores)) if module_scores else 0.0
    module_details.sort(key=lambda d: -d["delta"])
    return score, module_details, module_counts


def _compute_residual_violations(
    X: np.ndarray,
    model: ConstraintModel,
    ae_model=None,
    scaler=None,
) -> tuple[float, list[dict]]:
    """Per-feature AE reconstruction residual violations (optional)."""
    if model.residual_means is None or ae_model is None or scaler is None:
        return 0.0, []

    try:
        import torch
    except ImportError:
        return 0.0, []

    with torch.no_grad():
        X_scaled = scaler.transform(X)
        X_tensor = torch.tensor(X_scaled, dtype=torch.float32)
        recon = ae_model(X_tensor).numpy()
        test_residuals = np.abs(X_scaled - recon).mean(axis=0)

    safe_std = np.maximum(model.residual_stds, 1e-10)
    z_scores = (test_residuals - model.residual_means) / safe_std

    top_idx = np.argsort(z_scores)[::-1][:20]
    details = []
    for idx in top_idx:
        if z_scores[idx] > 1.0:
            name = model.feature_names[idx] if idx < len(model.feature_names) else f"f{idx}"
            details.append(
                {
                    "feature": name,
                    "feature_idx": int(idx),
                    "z_score": round(float(z_scores[idx]), 3),
                    "test_residual": round(float(test_residuals[idx]), 4),
                    "ref_mean": round(float(model.residual_means[idx]), 4),
                }
            )

    violation_frac = float((z_scores > 2.0).mean())
    return violation_frac, details


def _classify_violation(
    pw_score: float,
    mod_score: float,
    res_score: float,
    n_violated_modules: int,
    n_total_modules: int,
) -> tuple[str, bool]:
    """Classify violation into one of 4 categories.

    Returns (violation_class, review_required).
    Categories:
      clean             - all scores low, no review needed
      technical_noise   - minor scattered violations, likely noise
      local_break       - 1-2 modules broken, rest intact
      structural_anomaly - broad violation across many modules/pairs
    """
    combined = 0.5 * pw_score + 0.3 * mod_score + 0.2 * res_score

    if combined < 0.02:
        return "clean", False

    if combined < 0.10:
        return "technical_noise", False

    frac_modules_broken = n_violated_modules / max(n_total_modules, 1)
    if frac_modules_broken < 0.30 and pw_score < 0.30:
        return "local_break", True

    return "structural_anomaly", True


def compute_syndrome_pairwise(
    X: np.ndarray,
    model: ConstraintModel,
    ae_model=None,
    scaler=None,
) -> SyndromeResult:
    """Full syndrome analysis: pairwise + module + residual."""
    n_samples = X.shape[0]

    if n_samples < 5:
        return SyndromeResult(
            syndrome_score=0.0,
            pairwise_violation_score=0.0,
            module_violation_score=0.0,
            residual_violation_score=0.0,
            stability_score=0.0,
            noise_sensitivity="high",
            violation_class="clean",
            review_required=False,
            top_violated_pairs=[],
            top_violated_modules=[],
            top_violated_features=[],
            module_violation_counts={},
            n_constraints=0,
            n_modules=0,
            n_samples=n_samples,
        )

    # Pairwise
    pw_score, pw_details = _compute_pairwise_violations(X, model)

    # Module
    mod_score, mod_details, mod_counts = _compute_module_violations(X, model)

    # Residual (optional)
    res_score, res_details = _compute_residual_violations(X, model, ae_model, scaler)

    # Aggregate syndrome
    syndrome = 0.5 * pw_score + 0.3 * mod_score + 0.2 * res_score

    # Stability
    n_constraints = len(model.pairwise)
    n_modules = len(model.modules)
    stab = min(1.0, n_constraints / 100) * min(1.0, n_samples / 50)

    # Noise sensitivity
    if n_samples < 20 or n_constraints < 20:
        noise = "high"
    elif n_samples < 50 or n_constraints < 50:
        noise = "medium"
    else:
        noise = "low"

    # 3-class violation classification
    n_violated_mods = sum(1 for d in mod_details if d["delta"] > 0.10)
    vclass, review = _classify_violation(pw_score, mod_score, res_score, n_violated_mods, n_modules)

    return SyndromeResult(
        syndrome_score=round(syndrome, 4),
        pairwise_violation_score=round(pw_score, 4),
        module_violation_score=round(mod_score, 4),
        residual_violation_score=round(res_score, 4),
        stability_score=round(stab, 4),
        noise_sensitivity=noise,
        violation_class=vclass,
        review_required=review,
        top_violated_pairs=pw_details[:10],
        top_violated_modules=mod_details[:10],
        top_violated_features=res_details[:10],
        module_violation_counts=mod_counts,
        n_constraints=n_constraints,
        n_modules=n_modules,
        n_samples=n_samples,
    )
