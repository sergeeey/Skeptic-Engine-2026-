"""H28 — Paper Mill Detection via P-value Behavioral + Metadata Features.

Combines H23 p-value behavioral features with authorship/submission
metadata to distinguish retracted from non-retracted papers.

Pipeline:
  1. Search PubMed for retracted publications
  2. Match controls from same journals/years
  3. Extract p-value behavioral features (18) + metadata features (8)
  4. Train RF/GBM/LR with 5-fold CV
  5. Ablation: p-value only vs metadata only vs combined
  6. Report AUC, feature importance

Usage:
    python experiments/h28_paper_mills/run_h28.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))

from metadata_features import METADATA_FEATURE_NAMES, extract_metadata_features
from retraction_api import (
    fetch_pmc_fulltext,
    fetch_pubmed_xml,
    parse_article_metadata,
    search_controls,
    search_retracted_papers,
)

RESULTS_DIR = Path(__file__).resolve().parent / "results"
DATA_DIR = Path(__file__).resolve().parent / "data"


def extract_pvalues_regex(text: str) -> list[float]:
    """Fast regex extraction of p-values from text."""
    results = []
    patterns = [
        r"[pP]\s*[=<>≤≥]\s*(\.?\d+\.?\d*(?:[eE][+-]?\d+)?)",
        r"[FtZrχ²]\s*\([^)]*\)\s*=\s*[\d.]+\s*,\s*[pP]\s*[=<>≤≥]\s*(\.?\d+\.?\d*)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            try:
                p_str = match.group(1)
                if p_str.startswith("."):
                    p_str = "0" + p_str
                p_val = float(p_str)
                if 0 < p_val <= 1:
                    results.append(p_val)
            except (ValueError, IndexError):
                continue
    return results


def extract_behavioral_features(p_values: list[float]) -> np.ndarray:
    """Extract 18 behavioral features from a p-value sequence."""
    n = len(p_values)
    if n == 0:
        return np.zeros(18)

    p = np.clip(np.array(p_values), 1e-15, 1.0)
    features: list[float] = []

    features.append(float(np.mean(p)))
    features.append(float(np.std(p)) if n > 1 else 0.0)
    features.append(float(np.min(p)))
    features.append(float((p < 0.05).sum() / n))
    features.append(float(((p > 0.04) & (p < 0.05)).sum() / n))
    features.append(float(((p > 0.01) & (p < 0.05)).sum() / n))

    if n > 1:
        diffs = np.diff(p)
        features.append(float(np.mean(diffs)))
        features.append(float(np.std(diffs)))
        features.append(float((diffs < 0).sum() / len(diffs)))
    else:
        features.extend([0.0, 0.0, 0.0])

    features.append(float(p[-1]))
    features.append(1.0 if p[-1] < 0.05 else 0.0)
    features.append(float(p[-1] - p[0]) if n > 1 else 0.0)

    hist, _ = np.histogram(p, bins=10, range=(0, 1))
    hist_norm = hist / max(hist.sum(), 1)
    entropy = -np.sum(hist_norm[hist_norm > 0] * np.log2(hist_norm[hist_norm > 0]))
    features.append(float(entropy))
    features.append(float(n))
    features.append(float(np.log1p(n)))

    features.append(
        float(np.sum(np.abs(np.diff(np.sign(np.diff(p)))) > 0) / max(n - 2, 1)) if n > 2 else 0.0
    )
    features.append(float(np.max(np.abs(np.diff(p)))) if n > 1 else 0.0)
    features.append(float(np.corrcoef(np.arange(n), p)[0, 1]) if n > 2 else 0.0)

    return np.array(features[:18])


def _cv_evaluate(X: np.ndarray, y: np.ndarray, model_factory, n_splits: int = 5) -> dict:
    """Run stratified k-fold CV and return mean AUC/AP."""
    kf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    aucs, aps = [], []

    for train_idx, test_idx in kf.split(X, y):
        model = model_factory()
        model.fit(X[train_idx], y[train_idx])
        y_prob = model.predict_proba(X[test_idx])[:, 1]
        try:
            aucs.append(roc_auc_score(y[test_idx], y_prob))
            aps.append(average_precision_score(y[test_idx], y_prob))
        except ValueError:
            continue

    if not aucs:
        return {"mean_auc": 0.0, "std_auc": 0.0, "mean_ap": 0.0}
    return {
        "mean_auc": round(float(np.mean(aucs)), 4),
        "std_auc": round(float(np.std(aucs)), 4),
        "mean_ap": round(float(np.mean(aps)), 4),
    }


def main() -> None:
    max_retracted = 200
    max_controls_per_journal = 3

    for i, arg in enumerate(sys.argv[1:], 1):
        try:
            max_retracted = int(arg)
            break
        except ValueError:
            pass

    print("=" * 70)
    print(f"H28 — Paper Mill Detection ({max_retracted} retracted + matched controls)")
    print("=" * 70)
    t0 = time.time()

    # Step 1: Find retracted papers
    print("\n[1/6] Searching PubMed for retracted publications...")
    retracted_pmids = search_retracted_papers(max_retracted)
    print(f"  Found {len(retracted_pmids)} retracted PMIDs")

    if len(retracted_pmids) < 10:
        print("  ERROR: Too few retracted papers found.")
        return

    # Step 2: Fetch metadata for retracted papers
    print("\n[2/6] Fetching metadata for retracted papers...")
    retracted_articles = []
    for batch_start in range(0, len(retracted_pmids), 50):
        batch = retracted_pmids[batch_start : batch_start + 50]
        xml = fetch_pubmed_xml(batch)
        if xml:
            articles = parse_article_metadata(xml)
            retracted_articles.extend(articles)
        print(f"    Fetched {len(retracted_articles)} articles...")

    print(f"  Parsed {len(retracted_articles)} retracted articles")

    # Step 3: Find matched controls
    print("\n[3/6] Finding matched control papers...")
    journals_years = set()
    for art in retracted_articles:
        if art["journal"] and art["year"]:
            journals_years.add((art["journal"], art["year"]))

    control_pmids = set()
    for journal, year in list(journals_years)[:50]:  # Cap at 50 journal-years
        pmids = search_controls(journal, year, max_controls_per_journal)
        # Exclude any that are also retracted
        for pid in pmids:
            if pid not in set(retracted_pmids):
                control_pmids.add(pid)
        if len(control_pmids) >= len(retracted_articles):
            break

    print(
        f"  Found {len(control_pmids)} control PMIDs from {len(journals_years)} journal-year pairs"
    )

    control_articles = []
    control_list = list(control_pmids)
    for batch_start in range(0, len(control_list), 50):
        batch = control_list[batch_start : batch_start + 50]
        xml = fetch_pubmed_xml(batch)
        if xml:
            articles = parse_article_metadata(xml)
            control_articles.extend(articles)

    print(f"  Parsed {len(control_articles)} control articles")

    # Step 4: Extract features
    print("\n[4/6] Extracting features...")
    all_features_pval = []
    all_features_meta = []
    all_labels = []
    all_info = []
    n_with_pvals = 0

    for label, articles in [(1, retracted_articles), (0, control_articles)]:
        for art in articles:
            # Metadata features (always available)
            meta_feat = extract_metadata_features(art)
            meta_vec = np.array([meta_feat[k] for k in METADATA_FEATURE_NAMES])

            # P-value features (try to get full text)
            pval_vec = np.zeros(18)
            fulltext = fetch_pmc_fulltext(art["pmid"])
            if fulltext:
                pvals = extract_pvalues_regex(fulltext)
                if len(pvals) >= 2:
                    pval_vec = extract_behavioral_features(pvals)
                    n_with_pvals += 1

            all_features_pval.append(pval_vec)
            all_features_meta.append(meta_vec)
            all_labels.append(label)
            all_info.append(
                {
                    "pmid": art["pmid"],
                    "title": art["title"][:80],
                    "label": "retracted" if label == 1 else "control",
                    "n_pvalues": len(pvals) if fulltext else 0,
                }
            )

        print(f"    {'Retracted' if label == 1 else 'Control'}: {len(articles)} articles processed")

    X_pval = np.array(all_features_pval)
    X_meta = np.array(all_features_meta)
    X_combined = np.hstack([X_pval, X_meta])
    y = np.array(all_labels)

    X_pval = np.nan_to_num(X_pval, nan=0.0, posinf=10.0, neginf=-10.0)
    X_meta = np.nan_to_num(X_meta, nan=0.0, posinf=10.0, neginf=-10.0)
    X_combined = np.nan_to_num(X_combined, nan=0.0, posinf=10.0, neginf=-10.0)

    n_retracted = int(y.sum())
    n_control = int((y == 0).sum())
    print(f"\n  Total: {n_retracted} retracted + {n_control} control = {len(y)} papers")
    print(f"  Papers with p-values: {n_with_pvals}")
    print(
        f"  Feature dims: pval={X_pval.shape[1]}, meta={X_meta.shape[1]}, combined={X_combined.shape[1]}"
    )

    if n_retracted < 20 or n_control < 20:
        print("  ERROR: Not enough samples per class for meaningful CV.")
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        (RESULTS_DIR / "h28_results.json").write_text(
            json.dumps(
                {
                    "experiment": "H28_paper_mills",
                    "error": "insufficient data",
                    "n_retracted": n_retracted,
                    "n_control": n_control,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return

    # Step 5: Classification with ablation
    print("\n[5/6] Running 5-fold CV with ablation...")

    scaler_p = StandardScaler()
    scaler_m = StandardScaler()
    scaler_c = StandardScaler()
    X_p_scaled = scaler_p.fit_transform(X_pval)
    X_m_scaled = scaler_m.fit_transform(X_meta)
    X_c_scaled = scaler_c.fit_transform(X_combined)

    models = {
        "RF": lambda: RandomForestClassifier(
            n_estimators=200, max_depth=10, random_state=42, n_jobs=-1
        ),
        "GBM": lambda: GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=42),
        "LR": lambda: LogisticRegression(max_iter=2000, random_state=42),
    }

    ablation = {}
    for track_name, X_track in [
        ("pvalue_only", X_p_scaled),
        ("metadata_only", X_m_scaled),
        ("combined", X_c_scaled),
    ]:
        print(f"\n  --- {track_name} ---")
        track_results = {}
        for model_name, model_factory in models.items():
            result = _cv_evaluate(X_track, y, model_factory)
            track_results[model_name] = result
            print(
                f"    {model_name}: AUC={result['mean_auc']:.4f} ± {result['std_auc']:.4f}  AP={result['mean_ap']:.4f}"
            )
        ablation[track_name] = track_results

    # Step 6: Feature importance (combined RF)
    print("\n[6/6] Computing feature importance...")
    rf_full = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42, n_jobs=-1)
    rf_full.fit(X_c_scaled, y)

    pval_feat_names = [
        "mean_p",
        "std_p",
        "min_p",
        "frac_sig",
        "frac_just_below_05",
        "frac_01_05",
        "mean_diff",
        "std_diff",
        "frac_decreasing",
        "last_p",
        "last_sig",
        "last_minus_first",
        "entropy",
        "n_pvalues",
        "log_n",
        "reversals",
        "max_jump",
        "correlation",
    ]
    all_feat_names = pval_feat_names + METADATA_FEATURE_NAMES
    importances = rf_full.feature_importances_
    feat_ranking = sorted(
        [
            {"feature": all_feat_names[i], "importance": round(float(importances[i]), 4)}
            for i in range(len(all_feat_names))
        ],
        key=lambda x: x["importance"],
        reverse=True,
    )

    print("\n  Top 10 features:")
    for item in feat_ranking[:10]:
        print(f"    {item['feature']:30s} {item['importance']:.4f}")

    # Verdict
    best_combined = max(ablation["combined"].values(), key=lambda r: r["mean_auc"])
    best_meta = max(ablation["metadata_only"].values(), key=lambda r: r["mean_auc"])
    best_pval = max(ablation["pvalue_only"].values(), key=lambda r: r["mean_auc"])

    best_auc = best_combined["mean_auc"]
    if best_auc >= 0.80:
        verdict = f"POSITIVE — combined features detect retracted papers (AUC={best_auc:.3f})"
    elif best_auc >= 0.65:
        verdict = f"WEAK_SIGNAL — marginal detection (AUC={best_auc:.3f})"
    else:
        verdict = f"REJECT — insufficient signal (AUC={best_auc:.3f})"

    if best_meta["mean_auc"] > best_pval["mean_auc"] + 0.05:
        verdict += " | metadata dominates over p-value features"
    elif best_pval["mean_auc"] > best_meta["mean_auc"] + 0.05:
        verdict += " | p-value features dominate over metadata"
    else:
        verdict += " | both feature groups contribute"

    elapsed = time.time() - t0

    print(f"\n{'=' * 70}")
    print(f"VERDICT: {verdict}")
    print(f"Total time: {elapsed:.1f}s")

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "experiment": "H28_paper_mills",
        "n_retracted": n_retracted,
        "n_control": n_control,
        "n_with_pvalues": n_with_pvals,
        "feature_groups": {
            "pvalue_behavioral": 18,
            "metadata": 8,
            "total": 26,
        },
        "ablation": {
            track: {model: result for model, result in results.items()}
            for track, results in ablation.items()
        },
        "feature_ranking": feat_ranking,
        "verdict": verdict,
        "elapsed_s": round(elapsed, 1),
    }

    out_path = RESULTS_DIR / "h28_results.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Results saved: {out_path}")

    # Cache data
    (DATA_DIR / "paper_data.json").write_text(json.dumps(all_info, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
