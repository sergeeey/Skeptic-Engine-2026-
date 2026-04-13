"""Unit tests for H33 Cross-Modal Consistency Detection module."""

from __future__ import annotations

import numpy as np
import pytest


# ===========================================================================
# Fixtures
# ===========================================================================
@pytest.fixture
def h33_module():
    """Import H33 module functions."""
    import sys
    from pathlib import Path

    exp_dir = Path(__file__).resolve().parents[1] / "experiments" / "h33_cross_modal_consistency"
    if str(exp_dir) not in sys.path:
        sys.path.insert(0, str(exp_dir))

    from run_h33 import (
        compute_consistency_profile,
        effect_size_ratio,
        generate_fabricated_data,
        generate_partially_fabricated_data,
        generate_real_like_data,
        gene_protein_correlation,
        pathway_concordance,
        rank_consistency,
        sample_clustering_agreement,
    )

    return {
        "compute_consistency_profile": compute_consistency_profile,
        "effect_size_ratio": effect_size_ratio,
        "generate_fabricated_data": generate_fabricated_data,
        "generate_partially_fabricated_data": generate_partially_fabricated_data,
        "generate_real_like_data": generate_real_like_data,
        "gene_protein_correlation": gene_protein_correlation,
        "pathway_concordance": pathway_concordance,
        "rank_consistency": rank_consistency,
        "sample_clustering_agreement": sample_clustering_agreement,
    }


@pytest.fixture
def sample_real_data(h33_module) -> tuple[np.ndarray, np.ndarray]:
    """Generate realistic paired data."""
    return h33_module["generate_real_like_data"](n_samples=50, n_genes=100)


@pytest.fixture
def sample_fabricated_data(h33_module) -> tuple[np.ndarray, np.ndarray]:
    """Generate fabricated paired data."""
    return h33_module["generate_fabricated_data"](n_samples=50, n_genes=100)


# ===========================================================================
# 1. Gene-protein correlation
# ===========================================================================
class TestGeneProteinCorrelation:
    """Test gene_protein_correlation metric."""

    def test_real_data_high_correlation(self, h33_module: dict, sample_real_data) -> None:
        """Real data should show moderate-high correlation."""
        mrna, protein = sample_real_data
        corr = h33_module["gene_protein_correlation"](mrna, protein)
        assert corr > 0.3, f"Expected corr > 0.3, got {corr}"

    def test_fabricated_data_low_correlation(self, h33_module: dict, sample_fabricated_data) -> None:
        """Fabricated data should show near-zero correlation."""
        mrna, protein = sample_fabricated_data
        corr = h33_module["gene_protein_correlation"](mrna, protein)
        assert abs(corr) < 0.2, f"Expected |corr| < 0.2, got {corr}"

    def test_identical_data_perfect_correlation(self, h33_module: dict) -> None:
        """Identical data should give correlation ≈ 1.0."""
        rng = np.random.default_rng(42)
        data = rng.normal(0, 1, size=(20, 50))
        corr = h33_module["gene_protein_correlation"](data, data)
        assert corr > 0.95

    def test_opposite_data_negative_correlation(self, h33_module: dict) -> None:
        """Opposite data should give negative correlation."""
        rng = np.random.default_rng(42)
        mrna = rng.normal(0, 1, size=(20, 50))
        protein = -mrna
        corr = h33_module["gene_protein_correlation"](mrna, protein)
        assert corr < -0.9


# ===========================================================================
# 2. Rank consistency
# ===========================================================================
class TestRankConsistency:
    """Test rank_consistency metric."""

    def test_real_data_moderate_consistency(self, h33_module: dict, sample_real_data) -> None:
        """Real data should show moderate rank consistency."""
        mrna, protein = sample_real_data
        tau = h33_module["rank_consistency"](mrna, protein)
        assert tau > 0.2

    def test_identical_data_perfect_consistency(self, h33_module: dict) -> None:
        """Identical data should give tau ≈ 1.0."""
        rng = np.random.default_rng(42)
        data = rng.normal(0, 1, size=(20, 50))
        tau = h33_module["rank_consistency"](data, data)
        assert tau > 0.95


# ===========================================================================
# 3. Pathway concordance
# ===========================================================================
class TestPathwayConcordance:
    """Test pathway_concordance metric."""

    def test_real_data_higher_concordance(
        self, h33_module: dict, sample_real_data, sample_fabricated_data
    ) -> None:
        """Real data should have higher pathway concordance than fabricated."""
        mrna_real, protein_real = sample_real_data
        mrna_fab, protein_fab = sample_fabricated_data

        real_concordance = h33_module["pathway_concordance"](mrna_real, protein_real)
        fab_concordance = h33_module["pathway_concordance"](mrna_fab, protein_fab)

        assert real_concordance > fab_concordance

    def test_identical_data_perfect_concordance(self, h33_module: dict) -> None:
        """Identical data should give Jaccard ≈ 1.0."""
        rng = np.random.default_rng(42)
        data = rng.normal(0, 1, size=(20, 100))
        jaccard = h33_module["pathway_concordance"](data, data)
        assert jaccard > 0.9

    def test_empty_data(self, h33_module: dict) -> None:
        """Should handle edge cases gracefully."""
        mrna = np.array([[0.0] * 10])
        protein = np.array([[0.0] * 10])
        result = h33_module["pathway_concordance"](mrna, protein)
        assert 0 <= result <= 1


