"""H21 — Isolation Forest anomaly scoring on scRNA-seq count matrices.

Fraud-style isolation forest trained on real count vectors,
then used to score fabricated samples as anomalies.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from sklearn.ensemble import IsolationForest


def cell_level_features(count_matrix: NDArray[np.int64]) -> NDArray[np.float64]:
    """Extract per-cell summary features from raw count matrix.

    Returns (n_cells, 8) feature matrix:
      0: total_counts (library size)
      1: n_genes_detected (nonzero count)
      2: fraction_zeros
      3: mean_nonzero
      4: variance_nonzero
      5: max_count
      6: log1p_total_counts
      7: coefficient_of_variation (std/mean of nonzero)

    Vectorized where possible for performance on large matrices.
    """
    mat = count_matrix.astype(np.float64)
    n_cells, n_genes = mat.shape

    total_counts = mat.sum(axis=1)
    nonzero_mask = mat > 0
    n_detected = nonzero_mask.sum(axis=1)
    fraction_zeros = 1.0 - (n_detected / n_genes) if n_genes > 0 else np.ones(n_cells)
    max_count = mat.max(axis=1)
    log1p_total = np.log1p(total_counts)

    # Per-row nonzero stats require a loop (ragged arrays), but row-level ops are fast
    mean_nonzero = np.zeros(n_cells, dtype=np.float64)
    var_nonzero = np.zeros(n_cells, dtype=np.float64)
    cv_nonzero = np.zeros(n_cells, dtype=np.float64)

    for i in range(n_cells):
        nz = mat[i, nonzero_mask[i]]
        nd = len(nz)
        if nd > 0:
            m = nz.mean()
            mean_nonzero[i] = m
            if nd > 1:
                var_nonzero[i] = nz.var()
            if m > 0:
                cv_nonzero[i] = nz.std() / m

    features = np.column_stack(
        [
            total_counts,
            n_detected,
            fraction_zeros,
            mean_nonzero,
            var_nonzero,
            max_count,
            log1p_total,
            cv_nonzero,
        ]
    )
    return features


def train_isolation_forest(
    real_features: NDArray[np.float64],
    contamination: float = 0.05,
    random_state: int = 42,
) -> IsolationForest:
    """Train Isolation Forest on real data features (one-class)."""
    # WHY: 200 trees (vs 100 in RF classifiers) — IF is one-class, needs more trees
    # to model the real-data manifold reliably for anomaly scoring
    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(real_features)
    return model


def score_anomalies(
    model: IsolationForest,
    features: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Return anomaly scores (lower = more anomalous)."""
    return model.decision_function(features)
