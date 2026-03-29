"""H-L09 / Adversarial Robustness Test for H24 Benford Detector.

Question: If a fabricator KNOWS about Benford's Law and forces first-digit
compliance in their synthetic data, can our detector still catch them?

Strategy:
  1. Generate Benford-aware fabrication (force first-digit to match Benford distribution)
  2. Test if single-feature detectors (first-digit only) fail
  3. Test if our FULL fusion (including second-digit, chi2, cell-level) still works

Usage:
    python experiments/h24_benford_scrna/run_adversarial.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.io import mmread
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedShuffleSplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

from digit_features import BENFORD_FIRST, extract_features_per_sample
from isolation_forest import cell_level_features

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def fabricate_benford_aware(
    real_matrix: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate fabricated data that MATCHES Benford first-digit distribution.

    Strategy: for each cell, sample values from real data but rotate digits
    to force first-digit frequencies to match Benford expected.
    This simulates a sophisticated fabricator who knows about digit tests.
    """
    n_cells, n_genes = real_matrix.shape
    fake = np.zeros_like(real_matrix)

    for i in range(n_cells):
        row = real_matrix[i].copy()
        nonzero_mask = row > 0
        nonzero_vals = row[nonzero_mask].astype(np.float64)

        if len(nonzero_vals) < 10:
            fake[i] = row
            continue

        # Shuffle the nonzero values (destroy cell identity)
        rng.shuffle(nonzero_vals)

        # Now adjust first digits to match Benford distribution
        n_nonzero = len(nonzero_vals)
        target_counts = (BENFORD_FIRST * n_nonzero).astype(int)
        # Fix rounding to match total
        target_counts[0] += n_nonzero - target_counts.sum()

        # Sort values by magnitude, assign to digit bins
        sorted_idx = np.argsort(nonzero_vals)
        adjusted = nonzero_vals.copy()

        ptr = 0
        for digit in range(1, 10):
            count = target_counts[digit - 1]
            for j in range(count):
                if ptr >= n_nonzero:
                    break
                idx = sorted_idx[ptr]
                val = nonzero_vals[idx]
                if val > 0:
                    # Replace first digit while preserving magnitude
                    magnitude = 10 ** int(np.floor(np.log10(max(val, 1))))
                    remainder = val % magnitude
                    adjusted[idx] = digit * magnitude + int(remainder) % magnitude
                ptr += 1

        adjusted = np.clip(adjusted, 1, None).astype(np.int64)
        fake[i, nonzero_mask] = adjusted

    return fake


