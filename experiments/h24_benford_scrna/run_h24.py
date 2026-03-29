"""H24 MVP — Benford Digit Forensics on scRNA-seq UMI Count Matrices.

End-to-end experiment:
  1. Load real scRNA-seq count matrix (PBMC3k from 10x Genomics)
  2. Simulate fabrication (3 methods)
  3. Extract Benford digit features
  4. Train RF + LogReg classifiers
  5. Report AUC with kill criterion

Usage:
    python experiments/h24_benford_scrna/run_h24.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from scipy.io import mmread
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedShuffleSplit

# Add experiment dir to path for local imports.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from digit_features import extract_features_per_sample
from fabrication import FABRICATION_METHODS

RESULTS_DIR = Path(__file__).resolve().parent / "results"
DATA_DIR = Path(__file__).resolve().parent / "data"
PBMC3K_URL = "https://cf.10xgenomics.com/samples/cell-exp/1.1.0/pbmc3k/pbmc3k_filtered_gene_bc_matrices.tar.gz"

KILL_THRESHOLD = 0.80
REJECT_THRESHOLD = 0.65


def _download_pbmc3k() -> Path:
    """Download and extract PBMC3k filtered count matrix."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tar_path = DATA_DIR / "pbmc3k_filtered_gene_bc_matrices.tar.gz"
    mtx_dir = DATA_DIR / "filtered_gene_bc_matrices" / "hg19"

    if (mtx_dir / "matrix.mtx").exists():
        print(f"Data already exists: {mtx_dir}")
        return mtx_dir

    print(f"Downloading PBMC3k from 10x Genomics...")
    import tarfile
    import urllib.request

    req = urllib.request.Request(PBMC3K_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp, open(tar_path, "wb") as out:
        out.write(resp.read())
    print(f"Extracting...")
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(DATA_DIR, filter="data")

    if not (mtx_dir / "matrix.mtx").exists():
        raise FileNotFoundError(f"Expected matrix.mtx not found in {mtx_dir}")

    print(f"Data ready: {mtx_dir}")
    return mtx_dir


def _load_count_matrix(mtx_dir: Path) -> np.ndarray:
    """Load 10x Genomics Market Exchange format as dense integer matrix (cells × genes)."""
    mtx_path = mtx_dir / "matrix.mtx"
    sparse = mmread(str(mtx_path))
    # 10x format is genes × cells (transposed from what we want)
    dense = sparse.toarray().T.astype(np.int64)
    return dense


def _run_classification(
    X_real: np.ndarray,
    X_fake: np.ndarray,
    method_name: str,
) -> dict:
    """Train classifiers on real(0) vs fake(1) and return metrics."""
    X = np.vstack([X_real, X_fake])
    y = np.concatenate([np.zeros(len(X_real)), np.ones(len(X_fake))])

    # Stratified 80/20 split
    splitter = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(splitter.split(X, y))
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    results = {"method": method_name, "n_real": int(len(X_real)), "n_fake": int(len(X_fake))}

    for model_name, model in [
        ("random_forest", RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)),
        ("logistic_regression", LogisticRegression(max_iter=1000, random_state=42)),
    ]:
        model.fit(X_train, y_train)
        y_prob = model.predict_proba(X_test)[:, 1]
        y_pred = model.predict(X_test)

        auc = roc_auc_score(y_test, y_prob)
        ap = average_precision_score(y_test, y_prob)
        f1 = f1_score(y_test, y_pred)
        ba = balanced_accuracy_score(y_test, y_pred)

        results[model_name] = {
            "auc_roc": round(auc, 4),
            "average_precision": round(ap, 4),
            "f1": round(f1, 4),
            "balanced_accuracy": round(ba, 4),
        }
        print(f"  {model_name:25s} | AUC={auc:.4f} AP={ap:.4f} F1={f1:.4f} BA={ba:.4f}")

    return results


