"""H35 — Mpemba Sweet Spot Thresholds.

Demonstrates that domain-specific adaptive thresholds outperform
a single global threshold for anomaly detection.

Uses the same historical calibration data as H34 to find
the optimal decision boundary for each detector type.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "experiments"
H35_DIR = Path(__file__).resolve().parent


def run_experiment() -> dict[str, Any]:
    """Run H35 threshold optimization experiment."""
    print("=" * 60)
    print("H35: Mpemba Sweet Spot — Adaptive Thresholds")
    print("=" * 60)

    from skeptic_engine.utils.threshold_optimizer import (
        ThresholdOptimizer,
        find_sweet_spots,
    )

    # 1. Collect Data
    print("\n[1/4] Collecting calibration data...")
    # Import from H34 to reuse the same collection logic
    from h34_calibrated_uncertainty.run_h34 import collect_historical_results

    hist_data = collect_historical_results()
    total_samples = sum(len(e["scores"]) for e in hist_data)
    print(f"  Total samples: {total_samples}")
    print(f"  Detectors: {len(hist_data)}")

    # 2. Compare Global vs Domain-Specific
    print("\n[2/4] Computing Global vs Domain-Specific thresholds...")
    
    # Global baseline (fixed 0.5)
    global_scores = []
    global_labels = []
    for entry in hist_data:
        global_scores.extend(entry["scores"])
        global_labels.extend(entry["labels"])
    
    global_scores = np.array(global_scores)
    global_labels = np.array(global_labels)

    # Find global sweet spot
    global_opt = ThresholdOptimizer(domain="global_fixed")
    global_opt.fit(global_scores, global_labels)
    
    print(f"  Global Sweet Spot Threshold: {global_opt.threshold_:.4f}")
    print(f"  Global F1: {global_opt.f1_score_:.4f}")

    # Find domain-specific sweet spots
    domain_results = find_sweet_spots(hist_data)
    
    print(f"\n  Domain-Specific Sweet Spots:")
    domain_improvements = []
    
    for detector, res in domain_results.items():
        print(f"    {detector}: thresh={res.optimal_threshold:.3f}, F1={res.f1_score:.4f}")
        
        # Calculate what F1 we would get with global threshold for this domain
        entry_data = next((e for e in hist_data if e["detector"] == detector), None)
        if entry_data:
            sc = np.array(entry_data["scores"])
            lb = np.array(entry_data["labels"])
            
            # Evaluate global threshold on this domain
            from sklearn.metrics import f1_score
            global_preds = (sc >= global_opt.threshold_).astype(int)
            f1_global_on_domain = f1_score(lb, global_preds, zero_division=0)
            
            improvement = res.f1_score - f1_global_on_domain
            domain_improvements.append({
                "detector": detector,
                "domain_threshold": res.optimal_threshold,
                "domain_f1": res.f1_score,
                "global_f1_on_domain": f1_global_on_domain,
                "improvement": improvement,
            })

    # 3. Aggregate Impact
    print("\n[3/4] Calculating aggregate impact...")
    
    if domain_improvements:
        improvements = np.array([d["improvement"] for d in domain_improvements])
        weights = []
        for imp in domain_improvements:
            d_res = domain_results.get(imp["detector"])
            if d_res:
                weights.append(d_res.n_samples)
        weights = np.array(weights)
        
        avg_improvement = float(np.average(improvements, weights=weights)) if len(weights) > 0 else 0
        
        print(f"  Average F1 Improvement: {avg_improvement:+.4f}")
        
        summary_improvements = {
            "mean_delta_f1": float(np.mean(improvements)),
            "weighted_delta_f1": avg_improvement,
            "max_gain": float(np.max(improvements)),
            "min_gain": float(np.min(improvements)),
        }
    else:
        summary_improvements = {}
        avg_improvement = 0

    # 4. Demonstrate "Mpemba Crossing"
    print("\n[4/4] Demonstrating Mpemba Crossing effect...")
    print("  (The point where Precision and Recall curves intersect)")
    
    # For the best performing domain, show the P/R intersection
    best_domain = max(domain_improvements, key=lambda x: x["improvement"])
    best_det = best_domain["detector"]
    best_entry = next(e for e in hist_data if e["detector"] == best_det)
    
    from sklearn.metrics import precision_recall_curve
    pr, rec, thresh = precision_recall_curve(
        np.array(best_entry["labels"]),
        np.array(best_entry["scores"])
    )
    # Find crossing point
    diff = np.abs(pr - rec)
    crossing_idx = np.argmin(diff)
    crossing_thresh = thresh[crossing_idx] if crossing_idx < len(thresh) else 0.5
    
    print(f"  Best Domain: {best_det}")
    print(f"  Mpemba Crossing Point: {crossing_thresh:.4f}")
    print(f"  Optimized Threshold: {best_domain['domain_threshold']:.4f}")
    print(f"  Gain over Global: {best_domain['improvement']:+.4f}")

    # Build results
    results = {
        "experiment": "H35",
        "description": "Mpemba Sweet Spot — Adaptive Thresholds",
        "summary": {
            "global_threshold": global_opt.threshold_,
            "global_f1": global_opt.f1_score_,
            "avg_improvement": avg_improvement,
            "summary_improvements": summary_improvements,
            "n_domains_optimized": len(domain_results),
        },
        "domain_results": {k: v.to_dict() for k, v in domain_results.items()},
        "improvements": domain_improvements,
        "mpemba_crossing": {
            "detector": best_det,
            "crossing_threshold": crossing_thresh,
            "optimized_threshold": best_domain["domain_threshold"],
        },
    }

    # Print Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Global Threshold: {global_opt.threshold_:.4f} (F1: {global_opt.f1_score_:.4f})")
    print(f"  Avg Improvement: {avg_improvement:+.4f}")
    print(f"  Best Domain: {best_det} (+{best_domain['improvement']:.4f})")
    print(f"  Domains calibrated: {len(domain_results)}")

    return results


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    
    results = run_experiment()

    out_path = H35_DIR / "results" / "h35_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nResults saved to: {out_path}")
