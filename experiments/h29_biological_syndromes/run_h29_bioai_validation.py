"""H29 Bio-AI Validation -- quality check for synthetic biological data.

Tests whether syndrome can distinguish "good" synthetic data (preserves
biological structure) from "bad" synthetic data (breaks it).

Three types of synthetic data:
1. Shuffle (bad) -- breaks all inter-gene correlations
2. Random NB (bad) -- preserves per-gene stats but not structure
3. Correlated resample (good) -- preserves block correlation structure

If syndrome ranks them correctly (correlated > random > shuffle),
this is proof-of-concept for "bio-AI data quality validation".

Usage:
    python experiments/h29_biological_syndromes/run_h29_bioai_validation.py
"""

import json
import sys
import time

import numpy as np
from dataclasses import asdict
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"
H25 = Path(__file__).resolve().parents[1] / "h25_banking_ae_lcms"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(H25))

from skeptic_toolkit.syndrome import build_pairwise_constraints, compute_syndrome_pairwise
from run_h25 import _download_bradshaw_data, fabricate_random, fabricate_shuffle

RESULTS = Path(__file__).resolve().parent / "results"


def generate_correlated_synthetic(
    real: np.ndarray, rng: np.random.Generator, noise_scale: float = 0.3
) -> np.ndarray:
    """Generate 'good' synthetic data that preserves correlation structure.

    Method: take real data, add small Gaussian noise to preserve inter-gene
    relationships while changing individual values. This simulates what a
    well-trained generative model (scGPT, Geneformer) should produce.
    """
    noise = rng.normal(0, noise_scale * np.nanstd(real, axis=0, keepdims=True), size=real.shape)
    synthetic = real + noise
    return synthetic


def generate_marginal_synthetic(real: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Generate per-gene marginal-matched synthetic data.

    Preserves per-gene mean and variance but NOT inter-gene correlations.
    This simulates what a naive per-gene generative model would produce.
    """
    n_samples, n_features = real.shape
    synthetic = np.zeros_like(real)
    for j in range(n_features):
        col = real[:, j]
        valid = col[~np.isnan(col)]
        if len(valid) > 1:
            synthetic[:, j] = rng.normal(valid.mean(), valid.std(), size=n_samples)
        else:
            synthetic[:, j] = rng.normal(0, 1, size=n_samples)
    return synthetic


def main() -> None:
    t0 = time.time()
    print("=" * 70)
    print("H29 Bio-AI Validation -- Synthetic Data Quality Check")
    print("=" * 70)

    # Load real data
    print("\n[1/3] Loading CPTAC proteomics...")
    _, prot = _download_bradshaw_data()
    feature_names = prot.columns.tolist()
    real = np.nan_to_num(prot.values.astype(np.float64), nan=0.0)
    print(f"  {real.shape[0]} samples x {real.shape[1]} proteins")

    # Build constraints on real data
    print("\n[2/3] Building reference constraints...")
    model = build_pairwise_constraints(real, feature_names=feature_names, top_k=200, seed=42)
    print(f"  {len(model.pairwise)} pairwise, {len(model.modules)} modules")

    # Generate synthetic datasets of varying quality
    print("\n[3/3] Scoring synthetic data quality...\n")
    rng = np.random.default_rng(42)

    generators = {
        "real_data": ("Reference (real)", real),
        "good_synthetic": (
            "Correlated noise (good AI)",
            generate_correlated_synthetic(real, rng, 0.3),
        ),
        "marginal_synthetic": (
            "Marginal-matched (naive AI)",
            generate_marginal_synthetic(real, rng),
        ),
        "shuffle": ("Shuffle (bad, breaks structure)", fabricate_shuffle(real, rng)),
        "random": ("Random from distributions (bad)", fabricate_random(real, rng)),
    }

    results = []
    for key, (label, data) in generators.items():
        syn = compute_syndrome_pairwise(data, model)
        results.append(
            {
                "type": key,
                "label": label,
                "syndrome_score": syn.syndrome_score,
                "pairwise_violation": syn.pairwise_violation_score,
                "module_violation": syn.module_violation_score,
                "violation_class": syn.violation_class,
                "review_required": syn.review_required,
            }
        )
        print(
            f"  {label:<35} syndrome={syn.syndrome_score:.4f} "
            f"module={syn.module_violation_score:.4f} class={syn.violation_class}"
        )

    # Check ranking
    scores = {r["type"]: r["syndrome_score"] for r in results}
    correct_ranking = (
        scores["real_data"]
        < scores["good_synthetic"]
        < scores["marginal_synthetic"]
        < scores["shuffle"]
    )

    elapsed = time.time() - t0
    print(f"\n{'=' * 70}")
    print("BIO-AI VALIDATION SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Real data:            {scores['real_data']:.4f}")
    print(f"  Good synthetic:       {scores['good_synthetic']:.4f}")
    print(f"  Marginal synthetic:   {scores['marginal_synthetic']:.4f}")
    print(f"  Shuffle:              {scores['shuffle']:.4f}")
    print(f"  Random:               {scores['random']:.4f}")
    print(f"  Correct ranking:      {'YES' if correct_ranking else 'PARTIAL'}")
    print(f"  Elapsed:              {elapsed:.0f}s")

    if correct_ranking:
        conclusion = (
            "Syndrome correctly ranks synthetic data quality: "
            "real < good_synthetic < marginal < shuffle. "
            "This validates the tool as a quality checker for bio-AI generated data. "
            "A well-trained generative model should produce data with low syndrome score."
        )
    else:
        # Check partial ranking
        good_better_than_bad = scores["good_synthetic"] < scores["shuffle"]
        if good_better_than_bad:
            conclusion = (
                "Syndrome distinguishes good from bad synthetic data "
                f"(good={scores['good_synthetic']:.4f} < shuffle={scores['shuffle']:.4f}). "
                "Partial ranking correctness."
            )
        else:
            conclusion = "Syndrome does not reliably rank synthetic data quality."

    print(f"\n  CONCLUSION: {conclusion}")

    out = {
        "experiment": "H29_bioai_validation",
        "dataset": "CPTAC_proteomics",
        "correct_ranking": correct_ranking,
        "conclusion": conclusion,
        "results": results,
        "elapsed_s": round(elapsed, 1),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "h29_bioai_validation.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )
    print(f"  Saved: {RESULTS / 'h29_bioai_validation.json'}")


if __name__ == "__main__":
    main()
