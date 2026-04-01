"""Reference constraint model from real/control data.

Three types of constraints:
1. Pairwise rank-correlation (Spearman) with bootstrap stability selection
2. Module-level (hierarchical clustering of correlated features)
3. Latent reconstruction residual norms (optional, requires torch)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from scipy.stats import spearmanr


@dataclass
class Module:
    """A co-expression module (cluster of correlated features)."""

    module_id: int
    feature_indices: list[int]
    feature_names: list[str]
    mean_internal_rho: float  # average pairwise rho within module on reference


@dataclass
class ConstraintModel:
    """Reference model of normal dependencies (pairwise + module + residual)."""

    # Pairwise: (feature_i, feature_j, expected_rho, stability)
    pairwise: list[tuple[int, int, float, float]] = field(default_factory=list)
    # Module-level constraints
    modules: list[Module] = field(default_factory=list)
    # Per-feature AE residual norms (optional)
    residual_means: np.ndarray | None = None
    residual_stds: np.ndarray | None = None
    # Metadata
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
    if not hasattr(rho_full, "ndim") or rho_full.ndim == 0:
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

    model = ConstraintModel(pairwise=result, feature_names=names, n_reference=n_samples)

    # Build module-level constraints via hierarchical clustering
    if verbose:
        print("  Building modules...", end=" ", flush=True)
    model.modules = _build_modules(X, rho_full, names, verbose=verbose)

    return model


def _build_modules(
    X: np.ndarray,
    rho_full: np.ndarray,
    feature_names: list[str],
    max_modules: int = 30,
    min_module_size: int = 5,
    distance_threshold: float = 0.5,
    verbose: bool = True,
) -> list[Module]:
    """Cluster features into co-expression modules via hierarchical clustering.

    Uses 1 - |rho| as distance metric. Modules with < min_module_size features
    are discarded. For each module, stores mean internal rho on reference data.
    """
    n_features = rho_full.shape[0]
    # Distance matrix: 1 - |rho|
    dist = 1.0 - np.abs(rho_full)
    np.fill_diagonal(dist, 0)
    # WHY: NaN correlations (constant columns) produce NaN distances.
    # Replace with max distance (1.0) so they don't crash linkage.
    dist = np.nan_to_num(dist, nan=1.0)
    dist = np.clip(dist, 0, 1)

    # Hierarchical clustering
    condensed = squareform(dist, checks=False)
    Z = linkage(condensed, method="average")
    labels = fcluster(Z, t=distance_threshold, criterion="distance")

    # Group features by module
    modules = []
    for mod_id in range(1, labels.max() + 1):
        indices = list(np.where(labels == mod_id)[0])
        if len(indices) < min_module_size:
            continue

        # Compute mean internal correlation
        internal_rhos = []
        for ii in range(len(indices)):
            for jj in range(ii + 1, len(indices)):
                internal_rhos.append(abs(rho_full[indices[ii], indices[jj]]))
        mean_rho = float(np.mean(internal_rhos)) if internal_rhos else 0.0

        names = [feature_names[i] if i < len(feature_names) else f"f{i}" for i in indices]
        modules.append(
            Module(
                module_id=mod_id,
                feature_indices=indices,
                feature_names=names,
                mean_internal_rho=round(mean_rho, 4),
            )
        )

    # Sort by mean internal rho (strongest modules first), keep top
    modules.sort(key=lambda m: -m.mean_internal_rho)
    modules = modules[:max_modules]
    if verbose:
        print(f"{len(modules)} modules (size >= {min_module_size}).")
    return modules


def build_residual_constraints(
    X: np.ndarray,
    ae_model,
    scaler,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute per-feature AE reconstruction residual norms on reference data.

    Requires torch. Returns (mean_residuals, std_residuals) per feature.
    """
    import torch

    with torch.no_grad():
        X_scaled = scaler.transform(X)
        X_tensor = torch.tensor(X_scaled, dtype=torch.float32)
        recon = ae_model(X_tensor).numpy()
        residuals = np.abs(X_scaled - recon)

    return residuals.mean(axis=0), residuals.std(axis=0)
