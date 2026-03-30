"""H27 — Behavioral P-value Analysis on Clinical Trials.

Transfer H23 behavioral sequence analysis from psychology papers to
registered clinical trials on ClinicalTrials.gov.

Pipeline:
  1. Fetch completed trials with posted results via API v2
  2. Extract p-values from structured outcome analyses
  3. Compute 18 behavioral features + 4 trial metadata features
  4. Track A: IsolationForest unsupervised anomaly detection
  5. Track B: Supervised (withdrawn/terminated vs completed) if enough labels
  6. Report ranked anomalous trials + metrics

Usage:
    python experiments/h27_clinical_trials/run_h27.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import roc_auc_score, average_precision_score, f1_score
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "h23_phacking_behavioral"))

from clinicaltrials_api import (
    extract_pvalues_from_trial,
    extract_trial_metadata,
    search_trials_with_results,
)

RESULTS_DIR = Path(__file__).resolve().parent / "results"
DATA_DIR = Path(__file__).resolve().parent / "data"
MIN_PVALUES = 3


def extract_behavioral_features(p_values: list[float]) -> np.ndarray:
    """Extract 18 behavioral features from a p-value sequence.

    Reimplemented here to avoid fragile cross-experiment imports.
    Matches run_h23_extract.py:extract_behavioral_features_from_pvalues.
    """
    n = len(p_values)
    if n == 0:
        return np.zeros(18)

    p = np.clip(np.array(p_values), 1e-15, 1.0)
    features: list[float] = []

    # 1-3: Basic stats
    features.append(float(np.mean(p)))
    features.append(float(np.std(p)) if n > 1 else 0.0)
    features.append(float(np.min(p)))

    # 4-6: Threshold clustering
    features.append(float((p < 0.05).sum() / n))
    features.append(float(((p > 0.04) & (p < 0.05)).sum() / n))
    features.append(float(((p > 0.01) & (p < 0.05)).sum() / n))

    # 7-9: Sequence dynamics
    if n > 1:
        diffs = np.diff(p)
        features.append(float(np.mean(diffs)))
        features.append(float(np.std(diffs)))
        features.append(float((diffs < 0).sum() / len(diffs)))
    else:
        features.extend([0.0, 0.0, 0.0])

    # 10-12: Terminal behavior
    features.append(float(p[-1]))
    features.append(1.0 if p[-1] < 0.05 else 0.0)
    features.append(float(p[-1] - p[0]) if n > 1 else 0.0)

    # 13-15: Entropy and volume
    hist, _ = np.histogram(p, bins=10, range=(0, 1))
    hist_norm = hist / max(hist.sum(), 1)
    entropy = -np.sum(hist_norm[hist_norm > 0] * np.log2(hist_norm[hist_norm > 0]))
    features.append(float(entropy))
    features.append(float(n))
    features.append(float(np.log1p(n)))

    # 16-18: Patterns
    features.append(
        float(np.sum(np.abs(np.diff(np.sign(np.diff(p)))) > 0) / max(n - 2, 1)) if n > 2 else 0.0
    )
    features.append(float(np.max(np.abs(np.diff(p)))) if n > 1 else 0.0)
    features.append(float(np.corrcoef(np.arange(n), p)[0, 1]) if n > 2 else 0.0)

    return np.array(features[:18])


def main() -> None:
    # WHY: ~21% of trials have 3+ structured p-values, so fetch more to get enough
    max_trials = 1000
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg.lstrip("-").startswith("max"):
            if i < len(sys.argv) - 1:
                max_trials = int(sys.argv[i + 1])
            break
        else:
            try:
                max_trials = int(arg)
                break
            except ValueError:
                pass

    print("=" * 70)
    print(f"H27 — Behavioral P-value Analysis on {max_trials} Clinical Trials")
    print("=" * 70)
    t0 = time.time()

    # Step 1: Fetch trials
    print("\n[1/5] Fetching completed trials with results...")
    studies = search_trials_with_results(max_results=max_trials)
    print(f"  Fetched {len(studies)} studies")

    if not studies:
        print("  ERROR: No studies returned from API. Check network connectivity.")
        return

    # Step 2: Extract p-values and metadata
    print("\n[2/5] Extracting p-values and metadata...")
    trial_data: list[dict] = []

    for idx, study in enumerate(studies):
        p_values = extract_pvalues_from_trial(study)
        metadata = extract_trial_metadata(study)

        if len(p_values) >= MIN_PVALUES:
            trial_data.append(
                {
                    "nct_id": metadata["nct_id"],
                    "title": metadata["title"],
                    "status": metadata["status"],
                    "p_values": p_values,
                    "n_pvalues": len(p_values),
                    "metadata": metadata,
                }
            )

        if (idx + 1) % 100 == 0:
            print(
                f"    Processed {idx + 1}/{len(studies)} studies, {len(trial_data)} with {MIN_PVALUES}+ p-values"
            )

    print(f"  Trials with {MIN_PVALUES}+ p-values: {len(trial_data)}")

    if len(trial_data) < 10:
        print("  WARNING: Too few trials with p-values. Results may be unreliable.")
    if len(trial_data) == 0:
        print("  ERROR: No trials with enough p-values. Exiting.")
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        (RESULTS_DIR / "h27_results.json").write_text(
            json.dumps(
                {
                    "experiment": "H27_clinical_trials",
                    "error": "no trials with p-values",
                    "n_fetched": len(studies),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return

    # Cache data
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = DATA_DIR / "trials_cache.json"
    cache_path.write_text(json.dumps(trial_data, indent=2, default=str), encoding="utf-8")
    print(f"  Cached to {cache_path}")

    # Step 3: Extract features
    print("\n[3/5] Extracting behavioral features...")
    features_list = []
    for trial in trial_data:
        behavioral = extract_behavioral_features(trial["p_values"])
        meta = trial["metadata"]
        meta_features = np.array(
            [
                meta["n_outcome_measures"],
                meta["n_primary_outcomes"],
                meta["frac_primary_significant"],
                meta["n_enrolled"],
            ],
            dtype=np.float64,
        )
        combined = np.concatenate([behavioral, meta_features])
        features_list.append(combined)

    X = np.array(features_list)
    X = np.nan_to_num(X, nan=0.0, posinf=10.0, neginf=-10.0)
    print(f"  Feature matrix: {X.shape}")

    # Step 4: Unsupervised anomaly detection
    print("\n[4/5] Running unsupervised anomaly detection (IsolationForest)...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    iso = IsolationForest(n_estimators=200, contamination=0.10, random_state=42, n_jobs=-1)
    iso.fit(X_scaled)
    anomaly_scores = iso.decision_function(X_scaled)
    anomaly_labels = iso.predict(X_scaled)

    n_flagged = int((anomaly_labels == -1).sum())
    print(
        f"  Flagged as anomalous: {n_flagged}/{len(trial_data)} ({n_flagged / len(trial_data):.1%})"
    )

    # Rank by anomaly score (lower = more anomalous)
    ranked_idx = np.argsort(anomaly_scores)
    top20 = []
    for rank, idx in enumerate(ranked_idx[:20]):
        trial = trial_data[idx]
        top20.append(
            {
                "rank": rank + 1,
                "nct_id": trial["nct_id"],
                "title": trial["title"][:80],
                "status": trial["status"],
                "n_pvalues": trial["n_pvalues"],
                "anomaly_score": round(float(anomaly_scores[idx]), 4),
                "frac_significant": round(float((np.array(trial["p_values"]) < 0.05).mean()), 3),
            }
        )
        print(
            f"    #{rank + 1}: {trial['nct_id']} | score={anomaly_scores[idx]:.4f} | {trial['title'][:50]}..."
        )

    # Step 5: Supervised (if labels available)
    print("\n[5/5] Attempting supervised analysis (withdrawn/terminated vs completed)...")
    supervised_results = None

    # Try to get withdrawn/terminated trials as "suspicious" class
    statuses = [t["status"] for t in trial_data]
    y = np.array([1 if s in ("WITHDRAWN", "TERMINATED", "SUSPENDED") else 0 for s in statuses])

    n_pos = int(y.sum())
    n_neg = int((y == 0).sum())
    print(f"  Labels: {n_pos} withdrawn/terminated, {n_neg} completed")

    if n_pos >= 20 and n_neg >= 20:
        splitter = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        train_idx, test_idx = next(splitter.split(X_scaled, y))

        rf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
        rf.fit(X_scaled[train_idx], y[train_idx])
        y_prob = rf.predict_proba(X_scaled[test_idx])[:, 1]
        y_pred = rf.predict(X_scaled[test_idx])

        auc = roc_auc_score(y[test_idx], y_prob)
        ap = average_precision_score(y[test_idx], y_prob)
        f1 = f1_score(y[test_idx], y_pred)

        print(f"  RF AUC={auc:.4f}  AP={ap:.4f}  F1={f1:.4f}")

        # Feature importance
        feat_names = [
            "mean_p",
            "std_p",
            "min_p",
            "frac_sig",
            "frac_just_below_05",
            "frac_01_05",
            "mean_diff",
            "std_diff",
            "frac_decreasing",
            "last_p",
            "last_sig",
            "last_minus_first",
            "entropy",
            "n_pvalues",
            "log_n",
            "reversals",
            "max_jump",
            "correlation",
            "n_outcomes",
            "n_primary",
            "frac_primary_sig",
            "n_enrolled",
        ]
        importances = rf.feature_importances_
        feat_ranking = sorted(
            [
                {"feature": feat_names[i], "importance": round(float(importances[i]), 4)}
                for i in range(len(feat_names))
            ],
            key=lambda x: x["importance"],
            reverse=True,
        )

        supervised_results = {
            "n_positive": n_pos,
            "n_negative": n_neg,
            "rf_auc": round(auc, 4),
            "rf_ap": round(ap, 4),
            "rf_f1": round(f1, 4),
            "feature_ranking": feat_ranking[:10],
        }
    else:
        print("  Skipping supervised — not enough labels per class")

    # Summary stats
    all_pvalues = [p for t in trial_data for p in t["p_values"]]
    elapsed = time.time() - t0

    # Verdict
    if supervised_results and supervised_results["rf_auc"] >= 0.70:
        verdict = f"POSITIVE — behavioral features discriminate withdrawn trials (AUC={supervised_results['rf_auc']:.3f})"
    elif n_flagged > 0:
        verdict = f"SCREENING — {n_flagged} trials flagged as anomalous by IsolationForest ({n_flagged / len(trial_data):.1%})"
    else:
        verdict = "NEUTRAL — no clear anomalous patterns detected"

    print(f"\n{'=' * 70}")
    print(f"VERDICT: {verdict}")
    print(f"Total time: {elapsed:.1f}s")

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "experiment": "H27_clinical_trials",
        "n_trials_fetched": len(studies),
        "n_trials_with_pvalues": len(trial_data),
        "min_pvalues": MIN_PVALUES,
        "median_pvalues_per_trial": round(float(np.median([t["n_pvalues"] for t in trial_data])), 1)
        if trial_data
        else 0,
        "mean_frac_significant": round(
            float(np.mean([(np.array(t["p_values"]) < 0.05).mean() for t in trial_data])), 4
        )
        if trial_data
        else 0,
        "mean_frac_just_below_05": round(
            float(
                np.mean(
                    [
                        ((np.array(t["p_values"]) > 0.04) & (np.array(t["p_values"]) < 0.05)).mean()
                        for t in trial_data
                    ]
                )
            ),
            4,
        )
        if trial_data
        else 0,
        "unsupervised": {
            "method": "IsolationForest",
            "contamination": 0.10,
            "n_flagged": n_flagged,
            "frac_flagged": round(n_flagged / max(len(trial_data), 1), 4),
            "top20_anomalous": top20,
        },
        "supervised": supervised_results,
        "verdict": verdict,
        "elapsed_s": round(elapsed, 1),
    }

    out_path = RESULTS_DIR / "h27_results.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Results saved: {out_path}")


if __name__ == "__main__":
    main()
