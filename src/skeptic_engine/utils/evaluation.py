"""Evaluation utilities for model training, cross-validation, and metrics.

Consolidates common patterns from H24, H25, H27 for:
- Stratified train/test splits
- Cross-validation
- Metric computation (AUC, AP, F1)
- Standard model configurations
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
from sklearn.metrics import average_precision_score, f1_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, StratifiedShuffleSplit

__all__ = [
    "DEFAULT_SPLITTER",
    "run_classification",
    "run_cv_evaluate",
    "compute_metrics",
    "clean_features",
]

# Default 80/20 stratified split
DEFAULT_SPLITTER = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)


def run_classification(
    x: np.ndarray,
    y: np.ndarray,
    model_factory: Callable[[], Any],
    test_size: float = 0.2,
    random_state: int = 42,
) -> dict[str, float]:
    """Run train/test classification with standard 80/20 split.

    Parameters
    ----------
    x : np.ndarray
        Feature matrix.
    y : np.ndarray
        Binary labels (0=real, 1=fake).
    model_factory : Callable
        Function that returns a fresh model instance.
    test_size : float
        Fraction of data for testing.
    random_state : int
        Random seed for reproducibility.

    Returns
    -------
    dict[str, float]
        Dictionary with 'auc', 'ap', 'f1', 'threshold' metrics.
    """
    splitter = StratifiedShuffleSplit(
        n_splits=1, test_size=test_size, random_state=random_state
    )
    train_idx, test_idx = next(splitter.split(x, y))

    x_train, x_test = x[train_idx], x[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    model = model_factory()
    model.fit(x_train, y_train)

    # Get probability scores
    if hasattr(model, "predict_proba"):
        y_score = model.predict_proba(x_test)[:, 1]
    else:
        y_score = model.decision_function(x_test)

    return compute_metrics(y_test, y_score)


def run_cv_evaluate(
    x: np.ndarray,
    y: np.ndarray,
    model_factory: Callable[[], Any],
    n_splits: int = 5,
    clean_fn: Callable[[np.ndarray], np.ndarray] | None = None,
) -> dict[str, list[float]]:
    """Run stratified K-fold cross-validation.

    Parameters
    ----------
    x : np.ndarray
        Feature matrix.
    y : np.ndarray
        Binary labels.
    model_factory : Callable
        Function that returns a fresh model instance.
    n_splits : int
        Number of CV folds.
    clean_fn : Callable, optional
        Function to clean features (e.g., handle NaN/Inf).

    Returns
    -------
    dict[str, list[float]]
        Lists of 'auc', 'ap', 'f1' scores for each fold.
    """
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    auc_scores = []
    ap_scores = []
    f1_scores = []

    for train_idx, test_idx in cv.split(x, y):
        x_train, x_test = x[train_idx], x[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        # Clean features if function provided
        if clean_fn is not None:
            x_train = clean_fn(x_train)
            x_test = clean_fn(x_test)

        model = model_factory()
        model.fit(x_train, y_train)

        if hasattr(model, "predict_proba"):
            y_score = model.predict_proba(x_test)[:, 1]
        else:
            y_score = model.decision_function(x_test)

        metrics = compute_metrics(y_test, y_score)
        auc_scores.append(metrics["auc"])
        ap_scores.append(metrics["ap"])
        f1_scores.append(metrics["f1"])

    return {"auc": auc_scores, "ap": ap_scores, "f1": f1_scores}


def compute_metrics(y_true: np.ndarray, y_score: np.ndarray) -> dict[str, float]:
    """Compute classification metrics with optimal threshold.

    Parameters
    ----------
    y_true : np.ndarray
        True binary labels.
    y_score : np.ndarray
        Prediction scores (probabilities or decision function).

    Returns
    -------
    dict[str, float]
        Dictionary with 'auc', 'ap', 'f1', 'threshold'.
    """
    auc = roc_auc_score(y_true, y_score)
    ap = average_precision_score(y_true, y_score)

    # Find optimal threshold using F1
    thresholds = np.percentile(y_score, np.linspace(0, 100, 100))
    best_f1 = 0
    best_threshold = 0.5

    for threshold in thresholds:
        y_pred = (y_score >= threshold).astype(int)
        if y_pred.sum() == 0 or y_pred.sum() == len(y_pred):
            continue
        f1 = f1_score(y_true, y_pred)
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold

    return {
        "auc": float(auc),
        "ap": float(ap),
        "f1": float(best_f1),
        "threshold": float(best_threshold),
    }


def clean_features(
    x: np.ndarray,
    nan: float = 0.0,
    posinf: float = 10.0,
    neginf: float = -10.0,
) -> np.ndarray:
    """Clean feature matrix by replacing NaN and Inf values.

    Parameters
    ----------
    x : np.ndarray
        Input feature matrix.
    nan : float
        Replacement value for NaN.
    posinf : float
        Replacement value for +Inf.
    neginf : float
        Replacement value for -Inf.

    Returns
    -------
    np.ndarray
        Cleaned feature matrix.

    Notes
    -----
    This is a wrapper around `np.nan_to_num` with sensible defaults
    for machine learning pipelines.
    """
    return np.nan_to_num(x, nan=nan, posinf=posinf, neginf=neginf)
