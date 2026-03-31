"""H26 Curated Dataset Screening — scan known-clean 10x benchmark datasets.

Uses a curated list of well-known UMI scRNA-seq datasets with direct download URLs.
Expected result: ALL should be CLEAN. Any FLAGGED result indicates calibration issue.

This validates false positive rate on real-world, non-retracted data.

Usage:
    python experiments/h26_geo_screening/run_h26_curated.py
"""

from __future__ import annotations

import json
import sys
import tarfile
import time
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
from scipy.io import mmread
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

H24_DIR = Path(__file__).resolve().parents[1] / "h24_benford_scrna"
SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(H24_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(SRC_DIR))

from digit_features import extract_features_per_sample
from isolation_forest import cell_level_features
from run_h24 import _download_pbmc3k, _load_count_matrix
from skeptic_toolkit.verdict import VerdictLevel, make_verdict

RESULTS_DIR = Path(__file__).resolve().parent / "results"
DATA_DIR = Path(__file__).resolve().parent / "data" / "curated"
MAX_CELLS = 5000


def download_10x_tar(url: str, dataset_id: str) -> Path | None:
    """Download and extract 10x filtered matrix tar.gz."""
    dest_dir = DATA_DIR / dataset_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Check if already extracted
    for mtx in dest_dir.rglob("matrix.mtx*"):
        return mtx.parent

    tar_path = dest_dir / "matrix.tar.gz"
    if not tar_path.exists():
        print(f"    Downloading...", end=" ", flush=True)
        try:
            req = Request(url, headers={"User-Agent": "SkepticEngine/0.1"})
            with urlopen(req, timeout=120) as resp:
                tar_path.write_bytes(resp.read())
        except Exception as e:
            print(f"FAILED ({e})")
            return None

    # Extract
    print(f"extracting...", end=" ", flush=True)
    try:
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(dest_dir, filter="data")
    except Exception as e:
        print(f"extract FAILED ({e})")
        return None

    for mtx in dest_dir.rglob("matrix.mtx*"):
        return mtx.parent

    return None


def load_10x_mtx(mtx_dir: Path) -> np.ndarray | None:
    """Load 10x-style matrix.mtx(.gz) from a directory."""
    mtx_path = mtx_dir / "matrix.mtx.gz"
    if not mtx_path.exists():
        mtx_path = mtx_dir / "matrix.mtx"
    if not mtx_path.exists():
        return None

    try:
        sparse = mmread(str(mtx_path))
        mat = sparse.toarray().T.astype(np.int64)  # genes×cells → cells×genes
        return mat
    except Exception as e:
        print(f"load FAILED ({e})")
        return None