def fabricate_second_digit_aware(
    real_matrix: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Even more sophisticated: match both first AND second digit distributions.

    Simulates fabricator who read the Benford second-digit literature too.
    """
    # Start with Benford-aware first-digit fabrication
    fake = fabricate_benford_aware(real_matrix, rng)

    # For values >= 10, adjust second digit to be more uniform
    # (real data has Benford second-digit distribution; making it uniform
    # actually makes it WORSE, but fabricator might try to match expected)
    for i in range(fake.shape[0]):
        for j in range(fake.shape[1]):
            val = fake[i, j]
            if val >= 10:
                # Extract and redistribute second digit
                s = str(int(val))
                if len(s) >= 2:
                    target_d2 = rng.integers(0, 10)
                    new_s = s[0] + str(target_d2) + s[2:]
                    fake[i, j] = int(new_s)

    return fake.astype(np.int64)


def main() -> None:
    print("=" * 70)
    print("Adversarial Robustness Test — Can Benford-Aware Fabrication Evade?")
    print("=" * 70)
    t0 = time.time()

    # Load real data (download if needed)
    mtx_path = (
        Path(__file__).resolve().parent
        / "data"
        / "filtered_gene_bc_matrices"
        / "hg19"
        / "matrix.mtx"
    )
    if not mtx_path.exists():
        from run_h24 import _download_pbmc3k

        _download_pbmc3k()
    real = mmread(str(mtx_path)).toarray().T.astype(np.int64)
    n_cells = real.shape[0]
    print(f"\nLoaded: {n_cells} cells × {real.shape[1]} genes")

    # Extract real features
    benford_real = extract_features_per_sample(real)
    cell_real = cell_level_features(real)
    X_real = np.hstack([benford_real, cell_real])

    rng = np.random.default_rng(2026)

    adversarial_methods = {
        "benford_aware_fd": fabricate_benford_aware,
        "benford_aware_fd_sd": fabricate_second_digit_aware,
    }

    all_results = []

    for adv_name, adv_fn in adversarial_methods.items():
        print(f"\n{'=' * 50}")
        print(f"Adversarial: {adv_name}")
        print(f"{'=' * 50}")

        # WHY: use loop rng (not a fresh seed) so each adversarial method gets independent state
        fake = adv_fn(real, rng=rng)
        benford_fake = extract_features_per_sample(fake)
        cell_fake = cell_level_features(fake)
        X_fake = np.hstack([benford_fake, cell_fake])

        # Check: did adversarial fabrication actually match Benford?
        real_fd_mean = benford_real[:, :9].mean(axis=0)
        fake_fd_mean = benford_fake[:, :9].mean(axis=0)
        fd_diff = np.abs(real_fd_mean - fake_fd_mean).mean()
        print(f"  First-digit mean diff from real: {fd_diff:.6f}")
        print(f"  Real fd_1 freq:  {real_fd_mean[0]:.4f}")
        print(f"  Fake fd_1 freq:  {fake_fd_mean[0]:.4f}")
        print(f"  Benford expected: {BENFORD_FIRST[0]:.4f}")

        y = np.concatenate([np.zeros(n_cells), np.ones(n_cells)])
        splitter = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        train_idx, test_idx = next(splitter.split(np.vstack([X_real, X_fake]), y))

        result = {"adversarial": adv_name}

        # Test 1: First-digit features ONLY (should fail against Benford-aware)
        X_fd = np.vstack([benford_real[:, :9], benford_fake[:, :9]])
        rf_fd = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        rf_fd.fit(X_fd[train_idx], y[train_idx])
        auc_fd = roc_auc_score(y[test_idx], rf_fd.predict_proba(X_fd[test_idx])[:, 1])
        print(f"  First-digit ONLY AUC:  {auc_fd:.4f} {'← EVADED!' if auc_fd < 0.70 else ''}")
        result["first_digit_only_auc"] = round(auc_fd, 4)

        # Test 2: Benford FULL (21 features — includes chi2 and second-digit)
        X_benford = np.vstack([benford_real, benford_fake])
        rf_bf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        rf_bf.fit(X_benford[train_idx], y[train_idx])
        auc_bf = roc_auc_score(y[test_idx], rf_bf.predict_proba(X_benford[test_idx])[:, 1])
        print(f"  Benford FULL AUC:      {auc_bf:.4f}")
        result["benford_full_auc"] = round(auc_bf, 4)

        # Test 3: Cell-level ONLY
        X_cell = np.vstack([cell_real, cell_fake])
        rf_cell = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        rf_cell.fit(X_cell[train_idx], y[train_idx])
        auc_cell = roc_auc_score(y[test_idx], rf_cell.predict_proba(X_cell[test_idx])[:, 1])
        print(f"  Cell-level ONLY AUC:   {auc_cell:.4f}")
        result["cell_level_only_auc"] = round(auc_cell, 4)

        # Test 4: FULL FUSION
        X_full = np.vstack([X_real, X_fake])
        rf_full = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        rf_full.fit(X_full[train_idx], y[train_idx])
        auc_full = roc_auc_score(y[test_idx], rf_full.predict_proba(X_full[test_idx])[:, 1])
        print(f"  FUSION AUC:            {auc_full:.4f}")
        result["fusion_auc"] = round(auc_full, 4)

        # Verdict for this adversarial method
        if auc_fd < 0.70 and auc_full > 0.80:
            result["verdict"] = "PARTIAL_EVASION — first-digit evaded but fusion catches it"
        elif auc_full < 0.70:
            result["verdict"] = "FULL_EVASION — adversary evades all detectors"
        else:
            result["verdict"] = "DETECTION_HOLDS — adversary fails to evade"

        print(f"  Verdict: {result['verdict']}")
        all_results.append(result)

    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed:.1f}s")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "h24_adversarial.json"
    out_path.write_text(
        json.dumps({"results": all_results, "elapsed_s": round(elapsed, 1)}, indent=2),
        encoding="utf-8",
    )
    print(f"Results saved: {out_path}")


if __name__ == "__main__":
    main()
