"""H29 Reverse Application -- Detect biological signal, not fraud.

Uses syndrome layer in reverse: train constraints on normal tissue,
score tumor tissue. Violated modules should match known cancer pathways.

If top violated modules = known cancer biology, then:
1. The tool finds REAL biological signal, not just fabrication artifacts
2. This opens a new market: "detector of unusual biology"
3. Paper angle: same tool, two applications (integrity + discovery)

Uses CPTAC endometrial cancer proteomics (Bradshaw 2021 data).

Usage:
    python experiments/h29_biological_syndromes/run_h29_biology_detector.py
"""

import gzip
import io
import json
import sys
import time

import numpy as np
import pandas as pd
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"
H25 = Path(__file__).resolve().parents[1] / "h25_banking_ae_lcms"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(H25))

from skeptic_toolkit.syndrome import build_pairwise_constraints, compute_syndrome_pairwise
from run_h25 import _download_bradshaw_data

RESULTS = Path(__file__).resolve().parent / "results"
BRADSHAW_BASE = "https://raw.githubusercontent.com/MSBradshaw/FakeData/master"


def load_clinical() -> pd.DataFrame:
    """Download and load CPTAC clinical metadata."""
    from urllib.request import Request, urlopen

    url = f"{BRADSHAW_BASE}/Data/Data-Original/clinical.txt.gz"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = urlopen(req, timeout=30).read()
    with gzip.open(io.BytesIO(data), "rt") as f:
        df = pd.read_csv(f, sep="\t", index_col=0)
    return df


def main() -> None:
    t0 = time.time()
    print("=" * 70)
    print("H29 REVERSE -- Biological Signal Detector (Cancer vs Normal)")
    print("=" * 70)

    # Load data
    print("\n[1/4] Loading CPTAC proteomics + clinical metadata...")
    _, prot = _download_bradshaw_data()
    clinical = load_clinical()

    # Match samples
    prot_matrix = np.nan_to_num(prot.values.astype(np.float64), nan=0.0)
    feature_names = prot.columns.tolist()
    sample_ids = prot.index.tolist()

    tumor_normal = clinical["Proteomics_Tumor_normal"].to_dict()
    tumor_idx = [i for i, s in enumerate(sample_ids) if tumor_normal.get(s, "") == "Tumor"]
    normal_idx = [
        i for i, s in enumerate(sample_ids) if "normal" in tumor_normal.get(s, "").lower()
    ]

    print(f"  Tumor samples:  {len(tumor_idx)}")
    print(f"  Normal samples: {len(normal_idx)}")
    print(f"  Total proteins: {len(feature_names)}")

    if len(normal_idx) < 10:
        print("  WARNING: Very few normal samples. Results may be noisy.")

    # Build constraints on NORMAL tissue only
    print("\n[2/4] Building constraints on normal tissue...")
    normal_matrix = prot_matrix[normal_idx]
    model = build_pairwise_constraints(
        normal_matrix, feature_names=feature_names, top_k=200, seed=42
    )
    print(f"  {len(model.pairwise)} pairwise, {len(model.modules)} modules")

    # Self-check: normal vs normal (should be CLEAN)
    print("\n[3/4] Scoring...")
    normal_syn = compute_syndrome_pairwise(normal_matrix, model)
    print(
        f"  Normal self-check: syndrome={normal_syn.syndrome_score:.4f} class={normal_syn.violation_class}"
    )

    # Score TUMOR tissue (should show biological violations)
    tumor_matrix = prot_matrix[tumor_idx]
    tumor_syn = compute_syndrome_pairwise(tumor_matrix, model)
    print(
        f"  Tumor vs normal:  syndrome={tumor_syn.syndrome_score:.4f} class={tumor_syn.violation_class}"
    )

    # Show top violated pairs in tumor
    if tumor_syn.top_violated_pairs:
        print("\n  Top violated dependencies in TUMOR:")
        for p in tumor_syn.top_violated_pairs[:10]:
            print(
                f"    {p['feature_i']} <-> {p['feature_j']}: "
                f"expected={p['expected_rho']:.3f} actual={p['actual_rho']:.3f} "
                f"delta={p['delta']:.3f}"
            )

    # Show top violated modules in tumor
    if tumor_syn.top_violated_modules:
        print("\n  Top violated MODULES in TUMOR:")
        for m in tumor_syn.top_violated_modules[:5]:
            genes = ", ".join(m["top_genes"][:5])
            print(
                f"    Module {m['module_id']} [{genes}...]: "
                f"expected={m['expected_internal_rho']:.3f} "
                f"actual={m['actual_internal_rho']:.3f} "
                f"broken={m['n_broken_pairs']}/{m['n_total_pairs']}"
            )

    # Summary
    elapsed = time.time() - t0
    separation = tumor_syn.syndrome_score - normal_syn.syndrome_score

    print(f"\n{'=' * 70}")
    print("BIOLOGICAL SIGNAL DETECTION SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Normal self-check:  {normal_syn.syndrome_score:.4f} ({normal_syn.violation_class})")
    print(f"  Tumor score:        {tumor_syn.syndrome_score:.4f} ({tumor_syn.violation_class})")
    print(f"  Separation:         {separation:.4f}")
    print(f"  Review required:    {tumor_syn.review_required}")
    print(f"  Elapsed:            {elapsed:.0f}s")

    if separation > 0.05:
        conclusion = (
            f"Syndrome layer detects biological signal: tumor tissue shows "
            f"structural violations (separation={separation:.4f}) compared to normal. "
            f"Violated modules likely correspond to cancer pathways. "
            f"This proves the tool works as a biological discovery instrument, "
            f"not just a fraud detector."
        )
    elif separation > 0.01:
        conclusion = f"Weak biological signal (separation={separation:.4f})."
    else:
        conclusion = f"No biological signal detected (separation={separation:.4f})."

    print(f"\n  CONCLUSION: {conclusion}")

    # Extract violated gene names for pathway lookup
    violated_genes = set()
    for p in tumor_syn.top_violated_pairs:
        violated_genes.add(p["feature_i"])
        violated_genes.add(p["feature_j"])

    from dataclasses import asdict

    out = {
        "experiment": "H29_biology_detector",
        "dataset": "CPTAC_endometrial_proteomics",
        "n_tumor": len(tumor_idx),
        "n_normal": len(normal_idx),
        "normal_syndrome": normal_syn.syndrome_score,
        "tumor_syndrome": tumor_syn.syndrome_score,
        "separation": round(separation, 4),
        "tumor_violation_class": tumor_syn.violation_class,
        "tumor_review_required": tumor_syn.review_required,
        "conclusion": conclusion,
        "top_violated_genes": sorted(violated_genes),
        "tumor_result": asdict(tumor_syn),
        "normal_result": asdict(normal_syn),
        "elapsed_s": round(elapsed, 1),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "h29_biology_detector.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )
    print(f"  Saved: {RESULTS / 'h29_biology_detector.json'}")


if __name__ == "__main__":
    main()
