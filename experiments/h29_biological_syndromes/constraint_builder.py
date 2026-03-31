"""Build reference constraint model from real/control data.

Two types of constraints:
1. Pairwise rank-correlation constraints (Spearman) with stability selection
2. Latent reconstruction residual constraints (per-feature AE residual norms)

The constraint model captures "what normal data looks like" so that
violations can be detected and localized in test samples.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.stats import spearmanr


@dataclass
class ConstraintModel:
    """Reference model of normal dependencies."""

    # Pairwise constraints: list of (gene_i, gene_j, expected_rho, stability)
    pairwise: list[tuple[int, int, float, float]] = field(default_factory=list)
    # Per-feature residual norms from AE (mean, std per feature on reference)
    residual_means: np.ndarray | None = None
    residual_stds: np.ndarray | None = None
    # Feature names for reporting
    feature_names: list[str] = field(default_factory=list)
    # Number of reference samples used
    n_reference: int = 0


def build_pairwise_constraints(
    X: np.ndarray,
    feature_names: list[str] | None = None,
    top_k: int = 200,
    n_bootstrap: int = 50,
    min_stability: float = 0.70,
    min_abs_rho: float = 0.50,
    seed: int = 42,
) -> list[tuple[int, int, float, float]]:
    """Find stable, strong pairwise Spearman correlations via bootstrap.

    Args:
        X: reference data (samples x features), NaN-free
        top_k: max number of constraints to return
        n_bootstrap: number of bootstrap iterations for stability
        min_stability: fraction of bootstraps where |rho| > min_abs_rho
        min_abs_rho: minimum absolute correlation to consider
        seed: random seed

    Returns:
        List of (feature_i, feature_j, median_rho, stability_score)
    """
    rng = np.random.default_rng(seed)
    n_samples, n_features = X.shape

    # Pre-screen: compute full correlation matrix once to find candidates
    # WHY: computing 9585^2 correlations in bootstrap is too slow.
    # Pre-screen top candidates on full data, then bootstrap only those.
    print("    Pre-screening correlations...", end=" ", flush=True)
    rho_full, _ = spearmanr(X)
    if rho_full.ndim == 0:
        return []

    np.fill_diagonal(rho_full, 0)
    abs_rho = np.abs(rho_full)

    # Find top candidate pairs (above threshold)
    candidates = []
    # Get indices of top pairs by absolute correlation
    flat_idx = np.argsort(abs_rho.ravel())[::-1]
    seen = set()
    for idx in flat_idx:
        i, j = divmod(idx, n_features)
        if i >= j:
            continue
        if abs_rho[i, j] < min_abs_rho:
            break
        pair = (min(i, j), max(i, j))
        if pair not in seen:
            seen.add(pair)
            candidates.append(pair)
        if len(candidates) >= top_k * 3:  # over-select for bootstrap filtering
            break
    print(f"{len(candidates)} candidate pairs")

    if not candidates:
        return []

    # Bootstrap stability selection
    # WHY: computing full 9585x9585 spearmanr per bootstrap is O(n_features^2).
    # Instead, compute only the ~600 candidate pairs per iteration.
    print(f"    Bootstrap stability ({n_bootstrap} iterations)...", end=" ", flush=True)
    pair_rhos = {pair: [] for pair in candidates}

    for b in range(n_bootstrap):
        idx = rng.choice(n_samples, n_samples, replace=True)
        X_boot = X[idx]
        for i, j in candidates:
            rho_val, _ = spearmanr(X_boot[:, i], X_boot[:, j])
            if not np.isnan(rho_val):
                pair_rhos[(i, j)].append(rho_val)

    # Filter by stability
    stable_pairs = []
    for (i, j), rhos in pair_rhos.items():
        if not rhos:
            continue
        rhos_arr = np.array(rhos)
        median_rho = float(np.median(rhos_arr))
        stability = float((np.abs(rhos_arr) > min_abs_rho).mean())
        if stability >= min_stability:
            stable_pairs.append((i, j, median_rho, stability))

    # Sort by stability * |rho|, take top_k
    stable_pairs.sort(key=lambda x: -x[3] * abs(x[2]))
    result = stable_pairs[:top_k]
    print(f"{len(result)} stable constraints")
    return result


def build_residual_constraints(
    X: np.ndarray,
    ae_model,
    scaler,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute per-feature reconstruction residual norms on reference data.

    Returns (mean_residuals, std_residuals) per feature.
    """
    import torch

    with torch.no_grad():
        X_scaled = scaler.transform(X)
        X_tensor = torch.tensor(X_scaled, dtype=torch.float32)
        recon = ae_model(X_tensor).numpy()
        residuals = np.abs(X_scaled - recon)  # per-sample, per-feature

    return residuals.mean(axis=0), residuals.std(axis=0)


def build_constraint_model(
    X: np.ndarray,
    feature_names: list[str] | None = None,
    ae_model=None,
    scaler=None,
    top_k: int = 200,
    seed: int = 42,
) -> ConstraintModel:
    """Build complete constraint model from reference data."""
    model = ConstraintModel()
    model.n_reference = X.shape[0]
    model.feature_names = feature_names or [f"f{i}" for i in range(X.shape[1])]

    # Pairwise constraints
    model.pairwise = build_pairwise_constraints(
        X, feature_names=feature_names, top_k=top_k, seed=seed
    )

    # Residual constraints (if AE provided)
    if ae_model is not None and scaler is not None:
        model.residual_means, model.residual_stds = build_residual_constraints(X, ae_model, scaler)

    return model
