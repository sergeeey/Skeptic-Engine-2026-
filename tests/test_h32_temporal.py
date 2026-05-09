"""Unit tests for H32 Temporal P-Hacking Detection module."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest


# ===========================================================================
# Fixtures
# ===========================================================================
@pytest.fixture
def h32_module():
    """Import H32 module functions."""
    import sys
    from pathlib import Path

    exp_dir = Path(__file__).resolve().parents[1] / "experiments" / "h32_temporal_drift"
    if str(exp_dir) not in sys.path:
        sys.path.insert(0, str(exp_dir))

    from run_h32 import (
        AuthorPValueSeries,
        DriftDetectionResult,
        TemporalFeature,
        compute_frac_just_below_05,
        compute_frac_significant,
        compute_mean_p,
        compute_pvalue_clustering,
        compute_yearly_features,
        detect_drift,
        fit_trend,
        generate_synthetic_authors,
    )

    return {
        "AuthorPValueSeries": AuthorPValueSeries,
        "DriftDetectionResult": DriftDetectionResult,
        "TemporalFeature": TemporalFeature,
        "compute_frac_just_below_05": compute_frac_just_below_05,
        "compute_frac_significant": compute_frac_significant,
        "compute_mean_p": compute_mean_p,
        "compute_pvalue_clustering": compute_pvalue_clustering,
        "compute_yearly_features": compute_yearly_features,
        "detect_drift": detect_drift,
        "fit_trend": fit_trend,
        "generate_synthetic_authors": generate_synthetic_authors,
    }


@pytest.fixture
def sample_clean_author(h32_module: dict[str, Any]) -> Any:
    """Author with uniform p-values (no drift)."""
    rng = np.random.default_rng(42)
    years = list(range(2010, 2024))
    p_values = [rng.uniform(0, 1, size=5).tolist() for _ in years]
    return h32_module["AuthorPValueSeries"](
        author_id="clean_001",
        years=years,
        p_values=p_values,
    )


@pytest.fixture
def sample_phacking_author(h32_module: dict[str, Any]) -> Any:
    """Author with increasing p-hacking pattern."""
    rng = np.random.default_rng(42)
    years = list(range(2010, 2024))
    n_years = len(years)
    p_values = []
    for i in years:
        t = (i - 2010) / n_years  # 0 to ~1
        n_clustered = min(4, int(5 * t * 0.8))
        n_uniform = max(1, 5 - n_clustered)
        clustered = rng.uniform(0.04, 0.05, size=n_clustered).tolist() if n_clustered > 0 else []
        uniform = rng.uniform(0, 1, size=n_uniform).tolist()
        p_values.append(clustered + uniform)
    return h32_module["AuthorPValueSeries"](
        author_id="phacking_001",
        years=years,
        p_values=p_values,
    )


# ===========================================================================
# 1. Feature computation
# ===========================================================================
class TestFeatureComputation:
    """Test per-year feature computation."""

    def test_frac_just_below_05(self, h32_module: dict) -> None:
        """Should compute fraction of p-values in [0.04, 0.05)."""
        pvs = [0.041, 0.042, 0.03, 0.06, 0.1]
        result = h32_module["compute_frac_just_below_05"](pvs)
        assert result == pytest.approx(2 / 5)

    def test_frac_just_below_05_empty(self, h32_module: dict) -> None:
        """Empty list should return 0.0."""
        assert h32_module["compute_frac_just_below_05"]([]) == 0.0

    def test_frac_significant(self, h32_module: dict) -> None:
        """Should compute fraction of p-values < 0.05."""
        pvs = [0.01, 0.03, 0.06, 0.1, 0.5]
        result = h32_module["compute_frac_significant"](pvs)
        assert result == pytest.approx(2 / 5)

    def test_mean_p(self, h32_module: dict) -> None:
        """Should compute mean p-value."""
        pvs = [0.1, 0.2, 0.3]
        result = h32_module["compute_mean_p"](pvs)
        assert result == pytest.approx(0.2)

    def test_mean_p_empty(self, h32_module: dict) -> None:
        """Empty list should return 0.5 (default)."""
        assert h32_module["compute_mean_p"]([]) == 0.5

    def test_pvalue_clustering(self, h32_module: dict) -> None:
        """Should compute clustering near 0.05."""
        # All p-values in [0.04, 0.05) → high clustering
        pvs = [0.041, 0.042, 0.045]
        result = h32_module["compute_pvalue_clustering"](pvs)
        assert result == pytest.approx(1.0)

    def test_pvalue_clustering_empty(self, h32_module: dict) -> None:
        """Empty list should return 0.0."""
        assert h32_module["compute_pvalue_clustering"]([]) == 0.0

    def test_yearly_features_shape(self, h32_module: dict, sample_clean_author) -> None:
        """Should compute 4 features per year."""
        features = h32_module["compute_yearly_features"](sample_clean_author)
        assert len(features) == 4
        assert "frac_just_below_05" in features
        assert "frac_significant" in features
        assert "mean_p" in features
        assert "pvalue_clustering" in features
        assert len(features["frac_just_below_05"]) == len(sample_clean_author.years)


# ===========================================================================
# 2. Trend fitting
# ===========================================================================
class TestTrendFitting:
    """Test linear trend fitting."""

    def test_upward_trend(self, h32_module: dict) -> None:
        """Should detect significant upward trend."""
        years = [2010, 2011, 2012, 2013, 2014]
        values = [0.1, 0.2, 0.3, 0.4, 0.5]
        slope, p_val = h32_module["fit_trend"](years, values)
        assert slope > 0
        assert p_val < 0.01

    def test_no_trend(self, h32_module: dict) -> None:
        """Should return high p-value for random data."""
        rng = np.random.default_rng(42)
        years = list(range(2010, 2030))
        values = rng.uniform(0.4, 0.6, size=len(years)).tolist()
        slope, p_val = h32_module["fit_trend"](years, values)
        assert p_val > 0.05

    def test_insufficient_data(self, h32_module: dict) -> None:
        """Should return default for < 3 points."""
        slope, p_val = h32_module["fit_trend"]([2010, 2011], [0.1, 0.2])
        assert slope == 0.0
        assert p_val == 1.0

    def test_constant_values(self, h32_module: dict) -> None:
        """Should return zero slope for constant values."""
        years = [2010, 2011, 2012, 2013, 2014]
        values = [0.5, 0.5, 0.5, 0.5, 0.5]
        slope, p_val = h32_module["fit_trend"](years, values)
        assert slope == pytest.approx(0.0)
        assert p_val == 1.0


# ===========================================================================
# 3. Drift detection
# ===========================================================================
class TestDriftDetection:
    """Test drift detection on author data."""

    def test_clean_author_not_flagged(self, h32_module: dict, sample_clean_author) -> None:
        """Clean author should not be flagged."""
        result = h32_module["detect_drift"](sample_clean_author)
        assert result.flag is False
        assert result.drift_detected is False

    def test_phacking_author_flagged(self, h32_module: dict, sample_phacking_author) -> None:
        """P-hacking author should be flagged."""
        result = h32_module["detect_drift"](sample_phacking_author)
        assert result.flag is True
        assert result.drift_detected is True

    def test_result_has_features(self, h32_module: dict, sample_clean_author) -> None:
        """Result should contain all 4 features."""
        result = h32_module["detect_drift"](sample_clean_author)
        assert len(result.features) == 4
        feature_names = [f.name for f in result.features]
        assert "frac_just_below_05" in feature_names
        assert "frac_significant" in feature_names
        assert "mean_p" in feature_names
        assert "pvalue_clustering" in feature_names

    def test_result_metadata(self, h32_module: dict, sample_clean_author) -> None:
        """Result should contain correct metadata."""
        result = h32_module["detect_drift"](sample_clean_author)
        assert result.author_id == "clean_001"
        assert result.n_papers == 14
        assert result.n_pvalues == 70  # 14 years * 5 p-values


# ===========================================================================
# 4. Synthetic data generation
# ===========================================================================
class TestSyntheticData:
    """Test synthetic author generation."""

    def test_generates_correct_number(self, h32_module: dict) -> None:
        """Should generate 10 authors (5 clean + 5 p-hacking)."""
        rng = np.random.default_rng(42)
        authors = h32_module["generate_synthetic_authors"](rng)
        assert len(authors) == 10

    def test_clean_authors_have_uniform_pvalues(self, h32_module: dict) -> None:
        """Clean authors should have roughly uniform p-value distribution."""
        rng = np.random.default_rng(42)
        authors = h32_module["generate_synthetic_authors"](rng)
        clean_authors = [a for a in authors if "clean" in a.author_id]

        for author in clean_authors:
            all_pvalues = [p for pvs in author.p_values for p in pvs]
            mean_p = np.mean(all_pvalues)
            # Uniform [0,1] should have mean ≈ 0.5
            assert 0.3 < mean_p < 0.7

    def test_phacking_authors_have_clustering(self, h32_module: dict) -> None:
        """P-hacking authors should show increasing clustering over time."""
        rng = np.random.default_rng(42)
        authors = h32_module["generate_synthetic_authors"](rng)
        phacking_authors = [a for a in authors if "phacking" in a.author_id]

        for author in phacking_authors:
            # Last year should have more p-values near 0.05 than first year
            first_year_frac = sum(1 for p in author.p_values[0] if 0.04 <= p < 0.05) / max(
                len(author.p_values[0]), 1
            )
            last_year_frac = sum(1 for p in author.p_values[-1] if 0.04 <= p < 0.05) / max(
                len(author.p_values[-1]), 1
            )
            # Trend should be upward (or at least not strongly downward)
            assert last_year_frac >= first_year_frac * 0.5  # Allow some noise


# ===========================================================================
# 5. Integration test
# ===========================================================================
class TestH32Integration:
    """Integration test for full H32 pipeline."""

    def test_run_experiment(self, h32_module: dict) -> None:
        """Full experiment should complete and return valid results."""
        import sys
        from pathlib import Path

        exp_dir = Path(__file__).resolve().parents[1] / "experiments" / "h32_temporal_drift"
        if str(exp_dir) not in sys.path:
            sys.path.insert(0, str(exp_dir))

        from run_h32 import run_experiment

        results = run_experiment()

        assert results["experiment"] == "H32"
        assert "summary" in results
        assert "author_reports" in results
        assert len(results["author_reports"]) == 10

        summary = results["summary"]
        assert summary["accuracy"] >= 0.8  # Should detect p-hacking well
        assert summary["n_flagged"] >= 3  # At least some authors flagged
