"""H29 Portability Test -- syndrome on H24 scRNA-seq data.

Tests whether syndrome layer works on scRNA-seq (UMI counts, high sparsity).
WHY: H29 was built on proteomics (dense, continuous). scRNA-seq has ~90% zeros
and integer counts. This tests portability across data types.

Usage:
    python experiments/h29_biological_syndromes/run_h29_h24_portability.py
"""
import json, sys, time, numpy as np
from dataclasses import asdict
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"
H24 = Path(__file__).resolve().parents[1] / "h24_benford_scrna"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(H24))

from skeptic_toolkit.syndrome import build_pairwise_constraints, compute_syndrome_pairwise
from run_h24 import _download_pbmc3k, _load_count_matrix
from fabrication import FABRICATION_METHODS

RESULTS = Path(__file__).resolve().parent / "results"
MAX_GENES = 2000  # limit genes for speed (top by variance)


def main():
    t0 = time.time()
    print("=" * 70)
    print("H29 Portability -- Syndrome on scRNA-seq (H24 PBMC3k)")
    print("=" * 70)

    mtx_dir = _download_pbmc3k()
    full_matrix = _load_count_matrix(mtx_dir)
    print(f"  Full: {full_matrix.shape[0]} cells x {full_matrix.shape[1]} genes")
    print(f"  Zero fraction: {(full_matrix == 0).mean():.4f}")

    # WHY: 32738 genes is too many for pairwise correlation (slow + noisy).
    # Keep top 2000 by variance -- these carry most biological signal.
    variances = full_matrix.astype(np.float64).var(axis=0)
    top_idx = np.argsort(variances)[::-1][:MAX_GENES]
    real = full_matrix[:, top_idx].astype(np.float64)
    gene_names = [f"gene_{i}" for i in top_idx]
    print(f"  Filtered to top {MAX_GENES} by variance: {real.shape}")

    print("\nBuilding constraints (may be sparse due to zero-inflation)...")
    model = build_pairwise_constraints(
        real, feature_names=gene_names, top_k=100, min_abs_rho=0.40, seed=42
    )
    print(f"  {len(model.pairwise)} pairwise, {len(model.modules)} modules")

    if len(model.pairwise) < 5:
        print("\n  WARNING: Very few constraints found. scRNA-seq zero-inflation "
              "makes rank-correlations sparse. This is a known limitation.")

    results = []

    # Real data baseline
    real_syn = compute_syndrome_pairwise(real, model)
    results.append({"label": "real", "fabrication": "none", **asdict(real_syn)})
    print(f"\n  real:    syndrome={real_syn.syndrome_score:.4f} "
          f"mod={real_syn.module_violation_score:.4f} class={real_syn.violation_class}")

    # Fabricated data
    for fab_name, fab_fn in FABRICATION_METHODS.items():
        rng = np.random.default_rng(42)
        fake_full = fab_fn(full_matrix, rng=rng)
        fake = fake_full[:, top_idx].astype(np.float64)
        syn = compute_syndrome_pairwise(fake, model)
        results.append({"label": f"fab_{fab_name}", "fabrication": fab_name, **asdict(syn)})
        print(f"  {fab_name:<12} syndrome={syn.syndrome_score:.4f} "
              f"mod={syn.module_violation_score:.4f} class={syn.violation_class}")

    elapsed = time.time() - t0
    real_s = results[0]["syndrome_score"]
    fab_s = [r["syndrome_score"] for r in results[1:]]

    if not fab_s:
        conclusion = "No fabrication methods tested."
    else:
        max_sep = max(fab_s) - real_s
        min_sep = min(fab_s) - real_s
        if max_sep > 0.05:
            conclusion = (f"Syndrome layer WORKS on scRNA-seq for structure-breaking fabrication "
                          f"(max separation={max_sep:.4f}). "
                          f"Zero-inflation limits number of constraints but signal persists.")
        elif max_sep > 0.01:
            conclusion = f"Weak portability (max separation={max_sep:.4f})."
        else:
            conclusion = (f"Syndrome does NOT port to scRNA-seq (max separation={max_sep:.4f}). "
                          f"Zero-inflation destroys rank-correlation signal.")

    print(f"\n  CONCLUSION: {conclusion}")
    print(f"  Elapsed: {elapsed:.0f}s")

    out = {"experiment": "H29_h24_portability", "dataset": "PBMC3k_top2000genes",
           "n_cells": int(real.shape[0]), "n_genes": int(real.shape[1]),
           "n_constraints": len(model.pairwise), "n_modules": len(model.modules),
           "conclusion": conclusion, "results": results, "elapsed_s": round(elapsed, 1)}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "h29_h24_portability.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"  Saved: {RESULTS / 'h29_h24_portability.json'}")


if __name__ == "__main__":
    main()
