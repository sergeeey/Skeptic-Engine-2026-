"""Feature importance analysis for H24+H21 fabrication detection.

Uses permutation importance (model-agnostic, no SHAP dependency needed).
Shows which features drive detection for each fabrication type.

Usage:
    python experiments/h24_benford_scrna/run_feature_importance.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.model_selection import StratifiedShuffleSplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

from digit_features import extract_features_per_sample
from fabrication import FABRICATION_METHODS
from isolation_forest import cell_level_features, score_anomalies, train_isolation_forest
from run_h24 import _download_pbmc3k, _load_count_matrix

RESULTS_DIR = Path(__file__).resolve().parent / "results"

FEATURE_NAMES = [
    # Benford first-digit (9)
    "fd_1",
    "fd_2",
    "fd_3",
    "fd_4",
    "fd_5",
    "fd_6",
    "fd_7",
    "fd_8",
    "fd_9",
    # Benford second-digit (10)
    "sd_0",
    "sd_1",
    "sd_2",
    "sd_3",
    "sd_4",
    "sd_5",
    "sd_6",
    "sd_7",
    "sd_8",
    "sd_9",
    # Chi-squared stats (2)
    "chi2_first_digit",
    "chi2_second_digit",
    # Cell-level (8)
    "total_counts",
    "n_genes",
    "frac_zeros",
    "mean_nonzero",
    "var_nonzero",
    "max_count",
    "log1p_total",
    "cv_nonzero",
    # IF score (1)
    "if_anomaly_score",
]


def main() -> None:
    print("=" * 70)
    print("Feature Importance Analysis — H24+H21")
    print("=" * 70)
    t0 = time.time()

    mtx_dir = _download_pbmc3k()
    real_matrix = _load_count_matrix(mtx_dir)
    n_cells = real_matrix.shape[0]
    print(f"Loaded: {n_cells} cells × {real_matrix.shape[1]} genes\n")

    # Extract real features
    benford_real = extract_features_per_sample(real_matrix)
    cell_real = cell_level_features(real_matrix)
    if_model = train_isolation_forest(cell_real)
    if_real = score_anomalies(if_model, cell_real).reshape(-1, 1)
    X_real = np.hstack([benford_real, cell_real, if_real])

    all_results = []

    for method_name, fab_fn in FABRICATION_METHODS.items():
        print(f"\n--- {method_name} ---")
        rng = np.random.default_rng(2026)
        fake_matrix = fab_fn(real_matrix, rng=rng)

        benford_fake = extract_features_per_sample(fake_matrix)
        cell_fake = cell_level_features(fake_matrix)
        if_fake = score_anomalies(if_model, cell_fake).reshape(-1, 1)
        X_fake = np.hstack([benford_fake, cell_fake, if_fake])

        X = np.vstack([X_real, X_fake])
        y = np.concatenate([np.zeros(n_cells), np.ones(n_cells)])

        # Train/test split
        splitter = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        train_idx, test_idx = next(splitter.split(X, y))

        rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        rf.fit(X[train_idx], y[train_idx])

        # Permutation importance on test set
        perm = permutation_importance(
            rf,
            X[test_idx],
            y[test_idx],
            n_repeats=10,
            random_state=42,
            n_jobs=-1,
            scoring="roc_auc",
        )

        # Sort by mean importance
        sorted_idx = np.argsort(perm.importances_mean)[::-1]

        print(f"  Top 10 features (by permutation importance on AUC):")
        feature_ranking = []
        for rank, idx in enumerate(sorted_idx[:10], 1):
            name = FEATURE_NAMES[idx] if idx < len(FEATURE_NAMES) else f"feat_{idx}"
            mean_imp = perm.importances_mean[idx]
            std_imp = perm.importances_std[idx]
            print(f"    {rank:2d}. {name:22s} | importance={mean_imp:.4f} ± {std_imp:.4f}")
            feature_ranking.append(
                {
                    "rank": rank,
                    "feature": name,
                    "importance_mean": round(float(mean_imp), 4),
                    "importance_std": round(float(std_imp), 4),
                }
            )

        # Also get RF native feature importance (Gini)
        gini_idx = np.argsort(rf.feature_importances_)[::-1]
        gini_ranking = []
        print(f"\n  Top 10 features (Gini importance):")
        for rank, idx in enumerate(gini_idx[:10], 1):
            name = FEATURE_NAMES[idx] if idx < len(FEATURE_NAMES) else f"feat_{idx}"
            imp = rf.feature_importances_[idx]
            print(f"    {rank:2d}. {name:22s} | gini={imp:.4f}")
            gini_ranking.append(
                {
                    "rank": rank,
                    "feature": name,
                    "gini_importance": round(float(imp), 4),
                }
            )

        # Feature group contributions
        groups = {
            "benford_first_digit": list(range(0, 9)),
            "benford_second_digit": list(range(9, 19)),
            "benford_chi2": list(range(19, 21)),
            "cell_level": list(range(21, 29)),
            "if_score": [29],
        }
        group_importance = {}
        for group_name, indices in groups.items():
            total = sum(perm.importances_mean[i] for i in indices if i < len(perm.importances_mean))
            group_importance[group_name] = round(float(total), 4)

        print(f"\n  Feature group contributions:")
        for gname, gimp in sorted(group_importance.items(), key=lambda x: -x[1]):
            print(f"    {gname:25s} | {gimp:.4f}")

        all_results.append(
            {
                "method": method_name,
                "permutation_top10": feature_ranking,
                "gini_top10": gini_ranking,
                "group_importance": group_importance,
            }
        )

    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed:.1f}s")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "h24_feature_importance.json"
    out_path.write_text(
        json.dumps({"results": all_results, "elapsed_s": round(elapsed, 1)}, indent=2),
        encoding="utf-8",
    )
    print(f"Results saved: {out_path}")

    # Plot
    try:
        _plot_importance(all_results)
    except Exception as exc:
        print(f"Plot skipped: {exc}")


def _plot_importance(all_results: list[dict]) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    for idx, result in enumerate(all_results):
        ax = axes[idx]
        groups = result["group_importance"]
        names = list(groups.keys())
        values = [groups[n] for n in names]
        colors = ["#2196F3", "#03A9F4", "#00BCD4", "#4CAF50", "#FF9800"]

        bars = ax.barh(names, values, color=colors[: len(names)])
        ax.set_xlabel("Permutation Importance (AUC)")
        ax.set_title(f"{result['method']}")
        ax.invert_yaxis()

    plt.suptitle("Feature Group Importance by Fabrication Type", fontsize=14)
    plt.tight_layout()
    plot_path = RESULTS_DIR / "h24_feature_importance.png"
    plt.savefig(plot_path, dpi=150)
    print(f"Plot saved: {plot_path}")
    plt.close()


if __name__ == "__main__":
    main()
