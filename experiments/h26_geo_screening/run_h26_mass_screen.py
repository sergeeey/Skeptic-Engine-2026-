"""H26 Mass Screening — scan real GEO scRNA-seq datasets with clean-bank calibration.

Downloads processed count matrices (not RAW.tar), screens only UMI-like sparse
matrices, and calibrates anomaly verdicts against a local bank of known-clean
references instead of a single PBMC3k baseline.

WHY:
- A single reference over-flags legitimate but distribution-shifted datasets.
- GEO contains both UMI-like matrices and out-of-scope full-length protocols.
- A conservative clean-bank calibration is better aligned with H24's stated
  deployment boundary: compare candidates against known-clean data from the
  same general measurement family, not against one universal template.

Usage:
    python experiments/h26_geo_screening/run_h26_mass_screen.py [--max-datasets 100]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# Import from sibling experiments / package source
H24_DIR = Path(__file__).resolve().parents[1] / "h24_benford_scrna"
SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(H24_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(SRC_DIR))

from digit_features import extract_features_per_sample
from format_loaders import load_count_matrix
from geo_api import (
    download_file,
    find_count_matrix_file,
    get_supplementary_files,
    search_geo_scrna,
)
from isolation_forest import cell_level_features
from run_cross_tissue import _download_brain_dataset
from run_crossval import _load_kang2018
from run_h24 import _download_pbmc3k, _load_count_matrix
from skeptic_toolkit.verdict import make_verdict

RESULTS_DIR = Path(__file__).resolve().parent / "results"
DATA_DIR = Path(__file__).resolve().parent / "data"

# Processed matrices larger than this are usually slow / out-of-scope for a smoke run.
MAX_FILE_SIZE_MB = 50
MIN_CELLS = 50
MAX_CELLS = 5000

# Conservative UMI-like domain gate. This excludes full-length / pseudo-bulk-like matrices
# such as Smart-seq2 tables with very large per-cell library sizes.
UMI_LIBRARY_SIZE_FACTOR = 5.0
UMI_GENES_DETECTED_FACTOR = 3.0
UMI_ZERO_FRACTION_SLACK = 0.05


def _subsample_cells(matrix: np.ndarray, limit: int = MAX_CELLS, seed: int = 42) -> np.ndarray:
    if matrix.shape[0] <= limit:
        return matrix
    rng = np.random.default_rng(seed)
    idx = rng.choice(matrix.shape[0], limit, replace=False)
    return matrix[idx]


def summarize_matrix(matrix: np.ndarray) -> dict[str, float | int]:
    """Return lightweight dataset-level summary stats used for domain checks."""
    return {
        "n_cells": int(matrix.shape[0]),
        "n_genes": int(matrix.shape[1]),
        "mean_library_size": round(float(matrix.sum(axis=1).mean()), 1),
        "mean_genes_detected": round(float((matrix > 0).sum(axis=1).mean()), 1),
        "zero_fraction": round(float((matrix == 0).mean()), 4),
    }


def build_reference_model(name: str, matrix: np.ndarray) -> dict:
    """Fit one clean reference model used for H26 bank calibration."""
    summary = summarize_matrix(matrix)
    model_matrix = _subsample_cells(matrix)
    benford = extract_features_per_sample(model_matrix)
    cell = cell_level_features(model_matrix)
    features = np.hstack([benford, cell])

    scaler = StandardScaler()
    scaled = scaler.fit_transform(features)
    if_model = IsolationForest(n_estimators=200, contamination="auto", random_state=42, n_jobs=-1)
    if_model.fit(scaled)
    if_scores = if_model.decision_function(scaled)

    return {
        "name": name,
        "matrix": model_matrix,
        "features": features,
        "scaler": scaler,
        "if_model": if_model,
        "if_scores": if_scores,
        "summary": summary,
    }


def load_reference_bank() -> dict[str, dict]:
    """Load a small clean bank spanning multiple known-clean scRNA-seq datasets."""
    pbmc = _load_count_matrix(_download_pbmc3k())
    kang = _load_kang2018()
    neurons = _download_brain_dataset()

    return {
        "PBMC3k_10x": build_reference_model("PBMC3k_10x", pbmc),
        "Kang2018_GSE96583": build_reference_model("Kang2018_GSE96583", kang),
        "Neurons900_10x": build_reference_model("Neurons900_10x", neurons),
    }


def score_dataset(candidate: np.ndarray, reference_model: dict) -> dict[str, float | int]:
    """Score a candidate dataset against one reference model."""
    candidate = _subsample_cells(candidate)

    benford = extract_features_per_sample(candidate)
    cell_feat = cell_level_features(candidate)
    fusion = np.hstack([benford, cell_feat])

    if_scores = reference_model["if_model"].decision_function(
        reference_model["scaler"].transform(fusion)
    )
    ref_features = reference_model["features"]
    ref_scores = reference_model["if_scores"]

    median_score = float(np.median(if_scores))
    frac_anomalous = float((if_scores < ref_scores.mean() - 2 * ref_scores.std()).mean())

    candidate_fd = benford[:, :9].mean(axis=0)
    ref_fd = ref_features[:, :9].mean(axis=0)
    chi2_vs_ref = float(np.sum((candidate_fd - ref_fd) ** 2 / (ref_fd + 1e-10)))

    return {
        **summarize_matrix(candidate),
        "median_if_score": round(median_score, 4),
        "frac_anomalous": round(frac_anomalous, 4),
        "chi2_vs_reference": round(chi2_vs_ref, 6),
    }


def aggregate_bank_scores(reference_scores: dict[str, dict[str, float | int]]) -> dict[str, float | str]:
    """Collapse per-reference scores into conservative best-match metrics."""
    best_frac_ref = min(reference_scores, key=lambda name: reference_scores[name]["frac_anomalous"])
    best_chi2_ref = min(
        reference_scores, key=lambda name: reference_scores[name]["chi2_vs_reference"]
    )
    best_if_ref = max(reference_scores, key=lambda name: reference_scores[name]["median_if_score"])
    best_overall_ref = min(
        reference_scores,
        key=lambda name: (
            reference_scores[name]["chi2_vs_reference"],
            reference_scores[name]["frac_anomalous"],
            -reference_scores[name]["median_if_score"],
        ),
    )

    best_median_if = float(reference_scores[best_if_ref]["median_if_score"])
    return {
        "best_overall_reference": best_overall_ref,
        "best_match_frac_reference": best_frac_ref,
        "best_match_frac_anomalous": float(reference_scores[best_frac_ref]["frac_anomalous"]),
        "best_match_chi2_reference": best_chi2_ref,
        "best_match_chi2_vs_reference": float(
            reference_scores[best_chi2_ref]["chi2_vs_reference"]
        ),
        "best_match_if_reference": best_if_ref,
        "best_match_median_if_score": best_median_if,
        "best_match_negative_median_if": round(-best_median_if, 4),
    }


def compute_clean_bank_calibration(reference_bank: dict[str, dict]) -> dict:
    """Estimate conservative clean-bank limits from leave-one-reference-out scoring."""
    clean_profiles = []
    for candidate_name, candidate_model in reference_bank.items():
        per_reference = {}
        for reference_name, reference_model in reference_bank.items():
            if reference_name == candidate_name:
                continue
            per_reference[reference_name] = score_dataset(candidate_model["matrix"], reference_model)
        aggregate = aggregate_bank_scores(per_reference)
        clean_profiles.append({"dataset": candidate_name, **aggregate})

    summaries = [model["summary"] for model in reference_bank.values()]
    return {
        "reference_bank": list(reference_bank.keys()),
        "clean_reference_profiles": clean_profiles,
        "clean_bank_max": {
            "best_match_frac_anomalous": round(
                max(profile["best_match_frac_anomalous"] for profile in clean_profiles), 4
            ),
            "best_match_chi2_vs_reference": round(
                max(profile["best_match_chi2_vs_reference"] for profile in clean_profiles), 6
            ),
            "best_match_negative_median_if": round(
                max(profile["best_match_negative_median_if"] for profile in clean_profiles), 4
            ),
        },
        "domain_bounds": {
            "max_mean_library_size": round(
                max(summary["mean_library_size"] for summary in summaries) * UMI_LIBRARY_SIZE_FACTOR,
                1,
            ),
            "max_mean_genes_detected": round(
                max(summary["mean_genes_detected"] for summary in summaries)
                * UMI_GENES_DETECTED_FACTOR,
                1,
            ),
            "min_zero_fraction": round(
                max(
                    0.0,
                    min(summary["zero_fraction"] for summary in summaries) - UMI_ZERO_FRACTION_SLACK,
                ),
                4,
            ),
        },
    }


def check_supported_scope(candidate_summary: dict[str, float | int], calibration: dict) -> list[str]:
    """Return reasons why a dataset falls outside the supported UMI-like scope."""
    bounds = calibration["domain_bounds"]
    reasons = []

    if float(candidate_summary["mean_library_size"]) > float(bounds["max_mean_library_size"]):
        reasons.append(
            "mean_library_size above UMI-like clean-bank range "
            f"({candidate_summary['mean_library_size']} > {bounds['max_mean_library_size']})"
        )
    if float(candidate_summary["mean_genes_detected"]) > float(bounds["max_mean_genes_detected"]):
        reasons.append(
            "mean_genes_detected above UMI-like clean-bank range "
            f"({candidate_summary['mean_genes_detected']} > {bounds['max_mean_genes_detected']})"
        )
    if float(candidate_summary["zero_fraction"]) < float(bounds["min_zero_fraction"]):
        reasons.append(
            "zero_fraction too low for sparse UMI-like matrix "
            f"({candidate_summary['zero_fraction']} < {bounds['min_zero_fraction']})"
        )

    return reasons


def calibrate_candidate(reference_scores: dict[str, dict], calibration: dict) -> dict[str, object]:
    """Map per-reference scores to a conservative calibrated verdict."""
    aggregate = aggregate_bank_scores(reference_scores)
    clean_max = calibration["clean_bank_max"]

    exceedances = []
    if aggregate["best_match_frac_anomalous"] > clean_max["best_match_frac_anomalous"]:
        exceedances.append("best_match_frac_anomalous")
    if aggregate["best_match_chi2_vs_reference"] > clean_max["best_match_chi2_vs_reference"]:
        exceedances.append("best_match_chi2_vs_reference")
    if aggregate["best_match_negative_median_if"] > clean_max["best_match_negative_median_if"]:
        exceedances.append("best_match_negative_median_if")

    if not exceedances:
        risk_score = 0.15
    elif len(exceedances) == 3:
        risk_score = 0.90
    else:
        risk_score = 0.55

    verdict = make_verdict(risk_score, threshold=0.55, uncertainty_band=0.20)
    return {
        "verdict": verdict.level.value,
        "risk_score": round(risk_score, 4),
        "calibration_exceedances": exceedances,
        **aggregate,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="H26 Mass GEO scRNA-seq Screening")
    parser.add_argument("--max-datasets", type=int, default=100)
    parser.add_argument(
        "--search-factor",
        type=int,
        default=10,
        help="Fetch more GEO accessions than needed to compensate for raw-only / unusable entries.",
    )
    args = parser.parse_args()

    start = time.time()

    print("=" * 70)
    print("H26 MASS SCREENING — Real GEO Dataset Integrity Check")
    print("=" * 70)

    print("\n[1/4] Building clean reference bank...")
    reference_bank = load_reference_bank()
    calibration = compute_clean_bank_calibration(reference_bank)
    print(f"  Reference bank: {', '.join(calibration['reference_bank'])}")
    print(
        "  Domain gate: "
        f"library_size <= {calibration['domain_bounds']['max_mean_library_size']}, "
        f"genes_detected <= {calibration['domain_bounds']['max_mean_genes_detected']}, "
        f"zero_fraction >= {calibration['domain_bounds']['min_zero_fraction']}"
    )
    print(
        "  Clean-bank maxima: "
        f"best_frac={calibration['clean_bank_max']['best_match_frac_anomalous']:.4f}, "
        f"best_chi2={calibration['clean_bank_max']['best_match_chi2_vs_reference']:.6f}, "
        f"best_neg_if={calibration['clean_bank_max']['best_match_negative_median_if']:.4f}"
    )

    search_budget = max(args.max_datasets * args.search_factor, args.max_datasets)
    print(
        f"\n[2/4] Searching GEO for scRNA-seq datasets "
        f"(target={args.max_datasets}, search_budget={search_budget})..."
    )
    accessions = search_geo_scrna(max_results=search_budget)
    print(f"  Found {len(accessions)} candidate GSE accessions")

    if not accessions:
        print("  No datasets found. Check network connection.")
        return

    print(f"\n[3/4] Screening datasets...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    dataset_results: list[dict] = []
    out_of_scope_datasets: list[dict] = []
    n_downloaded = 0
    n_processed = 0
    n_skipped_no_files = 0
    n_skipped_too_large = 0
    n_skipped_load_error = 0
    n_skipped_too_few_cells = 0
    n_skipped_raw_archive = 0
    n_skipped_out_of_scope = 0
    n_considered = 0

    for gse in accessions:
        if n_processed >= args.max_datasets:
            break

        n_considered += 1
        print(f"\n  [{n_considered}/{len(accessions)}] {gse}...", end=" ", flush=True)

        files = get_supplementary_files(gse)
        if not files:
            print("no supplementary files")
            n_skipped_no_files += 1
            continue

        matrix_file = find_count_matrix_file(files)
        if not matrix_file:
            print(f"no count matrix found ({len(files)} files)")
            n_skipped_no_files += 1
            continue

        if "_raw.tar" in matrix_file["name"].lower():
            print(f"raw archive only ({matrix_file['name']})")
            n_skipped_raw_archive += 1
            continue

        dest = DATA_DIR / gse / matrix_file["name"]
        print(f"downloading {matrix_file['name']}...", end=" ", flush=True)
        if not download_file(matrix_file["url"], dest):
            print("download failed")
            n_skipped_load_error += 1
            continue

        file_size_mb = dest.stat().st_size / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            print(f"too large ({file_size_mb:.1f}MB)")
            n_skipped_too_large += 1
            dest.unlink()
            continue

        n_downloaded += 1

        matrix = load_count_matrix(dest, max_cells=MAX_CELLS)
        if matrix is None:
            print("load failed")
            n_skipped_load_error += 1
            continue

        if matrix.shape[0] < MIN_CELLS:
            print(f"too few cells ({matrix.shape[0]})")
            n_skipped_too_few_cells += 1
            continue

        candidate_summary = summarize_matrix(matrix)
        scope_reasons = check_supported_scope(candidate_summary, calibration)
        if scope_reasons:
            print("out of scope")
            out_of_scope_datasets.append(
                {
                    "gse": gse,
                    "file": matrix_file["name"],
                    "candidate_summary": candidate_summary,
                    "scope_reasons": scope_reasons,
                }
            )
            n_skipped_out_of_scope += 1
            continue

        try:
            reference_scores = {
                reference_name: score_dataset(matrix, reference_model)
                for reference_name, reference_model in reference_bank.items()
            }
            calibrated = calibrate_candidate(reference_scores, calibration)
            result = {
                "gse": gse,
                "file": matrix_file["name"],
                "candidate_summary": candidate_summary,
                "verdict": calibrated["verdict"],
                "risk_score": calibrated["risk_score"],
                "best_overall_reference": calibrated["best_overall_reference"],
                "best_match_frac_reference": calibrated["best_match_frac_reference"],
                "best_match_frac_anomalous": calibrated["best_match_frac_anomalous"],
                "best_match_chi2_reference": calibrated["best_match_chi2_reference"],
                "best_match_chi2_vs_reference": calibrated["best_match_chi2_vs_reference"],
                "best_match_if_reference": calibrated["best_match_if_reference"],
                "best_match_median_if_score": calibrated["best_match_median_if_score"],
                "best_match_negative_median_if": calibrated["best_match_negative_median_if"],
                "calibration_exceedances": calibrated["calibration_exceedances"],
                "reference_scores": reference_scores,
            }
            dataset_results.append(result)
            n_processed += 1

            print(
                f"{calibrated['verdict']} "
                f"({candidate_summary['n_cells']}×{candidate_summary['n_genes']}, "
                f"best_ref={calibrated['best_overall_reference']}, risk={calibrated['risk_score']:.3f})"
            )
        except Exception as e:
            print(f"scoring error: {e}")
            n_skipped_load_error += 1

    elapsed = time.time() - start
    print("\n" + "=" * 70)
    print("SCREENING SUMMARY")
    print("=" * 70)

    n_clean = sum(1 for r in dataset_results if r["verdict"] == "CLEAN")
    n_uncertain = sum(1 for r in dataset_results if r["verdict"] == "UNCERTAIN")
    n_flagged = sum(1 for r in dataset_results if r["verdict"] == "FLAGGED")

    print(f"  Datasets searched:    {len(accessions)}")
    print(f"  Candidates tried:     {n_considered}")
    print(f"  Downloaded:           {n_downloaded}")
    print(f"  Processed:            {n_processed}")
    print(f"  Skipped (no files):   {n_skipped_no_files}")
    print(f"  Skipped (raw tar):    {n_skipped_raw_archive}")
    print(f"  Skipped (too large):  {n_skipped_too_large}")
    print(f"  Skipped (load err):   {n_skipped_load_error}")
    print(f"  Skipped (few cells):  {n_skipped_too_few_cells}")
    print(f"  Skipped (out scope):  {n_skipped_out_of_scope}")
    print()
    print(f"  CLEAN:                {n_clean}")
    print(f"  UNCERTAIN:            {n_uncertain}")
    print(f"  FLAGGED:              {n_flagged}")
    print(
        f"  Flag rate:            {n_flagged}/{max(n_processed, 1)} = "
        f"{n_flagged / max(n_processed, 1):.1%}"
    )
    print(f"  Elapsed:              {elapsed:.0f}s")

    if out_of_scope_datasets:
        print("\nOUT-OF-SCOPE DATASETS:")
        for item in out_of_scope_datasets[:5]:
            print(f"  {item['gse']}: {'; '.join(item['scope_reasons'])}")

    if n_flagged > 0:
        print("\nFLAGGED DATASETS (require expert review):")
        for r in dataset_results:
            if r["verdict"] == "FLAGGED":
                print(
                    f"  {r['gse']}: risk={r['risk_score']:.3f} "
                    f"best_frac={r['best_match_frac_anomalous']:.3f} "
                    f"best_chi2={r['best_match_chi2_vs_reference']:.6f}"
                )

    if n_uncertain > 0:
        print("\nUNCERTAIN DATASETS:")
        for r in dataset_results:
            if r["verdict"] == "UNCERTAIN":
                print(
                    f"  {r['gse']}: risk={r['risk_score']:.3f} "
                    f"exceeds={','.join(r['calibration_exceedances'])}"
                )

    if n_processed == 0 and n_skipped_out_of_scope > 0:
        conclusion = (
            "NO_SUPPORTED_DATA — downloadable matrices were outside the supported UMI-like "
            "scRNA-seq screening scope."
        )
    elif n_processed == 0:
        conclusion = "NO_DATA — no datasets could be processed. Check bandwidth/file availability."
    elif n_flagged == 0 and n_uncertain == 0:
        conclusion = (
            f"CLEAN_SWEEP — all {n_processed} supported real datasets scored CLEAN under "
            "clean-bank calibration."
        )
    elif n_flagged == 0:
        conclusion = (
            f"BORDERLINE_ONLY — {n_uncertain}/{n_processed} supported datasets were UNCERTAIN, "
            "none were strongly flagged."
        )
    else:
        conclusion = (
            f"FLAGGED_CASES — {n_flagged}/{n_processed} supported datasets exceeded conservative "
            "clean-bank maxima and warrant expert review."
        )

    print(f"\nCONCLUSION: {conclusion}")

    output = {
        "experiment": "H26_mass_screening",
        "target_processed": args.max_datasets,
        "search_budget": search_budget,
        "n_searched": len(accessions),
        "n_considered": n_considered,
        "n_downloaded": n_downloaded,
        "n_processed": n_processed,
        "n_clean": n_clean,
        "n_uncertain": n_uncertain,
        "n_flagged": n_flagged,
        "flag_rate": round(n_flagged / max(n_processed, 1), 4),
        "reference_bank": calibration["reference_bank"],
        "scoring_method": (
            "Per-reference IsolationForest + Benford divergence, aggregated by conservative "
            "best-match clean-bank calibration"
        ),
        "supported_scope": "UMI-like sparse scRNA-seq count matrices",
        "domain_bounds": calibration["domain_bounds"],
        "clean_bank_max": calibration["clean_bank_max"],
        "clean_reference_profiles": calibration["clean_reference_profiles"],
        "conclusion": conclusion,
        "datasets": dataset_results,
        "out_of_scope_datasets": out_of_scope_datasets,
        "skipped": {
            "no_files": n_skipped_no_files,
            "raw_archive_only": n_skipped_raw_archive,
            "too_large": n_skipped_too_large,
            "load_error": n_skipped_load_error,
            "too_few_cells": n_skipped_too_few_cells,
            "out_of_scope": n_skipped_out_of_scope,
        },
        "elapsed_s": round(elapsed, 1),
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "h26_mass_screening.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nResults saved: {out_path}")


if __name__ == "__main__":
    main()
