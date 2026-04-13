"""H36 — Debate-Driven Verdict.

Demonstrates how adversarial debate improves verdict interpretability
compared to raw anomaly scores.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
H36_DIR = Path(__file__).resolve().parent


def run_experiment() -> dict[str, Any]:
    """Run H36 debate experiment on synthetic cases."""
    print("=" * 60)
    print("H36: Debate-Driven Verdict")
    print("=" * 60)

    from skeptic_engine.utils.debate import run_debate

    # Define test cases: Clear Clean, Suspicious, Clear Anomalous, Edge Case
    test_cases = {
        "clear_clean": {
            "benford_mace": 0.02,
            "pvalue_frac_below_05": 0.05,
            "temporal_drift_slope": 0.001,
            "temporal_drift_p": 0.85,
            "cross_modal_corr": 0.75,
            "calibrated_score": 0.12,
            "n_samples": 5000,
        },
        "suspicious": {
            "benford_mace": 0.15,
            "pvalue_frac_below_05": 0.25,
            "temporal_drift_slope": 0.04,
            "temporal_drift_p": 0.005,
            "cross_modal_corr": 0.35,
            "calibrated_score": 0.65,
            "n_samples": 1200,
        },
        "clear_anomalous": {
            "benford_mace": 0.45,
            "pvalue_frac_below_05": 0.65,
            "temporal_drift_slope": 0.12,
            "temporal_drift_p": 0.0001,
            "cross_modal_corr": 0.05,
            "calibrated_score": 0.96,
            "n_samples": 300,
        },
        "edge_case": {
            "benford_mace": 0.08,
            "pvalue_frac_below_05": 0.15,
            "temporal_drift_slope": -0.005,
            "temporal_drift_p": 0.12,
            "cross_modal_corr": 0.45,
            "calibrated_score": 0.48,
            "n_samples": 800,
        },
    }

    results = {}
    for name, features in test_cases.items():
        print(f"\nProcessing: {name}...")
        verdict = run_debate(features)
        results[name] = verdict.to_dict()
        
        print(f"  Verdict: {verdict.status}")
        print(f"  Confidence: {verdict.confidence:.2f}")
        print(f"  Key Evidence: {len(verdict.key_evidence)} arguments")
        if verdict.unresolved_points:
            print(f"  Unresolved: {', '.join(verdict.unresolved_points)}")

    # Summary Analysis
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, res in results.items():
        print(f"  {name}: {res['status']} (conf: {res['confidence']:.2f})")

    return {
        "experiment": "H36",
        "description": "Debate-Driven Verdict",
        "results": results,
        "summary": {k: v["status"] for k, v in results.items()},
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    
    res = run_experiment()

    out_path = H36_DIR / "results" / "h36_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nResults saved to: {out_path}")
