"""Unit tests for Skeptic Engine calibration module."""

from __future__ import annotations

import numpy as np
import pytest


# ===========================================================================
# Fixtures
# ===========================================================================
@pytest.fixture
def calibration_module():
    """Import calibration module."""
    import sys
    from pathlib import Path

    src_dir = Path(__file__).resolve().parents[1] / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from skeptic_engine.utils.calibration import (
        CalibrationModel,
        CalibratedScore,
        build_calibration_dataset,
        compute_mace,
    )

    return {
        "CalibrationModel": CalibrationModel,
        "CalibratedScore": CalibratedScore,
        "build_calibration_dataset": build_calibration_dataset,
        "compute_mace": compute_mace,
    }


@pytest.fixture
def sample_calibration_data() -> tuple[np.ndarray, np.ndarray]:
    """Simple calibration data with known relationship."""
    rng = np.random.default_rng(42)
    # Real data: low scores, Fabricated data: high scores
    real_scores = rng.beta(2, 8, size=100)
    fake_scores = rng.beta(8, 2, size=100)
    scores = np.concatenate([real_scores, fake_scores])
    labels = np.array([0.0] * 100 + [1.0] * 100)
    return scores, labels


# ===========================================================================
# 1. CalibratedScore
# ===========================================================================
class TestCalibratedScore:
    """Test CalibratedScore dataclass."""

    def test_to_dict(self, calibration_module: dict) -> None:
        """Should convert to dict correctly."""
        cs = calibration_module["CalibratedScore"](
            raw_score=0.5,
            calibrated_score=0.45,
            ci_lower=0.40,
            ci_upper=0.50,
            mace=0.03,
        )
        d = cs.to_dict()
        assert d["raw_score"] == 0.5
        assert d["calibrated_score"] == 0.45
        assert d["ci_lower"] == 0.40
        assert d["ci_upper"] == 0.50
        assert d["mace"] == 0.03

    def test_str_format(self, calibration_module: dict) -> None:
        """Should produce readable string."""
        cs = calibration_module["CalibratedScore"](
            raw_score=0.87,
            calibrated_score=0.83,
            ci_lower=0.79,
            ci_upper=0.87,
            mace=0.04,
        )
        s = str(cs)
        assert "0.830" in s
        assert "0.870" in s
        assert "0.040" in s


# ===========================================================================
# 2. compute_mace
# ===========================================================================
class TestComputeMACE:
    """Test MACE computation."""

    def test_perfect_calibration(self, calibration_module: dict) -> None:
        """Perfect scores should give MACE = 0."""
        scores = np.array([0.0, 0.5, 1.0])
        labels = np.array([0.0, 0.5, 1.0])
        mace = calibration_module["compute_mace"](scores, labels)
        assert mace == pytest.approx(0.0)

    def test_worst_calibration(self, calibration_module: dict) -> None:
        """Completely wrong scores should give MACE = 1."""
        scores = np.array([1.0, 1.0, 0.0])
        labels = np.array([0.0, 0.0, 1.0])
        mace = calibration_module["compute_mace"](scores, labels)
        assert mace == pytest.approx(1.0)

    def test_partial_calibration(self, calibration_module: dict) -> None:
        """Should compute correct partial MACE."""
        scores = np.array([0.1, 0.9])
        labels = np.array([0.0, 1.0])
        mace = calibration_module["compute_mace"](scores, labels)
        assert mace == pytest.approx(0.1)  # |0.1-0| + |0.9-1| = 0.2 / 2 = 0.1

    def test_clips_scores(self, calibration_module: dict) -> None:
        """Should clip scores to [0, 1]."""
        scores = np.array([-0.5, 1.5])
        labels = np.array([0.0, 1.0])
        mace = calibration_module["compute_mace"](scores, labels)
        assert mace == pytest.approx(0.0)  # clipped to [0, 1]


