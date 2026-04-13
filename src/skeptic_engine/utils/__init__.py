"""Shared utilities for anomaly detection and data integrity screening.

This package consolidates common functionality previously duplicated
across experiments (H23-H28), including:

- Behavioral feature extraction from p-value sequences
- I/O helpers for NCBI API, file downloads, result persistence
- Evaluation utilities for model training and cross-validation
- Anomaly detection with Isolation Forest
"""

from skeptic_engine.utils.anomaly_detection import (
    DEFAULT_ISOLATION_FOREST,
    cell_level_features,
    score_anomalies,
    train_isolation_forest,
)
from skeptic_engine.utils.behavioral_features import (
    FEATURE_NAMES,
    extract_behavioral_features,
    extract_pvalues_regex,
    pcurve_test_stat,
)
from skeptic_engine.utils.evaluation import (
    DEFAULT_SPLITTER,
    clean_features,
    compute_metrics,
    run_classification,
    run_cv_evaluate,
)
from skeptic_engine.utils.io_helpers import (
    download_file,
    fetch_pmc_fulltext,
    ncbi_request,
    parse_pvalue_string,
    save_json_results,
)

__all__ = [
    # Behavioral features
    "FEATURE_NAMES",
    "extract_pvalues_regex",
    "extract_behavioral_features",
    "pcurve_test_stat",
    # I/O helpers
    "download_file",
    "fetch_pmc_fulltext",
    "ncbi_request",
    "parse_pvalue_string",
    "save_json_results",
    # Evaluation
    "DEFAULT_SPLITTER",
    "clean_features",
    "compute_metrics",
    "run_classification",
    "run_cv_evaluate",
    # Anomaly detection
    "DEFAULT_ISOLATION_FOREST",
    "cell_level_features",
    "score_anomalies",
    "train_isolation_forest",
]
