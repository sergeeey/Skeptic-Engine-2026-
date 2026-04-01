"""H30 Syndrome Analysis on Retracted scRNA-seq Data (GSE160269).

Run syndrome layer on REAL retracted data. This is the ultimate validation.

Usage:
    python experiments/h30_retracted_validation/run_h30_syndrome.py
"""

import gzip
import json
import sys
import time

import numpy as np
from dataclasses import asdict
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"
H24 = Path(__file__).resolve().parents[1] / "h24_benford_scrna"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(H24))

from skeptic_toolkit.syndrome import build_pairwise_constraints, compute_syndrome_pairwise
from run_h24 import _download_pbmc3k, _load_count_matrix

RESULTS = Path(__file__).resolve().parent / "results"
DATA = Path(__file__).resolve().parent / "data" / "GSE160269"
MAX_CELLS = 3000
MAX_GENES = 2000


def load_umi_matrix(
    path: Path, max_cells: int = MAX_CELLS, max_genes: int = MAX_GENES
) -> tuple[np.ndarray, list[str]]:
    """Load space-separated UMI matrix (genes x cells)."""
    print(f"    Loading {path.name}...", end=" ", flush=True)
    rows = []
    gene_names = []
    with gzip.open(path, "rt") as f:
        _header = f.readline()  # cell barcodes
        for line in f:
            parts = line.split()
            gene_names.append(parts[0])
            rows.append([int(x) for x in parts[1:]])
            if len(rows) >= 30000:
                break

    mat = np.array(rows, dtype=np.int64).T  # genes x cells -> cells x genes
    print(f"{mat.shape[0]} cells x {mat.shape[1]} genes", end=" ", flush=True)

    if mat.shape[0] > max_cells:
        rng = np.random.default_rng(42)
        idx = rng.choice(mat.shape[0], max_cells, replace=False)
        mat = mat[idx]

    if mat.shape[1] > max_genes:
        var = mat.astype(np.float64).var(axis=0)
        top = np.argsort(var)[::-1][:max_genes]
        mat = mat[:, top]
        gene_names = [gene_names[i] for i in top]
    else:
        gene_names = gene_names[: mat.shape[1]]

    zero_frac = (mat == 0).mean()
    print(f"-> {mat.shape[0]}x{mat.shape[1]} (zeros={zero_frac:.2%})")
    return mat, gene_names


def main() -> None:
    t0 = time.time()
    print("=" * 70)
    print("H30 -- Syndrome Analysis on RETRACTED scRNA-seq (GSE160269)")
    print("=" * 70)

    # Reference: clean PBMC3k
    print("\n[1/3] Building reference from clean PBMC3k...")
    ref_full = _load_count_matrix(_download_pbmc3k())
    var = ref_full.astype(np.float64).var(axis=0)
    top_ref = np.argsort(var)[::-1][:MAX_GENES]
    ref = ref_full[:, top_ref].astype(np.float64)
    ref_genes = [f"ref_gene_{i}" for i in top_ref]
    print(f"  Reference: {ref.shape[0]}x{ref.shape[1]}")

    ref_model = build_pairwise_constraints(
        ref, feature_names=ref_genes, top_k=100, min_abs_rho=0.40, seed=42
    )
    ref_syn = compute_syndrome_pairwise(ref, ref_model)
    print(
        f"  Reference self-check: syndrome={ref_syn.syndrome_score:.4f} class={ref_syn.violation_class}"
    )

    # Analyze retracted datasets
    print("\n[2/3] Analyzing retracted GSE160269...")
    retracted_files = sorted(DATA.glob("GSE160269_UMI_matrix_*.txt.gz"))
    if not retracted_files:
        print("  No UMI matrices found. Download first.")
        return

    results = []
    results.append(
        {
            "dataset": "PBMC3k_reference",
            "type": "clean_reference",
            "syndrome": ref_syn.syndrome_score,
            "module_violation": ref_syn.module_violation_score,
            "violation_class": ref_syn.violation_class,
            "review_required": ref_syn.review_required,
        }
    )

    for fpath in retracted_files:
        cell_type = fpath.name.replace("GSE160269_UMI_matrix_", "").replace(".txt.gz", "")
        print(f"\n  --- {cell_type} (RETRACTED) ---")

        try:
            mat, gnames = load_umi_matrix(fpath)
        except Exception as e:
            print(f"    Load failed: {e}")
            results.append(
                {"dataset": f"GSE160269_{cell_type}", "type": "retracted", "error": str(e)}
            )
            continue

        print("    Building self-constraints...", end=" ", flush=True)
        self_model = build_pairwise_constraints(
            mat.astype(np.float64), feature_names=gnames, top_k=100, min_abs_rho=0.40, seed=42
        )

        self_syn = compute_syndrome_pairwise(mat.astype(np.float64), self_model)
        print(
            f"    Self-check: syndrome={self_syn.syndrome_score:.4f} class={self_syn.violation_class}"
        )

        top_info = []
        if self_syn.top_violated_pairs:
            for p in self_syn.top_violated_pairs[:5]:
                top_info.append(f"{p['feature_i']}<->{p['feature_j']} d={p['delta']:.3f}")

        results.append(
            {
                "dataset": f"GSE160269_{cell_type}",
                "type": "retracted",
                "n_cells": int(mat.shape[0]),
                "n_genes": int(mat.shape[1]),
                "n_constraints": len(self_model.pairwise),
                "n_modules": len(self_model.modules),
                "syndrome": self_syn.syndrome_score,
                "pairwise_violation": self_syn.pairwise_violation_score,
                "module_violation": self_syn.module_violation_score,
                "violation_class": self_syn.violation_class,
                "review_required": self_syn.review_required,
                "noise_sensitivity": self_syn.noise_sensitivity,
                "top_violated_pairs": top_info,
            }
        )

    # Summary
    elapsed = time.time() - t0
    print(f"\n{'=' * 70}")
    print("H30 RETRACTED DATA ANALYSIS")
    print(f"{'=' * 70}")

    retracted = [r for r in results if r["type"] == "retracted" and "error" not in r]
    classes = {}
    for r in retracted:
        c = r["violation_class"]
        classes[c] = classes.get(c, 0) + 1

    print(f"  Reference (PBMC3k): {results[0]['violation_class']}")
    print(f"  Retracted analyzed: {len(retracted)}")
    for c, n in sorted(classes.items()):
        print(f"    {c}: {n}")
    print(f"  Elapsed: {elapsed:.0f}s")

    n_flagged = classes.get("structural_anomaly", 0) + classes.get("local_break", 0)
    if n_flagged > 0:
        conclusion = (
            f"Found structural violations in {n_flagged}/{len(retracted)} retracted datasets. "
            f"Tool detects real-world data quality issues in retracted paper. "
            f"Violations are structural breaks, not proof of fraud."
        )
    else:
        conclusion = (
            f"All {len(retracted)} retracted datasets pass self-consistency. "
            f"Retraction may be for non-data reasons."
        )

    print(f"\n  CONCLUSION: {conclusion}")

    out = {
        "experiment": "H30_retracted_syndrome",
        "source": "GSE160269",
        "paper_pmid": "38572681",
        "paper_status": "RETRACTED",
        "conclusion": conclusion,
        "results": results,
        "elapsed_s": round(elapsed, 1),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "h30_retracted_syndrome.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )
    print(f"  Saved: {RESULTS / 'h30_retracted_syndrome.json'}")


if __name__ == "__main__":
    main()
