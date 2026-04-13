"""H31 — Unified Anomaly Score (UAS).

Combines signals from H23-H30 experiments into a single anomaly score
for scientific dataset screening.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.model_selection import cross_val_score

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "experiments"
H31_DIR = Path(__file__).resolve().parent

# Signal weights (initial hypothesis)
DEFAULT_WEIGHTS = {
    "benford": 0.15,
    "ae_reconstruction": 0.15,
    "behavioral": 0.15,
    "syndrome": 0.20,
    "pvalue_cluster": 0.10,
    "metadata": 0.10,
    "cross_dataset": 0.15,
}


def load_json_results(path: Path) -> dict[str, Any] | None:
    """Load experiment results JSON."""
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def collect_signal_h24() -> dict[str, float]:
    """H24: Benford digit deviation score (1 - Benford_compliance)."""
    results = load_json_results(RESULTS_DIR / "h24_benford_scrna" / "results" / "h24_results.json")
    if not results:
        return {}
    
    signals = {}
    for sample in results.get("samples", []):
        name = sample.get("sample_name", sample.get("name", ""))
        # Use test_auc or separation as proxy for anomaly
        auc = sample.get("test_auc", sample.get("auc", 0.5))
        # Higher AUC = better detection = higher anomaly score
        signals[name] = max(0.0, min(1.0, auc))
    return signals


def collect_signal_h25() -> dict[str, float]:
    """H25: Autoencoder reconstruction error."""
    results = load_json_results(RESULTS_DIR / "h25_banking_ae_lcms" / "results" / "h25_results.json")
    if not results:
        return {}
    
    signals = {}
    for sample in results.get("samples", []):
        name = sample.get("sample_name", sample.get("name", ""))
        # Reconstruction error normalized
        error = sample.get("reconstruction_error", sample.get("ae_error", 0.5))
        signals[name] = max(0.0, min(1.0, error))
    return signals


def collect_signal_h23() -> dict[str, float]:
    """H23: Behavioral p-hacking detection."""
    results = load_json_results(RESULTS_DIR / "h23_phacking_behavioral" / "results" / "h23_results.json")
    if not results:
        return {}
    
    signals = {}
    for sample in results.get("results", []):
        name = sample.get("name", sample.get("paper_id", ""))
        # Classification score
        score = sample.get("auc", sample.get("score", 0.5))
        signals[name] = max(0.0, min(1.0, score))
    return signals


def collect_signal_h29() -> dict[str, float]:
    """H29: Syndrome violation scores per sample."""
    results = load_json_results(H31_DIR.parent / "h29_biological_syndromes" / "results" / "h29_results.json")
    if not results:
        return {}
    
    signals = {}
    for sample in results.get("results", []):
        label = sample.get("label", "")
        score = sample.get("global_anomaly_score", sample.get("syndrome_score", 0.5))
        if label:
            signals[f"h29_{label}"] = max(0.0, min(1.0, score))
    return signals


def collect_signal_h30() -> dict[str, float]:
    """H30: Retracted data syndrome scores (ground truth for validation)."""
    results = load_json_results(H31_DIR.parent / "h30_retracted_validation" / "results" / "h30_retracted_syndrome.json")
    if not results:
        return {}
    
    signals = {}
    for sample in results.get("results", []):
        dataset = sample.get("dataset", "")
        score = sample.get("syndrome", sample.get("syndrome_score", 0.5))
        if dataset:
            signals[dataset] = max(0.0, min(1.0, score))
    return signals


def normalize_signals(signal_matrix: np.ndarray) -> np.ndarray:
    """Min-max normalize each column to [0, 1]."""
    normalized = np.zeros_like(signal_matrix)
    for col in range(signal_matrix.shape[1]):
        col_data = signal_matrix[:, col]
        col_min = col_data.min()
        col_max = col_data.max()
        if col_max - col_min > 1e-10:
            normalized[:, col] = (col_data - col_min) / (col_max - col_min)
        else:
            normalized[:, col] = 0.5  # Constant signal → neutral
    return normalized


def compute_uas_weighted(signal_matrix: np.ndarray, weights: dict[str, float]) -> np.ndarray:
    """Compute weighted UAS from normalized signal matrix."""
    weight_array = np.array([weights.get(f"signal_{i}", 1.0/7) for i in range(signal_matrix.shape[1])])
    weight_array /= weight_array.sum()  # Normalize weights
    return signal_matrix @ weight_array


def compute_uas_stacking(
    X: np.ndarray,
    y: np.ndarray,
    n_splits: int = 3,
) -> dict[str, float]:
    """Train stacking ensemble and return CV metrics."""
    n_positive = y.sum()
    n_negative = len(y) - n_positive
    max_splits = min(int(n_positive), int(n_negative), 5)
    if max_splits < 2:
        return {"status": "insufficient_data_for_cv"}
    
    clf = GradientBoostingClassifier(n_estimators=50, max_depth=2, random_state=42)
    
    aucs = cross_val_score(clf, X, y, cv=max_splits, scoring="roc_auc")
    aps = cross_val_score(clf, X, y, cv=max_splits, scoring="average_precision")
    
    # Train final model on all data
    clf.fit(X, y)
    feature_importance = clf.feature_importances_
    
    return {
        "mean_auc": float(np.mean(aucs)),
        "std_auc": float(np.std(aucs)),
        "mean_ap": float(np.mean(aps)),
        "std_ap": float(np.std(aps)),
        "n_splits": max_splits,
        "feature_importance": feature_importance.tolist(),
    }


def run_experiment() -> dict[str, Any]:
    """Run H31 unified anomaly score experiment."""
    print("=" * 60)
    print("H31: Unified Anomaly Score (UAS)")
    print("=" * 60)
    
    # 1. Collect signals
    print("\n[1/5] Collecting signals from experiments...")
    signals_h24 = collect_signal_h24()
    signals_h25 = collect_signal_h25()
    signals_h23 = collect_signal_h23()
    signals_h29 = collect_signal_h29()
    signals_h30 = collect_signal_h30()
    
    all_datasets = set()
    for sigs in [signals_h24, signals_h25, signals_h23, signals_h29, signals_h30]:
        all_datasets.update(sigs.keys())
    
    all_datasets = sorted(all_datasets)
    print(f"  Found {len(all_datasets)} datasets across experiments")
    print(f"    H24: {len(signals_h24)} signals")
    print(f"    H25: {len(signals_h25)} signals")
    print(f"    H23: {len(signals_h23)} signals")
    print(f"    H29: {len(signals_h29)} signals")
    print(f"    H30: {len(signals_h30)} signals")
    
    # 2. Build signal matrix
    print("\n[2/5] Building signal matrix...")
    signal_names = ["h24_benford", "h25_ae", "h23_behavioral", "h29_syndrome", "h30_retracted"]
    signal_dicts = [signals_h24, signals_h25, signals_h23, signals_h29, signals_h30]
    
    signal_matrix = np.array([
        [sig_dict.get(ds, 0.5) for sig_dict in signal_dicts]
        for ds in all_datasets
    ])
    
    print(f"  Signal matrix shape: {signal_matrix.shape}")
    
    # 3. Normalize
    print("\n[3/5] Normalizing signals to [0, 1]...")
    normalized_matrix = normalize_signals(signal_matrix)
    
    # 4. Compute weighted UAS
    print("\n[4/5] Computing weighted UAS...")
    weights = {
        "signal_0": 0.15,  # H24 Benford
        "signal_1": 0.15,  # H25 AE
        "signal_2": 0.15,  # H23 Behavioral
        "signal_3": 0.20,  # H29 Syndrome
        "signal_4": 0.15,  # H30 Retracted
        "signal_5": 0.10,  # Reserved
        "signal_6": 0.10,  # Reserved
    }
    
    uas_scores = compute_uas_weighted(normalized_matrix, weights)
    
    # 5. Validation on H29 synthetic (fabricated = positive, real = negative)
    print("\n[5/5] Validating on H29 synthetic fabrication...")
    
    # H29 labels: fab_* = positive, real = negative
    h29_positive = {k for k in all_datasets if k.startswith("h29_fab")}
    h29_negative = {k for k in all_datasets if k.startswith("h29_real")}
    
    y_h29 = np.array([1.0 if ds in h29_positive else (0.0 if ds in h29_negative else -1.0) for ds in all_datasets])
    
    # Filter out unknown labels
    valid_mask = y_h29 >= 0
    y_valid = y_h29[valid_mask]
    uas_valid = uas_scores[valid_mask]
    
    validation_results: dict[str, float] = {}
    
    if y_valid.sum() > 0 and (1 - y_valid).sum() > 0:
        # Weighted UAS validation
        weighted_auc = roc_auc_score(y_valid, uas_valid)
        weighted_ap = average_precision_score(y_valid, uas_valid)
        validation_results["weighted_auc"] = weighted_auc
        validation_results["weighted_ap"] = weighted_ap
        print(f"  Weighted UAS — AUC: {weighted_auc:.3f}, AP: {weighted_ap:.3f}")
        
        # Also validate H30 separately
        h30_datasets = set(signals_h30.keys())
        if len(h30_datasets) > 0:
            h30_mask = np.array([ds in h30_datasets for ds in all_datasets])
            if h30_mask.sum() > 0 and (~h30_mask).sum() > 0:
                y_h30 = h30_mask.astype(float)
                h30_auc = roc_auc_score(y_h30, uas_scores)
                validation_results["h30_retracted_auc"] = h30_auc
                print(f"  H30 retracted detection — AUC: {h30_auc:.3f}")
        
        # Stacking ensemble
        if normalized_matrix.shape[0] >= 5 and valid_mask.sum() >= 4:
            n_pos = int(y_valid.sum())
            n_neg = int((1 - y_valid).sum())
            max_splits = min(n_pos, n_neg, 3)
            if max_splits >= 2:
                stacking_results = compute_uas_stacking(normalized_matrix[valid_mask], y_valid.astype(int), n_splits=max_splits)
                validation_results["stacking"] = stacking_results
                print(f"  Stacking — AUC: {stacking_results.get('mean_auc', 'N/A'):.3f}")
    else:
        print("  WARNING: Insufficient ground truth for validation")
        validation_results["status"] = "insufficient_ground_truth"
    
    # Build per-dataset report
    dataset_reports = []
    for i, ds_name in enumerate(all_datasets):
        is_positive = bool(y_h29[i] == 1.0) if i < len(y_h29) else False
        report = {
            "dataset": ds_name,
            "uas_score": float(uas_scores[i]),
            "signals": {
                signal_names[j]: float(normalized_matrix[i, j])
                for j in range(len(signal_names))
            },
            "is_fabricated": is_positive,
            "is_retracted": ds_name in set(signals_h30.keys()),
        }
        dataset_reports.append(report)
    
    # Sort by UAS score descending
    dataset_reports.sort(key=lambda x: x["uas_score"], reverse=True)
    
    # Summary
    summary = {
        "n_datasets": len(all_datasets),
        "n_signals": len(signal_names),
        "mean_uas": float(np.mean(uas_scores)),
        "std_uas": float(np.std(uas_scores)),
        "max_uas": float(np.max(uas_scores)),
        "min_uas": float(np.min(uas_scores)),
        "n_fabricated": int((y_h29 == 1.0).sum()) if len(y_h29) > 0 else 0,
        "n_retracted": len(signals_h30),
        "validation": validation_results,
    }
    
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"  Datasets: {summary['n_datasets']}")
    print(f"  Signals: {summary['n_signals']}")
    print(f"  UAS: {summary['mean_uas']:.3f} ± {summary['std_uas']:.3f}")
    print(f"  Range: [{summary['min_uas']:.3f}, {summary['max_uas']:.3f}]")
    print(f"  Fabricated: {summary['n_fabricated']}")
    print(f"  Retracted: {summary['n_retracted']}")
    
    print(f"\nTop 5 anomalous datasets:")
    for i, report in enumerate(dataset_reports[:5]):
        flags = []
        if report["is_fabricated"]:
            flags.append("⚠️ FABRICATED")
        if report["is_retracted"]:
            flags.append("🚫 RETRACTED")
        flag_str = " ".join(flags)
        print(f"  {i+1}. {report['dataset']}: UAS={report['uas_score']:.3f} {flag_str}")
    
    return {
        "experiment": "H31",
        "description": "Unified Anomaly Score",
        "summary": summary,
        "dataset_reports": dataset_reports,
        "weights": DEFAULT_WEIGHTS,
    }


if __name__ == "__main__":
    results = run_experiment()
    
    # Save results
    out_path = H31_DIR / "results" / "h31_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\nResults saved to: {out_path}")
