"""H23 Real Data Validation — Behavioral features on Reproducibility Project data.

Uses the Open Science Collaboration (2015) Reproducibility Project: Psychology dataset
(168 studies, each with original p-value and replication outcome).

Key question: can behavioral features of the ORIGINAL study's p-value and effect size
predict whether the study will FAIL to replicate?

Usage:
    python experiments/h23_phacking_behavioral/run_h23_real.py
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, classification_report
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

DATA_DIR = Path(__file__).resolve().parent / "data"
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _safe_float(val: str) -> float | None:
    """Parse float, return None on failure."""
    try:
        v = val.strip().replace(",", ".")
        if v in ("", "NA", "na", "N/A", "--"):
            return None
        return float(v)
    except (ValueError, TypeError):
        return None


def load_rpp_data() -> list[dict]:
    """Load RPP dataset, extract relevant features per study."""
    path = DATA_DIR / "rpp_data.csv"
    with open(path, "r", encoding="latin-1") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    studies = []
    for row in rows:
        # Original study p-value
        p_orig = _safe_float(row.get("T_pval_USE..O.", ""))
        # Replication outcome
        replicated = row.get("Replicate (R)", "").strip().lower()
        # Effect sizes
        p_repl = _safe_float(row.get("T_pval_USE..R.", ""))
        power_orig = _safe_float(row.get("Actual Power (O)", ""))
        power_repl = _safe_float(row.get("Power (R)", ""))

        if p_orig is None or replicated not in ("yes", "no"):
            continue

        # Extract study-level features (what a fraud detector would see from the original paper)
        features = {}
        features["p_original"] = p_orig
        features["p_original_log"] = np.log10(max(p_orig, 1e-15))
        features["p_is_borderline"] = 1.0 if 0.04 < p_orig < 0.05 else 0.0
        features["p_is_very_sig"] = 1.0 if p_orig < 0.001 else 0.0
        features["p_is_marginal"] = 1.0 if 0.01 < p_orig < 0.05 else 0.0

        # Power features (if reported)
        features["power_original"] = power_orig if power_orig is not None else 0.5
        features["power_deficit"] = 0.80 - (power_orig or 0.5)  # how far below 80% power

        # P-value suspiciousness indicators
        features["p_round_05"] = 1.0 if abs(p_orig - 0.05) < 0.005 else 0.0
        features["p_round_01"] = 1.0 if abs(p_orig - 0.01) < 0.005 else 0.0
        features["p_just_below_threshold"] = 1.0 if 0.04 <= p_orig < 0.05 else 0.0

        # Digit extraction (safe)
        sig_digits = str(f"{p_orig:.10f}").replace("0.", "").lstrip("0")
        features["p_digit_1"] = int(sig_digits[0]) if len(sig_digits) > 0 and p_orig > 0 else 0
        features["p_second_digit"] = int(sig_digits[1]) if len(sig_digits) > 1 and p_orig > 0 else 0

        # Replication label: 0 = replicated, 1 = failed to replicate
        label = 0 if replicated == "yes" else 1

        studies.append(
            {
                "features": features,
                "label": label,
                "p_orig": p_orig,
                "replicated": replicated,
            }
        )

    return studies


def main() -> None:
    print("=" * 70)
    print("H23 Real Data — Replication Failure Prediction from Original P-Values")
    print("=" * 70)
    t0 = time.time()

    studies = load_rpp_data()
    print(f"\nLoaded {len(studies)} studies with complete data")

    labels = [s["label"] for s in studies]
    n_replicated = labels.count(0)
    n_failed = labels.count(1)
    print(f"  Replicated: {n_replicated} ({n_replicated / len(labels):.1%})")
    print(f"  Failed: {n_failed} ({n_failed / len(labels):.1%})")

    # Build feature matrix
    feature_names = list(studies[0]["features"].keys())
    X = np.array([[s["features"][f] for f in feature_names] for s in studies])
    y = np.array(labels)

    # Handle any NaN
    X = np.nan_to_num(X, nan=0.0)

    print(f"  Features: {len(feature_names)}")
    print(f"  Feature names: {feature_names}")

    # ── Baseline: p-value alone ──────────────────────────────────
    # Higher original p-value → more likely to fail replication
    p_values = np.array([s["p_orig"] for s in studies])
    baseline_auc = roc_auc_score(y, p_values)
    print(f"\n  Baseline (p-value alone) AUC: {baseline_auc:.4f}")

    # ── Cross-validated evaluation ───────────────────────────────
    print("\n  5-fold stratified CV results:")

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scaler = StandardScaler()

    models = {
        "RF": lambda: RandomForestClassifier(n_estimators=200, max_depth=5, random_state=42),
        "GBM": lambda: GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=42),
        "LR": lambda: LogisticRegression(max_iter=2000, random_state=42),
    }

    all_results = {}
    for model_name, model_factory in models.items():
        fold_aucs = []
        fold_aps = []
        all_y_true = []
        all_y_prob = []

        for fold, (train_idx, test_idx) in enumerate(cv.split(X, y)):
            X_train = scaler.fit_transform(X[train_idx])
            X_test = scaler.transform(X[test_idx])

            model = model_factory()
            model.fit(X_train, y[train_idx])
            y_prob = model.predict_proba(X_test)[:, 1]

            auc = roc_auc_score(y[test_idx], y_prob)
            ap = average_precision_score(y[test_idx], y_prob)
            fold_aucs.append(auc)
            fold_aps.append(ap)
            all_y_true.extend(y[test_idx])
            all_y_prob.extend(y_prob)

        mean_auc = np.mean(fold_aucs)
        std_auc = np.std(fold_aucs)
        mean_ap = np.mean(fold_aps)

        delta = mean_auc - baseline_auc
        print(
            f"  {model_name:5s} AUC: {mean_auc:.4f} ± {std_auc:.4f}  AP: {mean_ap:.4f}  Δ vs baseline: {delta:+.4f}"
        )

        all_results[model_name] = {
            "mean_auc": round(mean_auc, 4),
            "std_auc": round(std_auc, 4),
            "mean_ap": round(mean_ap, 4),
            "fold_aucs": [round(a, 4) for a in fold_aucs],
            "delta_vs_baseline": round(delta, 4),
        }

    # ── Feature importance (from best model) ─────────────────────
    print("\n  Feature importance (RF on full data):")
    rf_full = RandomForestClassifier(n_estimators=200, max_depth=5, random_state=42)
    rf_full.fit(scaler.fit_transform(X), y)

    importances = rf_full.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]
    for rank, idx in enumerate(sorted_idx[:10], 1):
        print(f"    {rank:2d}. {feature_names[idx]:30s} | {importances[idx]:.4f}")

    # Verdict
    best_model = max(all_results.items(), key=lambda x: x[1]["mean_auc"])
    best_auc = best_model[1]["mean_auc"]
    delta = best_auc - baseline_auc

    if delta > 0.05:
        verdict = f"POSITIVE — {best_model[0]} beats p-value baseline by {delta:+.4f} AUC on REAL replication data"
    elif delta > 0.0:
        verdict = f"MARGINAL — {best_model[0]} slightly improves on baseline ({delta:+.4f})"
    else:
        verdict = f"NEGATIVE — behavioral features do not improve over simple p-value for replication prediction"

    print(f"\n  VERDICT: {verdict}")
    print(f"\n  CAVEAT: n={len(studies)} is small; results should be interpreted with caution")
    print(
        f"  CAVEAT: features are study-level, not sequence-level (no multi-test p-value sequences available)"
    )

    elapsed = time.time() - t0
    print(f"\n  Total time: {elapsed:.1f}s")

    # Save
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "experiment": "H23_real_rpp",
        "n_studies": len(studies),
        "n_replicated": n_replicated,
        "n_failed": n_failed,
        "baseline_pvalue_auc": round(baseline_auc, 4),
        "results": all_results,
        "best_model": best_model[0],
        "best_auc": round(best_auc, 4),
        "delta_vs_baseline": round(delta, 4),
        "verdict": verdict,
        "feature_importance": [
            {"feature": feature_names[idx], "importance": round(float(importances[idx]), 4)}
            for idx in sorted_idx[:10]
        ],
        "elapsed_s": round(elapsed, 1),
    }
    out_path = RESULTS_DIR / "h23_real_rpp_results.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"  Results saved: {out_path}")


if __name__ == "__main__":
    main()
