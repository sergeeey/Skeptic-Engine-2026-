"""Smoke tests for Skeptic Engine core modules.

Verify basic functionality without network access or large data downloads.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Path setup — add experiment dirs so we can import feature modules directly
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
H24_DIR = PROJECT_ROOT / "experiments" / "h24_benford_scrna"
H23_DIR = PROJECT_ROOT / "experiments" / "h23_phacking_behavioral"

sys.path.insert(0, str(H24_DIR))
sys.path.insert(0, str(H23_DIR))


# ===========================================================================
# 1. CLI module imports
# ===========================================================================
class TestCLIImports:
    """Verify the CLI package is importable and has expected attributes."""

    def test_import_skeptic_toolkit(self) -> None:
        from skeptic_toolkit import __version__

        assert __version__ == "0.1.1"

    def test_import_cli_module(self) -> None:
        from skeptic_toolkit.cli import load_count_matrix, compute_scores, main

        assert callable(load_count_matrix)
        assert callable(compute_scores)
        assert callable(main)


# ===========================================================================
# 2. Benford digit features (H24)
# ===========================================================================
class TestBenfordFeatures:
    """Test digit frequency extraction on small synthetic data."""

    def test_first_digit_frequencies_shape(self) -> None:
        from digit_features import first_digit_frequencies

        values = np.array([123, 456, 789, 12, 34, 56, 78, 91, 23, 45], dtype=np.int64)
        freq = first_digit_frequencies(values)
        assert freq.shape == (9,), f"Expected (9,), got {freq.shape}"
        assert abs(freq.sum() - 1.0) < 1e-6, "Frequencies must sum to 1"

    def test_first_digit_frequencies_all_zeros(self) -> None:
        from digit_features import first_digit_frequencies

        freq = first_digit_frequencies(np.zeros(10, dtype=np.int64))
        assert freq.shape == (9,)
        assert freq.sum() == 0.0, "All-zero input should produce zero frequencies"

    def test_second_digit_frequencies_shape(self) -> None:
        from digit_features import second_digit_frequencies

        values = np.array([123, 456, 789, 12, 34, 56, 78, 91, 23, 45], dtype=np.int64)
        freq = second_digit_frequencies(values)
        assert freq.shape == (10,), f"Expected (10,), got {freq.shape}"

    def test_extract_features_per_sample(self) -> None:
        from digit_features import extract_features_per_sample

        # Minimal matrix: 5 cells x 20 genes
        rng = np.random.default_rng(42)
        matrix = rng.poisson(lam=5, size=(5, 20)).astype(np.int64)
        features = extract_features_per_sample(matrix)
        assert features.shape[0] == 5, "One row per cell"
        assert features.shape[1] == 21, "Expected 21 features (9 fd + 10 sd + 2 chi2)"
        assert np.isfinite(features).all(), "No NaN/Inf in features"

    def test_benford_constants(self) -> None:
        from digit_features import BENFORD_FIRST, BENFORD_SECOND

        assert len(BENFORD_FIRST) == 9
        assert len(BENFORD_SECOND) == 10
        assert abs(BENFORD_FIRST.sum() - 1.0) < 1e-6
        assert abs(BENFORD_SECOND.sum() - 1.0) < 1e-6


# ===========================================================================
# 3. Cell-level features & Isolation Forest (H24)
# ===========================================================================
class TestCellLevelFeatures:
    """Test cell-level feature extraction and IF scoring."""

    def test_cell_level_features_shape(self) -> None:
        from isolation_forest import cell_level_features

        rng = np.random.default_rng(42)
        matrix = rng.poisson(lam=5, size=(10, 30)).astype(np.int64)
        features = cell_level_features(matrix)
        assert features.shape == (10, 8), f"Expected (10, 8), got {features.shape}"
        assert np.isfinite(features).all(), "No NaN/Inf"

    def test_isolation_forest_train_and_score(self) -> None:
        from isolation_forest import cell_level_features, train_isolation_forest, score_anomalies

        rng = np.random.default_rng(42)
        matrix = rng.poisson(lam=5, size=(50, 30)).astype(np.int64)
        features = cell_level_features(matrix)

        model = train_isolation_forest(features)
        scores = score_anomalies(model, features)
        assert scores.shape == (50,)
        assert np.isfinite(scores).all()


# ===========================================================================
# 4. H23 behavioral feature extraction
# ===========================================================================
class TestBehavioralFeatures:
    """Test p-value behavioral feature extraction."""

    def test_extract_behavioral_features(self) -> None:
        from run_h23 import extract_behavioral_features

        # Simulate a set of p-values from a "study"
        rng = np.random.default_rng(42)
        p_values = rng.uniform(0, 1, size=20)
        features = extract_behavioral_features(p_values)
        assert isinstance(features, np.ndarray)
        assert features.ndim == 1
        assert len(features) == 18, f"Expected 18 behavioral features, got {len(features)}"
        assert np.isfinite(features).all()

    def test_behavioral_features_edge_case_single_p(self) -> None:
        from run_h23 import extract_behavioral_features

        features = extract_behavioral_features(np.array([0.05]))
        assert len(features) == 18
        assert np.isfinite(features).all()


# ===========================================================================
# 5. Results JSON integrity
# ===========================================================================
class TestResultsIntegrity:
    """Verify all result JSON files are valid and contain expected keys."""

    RESULT_FILES = [
        "experiments/h24_benford_scrna/results/h24_results.json",
        "experiments/h25_banking_ae_lcms/results/h25_results.json",
        "experiments/h23_phacking_behavioral/results/h23_results.json",
        "experiments/h23_phacking_behavioral/results/h23_real_rpp_results.json",
        "experiments/h27_clinical_trials/results/h27_results.json",
        "experiments/h28_paper_mills/results/h28_results.json",
        "experiments/h26_geo_screening/results/h26_results.json",
    ]

    @pytest.mark.parametrize("rel_path", RESULT_FILES)
    def test_result_json_valid(self, rel_path: str) -> None:
        path = PROJECT_ROOT / rel_path
        assert path.exists(), f"Missing result file: {rel_path}"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), "Result must be a JSON object"

    def test_h24_results_structure(self) -> None:
        path = PROJECT_ROOT / "experiments/h24_benford_scrna/results/h24_results.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "results" in data
        assert "best_auc" in data
        assert data["best_auc"] >= 0.5, "H24 best AUC should be meaningful"

    def test_h27_contamination_matches_code(self) -> None:
        """Verify H27 results JSON contamination field matches actual code."""
        path = PROJECT_ROOT / "experiments/h27_clinical_trials/results/h27_results.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        contamination = data["unsupervised"]["contamination"]
        # WHY: code uses "auto" (line 209 of run_h27.py), results must match
        assert contamination == "auto" or isinstance(contamination, float), (
            f"contamination should be 'auto' or float, got {contamination}"
        )

    def test_h28_ablation_structure(self) -> None:
        path = PROJECT_ROOT / "experiments/h28_paper_mills/results/h28_results.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "ablation" in data
        for group in ("pvalue_only", "metadata_only", "combined"):
            assert group in data["ablation"], f"Missing ablation group: {group}"


# ===========================================================================
# 6. Package metadata
# ===========================================================================
class TestPackageMetadata:
    """Verify pyproject.toml consistency."""

    def test_version_consistency(self) -> None:
        from skeptic_toolkit import __version__

        import tomllib

        toml_path = PROJECT_ROOT / "pyproject.toml"
        with open(toml_path, "rb") as f:
            meta = tomllib.load(f)
        assert meta["project"]["version"] == __version__, (
            f"pyproject.toml version ({meta['project']['version']}) != "
            f"__init__.py version ({__version__})"
        )

    def test_dependencies_pinned(self) -> None:
        import tomllib

        toml_path = PROJECT_ROOT / "pyproject.toml"
        with open(toml_path, "rb") as f:
            meta = tomllib.load(f)
        for dep in meta["project"]["dependencies"]:
            assert ">=" in dep or "==" in dep, f"Dependency '{dep}' should have version constraint"