def main() -> None:
    print("=" * 70)
    print("H24 MVP — Benford Digit Forensics on scRNA-seq UMI Counts")
    print("=" * 70)
    t0 = time.time()

    # 1. Load data
    mtx_dir = _download_pbmc3k()
    real_matrix = _load_count_matrix(mtx_dir)
    n_cells, n_genes = real_matrix.shape
    nonzero_frac = (real_matrix > 0).mean()
    print(f"\nLoaded: {n_cells} cells × {n_genes} genes")
    print(f"Nonzero fraction: {nonzero_frac:.4f}")
    print(f"Value range: [{real_matrix.min()}, {real_matrix.max()}]")
    print(f"Median nonzero: {np.median(real_matrix[real_matrix > 0])}")

    # 2. Extract Benford features for real data
    print("\nExtracting Benford features for real data...")
    t_feat = time.time()
    real_features = extract_features_per_sample(real_matrix)
    print(f"  Features shape: {real_features.shape} ({time.time() - t_feat:.1f}s)")

    # 3. For each fabrication method: generate fake, extract features, classify
    all_results = []
    fake_features_cache: dict[str, np.ndarray] = {}
    rng = np.random.default_rng(2026)

    for method_name, fabricate_fn in FABRICATION_METHODS.items():
        print(f"\n--- Fabrication method: {method_name} ---")
        t_fab = time.time()
        fake_matrix = fabricate_fn(real_matrix, rng=rng)
        print(f"  Generated fake matrix: {fake_matrix.shape} ({time.time() - t_fab:.1f}s)")

        t_feat = time.time()
        fake_features = extract_features_per_sample(fake_matrix)
        fake_features_cache[method_name] = fake_features
        print(f"  Extracted features: {fake_features.shape} ({time.time() - t_feat:.1f}s)")

        result = _run_classification(real_features, fake_features, method_name)
        all_results.append(result)

    # 4. Summary and kill criterion
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    all_aucs = []
    for result in all_results:
        for model_name in ["random_forest", "logistic_regression"]:
            auc = result[model_name]["auc_roc"]
            all_aucs.append(auc)
            status = (
                "PASS" if auc >= KILL_THRESHOLD else ("WEAK" if auc >= REJECT_THRESHOLD else "FAIL")
            )
            print(f"  {result['method']:12s} | {model_name:25s} | AUC={auc:.4f} | {status}")

    best_auc = max(all_aucs)
    worst_auc = min(all_aucs)

    print(f"\nBest AUC:  {best_auc:.4f}")
    print(f"Worst AUC: {worst_auc:.4f}")

    if worst_auc >= KILL_THRESHOLD:
        verdict = "STRONG_SIGNAL — all methods detected at AUC >= 0.80. Proceed to paper."
    elif best_auc >= KILL_THRESHOLD:
        verdict = (
            "PARTIAL_SIGNAL — some methods detected. Investigate which fabrications are harder."
        )
    elif best_auc >= REJECT_THRESHOLD:
        verdict = "WEAK_SIGNAL — marginal detection. Hypothesis weakened but not killed."
    else:
        verdict = "REJECT — AUC < 0.65 for all methods. Kill H24."

    print(f"\nVERDICT: {verdict}")
    elapsed = time.time() - t0
    print(f"Total time: {elapsed:.1f}s")

    # 5. Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "experiment": "H24_benford_scrna",
        "dataset": "PBMC3k_10x",
        "n_cells": n_cells,
        "n_genes": n_genes,
        "nonzero_fraction": round(float(nonzero_frac), 4),
        "feature_count": 21,
        "kill_threshold": KILL_THRESHOLD,
        "reject_threshold": REJECT_THRESHOLD,
        "best_auc": round(best_auc, 4),
        "worst_auc": round(worst_auc, 4),
        "verdict": verdict,
        "elapsed_seconds": round(elapsed, 1),
        "results": all_results,
    }
    results_path = RESULTS_DIR / "h24_results.json"
    results_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nResults saved: {results_path}")

    # 6. Try to plot ROC curves (reuse cached features to avoid recomputation)
    try:
        _plot_summary(real_features, fake_features_cache)
    except Exception as exc:
        print(f"Plotting skipped: {exc}")


def _plot_summary(
    real_features: np.ndarray,
    fake_features_cache: dict[str, np.ndarray],
) -> None:
    """Generate summary plots if matplotlib is available.

    Uses pre-computed fake features to avoid redundant feature extraction.
    """
    import matplotlib.pyplot as plt
    from sklearn.metrics import RocCurveDisplay

    fig, axes = plt.subplots(1, len(fake_features_cache), figsize=(5 * len(fake_features_cache), 5))
    if len(fake_features_cache) == 1:
        axes = [axes]

    for idx, (method_name, fake_features) in enumerate(fake_features_cache.items()):
        X = np.vstack([real_features, fake_features])
        y = np.concatenate([np.zeros(len(real_features)), np.ones(len(fake_features))])
        splitter = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        train_idx, test_idx = next(splitter.split(X, y))

        rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        rf.fit(X[train_idx], y[train_idx])
        RocCurveDisplay.from_estimator(rf, X[test_idx], y[test_idx], ax=axes[idx], name="RF")
        axes[idx].set_title(f"{method_name}")
        axes[idx].plot([0, 1], [0, 1], "k--", alpha=0.3)

    plt.tight_layout()
    plot_path = RESULTS_DIR / "h24_roc_curves.png"
    plt.savefig(plot_path, dpi=150)
    print(f"ROC plot saved: {plot_path}")
    plt.close()


if __name__ == "__main__":
    main()
