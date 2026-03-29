"""H23 Scale-Up — Behavioral features on real statcheck-extracted p-values.

Uses statcheck meta-analyses dataset (OSF n5xba) with extracted p-values from
real published papers. Tests whether behavioral features of p-value reporting
per article predict reporting errors (a proxy for p-hacking/QRP).

Ground truth: statcheck Error flag (reported p != recalculated p) and
DecisionError flag (error that changes significance conclusion).

Usage:
    python experiments/h23_phacking_behavioral/run_h23_statcheck.py
"""

from __future__ import annotations

import csv
import json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

DATA_DIR = Path(__file__).resolve().parent / "data"
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def load_statcheck_data() -> dict[str, list[dict]]:
    """Load and group statcheck results by article (Source)."""
    path = DATA_DIR / "statcheckDataMetaAnalyses_Anonymized.txt"
    articles: dict[str, list[dict]] = defaultdict(list)

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=" ", quotechar='"')
        for row in reader:
            source = row.get("Source", "").strip()
            if not source:
                continue

            try:
                reported_p = float(row.get("Reported.P.Value", "nan"))
                computed_p = float(row.get("Computed", "nan"))
            except (ValueError, TypeError):
                continue

            if np.isnan(reported_p) or np.isnan(computed_p):
                continue

            articles[source].append(
                {
                    "reported_p": reported_p,
                    "computed_p": computed_p,
                    "error": row.get("Error", "FALSE") == "TRUE",
                    "decision_error": row.get("DecisionError", "FALSE") == "TRUE",
                    "statistic": row.get("Statistic", ""),
                    "value": float(row.get("Value", "0") or "0"),
                }
            )

    return dict(articles)


def extract_article_features(tests: list[dict]) -> np.ndarray:
    """Extract behavioral features from all statistical tests in one article.

    Features capture the "behavioral fingerprint" of statistical reporting:
    how many tests, how they cluster near thresholds, reporting inconsistencies.
    """
    n = len(tests)
    reported = np.array([t["reported_p"] for t in tests])
    computed = np.array([t["computed_p"] for t in tests])
    errors = np.array([t["error"] for t in tests])
    discrepancies = np.abs(reported - computed)

    features = []

    # 1-3: P-value distribution stats
    features.append(np.mean(reported))
    features.append(np.std(reported) if n > 1 else 0)
    features.append(np.min(reported))

    # 4-6: Threshold clustering (fraud-style)
    features.append(np.sum(reported < 0.05) / n)  # fraction significant
    features.append(np.sum((reported > 0.04) & (reported < 0.05)) / n)  # fraction just below 0.05
    features.append(np.sum((reported > 0.01) & (reported < 0.05)) / n)  # fraction in 0.01-0.05

    # 7-9: Discrepancy features (reporting quality)
    features.append(np.mean(discrepancies))  # mean p-value discrepancy
    features.append(np.max(discrepancies) if n > 0 else 0)  # max discrepancy
    features.append(np.sum(discrepancies > 0.01) / n)  # fraction with >0.01 discrepancy

    # 10-12: Sequence dynamics (if tests are ordered)
    if n > 1:
        diffs = np.diff(reported)
        features.append(np.mean(diffs))  # trend
        features.append(np.std(diffs))  # volatility
        features.append(np.sum(diffs < 0) / len(diffs))  # fraction decreasing
    else:
        features.extend([0, 0, 0])

    # 13-15: Volume and diversity
    features.append(n)  # number of tests reported
    features.append(np.log1p(n))  # log number of tests
    stat_types = set(t["statistic"] for t in tests)
    features.append(len(stat_types))  # diversity of test types

    # 16-18: Digit patterns (Benford-style)
    sig_digits = []
    for p in reported:
        if 0 < p < 1:
            s = f"{p:.10f}".replace("0.", "").lstrip("0")
            if s:
                sig_digits.append(int(s[0]))
    if sig_digits:
        digit_counts = np.bincount(sig_digits, minlength=10)[1:]  # digits 1-9
        digit_freq = digit_counts / max(digit_counts.sum(), 1)
        features.append(digit_freq[0] if len(digit_freq) > 0 else 0)  # freq of digit 1
        features.append(digit_freq[4] if len(digit_freq) > 4 else 0)  # freq of digit 5
    else:
        features.extend([0, 0])
    features.append(np.mean(reported < 0.001) if n > 0 else 0)  # fraction very significant

    return np.array(features[:18])


FEATURE_NAMES = [
    "mean_p",
    "std_p",
    "min_p",
    "frac_sig",
    "frac_just_below_05",
    "frac_01_05",
    "mean_discrepancy",
    "max_discrepancy",
    "frac_large_discrepancy",
    "trend",
    "volatility",
    "frac_decreasing",
    "n_tests",
    "log_n_tests",
    "stat_diversity",
    "digit_1_freq",
    "digit_5_freq",
    "frac_very_sig",
]


