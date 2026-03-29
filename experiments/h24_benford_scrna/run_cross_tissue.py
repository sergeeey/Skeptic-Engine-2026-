"""H24 Cross-Tissue Test — Does artifact detection generalize beyond PBMC?

Tests the PBMC3k-trained model on a brain dataset (10x Genomics 1.3M brain, 20k subset).
Key question: is the artifact signal tissue-specific or universal?

Usage:
    python experiments/h24_benford_scrna/run_cross_tissue.py
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

from digit_features import extract_features_per_sample
from fabrication import FABRICATION_METHODS
from isolation_forest import cell_level_features

DATA_DIR = Path(__file__).resolve().parent / "data"
RESULTS_DIR = Path(__file__).resolve().parent / "results"

# 10x Genomics brain 1.3M neuron dataset — filtered 20k subset
BRAIN_URL = "https://cf.10xgenomics.com/samples/cell-exp/1.3.0/1M_neurons/1M_neurons_filtered_gene_bc_matrices_h5.h5"
# Smaller: 10x Genomics 5k brain cells
BRAIN_5K_URL = "https://cf.10xgenomics.com/samples/cell-exp/6.0.0/5k_mouse_brain_CRISPR_A_1M/5k_mouse_brain_CRISPR_A_1M_filtered_feature_bc_matrix.h5"
# Simplest: neuron 900 cells (tiny)
NEURON_900_URL = "https://cf.10xgenomics.com/samples/cell-exp/2.1.0/neurons_900/neurons_900_filtered_gene_bc_matrices.tar.gz"


def _download_brain_dataset() -> np.ndarray:
    """Download and load a brain scRNA-seq dataset."""
    import urllib.request

    # Try neuron 900 first (smallest, fastest)
    tar_path = DATA_DIR / "neurons_900_filtered_gene_bc_matrices.tar.gz"
    mtx_dir = DATA_DIR / "filtered_gene_bc_matrices" / "mm10"

    if not (mtx_dir / "matrix.mtx").exists():
        # Check if we already have the tar
        if not tar_path.exists():
            print("  Downloading 10x Genomics neuron 900 dataset...")
            req = urllib.request.Request(NEURON_900_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                tar_path.parent.mkdir(parents=True, exist_ok=True)
                tar_path.write_bytes(resp.read())
            print(f"  Downloaded: {tar_path} ({tar_path.stat().st_size / 1e6:.1f}MB)")

        # Extract
        import tarfile

        print("  Extracting...")
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(DATA_DIR, filter="data")

    if not (mtx_dir / "matrix.mtx").exists():
        raise FileNotFoundError(f"Expected matrix.mtx in {mtx_dir}")

    print(f"  Loading from {mtx_dir}")
    sparse = mmread(str(mtx_dir / "matrix.mtx"))
    return sparse.toarray().T.astype(np.int64)


def _extract_all(matrix: np.ndarray) -> np.ndarray:
    benford = extract_features_per_sample(matrix)
    cell = cell_level_features(matrix)
    return np.hstack([benford, cell])


def main() -> None:
    print("=" * 70)
    print("H24 Cross-Tissue Test — PBMC (human) ↔ Brain (mouse)")
    print("=" * 70)
    t0 = time.time()

    # Load PBMC3k (human blood)
    print("\n[1/4] Loading PBMC3k (human)...")
    pbmc_mtx = DATA_DIR / "filtered_gene_bc_matrices" / "hg19" / "matrix.mtx"
    pbmc = mmread(str(pbmc_mtx)).toarray().T.astype(np.int64)
    print(f"  PBMC3k: {pbmc.shape[0]} cells × {pbmc.shape[1]} genes")

    # Load brain (mouse)
    print("\n[2/4] Loading brain dataset (mouse)...")
    brain = _download_brain_dataset()
    print(f"  Brain: {brain.shape[0]} cells × {brain.shape[1]} genes")

    all_results = []

    for method_name, fab_fn in FABRICATION_METHODS.items():
        print(f"\n{'=' * 50}")
        print(f"Fabrication: {method_name}")
        print(f"{'=' * 50}")

        rng_seed = 2026

        # ── Within PBMC (baseline) ──
        pbmc_real_feat = _extract_all(pbmc)
        pbmc_fake = fab_fn(pbmc, rng=np.random.default_rng(rng_seed))
        pbmc_fake_feat = _extract_all(pbmc_fake)
        X_pbmc = np.vstack([pbmc_real_feat, pbmc_fake_feat])
        y_pbmc = np.concatenate([np.zeros(len(pbmc)), np.ones(len(pbmc))])

        splitter = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        train_idx, test_idx = next(splitter.split(X_pbmc, y_pbmc))
        rf_pbmc = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        rf_pbmc.fit(X_pbmc[train_idx], y_pbmc[train_idx])
        within_pbmc = roc_auc_score(y_pbmc[test_idx], rf_pbmc.predict_proba(X_pbmc[test_idx])[:, 1])
        print(f"  Within PBMC3k:       AUC={within_pbmc:.4f}")

        # ── Within Brain ──
        brain_real_feat = _extract_all(brain)
        brain_fake = fab_fn(brain, rng=np.random.default_rng(rng_seed))
        brain_fake_feat = _extract_all(brain_fake)
        X_brain = np.vstack([brain_real_feat, brain_fake_feat])
        y_brain = np.concatenate([np.zeros(len(brain)), np.ones(len(brain))])

        train_idx_b, test_idx_b = next(splitter.split(X_brain, y_brain))
        rf_brain = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        rf_brain.fit(X_brain[train_idx_b], y_brain[train_idx_b])
        within_brain = roc_auc_score(
            y_brain[test_idx_b], rf_brain.predict_proba(X_brain[test_idx_b])[:, 1]
        )
        print(f"  Within Brain:        AUC={within_brain:.4f}")

        # ── Cross-tissue: PBMC-trained → Brain test ──
        cross_p2b = roc_auc_score(y_brain, rf_pbmc.predict_proba(X_brain)[:, 1])
        print(f"  PBMC → Brain:        AUC={cross_p2b:.4f}  ← CROSS-TISSUE TEST")

        # ── Cross-tissue: Brain-trained → PBMC test ──
        cross_b2p = roc_auc_score(y_pbmc, rf_brain.predict_proba(X_pbmc)[:, 1])
        print(f"  Brain → PBMC:        AUC={cross_b2p:.4f}  ← CROSS-TISSUE TEST")

        all_results.append(
            {
                "method": method_name,
                "within_pbmc": round(within_pbmc, 4),
                "within_brain": round(within_brain, 4),
                "cross_pbmc_to_brain": round(cross_p2b, 4),
                "cross_brain_to_pbmc": round(cross_b2p, 4),
            }
        )

    # Summary
    print(f"\n{'=' * 70}")
    print("CROSS-TISSUE SUMMARY (RF AUC)")
    print(f"{'=' * 70}")
    print(f"{'Method':<14} {'W-PBMC':>8} {'W-Brain':>8} {'P→B':>8} {'B→P':>8}")
    print("-" * 50)
    for r in all_results:
        print(
            f"{r['method']:<14} {r['within_pbmc']:>8.4f} {r['within_brain']:>8.4f} "
            f"{r['cross_pbmc_to_brain']:>8.4f} {r['cross_brain_to_pbmc']:>8.4f}"
        )

    # Verdict
    cross_aucs = []
    for r in all_results:
        cross_aucs.extend([r["cross_pbmc_to_brain"], r["cross_brain_to_pbmc"]])
    min_cross = min(cross_aucs)
    mean_cross = np.mean(cross_aucs)

    if min_cross >= 0.80:
        verdict = "CROSS-TISSUE GENERALIZES — artifact signal is tissue-independent"
    elif mean_cross >= 0.70:
        verdict = "PARTIAL GENERALIZATION — some artifact types transfer across tissues"
    else:
        verdict = "NO CROSS-TISSUE GENERALIZATION — artifact signal is tissue-specific"

    print(f"\nMin cross-tissue AUC: {min_cross:.4f}")
    print(f"Mean cross-tissue AUC: {mean_cross:.4f}")
    print(f"VERDICT: {verdict}")

    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed:.1f}s")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "experiment": "H24_cross_tissue",
        "tissue_a": "PBMC3k_human",
        "tissue_b": "neurons_900_mouse",
        "results": all_results,
        "min_cross_auc": round(min_cross, 4),
        "mean_cross_auc": round(mean_cross, 4),
        "verdict": verdict,
        "elapsed_s": round(elapsed, 1),
    }
    (RESULTS_DIR / "h24_cross_tissue.json").write_text(
        json.dumps(output, indent=2), encoding="utf-8"
    )
    print(f"Results saved: {RESULTS_DIR / 'h24_cross_tissue.json'}")


if __name__ == "__main__":
    main()
