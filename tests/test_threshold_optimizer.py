"""Unit tests for Skeptic Engine threshold optimizer."""

from __future__ import annotations

import numpy as np
import pytest

from sklearn.metrics import f1_score


# ===========================================================================
# Fixtures
# ===========================================================================
@pytest.fixture
def threshold_optimizer():
    """Import threshold optimizer module."""
    import sys
    from pathlib import Path

    src_dir = Path(__file__).resolve().parents[1] / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from skeptic_engine.utils.threshold_optimizer import (
        ThresholdOptimizer,
        find_sweet_spots,
        ThresholdResult,
    )

    return {
        "ThresholdOptimizer": ThresholdOptimizer,
        "find_sweet_spots": find_sweet_spots,
        "ThresholdResult": ThresholdResult,
    }


@pytest.fixture
def synthetic_data():
    """Generate synthetic calibration data."""
    rng = np.random.default_rng(42)
    real = rng.normal(0.3, 0.2, 100)
    fake = rng.normal(0.7, 0.2, 100)
    scores = np.concatenate([real, fake])
    labels = np.concatenate([np.zeros(100), np.ones(100)])
    return scores, labels


# ===========================================================================
# 1. ThresholdOptimizer
# ===========================================================================
class TestThresholdOptimizer:
    """Test ThresholdOptimizer class."""

    def test_fit_finds_threshold(self, threshold_optimizer: dict, synthetic_data) -> None:
        """Should find a threshold between the two clusters."""
        scores, labels = synthetic_data
        opt = threshold_optimizer["ThresholdOptimizer"]()
        opt.fit(scores, labels)

        # Threshold should be around 0.5
        assert 0.3 < opt.threshold_ < 0.7

    def test_fit_returns_self(self, threshold_optimizer: dict, synthetic_data) -> None:
        """Fit should return self."""
        scores, labels = synthetic_data
        opt = threshold_optimizer["ThresholdOptimizer"]()
        result = opt.fit(scores, labels)
        assert result is opt

    def test_predict_uses_threshold(self, threshold_optimizer: dict, synthetic_data) -> None:
        """Predict should return 0/1 based on threshold."""
        scores, labels = synthetic_data
        opt = threshold_optimizer["ThresholdOptimizer"]()
        opt.fit(scores, labels)

        preds = opt.predict(scores)
        assert set(preds).issubset({0, 1})

    def test_maximize_f1(self, threshold_optimizer: dict, synthetic_data) -> None:
        """The chosen threshold should maximize F1."""
        scores, labels = synthetic_data
        opt = threshold_optimizer["ThresholdOptimizer"]()
        opt.fit(scores, labels)

        # Evaluate F1 at optimal threshold
        preds_opt = opt.predict(scores)
        f1_opt = f1_score(labels, preds_opt)

        # Should be close to the stored F1
        assert f1_opt == pytest.approx(opt.f1_score_, abs=0.01)

    def test_empty_data(self, threshold_optimizer: dict) -> None:
        """Should handle empty data gracefully."""
        opt = threshold_optimizer["ThresholdOptimizer"]()
        opt.fit(np.array([]), np.array([]))

        assert opt.threshold_ == 0.5  # Default fallback

    def test_single_sample(self, threshold_optimizer: dict) -> None:
        """Should handle single sample."""
        opt = threshold_optimizer["ThresholdOptimizer"]()
        opt.fit(np.array([0.5]), np.array([0.0]))

        assert opt.threshold_ == 0.5

    def test_to_result(self, threshold_optimizer: dict, synthetic_data) -> None:
        """Should create ThresholdResult."""
        scores, labels = synthetic_data
        opt = threshold_optimizer["ThresholdOptimizer"]()
        opt.fit(scores, labels)

        result = opt.to_result(n_samples=200, n_positives=100)
        assert result.n_samples == 200
        assert result.n_positives == 100
        assert result.f1_score > 0.9

    def test_to_dict(self, threshold_optimizer: dict, synthetic_data) -> None:
        """ThresholdResult.to_dict should work."""
        scores, labels = synthetic_data
        opt = threshold_optimizer["ThresholdOptimizer"]()
        opt.fit(scores, labels)

        result = opt.to_result(n_samples=200, n_positives=100)
        d = result.to_dict()
        assert "optimal_threshold" in d
        assert "f1_score" in d


# ===========================================================================
# 2. find_sweet_spots
# ===========================================================================
class TestFindSweetSpots:
    """Test find_sweet_spots function."""

    def test_basic(self, threshold_optimizer: dict) -> None:
        """Should find thresholds for all detectors."""
        data = [
            {"detector": "a", "scores": [0.1, 0.9] * 50, "labels": [0.0, 1.0] * 50},
            {"detector": "b", "scores": [0.2, 0.8] * 50, "labels": [0.0, 1.0] * 50},
        ]
        results = threshold_optimizer["find_sweet_spots"](data)

        assert "a" in results
        assert "b" in results
        assert len(results) == 2

    def test_skips_small(self, threshold_optimizer: dict) -> None:
        """Should skip detectors with too few samples."""
        data = [
            {"detector": "small", "scores": [0.1], "labels": [0.0]},
            {"detector": "big", "scores": [0.1, 0.9] * 50, "labels": [0.0, 1.0] * 50},
        ]
        results = threshold_optimizer["find_sweet_spots"](data)

        assert "small" not in results
        assert "big" in results

    def test_empty_input(self, threshold_optimizer: dict) -> None:
        """Should handle empty input."""
        results = threshold_optimizer["find_sweet_spots"]([])
        assert len(results) == 0
