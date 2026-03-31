"""H24 Statistical Robustness — effect sizes, permutation tests, power analysis.

Provides formal statistical evidence that AUC claims are not due to chance:
  - 100-iteration stratified CV → AUC distribution
  - 95% bootstrap confidence intervals
  - Cohen's d effect sizes between real and fake features
  - Permutation test (1000 shuffles) → p-value
  - Empirical power (fraction of CVs with AUC > 0.5)

Usage:
    python experiments/h24_benford_scrna/run_statistical_robustness.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedShuffleSplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

from digit_features import extract_features_per_sample
from fabrication import FABRICATION_METHODS
from isolation_forest import cell_level_features
from run_h24 import _download_pbmc3k, _load_count_matrix

RESULTS_DIR = Path(__file__).resolve().parent / "results"

N_CV = 100
N_PERMUTATIONS = 1000


def compute_cohens_d(real_features: np.ndarray, fake_features: np.ndarray) -> tuple[float, float]:
    """Compute Cohen's d for each feature, return (mean_d, max_d).

    Cohen's d = |mean_real - mean_fake| / pooled_std
    Interpretation: 0.2 small, 0.5 medium, 0.8 large
    """
    ds = []
    for j in range(real_features.shape[1]):
        m1, m2 = real_features[:, j].mean(), fake_features[:, j].mean()
        s1, s2 = real_features[:, j].std(), fake_features[:, j].std()
        n1, n2 = len(real_features), len(fake_features)
        # Pooled std
        pooled = np.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))
        d = abs(m1 - m2) / pooled if pooled > 1e-12 else 0.0
        ds.append(d)
    return float(np.mean(ds)), float(np.max(ds))


def cv_auc_distribution(
    X: np.ndarray,
    y: np.ndarray,
    n_splits: int = N_CV,
    random_state: int = 42,
) -> np.ndarray:
    """Run repeated stratified splits and collect AUC distribution."""
    aucs = []
    splitter = StratifiedShuffleSplit(n_splits=n_splits, test_size=0.2, random_state=random_state)
    for train_idx, test_idx in splitter.split(X, y):
        rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        rf.fit(X[train_idx], y[train_idx])
        proba = rf.predict_proba(X[test_idx])[:, 1]
        aucs.append(roc_auc_score(y[test_idx], proba))
    return np.array(aucs)


def permutation_test(
    X: np.ndarray,
    y: np.ndarray,
    observed_auc: float,
    n_permutations: int = N_PERMUTATIONS,
    random_state: int = 42,
) -> float:
    """Compute p-value via label permutation test.

    Shuffle labels n_permutations times, compute AUC each time.
    p-value = fraction of permuted AUCs >= observed AUC.
    """
    rng = np.random.default_rng(random_state)
    splitter = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(splitter.split(X, y))

    null_aucs = []
    for _ in range(n_permutations):
        y_perm = rng.permutation(y)
        rf = RandomForestClassifier(n_estimators=50, random_state=42, n_jobs=-1)
        rf.fit(X[train_idx], y_perm[train_idx])
        proba = rf.predict_proba(X[test_idx])[:, 1]
        try:
            null_aucs.append(roc_auc_score(y_perm[test_idx], proba))
        except ValueError:
            null_aucs.append(0.5)

    null_aucs = np.array(null_aucs)
    # p-value: fraction of null AUCs >= observed (one-sided)
    p_value = float((null_aucs >= observed_auc).mean())
    return p_value


def bootstrap_ci(aucs: np.ndarray, confidence: float = 0.95) -> tuple[float, float]:
    """Compute percentile bootstrap CI from an AUC distribution."""
    alpha = 1 - confidence
    lower = float(np.percentile(aucs, 100 * alpha / 2))
    upper = float(np.percentile(aucs, 100 * (1 - alpha / 2)))
    return lower, upper


def run_robustness(real_matrix: np.ndarray, method_name: str, fabricate_fn: callable) -> dict:
    """Full statistical robustness analysis for one fabrication method."""
    print(f"\n=== {method_name} ===")
    rng = np.random.default_rng(42)
    fake_matrix = fabricate_fn(real_matrix, rng=rng)

    # Fusion features
    benford_real = extract_features_per_sample(real_matrix)
    benford_fake = extract_features_per_sample(fake_matrix)
    cell_real = cell_level_features(real_matrix)
    cell_fake = cell_level_features(fake_matrix)
    fusion_real = np.hstack([benford_real, cell_real])
    fusion_fake = np.hstack([benford_fake, cell_fake])

    X = np.vstack([fusion_real, fusion_fake])
    y = np.concatenate([np.zeros(len(real_matrix)), np.ones(len(fake_matrix))])

    # 1. Cohen's d
    d_mean, d_max = compute_cohens_d(fusion_real, fusion_fake)
    print(f"  Cohen's d: mean={d_mean:.3f} max={d_max:.3f}")

    # 2. 100-iteration CV
    print(f"  Running {N_CV}-iteration CV...", end=" ", flush=True)
    aucs = cv_auc_distribution(X, y)
    print(f"done. AUC={aucs.mean():.4f} ± {aucs.std():.4f}")

    # 3. Bootstrap CI
    ci_low, ci_high = bootstrap_ci(aucs)
    print(f"  95% CI: [{ci_low:.4f}, {ci_high:.4f}]")

    # 4. Permutation test
    print(f"  Running {N_PERMUTATIONS}-permutation test...", end=" ", flush=True)
    p_val = permutation_test(X, y, observed_auc=aucs.mean())
    print(f"done. p={p_val:.4f}")

    # 5. Empirical power
    power = float((aucs > 0.5).mean())
    print(f"  Empirical power: {power:.3f}")

    # Significance markers
    if p_val < 0.001:
        sig = "***"
    elif p_val < 0.01:
        sig = "**"
    elif p_val < 0.05:
        sig = "*"
    else:
        sig = "ns"

    return {
        "method": method_name,
        "n_cv_iterations": N_CV,
        "mean_auc": round(float(aucs.mean()), 4),
        "std_auc": round(float(aucs.std()), 4),
        "ci_95_lower": round(ci_low, 4),
        "ci_95_upper": round(ci_high, 4),
        "cohens_d_mean": round(d_mean, 4),
        "cohens_d_max": round(d_max, 4),
        "permutation_p_value": round(p_val, 4),
        "n_permutations": N_PERMUTATIONS,
        "empirical_power": round(power, 4),
        "significance": sig,
    }


def main() -> None:
    start = time.time()

    mtx_dir = _download_pbmc3k()
    real_matrix = _load_count_matrix(mtx_dir)
    print(f"Loaded: {real_matrix.shape[0]} cells × {real_matrix.shape[1]} genes")

    results = []
    for name, fn in FABRICATION_METHODS.items():
        r = run_robustness(real_matrix, name, fn)
        results.append(r)

    # Summary
    print("\n" + "=" * 80)
    print(
        f"{'Method':<12} {'AUC':>7} {'±std':>6} {'95% CI':>16} {'Cohen d':>8} {'p-value':>9} {'Power':>7} {'Sig':>4}"
    )
    print("-" * 80)
    for r in results:
        print(
            f"{r['method']:<12} {r['mean_auc']:>7.4f} {r['std_auc']:>6.4f} "
            f"[{r['ci_95_lower']:.4f},{r['ci_95_upper']:.4f}] "
            f"{r['cohens_d_mean']:>8.3f} {r['permutation_p_value']:>9.4f} "
            f"{r['empirical_power']:>7.3f} {r['significance']:>4}"
        )
    print("=" * 80)

    elapsed = time.time() - start

    # Overall conclusion
    all_sig = all(r["permutation_p_value"] < 0.05 for r in results)
    all_powered = all(r["empirical_power"] >= 0.80 for r in results)
    if all_sig and all_powered:
        conclusion = (
            "All fabrication detection results are statistically significant (p < 0.05) "
            "with adequate power (>= 0.80). AUC claims are robust."
        )
    elif all_sig:
        conclusion = (
            "All results statistically significant but some underpowered. "
            "Larger sample size may improve precision."
        )
    else:
        conclusion = "Some results not statistically significant. Interpret with caution."

    output = {
        "experiment": "H24_statistical_robustness",
        "dataset": "PBMC3k_10x",
        "n_cells": int(real_matrix.shape[0]),
        "results": results,
        "conclusion": conclusion,
        "elapsed_s": round(elapsed, 1),
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "h24_statistical_robustness.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nConclusion: {conclusion}")
    print(f"Results saved: {out_path}")
    print(f"Elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
