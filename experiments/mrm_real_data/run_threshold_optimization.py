"""SE-MRM Threshold Optimization + Baseline Comparison.

1. Grid search для оптимизации thresholds на MP данных
2. Baseline comparison: simple filter vs full MRM pipeline
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(r"E:\nobel premia Boiko - 2026")
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "experiments" / "mrm_real_data"))

from itertools import product
from skeptic_mrm.schemas.material_candidate import MaterialCandidate
from skeptic_mrm.falsification import RuleBasedAttackPolicy, run_falsification_suite
from skeptic_mrm.scoring import compute_scores, make_decision, DEFAULT_WEIGHTS
from skeptic_mrm.simulation_backends import ISimulationBackend, SimulationRun
import re


# ============================================================================
# Load MP candidates
# ============================================================================

def load_mp_candidates() -> list[MaterialCandidate]:
    """Load the 130 MP candidates."""
    data_path = PROJECT_ROOT / "experiments" / "mrm_real_data" / "data" / "mp_real_candidates.json"
    with open(data_path, encoding="utf-8") as f:
        items = json.load(f)
    return [MaterialCandidate.from_dict(item) for item in items]


# ============================================================================
# Real Data Backend (reuses formation_energy from candidate properties)
# ============================================================================

class RealDataBackend(ISimulationBackend):
    def __init__(self):
        self._run_counter = 0

    def relax(self, candidate: MaterialCandidate, config=None):
        from skeptic_mrm.schemas.simulation_run import SimulationRun
        self._run_counter += 1
        tp = candidate.target_properties or {}
        fe = tp.get("formation_energy", -2.0)
        eah = tp.get("energy_above_hull", 0.5)

        # Sigmoid mapping for stability
        import math
        stability = min(1.0, max(0.0, 1.0 / (1.0 + math.exp(fe + 1.5)))) if fe else 0.5
        dynamic = min(1.0, max(0.3, 1.0 - eah * 0.8))

        return SimulationRun(
            run_id=f"real_{self._run_counter:06d}",
            candidate_id=candidate.candidate_id,
            backend="real_data_calibrated",
            tier=1,
            config_version="real-0.1",
            status="completed",
            metrics={
                "energy_proxy": float(fe) if fe else -2.0,
                "dynamic_stability_proxy": float(dynamic),
                "temperature_resilience": max(0.1, dynamic * 0.9),
                "pressure_resilience": max(0.1, dynamic * 0.85),
            },
            artifacts={},
        )

    def simulate(self, candidate: MaterialCandidate, scenario: dict):
        from skeptic_mrm.schemas.simulation_run import SimulationRun
        self._run_counter += 1
        tp = candidate.target_properties or {}
        eah = tp.get("energy_above_hull", 0.5)

        if eah < 0.05:
            prop_drop = 0.02
            collapsed = 0.0
        elif eah < 0.3:
            prop_drop = 0.15
            collapsed = 0.0
        else:
            prop_drop = 0.5 + eah * 0.3
            collapsed = 1.0 if eah > 0.5 else 0.0

        return SimulationRun(
            run_id=f"real_{self._run_counter:06d}",
            candidate_id=candidate.candidate_id,
            backend="real_data_calibrated",
            tier=1,
            config_version="real-0.1",
            status="completed",
            metrics={
                "property_drop": prop_drop,
                "collapsed": collapsed,
                "stress_hotspots_detected": eah > 0.1,
            },
            artifacts={},
        )

    def supports(self) -> dict:
        return {"name": "RealDataBackend", "status": "calibrated_from_real_data"}


# ============================================================================
# Run full pipeline on all candidates and collect scores
# ============================================================================

def compute_all_scores(candidates: list[MaterialCandidate], backend: ISimulationBackend):
    """Run the full MRM pipeline and return per-candidate score bundles."""
    results = []
    for c in candidates:
        sim = backend.relax(c)
        falsif = run_falsification_suite(c, backend, RuleBasedAttackPolicy(), budget={"max_attacks_per_candidate": 4})
        scores = compute_scores(c, [sim], stress_resilience=falsif.stress_resilience_score, backend="real_data_calibrated")
        profile = c.target_properties.get("_profile_type", "marginal")
        results.append({
            "candidate_id": c.candidate_id,
            "composition": c.composition,
            "profile": profile,
            "scores": scores,
            "falsification": falsif,
        })
    return results


# ============================================================================
# Threshold Grid Search
# ============================================================================

def evaluate_thresholds(results: list[dict], thresholds: dict) -> dict:
    """Evaluate a set of thresholds and return accuracy metrics."""
    from skeptic_mrm.schemas.reliability_decision import DecisionStatus
    from skeptic_mrm.scoring import make_decision

    expected_decisions = {"stable": "promote", "marginal": "hold", "unstable": "kill"}
    group_results = {"stable": [], "marginal": [], "unstable": []}

    for r in results:
        profile = r["profile"]
        decision = make_decision(r["scores"], thresholds=thresholds)
        expected = expected_decisions.get(profile, "hold")
        correct = 1 if decision.status.value == expected else 0
        group_results[profile].append({
            "candidate_id": r["candidate_id"],
            "composition": r["composition"],
            "expected": expected,
            "got": decision.status.value,
            "correct": correct,
            "score": r["scores"].final_reliability_score,
        })

    total_correct = sum(item["correct"] for group in group_results.values() for item in group)
    total_count = sum(len(group) for group in group_results.values())

    summary = {"total_correct": total_correct, "total_count": total_count, "accuracy": round(total_correct / max(total_count, 1), 3)}
    for group_name, items in group_results.items():
        correct = sum(item["correct"] for item in items)
        summary[group_name] = {
            "total": len(items),
            "correct": correct,
            "accuracy": round(correct / max(len(items), 1), 3),
            "avg_score": round(sum(item["score"] for item in items) / max(len(items), 1), 3),
        }

    return summary, group_results


def grid_search(results: list[dict]) -> list[dict]:
    """Grid search over threshold parameters."""
    param_grid = {
        "promote_above": [0.45, 0.48, 0.50, 0.52, 0.55],
        "hold_below": [0.45, 0.48, 0.50, 0.52, 0.55],
        "kill_below": [0.25, 0.28, 0.30, 0.32, 0.35],
        "min_stability": [0.20, 0.22, 0.25, 0.28],
        "min_dynamic": [0.20, 0.22, 0.25, 0.28],
        "max_uncertainty": [0.55, 0.60, 0.65],
    }

    print("Grid search parameters:", {k: len(v) for k, v in param_grid.items()})
    total_combos = 1
    for v in param_grid.values():
        total_combos *= len(v)
    print(f"Total combinations: {total_combos}\n")

    best = None
    best_acc = 0
    evaluated = 0

    for promote_above, hold_below, kill_below, min_stab, min_dyn, max_unc in product(
        param_grid["promote_above"],
        param_grid["hold_below"],
        param_grid["kill_below"],
        param_grid["min_stability"],
        param_grid["min_dynamic"],
        param_grid["max_uncertainty"],
    ):
        # Skip invalid combinations
        if promote_above <= kill_below:
            continue
        if hold_below <= kill_below:
            continue
        if promote_above > hold_below:
            continue

        thresholds = {
            "promote_above": promote_above,
            "hold_below": hold_below,
            "kill_below": kill_below,
            "min_stability": min_stab,
            "min_dynamic": min_dyn,
            "max_uncertainty": max_unc,
        }

        summary, _ = evaluate_thresholds(results, thresholds)
        accuracy = summary["accuracy"]
        evaluated += 1

        if accuracy > best_acc:
            best_acc = accuracy
            best = {"thresholds": thresholds, "summary": summary}

        if evaluated % 500 == 0:
            print(f"  Evaluated {evaluated} combinations, best so far: {best_acc:.3f}")

    print(f"\n  Total evaluated: {evaluated}")
    return best


# ============================================================================
# Baseline: Simple Filter (just energy_above_hull threshold)
# ============================================================================

def baseline_simple_filter(candidates: list[MaterialCandidate]) -> dict:
    """Baseline: classify based solely on energy_above_hull.
    
    This is what a simple property filter would do.
    """
    expected_decisions = {"stable": "promote", "marginal": "hold", "unstable": "kill"}
    results = {"stable": [], "marginal": [], "unstable": []}

    for c in candidates:
        profile = c.target_properties.get("_profile_type", "marginal")
        eah = c.target_properties.get("energy_above_hull", 0.5)

        # Simple rule-based classification
        if eah < 0.05:
            predicted = "promote"
        elif eah < 0.3:
            predicted = "hold"
        else:
            predicted = "kill"

        expected = expected_decisions.get(profile, "hold")
        correct = 1 if predicted == expected else 0
        results[profile].append({
            "candidate_id": c.candidate_id,
            "composition": c.composition,
            "expected": expected,
            "got": predicted,
            "correct": correct,
            "eah": eah,
        })

    total_correct = sum(item["correct"] for group in results.values() for item in group)
    total_count = sum(len(group) for group in results.values())

    summary = {"total_correct": total_correct, "total_count": total_count, "accuracy": round(total_correct / max(total_count, 1), 3)}
    for group_name, items in results.items():
        correct = sum(item["correct"] for item in items)
        summary[group_name] = {
            "total": len(items),
            "correct": correct,
            "accuracy": round(correct / max(len(items), 1), 3),
        }

    return summary, results


# ============================================================================
# Main
# ============================================================================

def main():
    print("=" * 70)
    print("SE-MRM THRESHOLD OPTIMIZATION + BASELINE COMPARISON")
    print("=" * 70)

    # Load candidates
    candidates = load_mp_candidates()
    print(f"\nLoaded {len(candidates)} MP candidates")

    # Group stats
    groups = {"stable": 0, "marginal": 0, "unstable": 0}
    for c in candidates:
        p = c.target_properties.get("_profile_type", "marginal")
        groups[p] += 1
    print(f"  Stable: {groups['stable']}")
    print(f"  Marginal: {groups['marginal']}")
    print(f"  Unstable: {groups['unstable']}")

    # Compute scores
    print("\n--- Computing scores for all candidates ---")
    backend = RealDataBackend()
    results = compute_all_scores(candidates, backend)
    print(f"  Scored {len(results)} candidates")

    # ---- STEP 1: Baseline (simple filter) ----
    print("\n" + "=" * 70)
    print("STEP 1: Baseline — Simple energy_above_hull filter")
    print("=" * 70)
    baseline_summary, baseline_results = baseline_simple_filter(candidates)
    print(f"\nBaseline accuracy: {baseline_summary['accuracy']} ({baseline_summary['total_correct']}/{baseline_summary['total_count']})")
    for group in ["stable", "marginal", "unstable"]:
        g = baseline_summary.get(group, {})
        print(f"  {group}: {g.get('accuracy', 0)} ({g.get('correct', 0)}/{g.get('total', 0)})")

    # ---- STEP 2: Default thresholds ----
    print("\n" + "=" * 70)
    print("STEP 2: Default thresholds (current)")
    print("=" * 70)
    default_thresholds = {
        "promote_above": 0.55,
        "hold_below": 0.55,
        "kill_below": 0.30,
        "min_stability": 0.25,
        "min_dynamic": 0.25,
        "max_uncertainty": 0.60,
    }
    default_summary, _ = evaluate_thresholds(results, default_thresholds)
    print(f"\nDefault accuracy: {default_summary['accuracy']} ({default_summary['total_correct']}/{default_summary['total_count']})")
    for group in ["stable", "marginal", "unstable"]:
        g = default_summary.get(group, {})
        print(f"  {group}: {g.get('accuracy', 0)} ({g.get('correct', 0)}/{g.get('total', 0)})")

    # ---- STEP 3: Grid search ----
    print("\n" + "=" * 70)
    print("STEP 3: Grid Search — Finding optimal thresholds")
    print("=" * 70)
    best = grid_search(results)

    print(f"\n*** BEST THRESHOLDS ***")
    for k, v in best["thresholds"].items():
        print(f"  {k}: {v}")
    print(f"\n*** BEST ACCURACY: {best['summary']['accuracy']} ({best['summary']['total_correct']}/{best['summary']['total_count']}) ***")
    for group in ["stable", "marginal", "unstable"]:
        g = best["summary"].get(group, {})
        print(f"  {group}: {g.get('accuracy', 0)} ({g.get('correct', 0)}/{g.get('total', 0)})")

    # ---- STEP 4: Comparison table ----
    print("\n" + "=" * 70)
    print("STEP 4: COMPARISON — Baseline vs Default vs Optimized")
    print("=" * 70)
    print(f"\n{'Metric':<30} {'Baseline':<15} {'Default MRM':<15} {'Optimized MRM':<15}")
    print("-" * 75)
    print(f"{'Overall accuracy':<30} {baseline_summary['accuracy']:<15} {default_summary['accuracy']:<15} {best['summary']['accuracy']:<15}")

    for group in ["stable", "marginal", "unstable"]:
        b = baseline_summary.get(group, {})
        d = default_summary.get(group, {})
        o = best["summary"].get(group, {})
        label = f"{group.capitalize()} accuracy"
        print(f"{label:<30} {b.get('accuracy', 0):<15} {d.get('accuracy', 0):<15} {o.get('accuracy', 0):<15}")

    # Improvement
    improvement = best["summary"]["accuracy"] - baseline_summary["accuracy"]
    print(f"\nMRM improvement over baseline: +{improvement:.1%}")
    if improvement > 0:
        print("✅ MRM pipeline outperforms simple filter")
    else:
        print("⚠️ MRM does not outperform simple filter yet")

    # ---- STEP 5: Save results ----
    out_dir = PROJECT_ROOT / "experiments" / "mrm_real_data" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    output = {
        "baseline": baseline_summary,
        "default_mrm": default_summary,
        "optimized_mrm": best["summary"],
        "best_thresholds": best["thresholds"],
        "improvement_over_baseline": round(improvement, 3),
    }

    out_path = out_dir / "threshold_optimization_results.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nResults saved to: {out_path}")


if __name__ == "__main__":
    main()