def main() -> None:
    print("=" * 70)
    print("H23 Scale-Up — Statcheck Real P-Values from Meta-Analyses")
    print("=" * 70)
    t0 = time.time()

    articles = load_statcheck_data()
    print(f"\nLoaded {len(articles)} articles with {sum(len(v) for v in articles.values())} tests")

    # Build per-article features and labels
    X_list = []
    y_list = []
    article_names = []

    for source, tests in articles.items():
        if len(tests) < 2:  # Need at least 2 tests for sequence features
            continue

        features = extract_article_features(tests)
        has_error = any(t["error"] for t in tests)
        has_decision_error = any(t["decision_error"] for t in tests)

        X_list.append(features)
        y_list.append(1 if has_error else 0)
        article_names.append(source)

    X = np.array(X_list)
    y = np.array(y_list)
    X = np.nan_to_num(X, nan=0.0, posinf=10.0, neginf=-10.0)

    n_clean = (y == 0).sum()
    n_error = (y == 1).sum()
    print(f"\nArticles with ≥2 tests: {len(y)}")
    print(f"  Clean (no errors): {n_clean} ({n_clean / len(y):.1%})")
    print(f"  Has error: {n_error} ({n_error / len(y):.1%})")

    if n_error < 5 or n_clean < 5:
        print("\nInsufficient class balance for classification. Switching to anomaly scoring.")
        # Use discrepancy features as continuous anomaly score
        mean_disc = X[:, 6]  # mean_discrepancy
        if np.std(mean_disc) > 0:
            auc = roc_auc_score(y, mean_disc)
            print(f"  Mean discrepancy as anomaly score AUC: {auc:.4f}")
        return

    # Baseline: mean p-value alone
    baseline_auc = roc_auc_score(y, -X[:, 0])  # lower mean p → more likely error? inverted
    # Actually: higher discrepancy → more likely error
    disc_auc = roc_auc_score(y, X[:, 6])
    print(f"\n  Baseline (mean_p alone) AUC: {baseline_auc:.4f}")
    print(f"  Baseline (mean_discrepancy) AUC: {disc_auc:.4f}")

    # Cross-validated evaluation
    best_baseline = max(baseline_auc, disc_auc)
    print(f"  Best single-feature baseline AUC: {best_baseline:.4f}")

    n_splits = min(5, min(n_clean, n_error))
    if n_splits < 2:
        print("  Too few samples for CV")
        return

    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    scaler = StandardScaler()

    models = {
        "RF": lambda: RandomForestClassifier(n_estimators=200, max_depth=4, random_state=42),
        "GBM": lambda: GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=42),
        "LR": lambda: LogisticRegression(max_iter=2000, random_state=42),
    }

    all_results = {}
    for model_name, model_factory in models.items():
        fold_aucs = []
        for train_idx, test_idx in cv.split(X, y):
            X_train = scaler.fit_transform(X[train_idx])
            X_test = scaler.transform(X[test_idx])
            model = model_factory()
            model.fit(X_train, y[train_idx])
            y_prob = model.predict_proba(X_test)[:, 1]
            try:
                auc = roc_auc_score(y[test_idx], y_prob)
                fold_aucs.append(auc)
            except ValueError:
                continue

        if fold_aucs:
            mean_auc = np.mean(fold_aucs)
            std_auc = np.std(fold_aucs)
            delta = mean_auc - best_baseline
            print(
                f"  {model_name:5s} AUC: {mean_auc:.4f} ± {std_auc:.4f}  Δ vs baseline: {delta:+.4f}"
            )
            all_results[model_name] = {
                "mean_auc": round(mean_auc, 4),
                "std_auc": round(std_auc, 4),
                "delta": round(delta, 4),
            }

    # Feature importance
    rf_full = RandomForestClassifier(n_estimators=200, max_depth=4, random_state=42)
    rf_full.fit(scaler.fit_transform(X), y)
    importances = rf_full.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]

    print(f"\nTop features:")
    feat_ranking = []
    for rank, idx in enumerate(sorted_idx[:10], 1):
        name = FEATURE_NAMES[idx] if idx < len(FEATURE_NAMES) else f"feat_{idx}"
        print(f"  {rank:2d}. {name:25s} | {importances[idx]:.4f}")
        feat_ranking.append(
            {"rank": rank, "feature": name, "importance": round(float(importances[idx]), 4)}
        )

    best_model = (
        max(all_results.items(), key=lambda x: x[1]["mean_auc"])
        if all_results
        else ("none", {"mean_auc": 0})
    )
    delta = best_model[1]["mean_auc"] - best_baseline if all_results else 0

    if delta > 0.05:
        verdict = (
            f"POSITIVE — {best_model[0]} beats baseline by {delta:+.4f} on real statcheck data"
        )
    elif delta > 0:
        verdict = f"MARGINAL — slight improvement ({delta:+.4f})"
    else:
        verdict = f"NEGATIVE — behavioral features do not improve over single-feature baseline"

    print(f"\nVERDICT: {verdict}")

    elapsed = time.time() - t0
    print(f"Total time: {elapsed:.1f}s")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "experiment": "H23_statcheck_real",
        "n_articles": len(y),
        "n_clean": int(n_clean),
        "n_error": int(n_error),
        "best_baseline_auc": round(best_baseline, 4),
        "results": all_results,
        "verdict": verdict,
        "feature_ranking": feat_ranking,
        "elapsed_s": round(elapsed, 1),
    }
    out_path = RESULTS_DIR / "h23_statcheck_results.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Results saved: {out_path}")


if __name__ == "__main__":
    main()
