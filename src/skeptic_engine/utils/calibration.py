"""Calibrated uncertainty for anomaly detection scores.

This module implements isotonic recalibration for anomaly detection scores,
transforming raw scores (e.g., 0.87) into calibrated probabilities with
confidence intervals (e.g., "0.87, CI: [0.83, 0.91], MACE: 0.04").

The calibration is trained on historical experiment results where ground truth
labels (real vs fabricated) are known.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import cross_val_predict


@dataclass
class CalibratedScore:
    """A single calibrated score with confidence interval."""

    raw_score: float
    calibrated_score: float
    ci_lower: float
    ci_upper: float
    confidence_level: float = 0.95
    mace: float = 0.0  # Mean Absolute Calibration Error

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_score": self.raw_score,
            "calibrated_score": self.calibrated_score,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "confidence_level": self.confidence_level,
            "mace": self.mace,
        }

    def __str__(self) -> str:
        return (
            f"{self.calibrated_score:.3f} "
            f"(raw: {self.raw_score:.3f}, "
            f"CI [{self.ci_lower:.3f}, {self.ci_upper:.3f}], "
            f"MACE: {self.mace:.3f})"
        )


@dataclass
class CalibrationModel:
    """Isotonic regression calibration model for a detector."""

    detector_name: str
    isotonic: IsotonicRegression | None = None
    mace: float = 1.0
    n_calibration_samples: int = 0
    score_range: tuple[float, float] = (0.0, 1.0)

    def fit(self, raw_scores: np.ndarray, true_labels: np.ndarray) -> CalibrationModel:
        """Fit isotonic regression on calibration data.

        Parameters
        ----------
        raw_scores : np.ndarray
            Raw anomaly scores from the detector.
        true_labels : np.ndarray
            Ground truth labels (0 = real, 1 = fabricated).

        Returns
        -------
        self
        """
        if len(raw_scores) < 4:
            # Not enough data for calibration
            self.mace = 1.0
            self.n_calibration_samples = len(raw_scores)
            return self

        # Clip to valid range
        raw_scores = np.clip(raw_scores, 0.0, 1.0)

        # Fit isotonic regression
        self.isotonic = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        self.isotonic.fit(raw_scores, true_labels)

        # Compute MACE via cross-validation if enough samples
        if len(raw_scores) >= 10:
            try:
                cv_preds = cross_val_predict(
                    IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip"),
                    raw_scores.reshape(-1, 1),
                    true_labels,
                    cv=min(5, len(raw_scores) // 2),
                )
                self.mace = float(np.mean(np.abs(cv_preds - true_labels)))
            except ValueError:
                # CV failed (e.g., single class), compute in-sample MACE
                preds = self.isotonic.predict(raw_scores)
                self.mace = float(np.mean(np.abs(preds - true_labels)))
        else:
            # In-sample MACE for small datasets
            preds = self.isotonic.predict(raw_scores)
            self.mace = float(np.mean(np.abs(preds - true_labels)))

        self.n_calibration_samples = len(raw_scores)
        self.score_range = (float(raw_scores.min()), float(raw_scores.max()))

        return self

    def predict(self, raw_score: float) -> CalibratedScore:
        """Calibrate a single raw score.

        Parameters
        ----------
        raw_score : float
            Raw anomaly score to calibrate.

        Returns
        -------
        CalibratedScore
        """
        raw_score = float(np.clip(raw_score, 0.0, 1.0))

        if self.isotonic is None or self.n_calibration_samples < 4:
            # No calibration available — return raw score with wide CI
            return CalibratedScore(
                raw_score=raw_score,
                calibrated_score=raw_score,
                ci_lower=max(0.0, raw_score - 0.15),
                ci_upper=min(1.0, raw_score + 0.15),
                mace=1.0,
            )

        calibrated = float(self.isotonic.predict([raw_score])[0])

        # Estimate CI width based on MACE
        ci_half_width = max(0.02, self.mace * 1.5)  # At least ±0.02
        ci_lower = max(0.0, calibrated - ci_half_width)
        ci_upper = min(1.0, calibrated + ci_half_width)

        return CalibratedScore(
            raw_score=raw_score,
            calibrated_score=calibrated,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            confidence_level=0.95,
            mace=self.mace,
        )

    def predict_batch(self, raw_scores: np.ndarray) -> list[CalibratedScore]:
        """Calibrate a batch of raw scores."""
        return [self.predict(float(s)) for s in raw_scores]

    def to_dict(self) -> dict[str, Any]:
        return {
            "detector_name": self.detector_name,
            "mace": self.mace,
            "n_calibration_samples": self.n_calibration_samples,
            "score_range": list(self.score_range),
            "is_fitted": self.isotonic is not None,
        }


def compute_mace(raw_scores: np.ndarray, true_labels: np.ndarray) -> float:
    """Compute Mean Absolute Calibration Error for raw scores.

    This is the in-sample MACE without fitting a model. Useful for
    evaluating baseline calibration quality.

    Parameters
    ----------
    raw_scores : np.ndarray
        Raw anomaly scores.
    true_labels : np.ndarray
        Ground truth labels.

    Returns
    -------
    float
        Mean Absolute Calibration Error.
    """
    return float(np.mean(np.abs(np.clip(raw_scores, 0, 1) - true_labels)))


def build_calibration_dataset(
    experiment_results: list[dict[str, Any]],
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Build a calibration dataset from experiment results.

    Parameters
    ----------
    experiment_results : list[dict]
        List of experiment result dicts with 'scores' and 'labels'.

    Returns
    -------
    scores : np.ndarray
        Flat array of raw anomaly scores.
    labels : np.ndarray
        Flat array of ground truth labels (0=real, 1=fabricated).
    detector_names : list[str]
        Names of detectors that contributed scores.
    """
    all_scores = []
    all_labels = []
    detectors = set()

    for exp in experiment_results:
        detector = exp.get("detector", exp.get("method", "unknown"))
        scores = exp.get("scores", [])
        labels = exp.get("labels", [])

        if len(scores) == len(labels) and len(scores) > 0:
            all_scores.extend(scores)
            all_labels.extend(labels)
            detectors.add(detector)

    return (
        np.array(all_scores, dtype=np.float64),
        np.array(all_labels, dtype=np.float64),
        sorted(detectors),
    )
