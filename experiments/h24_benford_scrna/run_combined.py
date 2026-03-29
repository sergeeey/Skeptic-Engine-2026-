"""Combined H24+H21 — Benford Digits + Isolation Forest on scRNA-seq.

Runs both detection methods on the same PBMC3k data and fabrication methods,
then compares and fuses results. This is the basis for a combined paper.

Usage:
    python experiments/h24_benford_scrna/run_combined.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedShuffleSplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

from digit_features import extract_features_per_sample
from fabrication import FABRICATION_METHODS
from isolation_forest import cell_level_features, score_anomalies, train_isolation_forest
from run_h24 import _download_pbmc3k, _load_count_matrix

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _classify(X: np.ndarray, y: np.ndarray, label: str) -> dict:
    """Train RF+LogReg, return metrics dict."""
    splitter = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(splitter.split(X, y))
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    out: dict = {"label": label}
    for name, model in [
        ("RF", RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)),
        ("LR", LogisticRegression(max_iter=1000, random_state=42)),
    ]:
        model.fit(X_train, y_train)
        y_prob = model.predict_proba(X_test)[:, 1]
        y_pred = model.predict(X_test)
        out[name] = {
            "auc": round(roc_auc_score(y_test, y_prob), 4),
            "ap": round(average_precision_score(y_test, y_prob), 4),
            "f1": round(f1_score(y_test, y_pred), 4),
            "ba": round(balanced_accuracy_score(y_test, y_pred), 4),
        }
    return out


def main() -> None:
    print("=" * 70)
    print("Combined H24+H21 — Benford + Isolation Forest on scRNA-seq")
    print("=" * 70)
    t0 = time.time()

    # Load data
    mtx_dir = _download_pbmc3k()
    real_matrix = _load_count_matrix(mtx_dir)
    n_cells, n_genes = real_matrix.shape
    print(f"Loaded: {n_cells} cells × {n_genes} genes\n")

    # Extract features once for real data
    print("Extracting features for real data...")
    benford_real = extract_features_per_sample(real_matrix)
    cell_real = cell_level_features(real_matrix)
    combined_real = np.hstack([benford_real, cell_real])
    print(f"  Benford: {benford_real.shape[1]} features")
    print(f"  Cell-level: {cell_real.shape[1]} features")
    print(f"  Combined: {combined_real.shape[1]} features")

    # Train IF on real data only
    print("\nTraining Isolation Forest on real cell-level features...")
    if_model = train_isolation_forest(cell_real)
    real_if_scores = score_anomalies(if_model, cell_real)
    print(f"  Real data IF score: mean={real_if_scores.mean():.4f} std={real_if_scores.std():.4f}")

    all_results = []

    for method_name, fabricate_fn in FABRICATION_METHODS.items():
        print(f"\n{'=' * 50}")
        print(f"Fabrication: {method_name}")
        print(f"{'=' * 50}")

        rng = np.random.default_rng(2026)
        fake_matrix = fabricate_fn(real_matrix, rng=rng)

        # Features
        benford_fake = extract_features_per_sample(fake_matrix)
        cell_fake = cell_level_features(fake_matrix)
        combined_fake = np.hstack([benford_fake, cell_fake])

        # IF scores
        fake_if_scores = score_anomalies(if_model, cell_fake)
        print(f"  Fake IF score: mean={fake_if_scores.mean():.4f} std={fake_if_scores.std():.4f}")

        # IF as binary classifier (threshold at 0)
        if_y_true = np.concatenate([np.zeros(n_cells), np.ones(n_cells)])
        if_scores_combined = np.concatenate([real_if_scores, fake_if_scores])
        # Negate scores: lower IF score = more anomalous = more likely fake
        if_auc = roc_auc_score(if_y_true, -if_scores_combined)
        print(f"  IF standalone AUC: {if_auc:.4f}")

        # Labels
        y = np.concatenate([np.zeros(n_cells), np.ones(n_cells)])

        # Method 1: Benford only
        X_benford = np.vstack([benford_real, benford_fake])
        res_benford = _classify(X_benford, y, f"{method_name}_benford")
        print(
            f"\n  Benford only:   RF AUC={res_benford['RF']['auc']:.4f}  LR AUC={res_benford['LR']['auc']:.4f}"
        )

        # Method 2: Cell-level only
        X_cell = np.vstack([cell_real, cell_fake])
        res_cell = _classify(X_cell, y, f"{method_name}_cell_features")
        print(
            f"  Cell-level only: RF AUC={res_cell['RF']['auc']:.4f}  LR AUC={res_cell['LR']['auc']:.4f}"
        )

        # Method 3: IF score as single feature
        X_if = np.concatenate([real_if_scores, fake_if_scores]).reshape(-1, 1)
        res_if = _classify(X_if, y, f"{method_name}_isolation_forest")
        print(
            f"  IF score only:   RF AUC={res_if['RF']['auc']:.4f}  LR AUC={res_if['LR']['auc']:.4f}"
        )

        # Method 4: FUSION (Benford + Cell + IF score)
        if_col = np.concatenate([real_if_scores, fake_if_scores]).reshape(-1, 1)
        X_fusion = np.hstack(
            [
                np.vstack([combined_real, combined_fake]),
                if_col,
            ]
        )
        res_fusion = _classify(X_fusion, y, f"{method_name}_fusion")
        print(
            f"  FUSION (all):    RF AUC={res_fusion['RF']['auc']:.4f}  LR AUC={res_fusion['LR']['auc']:.4f}"
        )

        all_results.append(
            {
                "method": method_name,
                "if_standalone_auc": round(if_auc, 4),
                "benford": res_benford,
                "cell_features": res_cell,
                "isolation_forest": res_if,
                "fusion": res_fusion,
            }
        )

    # Summary table
    print(f"\n{'=' * 70}")
    print("SUMMARY — RF AUC comparison across all approaches")
    print(f"{'=' * 70}")
    print(f"{'Method':<14} {'Benford':>10} {'Cell-Lvl':>10} {'IF-Only':>10} {'FUSION':>10}")
    print("-" * 58)
    for r in all_results:
        print(
            f"{r['method']:<14} "
            f"{r['benford']['RF']['auc']:>10.4f} "
            f"{r['cell_features']['RF']['auc']:>10.4f} "
            f"{r['isolation_forest']['RF']['auc']:>10.4f} "
            f"{r['fusion']['RF']['auc']:>10.4f}"
        )

    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed:.1f}s")

    # Save
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULTS_DIR / "h24_h21_combined.json"
    output_path.write_text(
        json.dumps(
            {
                "experiment": "H24+H21_combined",
                "results": all_results,
                "elapsed_s": round(elapsed, 1),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Results saved: {output_path}")

    # Plot comparison
    try:
        _plot_comparison(all_results)
    except Exception as exc:
        print(f"Plotting skipped: {exc}")


def _plot_comparison(all_results: list[dict]) -> None:
    import matplotlib.pyplot as plt

    methods = [r["method"] for r in all_results]
    approaches = ["benford", "cell_features", "isolation_forest", "fusion"]
    labels = ["Benford", "Cell-Level", "IF-Only", "FUSION"]
    colors = ["#2196F3", "#4CAF50", "#FF9800", "#E91E63"]

    x = np.arange(len(methods))
    width = 0.2

    fig, ax = plt.subplots(figsize=(10, 6))
    for i, (approach, label, color) in enumerate(zip(approaches, labels, colors)):
        aucs = [r[approach]["RF"]["auc"] for r in all_results]
        ax.bar(x + i * width, aucs, width, label=label, color=color, alpha=0.85)

    ax.set_ylabel("AUC-ROC (Random Forest)")
    ax.set_title("H24+H21: Fabrication Detection on scRNA-seq (PBMC3k)")
    ax.set_xticks(x + 1.5 * width)
    ax.set_xticklabels(methods)
    ax.set_ylim(0.5, 1.05)
    ax.axhline(y=0.80, color="red", linestyle="--", alpha=0.5, label="Kill threshold (0.80)")
    ax.legend()
    plt.tight_layout()

    plot_path = RESULTS_DIR / "h24_h21_comparison.png"
    plt.savefig(plot_path, dpi=150)
    print(f"Comparison plot saved: {plot_path}")
    plt.close()


if __name__ == "__main__":
    main()
