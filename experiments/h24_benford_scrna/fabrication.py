"""Simulated fabrication generators for scRNA-seq count matrices.

Three methods following Bradshaw et al. 2021 (adapted for UMI counts):
  - resample: shuffle gene values across cells (preserves marginal per-gene distributions)
  - noise: add structured noise to real matrix (low-level manipulation)
  - random: generate from fitted negative binomial (pure synthetic)
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def fabricate_resample(
    real_matrix: NDArray[np.int64],
    rng: np.random.Generator | None = None,
) -> NDArray[np.int64]:
    """Fabrication by column-wise resampling.

    For each gene, independently shuffle values across cells.
    This preserves per-gene marginal distributions but destroys
    inter-gene correlation structure (cell identity).
    """
    rng = rng or np.random.default_rng(42)
    fake = real_matrix.copy()
    for j in range(fake.shape[1]):
        rng.shuffle(fake[:, j])
    return fake


def fabricate_noise(
    real_matrix: NDArray[np.int64],
    noise_fraction: float = 0.15,
    rng: np.random.Generator | None = None,
) -> NDArray[np.int64]:
    """Fabrication by additive Poisson noise.

    Add Poisson noise proportional to each value, then clip to non-negative.
    This simulates subtle manipulation where values are "nudged".
    """
    rng = rng or np.random.default_rng(43)
    noise_scale = (real_matrix.astype(np.float64) * noise_fraction).clip(min=0.5)
    noise = rng.poisson(lam=noise_scale).astype(np.int64)
    # Randomly add or subtract
    signs = rng.choice([-1, 1], size=real_matrix.shape)
    fake = real_matrix.astype(np.int64) + signs * noise
    return np.clip(fake, 0, None).astype(np.int64)


def fabricate_random_nb(
    real_matrix: NDArray[np.int64],
    rng: np.random.Generator | None = None,
) -> NDArray[np.int64]:
    """Fabrication by per-gene negative binomial generation.

    Fit NB(n, p) per gene from real data, then generate synthetic counts.
    This is the most sophisticated fabrication: gene-level statistics match
    but digit distributions may not.
    """
    rng = rng or np.random.default_rng(44)
    n_cells, n_genes = real_matrix.shape
    fake = np.zeros_like(real_matrix)

    for j in range(n_genes):
        col = real_matrix[:, j].astype(np.float64)
        mean_val = col.mean()
        var_val = col.var()

        if var_val <= mean_val or mean_val < 0.01:
            # Poisson regime (variance ≈ mean)
            fake[:, j] = rng.poisson(lam=max(mean_val, 0.01), size=n_cells)
        else:
            # NB parametrization: n = mean^2 / (var - mean), p = mean / var
            n_param = mean_val**2 / (var_val - mean_val)
            p_param = mean_val / var_val
            n_param = max(n_param, 0.1)
            p_param = min(max(p_param, 0.01), 0.99)
            fake[:, j] = rng.negative_binomial(n=n_param, p=p_param, size=n_cells)

    return fake.astype(np.int64)


FABRICATION_METHODS = {
    "resample": fabricate_resample,
    "noise": fabricate_noise,
    "random_nb": fabricate_random_nb,
}