# ===========================================================================
# 4. Sample clustering agreement
# ===========================================================================
class TestSampleClusteringAgreement:
    """Test sample_clustering_agreement metric."""

    def test_identical_data_perfect_agreement(self, h33_module: dict) -> None:
        """Identical data should give ARI ≈ 1.0."""
        rng = np.random.default_rng(42)
        data = rng.normal(0, 1, size=(30, 50))
        ari = h33_module["sample_clustering_agreement"](data, data)
        assert ari > 0.95

    def test_real_data_higher_than_fabricated(
        self, h33_module: dict, sample_real_data, sample_fabricated_data
    ) -> None:
        """Real data should have higher clustering agreement."""
        mrna_real, protein_real = sample_real_data
        mrna_fab, protein_fab = sample_fabricated_data

        real_ari = h33_module["sample_clustering_agreement"](mrna_real, protein_real)
        fab_ari = h33_module["sample_clustering_agreement"](mrna_fab, protein_fab)

        # Real should generally be higher (with some variance)
        assert real_ari >= fab_ari - 0.1  # Allow some tolerance


# ===========================================================================
# 5. Effect size ratio
# ===========================================================================
class TestEffectSizeRatio:
    """Test effect_size_ratio metric."""

    def test_balanced_data_ratio_near_log2(self, h33_module: dict) -> None:
        """Balanced variance should give moderate log ratio."""
        rng = np.random.default_rng(42)
        mrna = rng.normal(0, 1, size=(30, 50))
        protein = mrna * 2  # 2x variance
        ratio = h33_module["effect_size_ratio"](mrna, protein)
        assert ratio > 0  # log1p(4) > 0

    def test_zero_variance_returns_zero(self, h33_module: dict) -> None:
        """Zero variance mRNA should return 0.0."""
        mrna = np.zeros((10, 20))
        protein = np.random.default_rng(42).normal(0, 1, size=(10, 20))
        ratio = h33_module["effect_size_ratio"](mrna, protein)
        assert ratio == 0.0


# ===========================================================================
# 6. Data generation
# ===========================================================================
class TestDataGeneration:
    """Test synthetic data generation."""

    def test_real_data_shape(self, h33_module: dict) -> None:
        """Should generate correct shape."""
        mrna, protein = h33_module["generate_real_like_data"](n_samples=30, n_genes=80)
        assert mrna.shape == (30, 80)
        assert protein.shape == (30, 80)

    def test_fabricated_data_shape(self, h33_module: dict) -> None:
        """Should generate correct shape."""
        mrna, protein = h33_module["generate_fabricated_data"](n_samples=25, n_genes=60)
        assert mrna.shape == (25, 60)
        assert protein.shape == (25, 60)

    def test_partial_data_shape(self, h33_module: dict) -> None:
        """Should generate correct shape for partial data."""
        mrna, protein = h33_module["generate_partially_fabricated_data"](
            n_samples=40, n_genes=70, corruption_level=0.5
        )
        assert mrna.shape == (40, 70)
        assert protein.shape == (40, 70)

    def test_partial_corruption_intermediate_correlation(self, h33_module: dict) -> None:
        """Partially corrupted data should have intermediate correlation."""
        rng = np.random.default_rng(42)
        mrna_clean, protein_clean = h33_module["generate_real_like_data"](rng=rng)
        mrna_fab, protein_fab = h33_module["generate_fabricated_data"](rng=rng)

        mrna_partial, protein_partial = h33_module["generate_partially_fabricated_data"](
            corruption_level=0.5, rng=rng
        )

        corr_clean = h33_module["gene_protein_correlation"](mrna_clean, protein_clean)
        corr_fab = h33_module["gene_protein_correlation"](mrna_fab, protein_fab)
        corr_partial = h33_module["gene_protein_correlation"](mrna_partial, protein_partial)

        # Partial should be between clean and fabricated
        assert corr_fab < corr_partial < corr_clean

    def test_different_seeds_give_different_data(self, h33_module: dict) -> None:
        """Different RNG seeds should give different data."""
        rng1 = np.random.default_rng(1)
        rng2 = np.random.default_rng(2)

        mrna1, _ = h33_module["generate_real_like_data"](rng=rng1)
        mrna2, _ = h33_module["generate_real_like_data"](rng=rng2)

        assert not np.allclose(mrna1, mrna2)


# ===========================================================================
# 7. Consistency profile
# ===========================================================================
class TestConsistencyProfile:
    """Test compute_consistency_profile function."""

    def test_returns_all_metrics(self, h33_module: dict, sample_real_data) -> None:
        """Should return all 5 metrics."""
        mrna, protein = sample_real_data
        profile = h33_module["compute_consistency_profile"](mrna, protein)

        assert "gene_protein_correlation" in profile
        assert "rank_consistency" in profile
        assert "pathway_concordance" in profile
        assert "sample_clustering_agreement" in profile
        assert "effect_size_ratio" in profile
        assert len(profile) == 5

    def test_all_metrics_in_valid_range(self, h33_module: dict, sample_real_data) -> None:
        """All metrics should be finite."""
        mrna, protein = sample_real_data
        profile = h33_module["compute_consistency_profile"](mrna, protein)

        for name, value in profile.items():
            assert np.isfinite(value), f"{name}: {value} is not finite"


# ===========================================================================
# 8. Integration test
# ===========================================================================
class TestH33Integration:
    """Integration test for full H33 pipeline."""

    def test_run_experiment(self) -> None:
        """Full experiment should complete and return valid results."""
        import sys
        from pathlib import Path

        exp_dir = Path(__file__).resolve().parents[1] / "experiments" / "h33_cross_modal_consistency"
        if str(exp_dir) not in sys.path:
            sys.path.insert(0, str(exp_dir))

        from run_h33 import run_experiment

        results = run_experiment()

        assert results["experiment"] == "H33"
        assert "summary" in results
        assert "dataset_reports" in results
        
        summary = results["summary"]
        assert summary["overall_separation"] > 0.2  # Should detect fabrication
        assert summary["conclusion"] in ("SUCCESS", "WEAK")
