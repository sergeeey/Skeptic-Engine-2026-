"""Unit tests for H31 Unified Anomaly Score (UAS) module.

Covers:
- load_json_results
- collect_signal_h29, collect_signal_h30
- normalize_signals (including edge cases)
- compute_uas_weighted
- compute_uas_stacking
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest


# ===========================================================================
# Fixtures
# ===========================================================================
@pytest.fixture
def h31_module():
    """Import H31 module functions."""
    import sys
    from pathlib import Path

    # Ensure experiments dir is importable
    exp_dir = Path(__file__).resolve().parents[1] / "experiments" / "h31_unified_anomaly_score"
    if str(exp_dir) not in sys.path:
        sys.path.insert(0, str(exp_dir))

    from run_h31 import (
        collect_signal_h29,
        collect_signal_h30,
        compute_uas_stacking,
        compute_uas_weighted,
        load_json_results,
        normalize_signals,
    )

    return {
        "load_json_results": load_json_results,
        "collect_signal_h29": collect_signal_h29,
        "collect_signal_h30": collect_signal_h30,
        "normalize_signals": normalize_signals,
        "compute_uas_weighted": compute_uas_weighted,
        "compute_uas_stacking": compute_uas_stacking,
    }


@pytest.fixture
def sample_h29_data() -> dict:
    """Sample H29 results structure."""
    return {
        "experiment": "H29",
        "n_samples": 140,
        "separation": 0.0045,
        "results": [
            {
                "label": "real",
                "fabrication": "none",
                "global_anomaly_score": 0.0014,
                "syndrome_score": 0.0009,
            },
            {
                "label": "fab_random",
                "fabrication": "random",
                "global_anomaly_score": 0.9653,
                "syndrome_score": 0.5915,
            },
            {
                "label": "fab_shuffle",
                "fabrication": "shuffle",
                "global_anomaly_score": 0.9695,
                "syndrome_score": 0.5917,
            },
        ],
    }


@pytest.fixture
def sample_h30_data() -> dict:
    """Sample H30 results structure."""
    return {
        "experiment": "H30_retracted_syndrome",
        "source": "GSE160269",
        "results": [
            {
                "dataset": "PBMC3k_reference",
                "type": "clean_reference",
                "syndrome": 0.0007,
            },
            {
                "dataset": "GSE160269_Bcell",
                "type": "retracted",
                "syndrome": 0.0005,
            },
            {
                "dataset": "GSE160269_Tcell",
                "type": "retracted",
                "syndrome": 0.0004,
            },
        ],
    }


# ===========================================================================
# 1. load_json_results
# ===========================================================================
class TestLoadJsonResults:
    """Test load_json_results function."""

    def test_load_existing_file(self, tmp_path: Path, h31_module: dict) -> None:
        """Should load and parse existing JSON file."""
        data = {"key": "value", "number": 42}
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")

        result = h31_module["load_json_results"](json_file)

        assert result == data

    def test_nonexistent_file(self, tmp_path: Path, h31_module: dict) -> None:
        """Should return None for non-existent file."""
        result = h31_module["load_json_results"](tmp_path / "nonexistent.json")
        assert result is None

    def test_empty_file(self, tmp_path: Path, h31_module: dict) -> None:
        """Should handle empty file gracefully."""
        json_file = tmp_path / "empty.json"
        json_file.write_text("", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            h31_module["load_json_results"](json_file)

    def test_unicode_content(self, tmp_path: Path, h31_module: dict) -> None:
        """Should handle Unicode content correctly."""
        data = {"name": "Сергей", "result": "✓ passed"}
        json_file = tmp_path / "unicode.json"
        json_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        result = h31_module["load_json_results"](json_file)
        assert result == data


# ===========================================================================
# 2. collect_signal_h29
# ===========================================================================
class TestCollectSignalH29:
    """Test collect_signal_h29 function."""

    def test_parses_real_data(self, h31_module: dict) -> None:
        """Should parse actual H29 results file."""
        signals = h31_module["collect_signal_h29"]()

        # Should have at least some signals from real H29 file
        assert isinstance(signals, dict)
        # Real H29 has labels like "real", "fab_random", etc.
        assert any(k.startswith("h29_") for k in signals)

    def test_all_scores_in_valid_range(self, h31_module: dict) -> None:
        """All scores should be in [0, 1]."""
        signals = h31_module["collect_signal_h29"]()

        for name, score in signals.items():
            assert 0.0 <= score <= 1.0, f"{name}: {score} out of range"


# ===========================================================================
# 3. collect_signal_h30
# ===========================================================================
class TestCollectSignalH30:
    """Test collect_signal_h30 function."""

    def test_parses_real_data(self, h31_module: dict) -> None:
        """Should parse actual H30 results file."""
        signals = h31_module["collect_signal_h30"]()

        # Should have at least some signals from real H30 file
        assert isinstance(signals, dict)
        # Real H30 has dataset names
        assert len(signals) > 0

    def test_all_scores_in_valid_range(self, h31_module: dict) -> None:
        """All scores should be in [0, 1]."""
        signals = h31_module["collect_signal_h30"]()

        for name, score in signals.items():
            assert 0.0 <= score <= 1.0, f"{name}: {score} out of range"


# ===========================================================================
# 4. normalize_signals
# ===========================================================================
class TestNormalizeSignals:
    """Test normalize_signals function."""

    def test_basic_normalization(self, h31_module: dict) -> None:
        """Should normalize columns to [0, 1]."""
        matrix = np.array(
            [
                [0.0, 10.0],
                [0.5, 20.0],
                [1.0, 30.0],
            ]
        )

        result = h31_module["normalize_signals"](matrix)

        # First column: [0, 0.5, 1.0]
        assert result[0, 0] == pytest.approx(0.0)
        assert result[1, 0] == pytest.approx(0.5)
        assert result[2, 0] == pytest.approx(1.0)

        # Second column: [0, 0.5, 1.0]
        assert result[0, 1] == pytest.approx(0.0)
        assert result[1, 1] == pytest.approx(0.5)
        assert result[2, 1] == pytest.approx(1.0)

    def test_constant_column(self, h31_module: dict) -> None:
        """Constant column should become 0.5."""
        matrix = np.array(
            [
                [1.0, 5.0],
                [2.0, 5.0],
                [3.0, 5.0],
            ]
        )

        result = h31_module["normalize_signals"](matrix)

        # Constant column → 0.5
        assert result[0, 1] == pytest.approx(0.5)
        assert result[1, 1] == pytest.approx(0.5)
        assert result[2, 1] == pytest.approx(0.5)

    def test_single_row(self, h31_module: dict) -> None:
        """Single row should become 0.5 (constant edge case)."""
        matrix = np.array([[1.0, 2.0, 3.0]])

        result = h31_module["normalize_signals"](matrix)

        # All constant (single value per column)
        assert np.allclose(result, 0.5)

    def test_preserves_shape(self, h31_module: dict) -> None:
        """Output shape should match input shape."""
        rng = np.random.default_rng(42)
        matrix = rng.random((10, 5))

        result = h31_module["normalize_signals"](matrix)

        assert result.shape == matrix.shape

    def test_all_values_finite(self, h31_module: dict) -> None:
        """All normalized values should be finite."""
        rng = np.random.default_rng(42)
        matrix = rng.random((20, 8))

        result = h31_module["normalize_signals"](matrix)

        assert np.isfinite(result).all()

    def test_negative_values(self, h31_module: dict) -> None:
        """Should handle negative input values."""
        matrix = np.array(
            [
                [-5.0, -10.0],
                [0.0, 0.0],
                [5.0, 10.0],
            ]
        )

        result = h31_module["normalize_signals"](matrix)

        # Should still be in [0, 1]
        assert (result >= 0.0).all()
        assert (result <= 1.0).all()


# ===========================================================================
# 5. compute_uas_weighted
# ===========================================================================
class TestComputeUasWeighted:
    """Test compute_uas_weighted function."""

    def test_basic_weighted_sum(self, h31_module: dict) -> None:
        """Should compute weighted sum correctly."""
        matrix = np.array(
            [
                [0.0, 1.0],
                [1.0, 0.0],
                [0.5, 0.5],
            ]
        )
        weights = {"signal_0": 0.3, "signal_1": 0.7}

        result = h31_module["compute_uas_weighted"](matrix, weights)

        # Row 0: 0.0*0.3 + 1.0*0.7 = 0.7
        assert result[0] == pytest.approx(0.7)
        # Row 1: 1.0*0.3 + 0.0*0.7 = 0.3
        assert result[1] == pytest.approx(0.3)
        # Row 2: 0.5*0.3 + 0.5*0.7 = 0.5
        assert result[2] == pytest.approx(0.5)

    def test_normalizes_weights(self, h31_module: dict) -> None:
        """Should normalize weights even if they don't sum to 1."""
        matrix = np.array([[1.0, 0.0]])
        weights = {"signal_0": 2.0, "signal_1": 3.0}

        result = h31_module["compute_uas_weighted"](matrix, weights)

        # 1.0 * (2/5) + 0.0 * (3/5) = 0.4
        assert result[0] == pytest.approx(0.4)

    def test_default_weights_for_missing(self, h31_module: dict) -> None:
        """Should use default weight for missing signal keys."""
        matrix = np.array([[1.0, 1.0, 1.0]])
        weights = {"signal_0": 1.0}  # Only first signal specified

        result = h31_module["compute_uas_weighted"](matrix, weights)

        # Should work with default 1/7 for unspecified signals
        assert np.isfinite(result[0])

    def test_output_shape(self, h31_module: dict) -> None:
        """Output should be 1D array with n_samples elements."""
        rng = np.random.default_rng(42)
        matrix = rng.random((10, 5))
        weights = {f"signal_{i}": 0.2 for i in range(5)}

        result = h31_module["compute_uas_weighted"](matrix, weights)

        assert result.shape == (10,)

    def test_all_finite_output(self, h31_module: dict) -> None:
        """Output should always be finite."""
        rng = np.random.default_rng(42)
        matrix = rng.random((20, 8))
        weights = {f"signal_{i}": 0.125 for i in range(8)}

        result = h31_module["compute_uas_weighted"](matrix, weights)

        assert np.isfinite(result).all()


