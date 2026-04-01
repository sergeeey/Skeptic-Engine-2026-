"""Reference constraint model from real/control data.

Pairwise rank-correlation constraints with bootstrap stability selection.
No torch dependency -- works with numpy/scipy only.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.stats import spearmanr


@dataclass
class ConstraintModel:
    """Reference model of normal pairwise dependencies."""

    # Each entry: (feature_i, feature_j, expected_rho, stability)
    pairwise: list[tuple[int, int, float, float]] = field(default_factory=list)
    feature_names: list[str] = field(default_factory=list)
    n_reference: int = 0


def build_pairwise_constraints(
    X: np.ndarray,
    feature_names: list[str] | None = None,
    top_k: int = 200,
    n_bootstrap: int = 50,
    min_stability: float = 0.70,
    min_abs_rho: float = 0.50,
    seed: int = 42,
    verbose: bool = True,
) -> ConstraintModel:
    """Build pairwise constraint model via bootstrap stability selection.

    Args:
        X: reference data (samples x features), NaN-free.
        top_k: max constraints to keep.
        n_bootstrap: bootstrap iterations for stability.
        min_stability: fraction of bootstraps where |rho| > min_abs_rho.
        min_abs_rho: minimum absolute correlation threshold.
        seed: random seed.
        verbose: print progress.

    Returns:
        ConstraintModel with stable pairwise constraints.
    """
    rng = np.random.default_rng(seed)
    n_samples, n_features = X.shape
    names = feature_names or [f"f{i}" for i in range(n_features)]

    # Pre-screen: full correlation matrix to find candidates
    if verbose:
        print("  Building constraints: pre-screening...", end=" ", flush=True)
    rho_full, _ = spearmanr(X)
    if rho_full.ndim == 0:
        return ConstraintModel(feature_names=names, n_reference=n_samples)

    np.fill_diagonal(rho_full, 0)
    abs_rho = np.abs(rho_full)

    candidates = []
    flat_idx = np.argsort(abs_rho.ravel())[::-1]
    seen: set[tuple[int, int]] = set()
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
        if len(candidates) >= top_k * 3:
            break

    if verbose:
        print(f"{len(candidates)} candidates.", end=" ", flush=True)

    if not candidates:
        return ConstraintModel(feature_names=names, n_reference=n_samples)

    # Bootstrap stability
    if verbose:
        print(f"Bootstrap ({n_bootstrap})...", end=" ", flush=True)
    pair_rhos: dict[tuple[int, int], list[float]] = {p: [] for p in candidates}
    for _ in range(n_bootstrap):
        idx = rng.choice(n_samples, n_samples, replace=True)
        X_boot = X[idx]
        for i, j in candidates:
            rho_val, _ = spearmanr(X_boot[:, i], X_boot[:, j])
            if not np.isnan(rho_val):
                pair_rhos[(i, j)].append(rho_val)

    stable = []
    for (i, j), rhos in pair_rhos.items():
        if not rhos:
            continue
        arr = np.array(rhos)
        median_rho = float(np.median(arr))
        stab = float((np.abs(arr) > min_abs_rho).mean())
        if stab >= min_stability:
            stable.append((i, j, median_rho, stab))

    stable.sort(key=lambda x: -x[3] * abs(x[2]))
    result = stable[:top_k]
    if verbose:
        print(f"{len(result)} stable constraints.")

    return ConstraintModel(pairwise=result, feature_names=names, n_reference=n_samples)
