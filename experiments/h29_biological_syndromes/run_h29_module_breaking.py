"""H29 Module-Breaking Perturbation Test.

Targeted corruption: pick a specific co-expression module, shuffle only
those features, verify top_violated_modules matches the injected target.

Usage:
    python experiments/h29_biological_syndromes/run_h29_module_breaking.py
"""
import json, sys, time, numpy as np
from dataclasses import asdict
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"
H25 = Path(__file__).resolve().parents[1] / "h25_banking_ae_lcms"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(H25))

from skeptic_toolkit.syndrome import build_pairwise_constraints, compute_syndrome_pairwise
from run_h25 import _download_bradshaw_data

RESULTS = Path(__file__).resolve().parent / "results"


def module_breaking_perturbation(
    real: np.ndarray, module_indices: list[int], rng: np.random.Generator
) -> np.ndarray:
    """Shuffle only the features in a specific module (targeted break)."""
    perturbed = real.copy()
    for j in module_indices:
        rng.shuffle(perturbed[:, j])
    return perturbed


def main():
    t0 = time.time()
    print("=" * 70)
    print("H29 Module-Breaking Perturbation Test")
    print("=" * 70)

    _, prot = _download_bradshaw_data()
    fnames = prot.columns.tolist()
    real = np.nan_to_num(prot.values.astype(np.float64), nan=0.0)
    print(f"  {real.shape[0]} samples x {real.shape[1]} proteins")

    print("\nBuilding constraints...")
    model = build_pairwise_constraints(real, feature_names=fnames, top_k=200, seed=42)
    print(f"  {len(model.pairwise)} pairwise, {len(model.modules)} modules")

    if not model.modules:
        print("  No modules found. Cannot run module-breaking test.")
        return

    results = []

    # Baseline: real data
    real_syn = compute_syndrome_pairwise(real, model)
    results.append({"test": "baseline_real", "syndrome": real_syn.syndrome_score,
                     "module_violation": real_syn.module_violation_score,
                     "violation_class": real_syn.violation_class})
    print(f"\n  Baseline: syndrome={real_syn.syndrome_score:.4f} class={real_syn.violation_class}")

    # Break each of top 3 modules independently
    for mod in model.modules[:3]:
        rng = np.random.default_rng(42)
        perturbed = module_breaking_perturbation(real, mod.feature_indices, rng)
        syn = compute_syndrome_pairwise(perturbed, model)

        # Check if broken module appears in top violated
        top_mod_ids = [m["module_id"] for m in syn.top_violated_modules[:5]]
        detected = mod.module_id in top_mod_ids

        genes_str = ", ".join(mod.feature_names[:3])
        print(f"\n  Break module {mod.module_id} [{genes_str}...] (size={len(mod.feature_indices)}):")
        print(f"    syndrome={syn.syndrome_score:.4f} mod_viol={syn.module_violation_score:.4f} "
              f"class={syn.violation_class}")
        print(f"    Target module in top-5 violated: {'YES' if detected else 'NO'}")

        results.append({
            "test": f"break_module_{mod.module_id}",
            "module_genes": mod.feature_names[:5],
            "module_size": len(mod.feature_indices),
            "syndrome": syn.syndrome_score,
            "module_violation": syn.module_violation_score,
            "violation_class": syn.violation_class,
            "target_detected_in_top5": detected,
            "review_required": syn.review_required,
        })

    # Full shuffle (all features) for comparison
    rng = np.random.default_rng(42)
    all_perturbed = real.copy()
    for j in range(real.shape[1]):
        rng.shuffle(all_perturbed[:, j])
    full_syn = compute_syndrome_pairwise(all_perturbed, model)
    results.append({"test": "full_shuffle", "syndrome": full_syn.syndrome_score,
                     "module_violation": full_syn.module_violation_score,
                     "violation_class": full_syn.violation_class})
    print(f"\n  Full shuffle: syndrome={full_syn.syndrome_score:.4f} class={full_syn.violation_class}")

    elapsed = time.time() - t0
    n_detected = sum(1 for r in results if r.get("target_detected_in_top5"))
    n_tested = sum(1 for r in results if "target_detected_in_top5" in r)

    if n_detected == n_tested and n_tested > 0:
        conclusion = f"All {n_tested}/{n_tested} broken modules detected in top-5 violations."
    elif n_detected > 0:
        conclusion = f"{n_detected}/{n_tested} broken modules detected."
    else:
        conclusion = "Module-breaking not detected. Constraints may be too coarse."

    print(f"\n  CONCLUSION: {conclusion}")
    print(f"  Elapsed: {elapsed:.0f}s")

    out = {"experiment": "H29_module_breaking", "conclusion": conclusion,
           "n_detected": n_detected, "n_tested": n_tested,
           "results": results, "elapsed_s": round(elapsed, 1)}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "h29_module_breaking.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"  Saved: {RESULTS / 'h29_module_breaking.json'}")


if __name__ == "__main__":
    main()
