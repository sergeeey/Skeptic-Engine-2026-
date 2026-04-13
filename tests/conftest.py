"""Pytest conftest — shared fixtures and path configuration for Skeptic Engine.

This module centralises all path management so individual test files
don't need sys.path.insert() hacks.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ===========================================================================
# Project root discovery
# ===========================================================================
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
EXPERIMENTS_DIR = PROJECT_ROOT / "experiments"
DATA_DIR = PROJECT_ROOT / "data"

# Ensure src/ is importable
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# ===========================================================================
# Experiment directory fixtures
# ===========================================================================
@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return absolute path to project root."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def src_dir() -> Path:
    """Return absolute path to src/ directory."""
    return SRC_DIR


@pytest.fixture(scope="session")
def experiments_dir() -> Path:
    """Return absolute path to experiments/ directory."""
    return EXPERIMENTS_DIR


@pytest.fixture(scope="session")
def data_dir() -> Path:
    """Return absolute path to data/ directory."""
    return DATA_DIR


# ===========================================================================
# Per-experiment directory fixtures
# ===========================================================================
@pytest.fixture(scope="session")
def h24_dir() -> Path:
    """H24: Benford digit forensics on scRNA-seq."""
    d = EXPERIMENTS_DIR / "h24_benford_scrna"
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))
    return d


@pytest.fixture(scope="session")
def h23_dir() -> Path:
    """H23: Behavioral p-hacking detection."""
    d = EXPERIMENTS_DIR / "h23_phacking_behavioral"
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))
    return d


@pytest.fixture(scope="session")
def h25_dir() -> Path:
    """H25: Banking autoencoder on proteomics/CNA."""
    d = EXPERIMENTS_DIR / "h25_banking_ae_lcms"
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))
    return d


@pytest.fixture(scope="session")
def h26_dir() -> Path:
    """H26: GEO mass screening."""
    d = EXPERIMENTS_DIR / "h26_geo_screening"
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))
    return d


@pytest.fixture(scope="session")
def h27_dir() -> Path:
    """H27: Clinical trials integrity."""
    d = EXPERIMENTS_DIR / "h27_clinical_trials"
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))
    return d


@pytest.fixture(scope="session")
def h28_dir() -> Path:
    """H28: Paper mills detection."""
    d = EXPERIMENTS_DIR / "h28_paper_mills"
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))
    return d


# ===========================================================================
# Common test data fixtures
# ===========================================================================
@pytest.fixture
def synthetic_count_matrix():
    """Generate a small synthetic scRNA-seq count matrix for testing."""
    import numpy as np

    rng = np.random.default_rng(42)
    return rng.poisson(lam=5, size=(50, 30)).astype(np.int64)


@pytest.fixture
def small_count_matrix():
    """Generate a very small count matrix (5x20) for fast tests."""
    import numpy as np

    rng = np.random.default_rng(42)
    return rng.poisson(lam=5, size=(5, 20)).astype(np.int64)


@pytest.fixture
def sample_pvalues():
    """Generate a sample of uniform p-values for behavioral tests."""
    import numpy as np

    rng = np.random.default_rng(42)
    return rng.uniform(0, 1, size=20)


# ===========================================================================
# Result file fixtures
# ===========================================================================
RESULT_FILES = [
    "experiments/h24_benford_scrna/results/h24_results.json",
    "experiments/h25_banking_ae_lcms/results/h25_results.json",
    "experiments/h23_phacking_behavioral/results/h23_results.json",
    "experiments/h23_phacking_behavioral/results/h23_real_rpp_results.json",
    "experiments/h27_clinical_trials/results/h27_results.json",
    "experiments/h28_paper_mills/results/h28_results.json",
    "experiments/h26_geo_screening/results/h26_results.json",
]


@pytest.fixture(scope="session")
def result_files() -> list[Path]:
    """Return list of all result JSON file paths."""
    return [PROJECT_ROOT / p for p in RESULT_FILES]


@pytest.fixture
def h24_spec_path() -> Path:
    """Path to H4 benchmark specification."""
    return DATA_DIR / "benchmarks" / "h4_mvp_spec.json"
