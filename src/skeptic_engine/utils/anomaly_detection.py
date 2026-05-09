"""Anomaly detection utilities for Isolation Forest and related methods.

Consolidates common patterns from H24, H26, H27 for:
- Isolation Forest training and scoring
- Cell-level feature extraction
- Default model configurations
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest

__all__ = [
    "DEFAULT_ISOLATION_FOREST",
    "train_isolation_forest",
    "score_anomalies",
    "cell_level_features",
]

# Default Isolation Forest configuration
DEFAULT_ISOLATION_FOREST = IsolationForest(
    n_estimators=200,
    contamination="auto",
    random_state=42,
    n_jobs=-1,
)


def train_isolation_forest(
    features: np.ndarray,
    contamination: str | float = "auto",
    random_state: int = 42,
    n_estimators: int = 200,
) -> IsolationForest:
    """Train Isolation Forest on feature matrix.

    Parameters
    ----------
    features : np.ndarray
        Feature matrix (n_samples, n_features).
    contamination : str | float
        Expected proportion of outliers ('auto' or float in (0, 0.5]).
    random_state : int
        Random seed for reproducibility.
    n_estimators : int
        Number of trees in the forest.

    Returns
    -------
    IsolationForest
        Trained model.
    """
    model = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(features)
    return model


def score_anomalies(
    model: IsolationForest,
    features: np.ndarray,
) -> np.ndarray:
    """Compute anomaly scores for samples.

    Parameters
    ----------
    model : IsolationForest
        Trained Isolation Forest model.
    features : np.ndarray
        Feature matrix to score.

    Returns
    -------
    np.ndarray
        Anomaly scores (more negative = more anomalous).

    Notes
    -----
    Uses decision_function which returns the average anomaly score.
    """
    return np.asarray(model.decision_function(features))


def cell_level_features(matrix: np.ndarray) -> np.ndarray:
    """Extract 8 cell-level features from scRNA-seq count matrix.

    Parameters
    ----------
    matrix : np.ndarray
        Count matrix (cells x genes).

    Returns
    -------
    np.ndarray
        Feature matrix (cells x 8) with:
        - mean expression
        - std of expression
        - fraction of zeros
        - total counts
        - detected genes (non-zero count)
        - log1p total counts
        - coefficient of variation
        - max expression

    Notes
    -----
    These features capture basic statistical properties of each cell's
    expression profile, useful for quality control and anomaly detection.
    """
    # Per-cell statistics
    mean_expr = matrix.mean(axis=1)
    std_expr = matrix.std(axis=1)
    zero_frac = (matrix == 0).mean(axis=1)
    total_counts = matrix.sum(axis=1)
    detected_genes = (matrix > 0).sum(axis=1)
    log_total = np.log1p(total_counts)

    # Coefficient of variation (avoid division by zero)
    cv = np.divide(
        std_expr, mean_expr, out=np.zeros_like(std_expr, dtype=np.float64), where=mean_expr != 0
    )

    # Max expression
    max_expr = matrix.max(axis=1)

    return np.column_stack(
        [
            mean_expr,
            std_expr,
            zero_frac,
            total_counts,
            detected_genes,
            log_total,
            cv,
            max_expr,
        ]
    )