# ===========================================================================
# 3. CalibrationModel
# ===========================================================================
class TestCalibrationModel:
    """Test CalibrationModel class."""

    def test_fit_and_predict(self, calibration_module: dict, sample_calibration_data) -> None:
        """Should calibrate scores after fitting."""
        scores, labels = sample_calibration_data
        model = calibration_module["CalibrationModel"](detector_name="test")
        model.fit(scores, labels)

        assert model.isotonic is not None
        assert model.mace < 0.2  # Should be well-calibrated

        # Low raw score should give low calibrated score
        low_result = model.predict(0.1)
        assert low_result.calibrated_score < 0.3

        # High raw score should give high calibrated score
        high_result = model.predict(0.9)
        assert high_result.calibrated_score > 0.7

    def test_predict_returns_calibrated_score(self, calibration_module: dict, sample_calibration_data) -> None:
        """Should return CalibratedScore object."""
        scores, labels = sample_calibration_data
        model = calibration_module["CalibrationModel"](detector_name="test")
        model.fit(scores, labels)

        result = model.predict(0.5)
        assert isinstance(result, calibration_module["CalibratedScore"])
        assert 0 <= result.calibrated_score <= 1
        assert 0 <= result.ci_lower <= result.ci_upper <= 1

    def test_predict_before_fit(self, calibration_module: dict) -> None:
        """Should return raw score with wide CI if not fitted."""
        model = calibration_module["CalibrationModel"](detector_name="unfitted")
        result = model.predict(0.5)

        assert result.calibrated_score == pytest.approx(0.5)
        assert result.mace == 1.0

    def test_too_few_samples(self, calibration_module: dict) -> None:
        """Should not crash with too few samples."""
        model = calibration_module["CalibrationModel"](detector_name="tiny")
        model.fit(np.array([0.3, 0.7]), np.array([0.0, 1.0]))

        result = model.predict(0.5)
        assert result.calibrated_score == pytest.approx(0.5)  # No calibration

    def test_predict_batch(self, calibration_module: dict, sample_calibration_data) -> None:
        """Should calibrate batch of scores."""
        scores, labels = sample_calibration_data
        model = calibration_module["CalibrationModel"](detector_name="test")
        model.fit(scores, labels)

        batch = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
        results = model.predict_batch(batch)

        assert len(results) == 5
        assert all(isinstance(r, calibration_module["CalibratedScore"]) for r in results)

    def test_to_dict(self, calibration_module: dict, sample_calibration_data) -> None:
        """Should return valid dict representation."""
        scores, labels = sample_calibration_data
        model = calibration_module["CalibrationModel"](detector_name="test_detector")
        model.fit(scores, labels)

        d = model.to_dict()
        assert d["detector_name"] == "test_detector"
        assert d["is_fitted"] is True
        assert d["n_calibration_samples"] == 200
        assert d["mace"] < 1.0

    def test_ci_width_scales_with_mace(self, calibration_module: dict) -> None:
        """Higher MACE should give wider CI."""
        model_good = calibration_module["CalibrationModel"](detector_name="good")
        model_bad = calibration_module["CalibrationModel"](detector_name="bad")

        rng = np.random.default_rng(42)
        # Good data: clear separation
        good_scores = np.concatenate([rng.beta(2, 8, 100), rng.beta(8, 2, 100)])
        good_labels = np.array([0.0] * 100 + [1.0] * 100)
        model_good.fit(good_scores, good_labels)

        # Bad data: no separation
        bad_scores = rng.uniform(0, 1, 200)
        bad_labels = np.array([0.0] * 100 + [1.0] * 100)
        model_bad.fit(bad_scores, bad_labels)

        result_good = model_good.predict(0.5)
        result_bad = model_bad.predict(0.5)

        # Bad model should have wider CI
        ci_good = result_good.ci_upper - result_good.ci_lower
        ci_bad = result_bad.ci_upper - result_bad.ci_lower
        assert ci_bad >= ci_good


# ===========================================================================
# 4. build_calibration_dataset
# ===========================================================================
class TestBuildCalibrationDataset:
    """Test build_calibration_dataset function."""

    def test_basic(self, calibration_module: dict) -> None:
        """Should extract scores and labels from experiment results."""
        exp_results = [
            {"detector": "test", "scores": [0.1, 0.9], "labels": [0.0, 1.0]},
            {"detector": "test2", "scores": [0.3, 0.7], "labels": [0.0, 1.0]},
        ]

        scores, labels, detectors = calibration_module["build_calibration_dataset"](exp_results)

        assert len(scores) == 4
        assert len(labels) == 4
        assert set(detectors) == {"test", "test2"}

    def test_skips_malformed(self, calibration_module: dict) -> None:
        """Should skip entries with mismatched scores/labels."""
        exp_results = [
            {"detector": "good", "scores": [0.5], "labels": [1.0]},
            {"detector": "bad", "scores": [0.5, 0.6], "labels": [1.0]},  # Mismatch
            {"detector": "empty", "scores": [], "labels": []},
        ]

        scores, labels, detectors = calibration_module["build_calibration_dataset"](exp_results)

        assert len(scores) == 1
        assert "good" in detectors
        assert "bad" not in detectors

    def test_empty_input(self, calibration_module: dict) -> None:
        """Should handle empty input gracefully."""
        scores, labels, detectors = calibration_module["build_calibration_dataset"]([])
        assert len(scores) == 0
        assert len(labels) == 0
        assert len(detectors) == 0


# ===========================================================================
# 5. Integration test
# ===========================================================================
class TestCalibrationIntegration:
    """Integration test for full calibration pipeline."""

    def test_full_pipeline(self, calibration_module: dict) -> None:
        """Should complete full calibration workflow."""
        rng = np.random.default_rng(42)

        # Simulate a detector with moderate calibration
        n = 200
        raw_scores = rng.uniform(0, 1, n)
        # Labels correlate with scores but imperfectly
        labels = (raw_scores > 0.5).astype(float)
        # Add 10% noise
        noise_mask = rng.random(n) < 0.1
        labels[noise_mask] = 1 - labels[noise_mask]

        model = calibration_module["CalibrationModel"](detector_name="integration_test")
        model.fit(raw_scores, labels)

        # Verify model is useful
        assert model.mace < 0.5  # Better than random

        # Calibrated scores should be reasonable
        for raw in [0.1, 0.5, 0.9]:
            result = model.predict(raw)
            assert 0 <= result.calibrated_score <= 1
            assert result.ci_lower <= result.calibrated_score <= result.ci_upper