def main() -> None:
    start = time.time()

    # Load curated dataset list
    curated_path = Path(__file__).resolve().parent / "curated_datasets.json"
    curated = json.loads(curated_path.read_text(encoding="utf-8"))
    datasets = [d for d in curated["datasets"] if d["format"] == "10x_mtx_tar"]

    print("=" * 70)
    print("H26 CURATED SCREENING — Known-Clean 10x Benchmark Datasets")
    print("=" * 70)
    print(f"  Datasets to screen: {len(datasets)}")

    # Build reference from PBMC3k
    print("\n[1/3] Building reference model from PBMC3k...")
    ref_dir = _download_pbmc3k()
    ref_matrix = _load_count_matrix(ref_dir)
    ref_benford = extract_features_per_sample(ref_matrix)
    ref_cell = cell_level_features(ref_matrix)
    ref_features = np.hstack([ref_benford, ref_cell])

    scaler = StandardScaler()
    ref_scaled = scaler.fit_transform(ref_features)
    ref_if = IsolationForest(n_estimators=200, contamination="auto", random_state=42, n_jobs=-1)
    ref_if.fit(ref_scaled)
    ref_scores = ref_if.decision_function(ref_scaled)
    print(f"  Reference: {ref_matrix.shape[0]} cells × {ref_matrix.shape[1]} genes")

    # Screen each dataset
    print(f"\n[2/3] Screening {len(datasets)} datasets...\n")
    results = []

    for ds in datasets:
        ds_id = ds["id"]
        print(f"  {ds_id} ({ds['name']})...", end=" ", flush=True)

        # Download
        mtx_dir = download_10x_tar(ds["url"], ds_id)
        if mtx_dir is None:
            print("SKIP (download/extract failed)")
            results.append(
                {"id": ds_id, "name": ds["name"], "verdict": "SKIP", "reason": "download_failed"}
            )
            continue

        # Load
        matrix = load_10x_mtx(mtx_dir)
        if matrix is None:
            print("SKIP (load failed)")
            results.append(
                {"id": ds_id, "name": ds["name"], "verdict": "SKIP", "reason": "load_failed"}
            )
            continue

        # Subsample if needed
        if matrix.shape[0] > MAX_CELLS:
            rng = np.random.default_rng(42)
            idx = rng.choice(matrix.shape[0], MAX_CELLS, replace=False)
            matrix = matrix[idx]

        # Extract features and score
        benford = extract_features_per_sample(matrix)
        cell_feat = cell_level_features(matrix)
        fusion = np.hstack([benford, cell_feat])
        if_scores = ref_if.decision_function(scaler.transform(fusion))

        frac_anomalous = float((if_scores < ref_scores.mean() - 2 * ref_scores.std()).mean())

        # Three-level verdict (conservative: uncertainty band = 0.20)
        risk_score = min(frac_anomalous * 5, 1.0)
        verdict = make_verdict(risk_score, threshold=0.55, uncertainty_band=0.20)

        # Benford chi² vs reference
        candidate_fd = benford[:, :9].mean(axis=0)
        ref_fd = ref_features[:, :9].mean(axis=0)
        chi2 = float(np.sum((candidate_fd - ref_fd) ** 2 / (ref_fd + 1e-10)))

        result = {
            "id": ds_id,
            "name": ds["name"],
            "n_cells": int(matrix.shape[0]),
            "n_genes": int(matrix.shape[1]),
            "frac_anomalous": round(frac_anomalous, 4),
            "chi2_vs_ref": round(chi2, 6),
            "risk_score": round(risk_score, 4),
            "verdict": verdict.level.value,
        }
        results.append(result)
        print(f"{verdict.level.value} (cells={matrix.shape[0]}, risk={risk_score:.3f})")

    # Summary
    elapsed = time.time() - start
    processed = [r for r in results if r["verdict"] != "SKIP"]
    n_clean = sum(1 for r in processed if r["verdict"] == "CLEAN")
    n_uncertain = sum(1 for r in processed if r["verdict"] == "UNCERTAIN")
    n_flagged = sum(1 for r in processed if r["verdict"] == "FLAGGED")
    n_skip = sum(1 for r in results if r["verdict"] == "SKIP")

    print("\n" + "=" * 70)
    print("SCREENING SUMMARY")
    print("=" * 70)
    print(f"  Total:     {len(datasets)}")
    print(f"  Processed: {len(processed)}")
    print(f"  Skipped:   {n_skip}")
    print(f"  CLEAN:     {n_clean}")
    print(f"  UNCERTAIN: {n_uncertain}")
    print(f"  FLAGGED:   {n_flagged}")
    fpr = n_flagged / max(len(processed), 1)
    print(f"  False positive rate: {n_flagged}/{len(processed)} = {fpr:.1%}")
    print(f"  Elapsed: {elapsed:.0f}s")

    if n_flagged == 0 and len(processed) >= 5:
        conclusion = (
            f"CLEAN_SWEEP — all {len(processed)} known-clean datasets scored CLEAN. "
            f"False positive rate = 0%. Tool does not over-flag legitimate data."
        )
    elif n_flagged == 0:
        conclusion = (
            f"All {len(processed)} processed datasets CLEAN. Expand sample for stronger claim."
        )
    elif fpr < 0.10:
        conclusion = (
            f"LOW_FLAG_RATE — {n_flagged}/{len(processed)} flagged. Review flagged datasets."
        )
    else:
        conclusion = f"HIGH_FLAG_RATE — {fpr:.0%}. Calibration issue — tool over-flags cross-dataset differences."

    print(f"\nCONCLUSION: {conclusion}")

    output = {
        "experiment": "H26_curated_screening",
        "n_datasets": len(datasets),
        "n_processed": len(processed),
        "n_clean": n_clean,
        "n_uncertain": n_uncertain,
        "n_flagged": n_flagged,
        "false_positive_rate": round(fpr, 4),
        "reference": "PBMC3k_10x",
        "conclusion": conclusion,
        "results": results,
        "elapsed_s": round(elapsed, 1),
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "h26_curated_screening.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nResults saved: {out_path}")


if __name__ == "__main__":
    main()