# ===========================================================================
# 6. compute_uas_stacking
# ===========================================================================
class TestComputeUasStacking:
    """Test compute_uas_stacking function."""

    def _make_cv_data(self, n_samples: int, n_features: int) -> tuple[np.ndarray, np.ndarray]:
        """Create simple CV data with balanced classes."""
        rng = np.random.default_rng(42)
        x = rng.random((n_samples, n_features))
        y = np.array([0] * (n_samples // 2) + [1] * (n_samples - n_samples // 2))
        return x, y

    def test_basic_stacking(self, h31_module: dict) -> None:
        """Should return CV metrics dict."""
        x, y = self._make_cv_data(20, 5)

        result = h31_module["compute_uas_stacking"](x, y, n_splits=3)

        assert "mean_auc" in result
        assert "mean_ap" in result
        assert "feature_importance" in result
        assert 0 <= result["mean_auc"] <= 1
        assert 0 <= result["mean_ap"] <= 1

    def test_insufficient_data(self, h31_module: dict) -> None:
        """Should return status dict when data is insufficient."""
        x = np.array([[0.5], [0.6]])
        y = np.array([0, 1])  # Only 1 positive, 1 negative

        result = h31_module["compute_uas_stacking"](x, y)

        assert result.get("status") == "insufficient_data_for_cv"

    def test_feature_importance_shape(self, h31_module: dict) -> None:
        """Feature importance should match number of features."""
        x, y = self._make_cv_data(30, 7)

        result = h31_module["compute_uas_stacking"](x, y, n_splits=3)

        assert len(result["feature_importance"]) == 7
        assert all(0 <= fi <= 1 for fi in result["feature_importance"])

    def test_n_splits_adaptive(self, h31_module: dict) -> None:
        """Should adapt n_splits to class balance."""
        x, y = self._make_cv_data(10, 3)  # 5 pos, 5 neg

        result = h31_module["compute_uas_stacking"](x, y)

        # Should have run with some n_splits
        assert "mean_auc" in result
        assert result.get("n_splits", 0) >= 2
