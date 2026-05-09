"""Adaptive threshold optimization (Mpemba Sweet Spot).

This module finds the optimal decision threshold for anomaly detectors
by analyzing the Precision-Recall curve on calibration data.

Instead of a fixed threshold (e.g., 0.5), we find the "Sweet Spot"
where the trade-off between False Positives and False Negatives is optimal
for the specific domain (e.g., scRNA-seq vs Proteomics).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.metrics import f1_score, precision_recall_curve, precision_score, recall_score


@dataclass
class ThresholdResult:
    """Result of threshold optimization."""

    domain: str
    optimal_threshold: float
    f1_score: float
    precision: float
    recall: float
    n_samples: int
    n_positives: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "optimal_threshold": self.optimal_threshold,
            "f1_score": self.f1_score,
            "precision": self.precision,
            "recall": self.recall,
            "n_samples": self.n_samples,
            "n_positives": self.n_positives,
        }


class ThresholdOptimizer:
    """Finds the optimal threshold for a binary classifier."""

    def __init__(self, domain: str = "default"):
        self.domain = domain
        self.threshold_ = 0.5
        self.f1_score_ = 0.0
        self.precision_ = 0.0
        self.recall_ = 0.0

    def fit(self, scores: np.ndarray, labels: np.ndarray) -> ThresholdOptimizer:
        """Find threshold that maximizes F1 score.

        Parameters
        ----------
        scores : np.ndarray
            Raw anomaly scores.
        labels : np.ndarray
            Ground truth labels (0 or 1).

        Returns
        -------
        self
        """
        if len(scores) < 2:
            return self

        # Compute precision-recall pairs
        precision, recall, thresholds = precision_recall_curve(labels, scores)

        # Compute F1 for each threshold
        # F1 = 2 * (P * R) / (P + R)
        # Avoid division by zero
        with np.errstate(divide="ignore", invalid="ignore"):
            f1_scores = 2 * precision * recall / (precision + recall)
            f1_scores = np.nan_to_num(f1_scores)

        # Find index of max F1
        best_idx = np.argmax(f1_scores)

        # Note: precision_recall_curve returns len(thresholds) = len(precision) - 1
        # The last precision corresponds to recall=0, which implies threshold=infinity.
        # We map back to the threshold array.
        if best_idx < len(thresholds):
            self.threshold_ = float(thresholds[best_idx])
            self.f1_score_ = float(f1_scores[best_idx])
            self.precision_ = float(precision[best_idx])
            self.recall_ = float(recall[best_idx])
        else:
            # Fallback to default
            self.threshold_ = 0.5

        return self

    def predict(self, scores: np.ndarray) -> np.ndarray:
        """Predict labels using the optimal threshold."""
        return (scores >= self.threshold_).astype(int)

    def to_result(self, n_samples: int, n_positives: int) -> ThresholdResult:
        """Package results into a ThresholdResult."""
        return ThresholdResult(
            domain=self.domain,
            optimal_threshold=self.threshold_,
            f1_score=self.f1_score_,
            precision=self.precision_,
            recall=self.recall_,
            n_samples=n_samples,
            n_positives=n_positives,
        )

    def evaluate(self, scores: np.ndarray, labels: np.ndarray) -> dict[str, float]:
        """Evaluate performance with current threshold."""
        preds = self.predict(scores)
        return {
            "f1": float(f1_score(labels, preds, zero_division=0)),
            "precision": float(precision_score(labels, preds, zero_division=0)),
            "recall": float(recall_score(labels, preds, zero_division=0)),
            "threshold_used": self.threshold_,
        }


def find_sweet_spots(
    calibration_data: list[dict[str, Any]],
) -> dict[str, ThresholdResult]:
    """Find optimal thresholds for all domains in calibration data.

    Parameters
    ----------
    calibration_data : list[dict]
        List of dicts with keys: "detector", "scores", "labels".

    Returns
    -------
    dict[str, ThresholdResult]
        Mapping from detector name to optimization result.
    """
    results = {}

    for entry in calibration_data:
        detector = entry.get("detector", "unknown")
        scores = np.array(entry.get("scores", []))
        labels = np.array(entry.get("labels", []))

        if len(scores) < 10:
            continue

        optimizer = ThresholdOptimizer(domain=detector)
        optimizer.fit(scores, labels)

        results[detector] = optimizer.to_result(
            n_samples=len(scores),
            n_positives=int(labels.sum()),
        )

    return results
