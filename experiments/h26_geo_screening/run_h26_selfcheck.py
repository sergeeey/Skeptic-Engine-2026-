"""H26 Self-Check — within-dataset consistency screening (no external reference).

Instead of comparing against PBMC3k (which causes domain-shift false positives),
this approach checks each dataset's INTERNAL consistency:
  1. Split cells 50/50
  2. Train IF on half A
  3. Score half B
  4. Train IF on half B
  5. Score half A
  6. If anomaly rates are symmetric and low → CLEAN
  7. If asymmetric or high → dataset may contain mixed fabricated cells

WHY: Cross-dataset comparison flags tissue differences as anomalies (83% FPR).
Self-check avoids this by never comparing different biological contexts.
Trade-off: cannot detect WHOLESALE fabrication (all cells fake), only MIXED.

Usage:
    python experiments/h26_geo_screening/run_h26_selfcheck.py
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
sys.path.insert(0, str(SRC_DIR))

from digit_features import extract_features_per_sample
from isolation_forest import cell_level_features
from skeptic_toolkit.verdict import VerdictLevel, make_verdict

RESULTS_DIR = Path(__file__).resolve().parent / "results"
DATA_DIR = Path(__file__).resolve().parent / "data" / "curated"
MAX_CELLS = 5000


def download_and_load(url: str, dataset_id: str) -> np.ndarray | None:
    """Download 10x tar.gz, extract, load as cells × genes matrix."""
    dest_dir = DATA_DIR / dataset_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Check if already extracted
    for mtx in dest_dir.rglob("matrix.mtx*"):
        mtx_path = mtx
        break
    else:
        tar_path = dest_dir / "matrix.tar.gz"
        if not tar_path.exists():
            try:
                req = Request(url, headers={"User-Agent": "SkepticEngine/0.1"})
                with urlopen(req, timeout=120) as resp:
                    tar_path.write_bytes(resp.read())
            except Exception as e:
                print(f"download FAILED ({e})")
                return None
        try:
            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extractall(dest_dir, filter="data")
        except Exception as e:
            print(f"extract FAILED ({e})")
            return None
        for mtx in dest_dir.rglob("matrix.mtx*"):
            mtx_path = mtx
            break
        else:
            return None

    try:
        sparse = mmread(str(mtx_path))
        mat = sparse.toarray().T.astype(np.int64)
        return mat
    except Exception as e:
        print(f"load FAILED ({e})")
        return None


def selfcheck_score(matrix: np.ndarray, seed: int = 42) -> dict:
    """Run symmetric self-consistency check on a single dataset.

    Split cells 50/50, train IF on each half, score the other.
    A consistent dataset yields symmetric, low anomaly rates.
    """
    rng = np.random.default_rng(seed)
    n = matrix.shape[0]
    idx = rng.permutation(n)
    half = n // 2

    splits = {
        "A": matrix[idx[:half]],
        "B": matrix[idx[half : half * 2]],
    }

    anomaly_rates = {}
    for train_name, test_name in [("A", "B"), ("B", "A")]:
        train_mat = splits[train_name]
        test_mat = splits[test_name]

        # Extract features
        train_benford = extract_features_per_sample(train_mat)
        train_cell = cell_level_features(train_mat)
        train_feat = np.hstack([train_benford, train_cell])

        test_benford = extract_features_per_sample(test_mat)
        test_cell = cell_level_features(test_mat)
        test_feat = np.hstack([test_benford, test_cell])

        # Scale + IF
        scaler = StandardScaler()
        train_scaled = scaler.fit_transform(train_feat)
        test_scaled = scaler.transform(test_feat)

        iso = IsolationForest(n_estimators=200, contamination="auto", random_state=42, n_jobs=-1)
        iso.fit(train_scaled)

        train_scores = iso.decision_function(train_scaled)
        test_scores = iso.decision_function(test_scaled)

        # Anomaly rate: fraction of test cells below 2σ threshold
        threshold = train_scores.mean() - 2 * train_scores.std()
        frac_anom = float((test_scores < threshold).mean())
        anomaly_rates[f"train_{train_name}_test_{test_name}"] = frac_anom

    # Symmetry check
    rate_ab = anomaly_rates["train_A_test_B"]
    rate_ba = anomaly_rates["train_B_test_A"]
    mean_rate = (rate_ab + rate_ba) / 2
    asymmetry = abs(rate_ab - rate_ba)

    # Verdict: high mean anomaly OR high asymmetry → suspicious
    # WHY: clean data should have symmetric, low anomaly rates (~2-5%)
    # Fabricated mixed data will have asymmetric rates (one half has more fakes)
    risk = min(mean_rate * 5, 1.0)  # scale: 0.20 mean_rate → risk 1.0
    if asymmetry > 0.10:
        risk = max(risk, 0.5)  # asymmetry is suspicious even if mean is low

    return {
        "anomaly_rate_AB": round(rate_ab, 4),
        "anomaly_rate_BA": round(rate_ba, 4),
        "mean_anomaly_rate": round(mean_rate, 4),
        "asymmetry": round(asymmetry, 4),
        "risk_score": round(risk, 4),
    }


def main() -> None:
    start = time.time()

    curated_path = Path(__file__).resolve().parent / "curated_datasets.json"
    curated = json.loads(curated_path.read_text(encoding="utf-8"))
    datasets = [d for d in curated["datasets"] if d["format"] == "10x_mtx_tar"]

    print("=" * 70)
    print("H26 SELF-CHECK — Within-Dataset Consistency Screening")
    print("=" * 70)
    print(f"  Datasets: {len(datasets)}")
    print("  Method: symmetric split-half IF consistency")
    print("  No external reference needed — each dataset checks itself\n")

    results = []
    for ds in datasets:
        ds_id = ds["id"]
        print(f"  {ds_id}...", end=" ", flush=True)

        matrix = download_and_load(ds["url"], ds_id)
        if matrix is None:
            results.append({"id": ds_id, "name": ds["name"], "verdict": "SKIP"})
            continue

        if matrix.shape[0] > MAX_CELLS:
            rng = np.random.default_rng(42)
            idx = rng.choice(matrix.shape[0], MAX_CELLS, replace=False)
            matrix = matrix[idx]

        if matrix.shape[0] < 100:
            print(f"SKIP (too few cells: {matrix.shape[0]})")
            results.append(
                {"id": ds_id, "name": ds["name"], "verdict": "SKIP", "reason": "too_few"}
            )
            continue

        scores = selfcheck_score(matrix)
        verdict = make_verdict(scores["risk_score"], threshold=0.55, uncertainty_band=0.20)

        result = {
            "id": ds_id,
            "name": ds["name"],
            "n_cells": int(matrix.shape[0]),
            "n_genes": int(matrix.shape[1]),
            "verdict": verdict.level.value,
            **scores,
        }
        results.append(result)
        print(
            f"{verdict.level.value} "
            f"(rate_AB={scores['anomaly_rate_AB']:.3f} "
            f"rate_BA={scores['anomaly_rate_BA']:.3f} "
            f"asym={scores['asymmetry']:.3f} "
            f"risk={scores['risk_score']:.3f})"
        )

    # Summary
    elapsed = time.time() - start
    processed = [r for r in results if r["verdict"] != "SKIP"]
    n_clean = sum(1 for r in processed if r["verdict"] == "CLEAN")
    n_uncertain = sum(1 for r in processed if r["verdict"] == "UNCERTAIN")
    n_flagged = sum(1 for r in processed if r["verdict"] == "FLAGGED")

    print("\n" + "=" * 70)
    print("SELF-CHECK SUMMARY")
    print("=" * 70)
    print(f"  Processed: {len(processed)}")
    print(f"  CLEAN:     {n_clean}")
    print(f"  UNCERTAIN: {n_uncertain}")
    print(f"  FLAGGED:   {n_flagged}")
    fpr = n_flagged / max(len(processed), 1)
    print(f"  False positive rate: {fpr:.1%}")
    print(f"  Elapsed: {elapsed:.0f}s")

    if n_flagged == 0 and len(processed) >= 5:
        conclusion = (
            f"CLEAN_SWEEP — all {len(processed)} datasets pass self-consistency check. "
            f"No evidence of mixed fabrication. FPR = 0%."
        )
    elif fpr < 0.10:
        conclusion = f"LOW_FLAG — {n_flagged}/{len(processed)} flagged. Acceptable FPR."
    else:
        conclusion = f"HIGH_FLAG — {fpr:.0%} FPR. Calibration or method issue."

    print(f"\nCONCLUSION: {conclusion}")

    output = {
        "experiment": "H26_selfcheck_screening",
        "method": "symmetric_split_half_IF_consistency",
        "n_datasets": len(datasets),
        "n_processed": len(processed),
        "n_clean": n_clean,
        "n_uncertain": n_uncertain,
        "n_flagged": n_flagged,
        "false_positive_rate": round(fpr, 4),
        "conclusion": conclusion,
        "results": results,
        "elapsed_s": round(elapsed, 1),
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "h26_selfcheck_screening.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Results saved: {out_path}")


if __name__ == "__main__":
    main()
