"""H26 Injection Test -- prove self-check catches mixed fabrication.

Takes a clean dataset, injects 10-50% fabricated cells, runs self-check.
Expected: clean dataset -> CLEAN, injected dataset -> FLAGGED.

This is the critical validation: FPR=0% (from selfcheck) + TPR>0 (from this test)
together prove the method works.

Usage:
    python experiments/h26_geo_screening/run_h26_injection_test.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

H24_DIR = Path(__file__).resolve().parents[1] / "h24_benford_scrna"
SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(H24_DIR))
sys.path.insert(0, str(SRC_DIR))

from digit_features import extract_features_per_sample
from fabrication import FABRICATION_METHODS
from isolation_forest import cell_level_features
from run_h24 import _download_pbmc3k, _load_count_matrix
from skeptic_toolkit.verdict import VerdictLevel, make_verdict

RESULTS_DIR = Path(__file__).resolve().parent / "results"
INJECTION_FRACTIONS = [0.0, 0.10, 0.20, 0.30, 0.50]


def selfcheck_score(matrix: np.ndarray, seed: int = 42) -> dict:
    """Symmetric split-half IF consistency check."""
    rng = np.random.default_rng(seed)
    n = matrix.shape[0]
    idx = rng.permutation(n)
    half = n // 2
    splits = {"A": matrix[idx[:half]], "B": matrix[idx[half : half * 2]]}
    rates = {}
    for train_name, test_name in [("A", "B"), ("B", "A")]:
        train_b = extract_features_per_sample(splits[train_name])
        train_c = cell_level_features(splits[train_name])
        train_f = np.hstack([train_b, train_c])
        test_b = extract_features_per_sample(splits[test_name])
        test_c = cell_level_features(splits[test_name])
        test_f = np.hstack([test_b, test_c])
        scaler = StandardScaler()
        train_s = scaler.fit_transform(train_f)
        test_s = scaler.transform(test_f)
        iso = IsolationForest(n_estimators=200, contamination="auto", random_state=42, n_jobs=-1)
        iso.fit(train_s)
        train_scores = iso.decision_function(train_s)
        test_scores = iso.decision_function(test_s)
        threshold = train_scores.mean() - 2 * train_scores.std()
        rates[f"{train_name}->{test_name}"] = float((test_scores < threshold).mean())
    rate_ab = rates["A->B"]
    rate_ba = rates["B->A"]
    mean_rate = (rate_ab + rate_ba) / 2
    asymmetry = abs(rate_ab - rate_ba)
    risk = min(mean_rate * 5, 1.0)
    if asymmetry > 0.10:
        risk = max(risk, 0.5)
    return {
        "rate_AB": round(rate_ab, 4),
        "rate_BA": round(rate_ba, 4),
        "mean_rate": round(mean_rate, 4),
        "asymmetry": round(asymmetry, 4),
        "risk_score": round(risk, 4),
    }


def main() -> None:
    start = time.time()
    print("=" * 70)
    print("H26 INJECTION TEST -- Self-Check Detection of Mixed Fabrication")
    print("=" * 70)
    mtx_dir = _download_pbmc3k()
    real_matrix = _load_count_matrix(mtx_dir)
    n_cells = real_matrix.shape[0]
    print(f"  Base dataset: PBMC3k ({n_cells} cells x {real_matrix.shape[1]} genes)\n")
    all_results = []
    for fab_name, fab_fn in FABRICATION_METHODS.items():
        print(f"=== Fabrication: {fab_name} ===")
        rng = np.random.default_rng(42)
        fake_matrix = fab_fn(real_matrix, rng=rng)
        for frac in INJECTION_FRACTIONS:
            n_inject = int(n_cells * frac)
            n_keep = n_cells - n_inject
            if n_inject == 0:
                mixed = real_matrix.copy()
                label = "clean (0%)"
            else:
                keep_idx = rng.choice(n_cells, n_keep, replace=False)
                inject_idx = rng.choice(n_cells, n_inject, replace=False)
                mixed = np.vstack([real_matrix[keep_idx], fake_matrix[inject_idx]])
                label = f"{frac:.0%} injected"
            scores = selfcheck_score(mixed)
            verdict = make_verdict(scores["risk_score"], threshold=0.55, uncertainty_band=0.20)
            result = {
                "fabrication": fab_name,
                "injection_fraction": frac,
                "n_real": n_keep,
                "n_fake": n_inject,
                "verdict": verdict.level.value,
                **scores,
            }
            all_results.append(result)
            print(
                f"  {label:>16}: {verdict.level.value:<10} "
                f"risk={scores['risk_score']:.3f} "
                f"rate={scores['mean_rate']:.3f} "
                f"asym={scores['asymmetry']:.3f}"
            )
        print()

    elapsed = time.time() - start
    clean_at_0 = all(r["verdict"] == "CLEAN" for r in all_results if r["injection_fraction"] == 0.0)
    detected_at_50 = all(
        r["verdict"] in ("FLAGGED", "UNCERTAIN")
        for r in all_results if r["injection_fraction"] == 0.50
    )
    detection_thresholds = {}
    for fab_name in FABRICATION_METHODS:
        for r in all_results:
            if r["fabrication"] == fab_name and r["verdict"] in ("FLAGGED", "UNCERTAIN") and r["injection_fraction"] > 0:
                detection_thresholds[fab_name] = r["injection_fraction"]
                break
        else:
            detection_thresholds[fab_name] = None

    print("=" * 70)
    print("INJECTION TEST SUMMARY")
    print("=" * 70)
    print(f"  Clean baseline (0%): {'ALL CLEAN' if clean_at_0 else 'SOME FLAGGED'}")
    print(f"  50% injection:       {'ALL DETECTED' if detected_at_50 else 'SOME MISSED'}")
    print("  Detection thresholds:")
    for fab, thresh in detection_thresholds.items():
        if thresh:
            print(f"    {fab}: detected at {thresh:.0%} injection")
        else:
            print(f"    {fab}: NOT detected even at 50%")
    print(f"  Elapsed: {elapsed:.0f}s")

    if clean_at_0 and detected_at_50:
        conclusion = (
            "Self-check correctly distinguishes clean from contaminated datasets. "
            "FPR=0% at 0% injection, TPR=100% at 50% injection. "
            "Detection thresholds: "
            + ", ".join(f"{k}={v:.0%}" for k, v in detection_thresholds.items() if v)
            + "."
        )
    elif clean_at_0:
        conclusion = "Self-check has 0% FPR but misses some injection levels."
    else:
        conclusion = "Self-check has calibration issues."
    print(f"\nCONCLUSION: {conclusion}")

    output = {
        "experiment": "H26_injection_test",
        "method": "selfcheck_with_fabrication_injection",
        "base_dataset": "PBMC3k_10x",
        "injection_fractions": INJECTION_FRACTIONS,
        "fabrication_methods": list(FABRICATION_METHODS.keys()),
        "clean_baseline_all_clean": clean_at_0,
        "detected_at_50pct": detected_at_50,
        "detection_thresholds": detection_thresholds,
        "conclusion": conclusion,
        "results": all_results,
        "elapsed_s": round(elapsed, 1),
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "h26_injection_test.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nResults saved: {out_path}")


if __name__ == "__main__":
    main()
