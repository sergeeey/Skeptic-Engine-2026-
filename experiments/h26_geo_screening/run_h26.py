"""H26 — GEO Screening: Scan Real scRNA-seq Datasets for Statistical Anomalies.

Applies H24 Benford + cell-level feature pipeline to real datasets from GEO.
Uses PBMC3k as a "clean" reference and scores each dataset via IsolationForest.

Pipeline:
  1. Search GEO for scRNA-seq datasets
  2. Download supplementary count matrices
  3. Extract Benford + cell-level features (29 per cell)
  4. Train IsolationForest on PBMC3k reference
  5. Score and rank each GEO dataset
  6. Output: ranked list of anomalous datasets

Usage:
    python experiments/h26_geo_screening/run_h26.py [max_datasets]
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "h24_benford_scrna"))

from digit_features import extract_features_per_sample
from format_loaders import load_count_matrix
from geo_api import (
    download_file,
    find_count_matrix_file,
    get_supplementary_files,
    search_geo_scrna,
)
from isolation_forest import cell_level_features

RESULTS_DIR = Path(__file__).resolve().parent / "results"
DATA_DIR = Path(__file__).resolve().parent / "data"
CACHE_DIR = DATA_DIR / "geo_cache"
H24_DATA = Path(__file__).resolve().parents[1] / "h24_benford_scrna" / "data"


def _load_pbmc3k_reference() -> np.ndarray:
    """Load PBMC3k as reference dataset."""
    from scipy.io import mmread

    mtx_path = H24_DATA / "filtered_gene_bc_matrices" / "hg19" / "matrix.mtx"
    if not mtx_path.exists():
        # Try downloading
        from run_h24 import _download_pbmc3k

        _download_pbmc3k()
    sparse = mmread(str(mtx_path))
    return sparse.toarray().T.astype(np.int64)


def _extract_combined_features(matrix: np.ndarray) -> np.ndarray:
    """Extract 29 combined features (21 Benford + 8 cell-level) per cell."""
    benford = extract_features_per_sample(matrix)
    cell = cell_level_features(matrix)
    return np.hstack([benford, cell])


def main() -> None:
    max_datasets = 30
    for arg in sys.argv[1:]:
        try:
            max_datasets = int(arg)
            break
        except ValueError:
            pass

    print("=" * 70)
    print(f"H26 — GEO Screening: Scan {max_datasets} scRNA-seq Datasets")
    print("=" * 70)
    t0 = time.time()

    # Step 1: Load reference
    print("\n[1/5] Loading PBMC3k reference...")
    ref_matrix = _load_pbmc3k_reference()
    ref_features = _extract_combined_features(ref_matrix)
    print(
        f"  Reference: {ref_matrix.shape[0]} cells × {ref_matrix.shape[1]} genes → {ref_features.shape} features"
    )

    # Step 2: Train anomaly detector on reference
    print("\n[2/5] Training IsolationForest on reference features...")
    scaler = StandardScaler()
    ref_scaled = scaler.fit_transform(ref_features)
    iso = IsolationForest(n_estimators=200, contamination=0.05, random_state=42, n_jobs=-1)
    iso.fit(ref_scaled)
    ref_scores = iso.decision_function(ref_scaled)
    print(f"  Reference anomaly score: mean={ref_scores.mean():.4f} std={ref_scores.std():.4f}")

    # Step 3: Search GEO
    print(f"\n[3/5] Searching GEO for scRNA-seq datasets (max {max_datasets})...")
    gse_list = search_geo_scrna(max_results=max_datasets * 3)
    print(f"  Found {len(gse_list)} GSE accessions")

    # Step 4: Download and score each dataset
    print(f"\n[4/5] Processing datasets...")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    dataset_results = []
    n_downloaded = 0
    n_failed = 0

    for gse in gse_list:
        if len(dataset_results) >= max_datasets:
            break

        print(f"\n  --- {gse} ---")

        # Find supplementary files
        files = get_supplementary_files(gse)
        if not files:
            print(f"    No supplementary files found")
            n_failed += 1
            continue

        # Find best count matrix file
        matrix_file = find_count_matrix_file(files)
        if not matrix_file:
            print(f"    No count matrix found in {len(files)} files")
            n_failed += 1
            continue

        # Download
        dest = CACHE_DIR / gse / matrix_file["name"]
        if not download_file(matrix_file["url"], dest):
            print(f"    Download failed")
            n_failed += 1
            continue
        n_downloaded += 1

        # Handle tar archives: extract and find mtx inside
        if dest.name.endswith(".tar"):
            import tarfile

            try:
                extract_dir = dest.parent / "extracted"
                extract_dir.mkdir(exist_ok=True)
                with tarfile.open(dest, "r") as tar:
                    tar.extractall(extract_dir, filter="data")
                # Find first mtx or h5 file
                from glob import glob

                candidates = list(extract_dir.rglob("*.mtx*")) + list(extract_dir.rglob("*.h5"))
                if candidates:
                    dest = candidates[0]
                    print(f"    Extracted: {dest.name}")
                else:
                    print(f"    No count matrix in tar archive")
                    n_failed += 1
                    continue
            except Exception as e:
                print(f"    Tar extraction failed: {e}")
                n_failed += 1
                continue

        # Load
        matrix = load_count_matrix(dest, max_cells=5000)
        if matrix is None:
            print(f"    Failed to load matrix")
            n_failed += 1
            continue

        if matrix.shape[0] < 50 or matrix.shape[1] < 100:
            print(f"    Matrix too small: {matrix.shape}")
            n_failed += 1
            continue

        print(f"    Loaded: {matrix.shape[0]} cells × {matrix.shape[1]} genes")

        # Extract features
        try:
            features = _extract_combined_features(matrix)
            features_scaled = scaler.transform(features)
            scores = iso.decision_function(features_scaled)
        except Exception as e:
            print(f"    Feature extraction failed: {e}")
            n_failed += 1
            continue

        # Compute dataset-level scores
        median_score = float(np.median(scores))
        frac_anomalous = float((scores < ref_scores.mean() - 2 * ref_scores.std()).mean())

        # Benford chi2 at dataset level
        from digit_features import chi2_vs_benford, first_digit_frequencies, BENFORD_FIRST

        all_values = matrix.flatten()
        fd_freq = first_digit_frequencies(all_values)
        chi2_fd = chi2_vs_benford(fd_freq, BENFORD_FIRST)

        result = {
            "accession": gse,
            "n_cells": matrix.shape[0],
            "n_genes": matrix.shape[1],
            "format": matrix_file["name"],
            "median_anomaly_score": round(median_score, 4),
            "frac_anomalous_cells": round(frac_anomalous, 4),
            "dataset_chi2_first_digit": round(chi2_fd, 6),
            "mean_fd1": round(float(fd_freq[0]), 4),
        }
        dataset_results.append(result)
        print(
            f"    Score: median={median_score:.4f} frac_anomalous={frac_anomalous:.3f} chi2={chi2_fd:.6f}"
        )

    # Step 5: Rank and report
    print(f"\n[5/5] Ranking datasets...")
    dataset_results.sort(key=lambda r: r["median_anomaly_score"])

    for rank, result in enumerate(dataset_results):
        result["rank"] = rank + 1

    elapsed = time.time() - t0

    # Score distribution stats
    if dataset_results:
        all_scores = [r["median_anomaly_score"] for r in dataset_results]
        score_dist = {
            "mean": round(float(np.mean(all_scores)), 4),
            "std": round(float(np.std(all_scores)), 4),
            "min": round(float(np.min(all_scores)), 4),
            "max": round(float(np.max(all_scores)), 4),
        }
    else:
        score_dist = {}

    # Verdict
    n_datasets = len(dataset_results)
    n_flagged = sum(1 for r in dataset_results if r["frac_anomalous_cells"] > 0.20)

    if n_datasets == 0:
        verdict = "NO_DATA — no datasets successfully processed"
    elif n_flagged > 0:
        verdict = f"SCREENING — {n_flagged}/{n_datasets} datasets show elevated anomaly rates (>20% cells flagged)"
    else:
        verdict = f"CLEAN — all {n_datasets} datasets within expected anomaly bounds"

    print(f"\n{'=' * 70}")
    print(f"Processed: {n_datasets} datasets ({n_downloaded} downloaded, {n_failed} failed)")
    print(f"Flagged (>20% anomalous cells): {n_flagged}")
    print(f"VERDICT: {verdict}")
    print(f"Total time: {elapsed:.1f}s")

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "experiment": "H26_geo_screening",
        "n_datasets_searched": len(gse_list),
        "n_datasets_processed": n_datasets,
        "n_datasets_downloaded": n_downloaded,
        "n_datasets_failed": n_failed,
        "reference_dataset": "PBMC3k_10x",
        "reference_n_cells": ref_matrix.shape[0],
        "scoring_method": "IsolationForest_trained_on_PBMC3k",
        "flagged_datasets": [r for r in dataset_results if r["frac_anomalous_cells"] > 0.20],
        "all_datasets": dataset_results,
        "score_distribution": score_dist,
        "n_flagged": n_flagged,
        "verdict": verdict,
        "elapsed_s": round(elapsed, 1),
    }

    out_path = RESULTS_DIR / "h26_results.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Results saved: {out_path}")


if __name__ == "__main__":
    main()
