"""H24+H21 Cross-Validation — Two datasets: PBMC3k + Kang2018 (GSE96583).

Tests whether Benford + IF fusion generalizes across datasets.
Key question: does a model trained on PBMC3k detect fabrication in Kang2018, and vice versa?

Usage:
    python experiments/h24_benford_scrna/run_crossval.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import h5py
import numpy as np
from scipy.io import mmread
from scipy.sparse import issparse
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedShuffleSplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

from digit_features import extract_features_per_sample
from fabrication import FABRICATION_METHODS
from isolation_forest import cell_level_features

DATA_DIR = Path(__file__).resolve().parent / "data"
RESULTS_DIR = Path(__file__).resolve().parent / "results"

KANG_CTRL_URL = "https://ndownloader.figshare.com/files/43108963"
KANG_STIM_URL = "https://ndownloader.figshare.com/files/43108966"


def _download_file(url: str, dest: Path) -> None:
    if dest.exists():
        return
    import urllib.request

    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  Downloading {dest.name}...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as out:
        out.write(resp.read())


def _load_h5_10x(path: Path) -> np.ndarray:
    """Load 10x-format HDF5 as dense int64 matrix (cells x genes)."""
    from scipy.sparse import csc_matrix

    with h5py.File(path, "r") as f:
        for group_name in ["matrix", "GRCh38", "hg19"]:
            if group_name in f:
                grp = f[group_name]
                break
        else:
            grp = f[list(f.keys())[0]]

        data = np.array(grp["data"])
        indices = np.array(grp["indices"])
        indptr = np.array(grp["indptr"])

        if "shape" in grp:
            shape = tuple(grp["shape"])
        else:
            # Infer shape: n_rows = max(indices)+1, n_cols = len(indptr)-1
            n_rows = int(indices.max()) + 1 if len(indices) > 0 else 0
            n_cols = len(indptr) - 1
            shape = (n_rows, n_cols)

        sparse = csc_matrix((data, indices, indptr), shape=shape)
        # Format: genes(rows) x cells(cols) → transpose to cells x genes
        return sparse.toarray().T.astype(np.int64)


def _load_pbmc3k() -> np.ndarray:
    """Load PBMC3k (already downloaded by run_h24.py)."""
    mtx_dir = DATA_DIR / "filtered_gene_bc_matrices" / "hg19"
    if not (mtx_dir / "matrix.mtx").exists():
        raise FileNotFoundError("Run run_h24.py first to download PBMC3k")
    sparse = mmread(str(mtx_dir / "matrix.mtx"))
    return sparse.toarray().T.astype(np.int64)


def _load_kang2018() -> np.ndarray:
    """Download and load Kang 2018 (GSE96583) ctrl + stim combined."""
    ctrl_path = DATA_DIR / "kang2018" / "pbmcs_ctrl.h5"
    stim_path = DATA_DIR / "kang2018" / "pbmcs_stim.h5"

    _download_file(KANG_CTRL_URL, ctrl_path)
    _download_file(KANG_STIM_URL, stim_path)

    ctrl = _load_h5_10x(ctrl_path)
    stim = _load_h5_10x(stim_path)
    print(f"  Kang ctrl: {ctrl.shape}, stim: {stim.shape}")

    # Combine ctrl + stim (same genes expected)
    if ctrl.shape[1] != stim.shape[1]:
        # Take minimum gene count
        min_genes = min(ctrl.shape[1], stim.shape[1])
        ctrl = ctrl[:, :min_genes]
        stim = stim[:, :min_genes]

    combined = np.vstack([ctrl, stim])
    return combined


def _extract_all_features(matrix: np.ndarray) -> np.ndarray:
    """Benford(21) + Cell-level(8) = 29 features."""
    benford = extract_features_per_sample(matrix)
    cell = cell_level_features(matrix)
    return np.hstack([benford, cell])


def _make_dataset(
    real_matrix: np.ndarray,
    method_name: str,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Create labeled feature matrix: real(0) + fabricated(1)."""
    fabricate_fn = FABRICATION_METHODS[method_name]
    fake_matrix = fabricate_fn(real_matrix, rng=rng)

    real_features = _extract_all_features(real_matrix)
    fake_features = _extract_all_features(fake_matrix)

    X = np.vstack([real_features, fake_features])
    y = np.concatenate([np.zeros(len(real_features)), np.ones(len(fake_features))])
    return X, y


def _evaluate(model, X_test: np.ndarray, y_test: np.ndarray) -> dict:
    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = model.predict(X_test)
    return {
        "auc": round(roc_auc_score(y_test, y_prob), 4),
        "ap": round(average_precision_score(y_test, y_prob), 4),
        "f1": round(f1_score(y_test, y_pred), 4),
        "n_test": len(y_test),
    }


def main() -> None:
    print("=" * 70)
    print("H24+H21 Cross-Validation: PBMC3k ↔ Kang2018")
    print("=" * 70)
    t0 = time.time()

    # Load both datasets
    print("\n[1/4] Loading PBMC3k...")
    pbmc3k = _load_pbmc3k()
    print(f"  PBMC3k: {pbmc3k.shape[0]} cells × {pbmc3k.shape[1]} genes")

    print("\n[2/4] Loading Kang2018 (GSE96583)...")
    kang = _load_kang2018()
    print(f"  Kang2018: {kang.shape[0]} cells × {kang.shape[1]} genes")

    # Subsample Kang to match PBMC3k size (for fair comparison)
    rng = np.random.default_rng(2026)
    if kang.shape[0] > pbmc3k.shape[0] * 2:
        idx = rng.choice(kang.shape[0], size=pbmc3k.shape[0], replace=False)
        kang_sub = kang[idx]
        print(f"  Kang2018 subsampled to {kang_sub.shape[0]} cells")
    else:
        kang_sub = kang

    # Align gene count (take minimum)
    min_genes = min(pbmc3k.shape[1], kang_sub.shape[1])
    pbmc3k_aligned = pbmc3k[:, :min_genes]
    kang_aligned = kang_sub[:, :min_genes]
    print(f"  Aligned to {min_genes} genes")

    all_results = []

    for method_name in FABRICATION_METHODS:
        print(f"\n{'=' * 60}")
        print(f"[3/4] Fabrication: {method_name}")
        print(f"{'=' * 60}")

        # Create datasets
        print("  Extracting features...")
        t1 = time.time()
        X_pbmc, y_pbmc = _make_dataset(pbmc3k_aligned, method_name, np.random.default_rng(2026))
        X_kang, y_kang = _make_dataset(kang_aligned, method_name, np.random.default_rng(2026))
        print(f"  Features ready ({time.time() - t1:.1f}s)")

        result = {"method": method_name}

        # --- Test A: Within-dataset (baseline) ---
        splitter = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)

        train_idx, test_idx = next(splitter.split(X_pbmc, y_pbmc))
        rf_pbmc = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        rf_pbmc.fit(X_pbmc[train_idx], y_pbmc[train_idx])
        within_pbmc = _evaluate(rf_pbmc, X_pbmc[test_idx], y_pbmc[test_idx])
        print(f"  Within PBMC3k:     AUC={within_pbmc['auc']:.4f}")

        train_idx, test_idx = next(splitter.split(X_kang, y_kang))
        rf_kang = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        rf_kang.fit(X_kang[train_idx], y_kang[train_idx])
        within_kang = _evaluate(rf_kang, X_kang[test_idx], y_kang[test_idx])
        print(f"  Within Kang2018:   AUC={within_kang['auc']:.4f}")

        # --- Test B: Cross-dataset generalization ---
        # Train on PBMC3k → test on ALL of Kang2018
        cross_pbmc_to_kang = _evaluate(rf_pbmc, X_kang, y_kang)
        print(f"  PBMC3k → Kang2018: AUC={cross_pbmc_to_kang['auc']:.4f}  ← KEY TEST")

        # Train on Kang2018 → test on ALL of PBMC3k
        cross_kang_to_pbmc = _evaluate(rf_kang, X_pbmc, y_pbmc)
        print(f"  Kang2018 → PBMC3k: AUC={cross_kang_to_pbmc['auc']:.4f}  ← KEY TEST")

        result["within_pbmc3k"] = within_pbmc
        result["within_kang2018"] = within_kang
        result["cross_pbmc_to_kang"] = cross_pbmc_to_kang
        result["cross_kang_to_pbmc"] = cross_kang_to_pbmc
        all_results.append(result)

    # Summary
    print(f"\n{'=' * 70}")
    print("CROSS-VALIDATION SUMMARY (RF AUC)")
    print(f"{'=' * 70}")
    print(f"{'Method':<14} {'Within-P':>10} {'Within-K':>10} {'P→K':>10} {'K→P':>10}")
    print("-" * 58)
    for r in all_results:
        print(
            f"{r['method']:<14} "
            f"{r['within_pbmc3k']['auc']:>10.4f} "
            f"{r['within_kang2018']['auc']:>10.4f} "
            f"{r['cross_pbmc_to_kang']['auc']:>10.4f} "
            f"{r['cross_kang_to_pbmc']['auc']:>10.4f}"
        )

    # Generalization verdict
    cross_aucs = []
    for r in all_results:
        cross_aucs.append(r["cross_pbmc_to_kang"]["auc"])
        cross_aucs.append(r["cross_kang_to_pbmc"]["auc"])

    min_cross = min(cross_aucs)
    mean_cross = sum(cross_aucs) / len(cross_aucs)

    if min_cross >= 0.80:
        verdict = "STRONG GENERALIZATION — cross-dataset AUC ≥ 0.80 for all methods. Paper-ready."
    elif mean_cross >= 0.75:
        verdict = (
            "MODERATE GENERALIZATION — most cross-dataset tests pass. Publishable with caveats."
        )
    elif mean_cross >= 0.65:
        verdict = "WEAK GENERALIZATION — some transfer, but dataset-specific features dominate."
    else:
        verdict = "NO GENERALIZATION — method is dataset-specific. Not publishable as general tool."

    print(f"\nMin cross-dataset AUC: {min_cross:.4f}")
    print(f"Mean cross-dataset AUC: {mean_cross:.4f}")
    print(f"VERDICT: {verdict}")

    elapsed = time.time() - t0
    print(f"Total time: {elapsed:.1f}s")

    # Save
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "experiment": "H24_H21_crossval",
        "datasets": ["PBMC3k", "Kang2018_GSE96583"],
        "min_cross_auc": round(min_cross, 4),
        "mean_cross_auc": round(mean_cross, 4),
        "verdict": verdict,
        "elapsed_s": round(elapsed, 1),
        "results": all_results,
    }
    out_path = RESULTS_DIR / "h24_h21_crossval.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nResults saved: {out_path}")


if __name__ == "__main__":
    main()
