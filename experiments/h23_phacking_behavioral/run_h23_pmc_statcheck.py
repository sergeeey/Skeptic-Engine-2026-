"""H23-pmc — Quasi-supervised p-value anomaly detection on PMC articles.

Uses statcheck_python to extract AND recompute p-values from PMC full-text.
The key: statcheck compares reported p vs recomputed p → Error flag = quasi-label.

This is NOT a replacement for H23-main (RPP/statcheck labeled data).
This is a scalability + quasi-supervision track.

What it proves: the pipeline can extract, recompute, and flag at scale.
What it does NOT prove: that flagged articles are actually p-hacked.

Usage:
    python experiments/h23_phacking_behavioral/run_h23_pmc_statcheck.py [--max-articles 300]
"""

from __future__ import annotations

import json
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

RESULTS_DIR = Path(__file__).resolve().parent / "results"
DATA_DIR = Path(__file__).resolve().parent / "data"

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def search_pmc(query: str, max_results: int = 300) -> list[str]:
    params = f"db=pmc&term={quote(query)}&retmax={max_results}&retmode=json"
    url = f"{ESEARCH_URL}?{params}"
    req = Request(url, headers={"User-Agent": "SkepticEngine/0.1"})
    with urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data.get("esearchresult", {}).get("idlist", [])


def fetch_pmc_text(pmc_id: str) -> str:
    url = f"{EFETCH_URL}?db=pmc&id={pmc_id}&rettype=xml&retmode=xml"
    req = Request(url, headers={"User-Agent": "SkepticEngine/0.1"})
    with urlopen(req, timeout=30) as resp:
        xml_text = resp.read().decode("utf-8", errors="replace")
    try:
        root = ET.fromstring(xml_text)
        paragraphs = []
        for p in root.iter("p"):
            text_parts = [p.text or ""]
            for child in p:
                text_parts.append(child.text or "")
                text_parts.append(child.tail or "")
            paragraphs.append(" ".join(text_parts))
        return " ".join(paragraphs)
    except ET.ParseError:
        return xml_text


def run_statcheck_on_text(text: str) -> pd.DataFrame | None:
    """Run statcheck_python on extracted text. Returns DataFrame or None."""
    try:
        from statcheck.st import statcheck as sc
        import io
        from contextlib import redirect_stdout, redirect_stderr

        # Suppress statcheck verbose output
        f = io.StringIO()
        with redirect_stdout(f), redirect_stderr(f):
            result = sc(text)

        if result is None:
            return None

        # statcheck returns a tuple of (stats_df, pvalues_df)
        if isinstance(result, tuple) and len(result) >= 1:
            stats_df = result[0]
            if isinstance(stats_df, pd.DataFrame) and len(stats_df) > 0:
                return stats_df

        return None
    except Exception:
        return None


def extract_article_features(df: pd.DataFrame) -> dict:
    """Extract behavioral features from statcheck results for one article."""
    n = len(df)

    # Reported p-values
    reported_p = []
    computed_p = []
    errors = []

    for _, row in df.iterrows():
        try:
            rp = float(row.get("Reported.P.Value", float("nan")))
            cp = float(row.get("Computed", float("nan")))
            err = bool(row.get("Error", False))
            if not np.isnan(rp) and 0 < rp <= 1:
                reported_p.append(rp)
            if not np.isnan(cp) and 0 < cp <= 1:
                computed_p.append(cp)
            errors.append(err)
        except (ValueError, TypeError):
            continue

    if len(reported_p) < 2:
        return {}

    rp = np.array(reported_p)
    n_tests = len(rp)
    n_errors = sum(errors)
    has_error = n_errors > 0

    features = {
        "n_tests": n_tests,
        "n_errors": n_errors,
        "has_error": has_error,
        "error_rate": n_errors / n_tests if n_tests > 0 else 0,
        # P-value distribution
        "mean_p": float(np.mean(rp)),
        "std_p": float(np.std(rp)),
        "min_p": float(np.min(rp)),
        "frac_sig": float((rp < 0.05).mean()),
        "frac_just_below_05": float(((rp > 0.04) & (rp < 0.05)).mean()),
        "frac_01_05": float(((rp > 0.01) & (rp < 0.05)).mean()),
        # Discrepancy (reported vs recomputed)
        "mean_discrepancy": 0.0,
        "max_discrepancy": 0.0,
    }

    if len(computed_p) == len(reported_p):
        disc = np.abs(np.array(reported_p) - np.array(computed_p))
        features["mean_discrepancy"] = float(np.mean(disc))
        features["max_discrepancy"] = float(np.max(disc))

    # Sequence dynamics
    if n_tests > 1:
        diffs = np.diff(rp)
        features["volatility"] = float(np.std(diffs))
        features["frac_decreasing"] = float((diffs < 0).mean())
    else:
        features["volatility"] = 0.0
        features["frac_decreasing"] = 0.0

    return features


def main() -> None:
    max_articles = 300
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg.lstrip("-").startswith("max"):
            if i < len(sys.argv) - 1:
                max_articles = int(sys.argv[i + 1])
            break
        else:
            try:
                max_articles = int(arg)
                break
            except ValueError:
                pass

    print("=" * 70)
    print(f"H23-pmc — Statcheck quasi-supervised on {max_articles} PMC articles")
    print("=" * 70)
    t0 = time.time()

    # Search for psychology articles with statistical results
    print("\n[1/4] Searching PMC for psychology articles...")
    query = (
        '("psychology"[Journal] OR "psychological"[Title/Abstract]) '
        'AND ("p < " OR "p = " OR "F(" OR "t(") '
        "AND open access[filter]"
    )
    pmc_ids = search_pmc(query, max_results=max_articles)
    print(f"  Found {len(pmc_ids)} PMC articles")

    # Process each article with statcheck
    print(f"\n[2/4] Running statcheck on each article...")
    articles = []
    n_no_stats = 0
    n_failed = 0

    for i, pmc_id in enumerate(pmc_ids):
        if (i + 1) % 25 == 0:
            n_with_stats = len(articles)
            print(
                f"  {i + 1}/{len(pmc_ids)} (extracted: {n_with_stats}, no stats: {n_no_stats}, failed: {n_failed})"
            )

        try:
            time.sleep(0.35)  # NCBI rate limit
            text = fetch_pmc_text(pmc_id)
            if len(text) < 500:
                n_no_stats += 1
                continue

            df = run_statcheck_on_text(text)
            if df is None or len(df) < 2:
                n_no_stats += 1
                continue

            features = extract_article_features(df)
            if not features:
                n_no_stats += 1
                continue

            features["pmc_id"] = pmc_id
            articles.append(features)

        except Exception:
            n_failed += 1
            continue

    print(f"\n  Articles with ≥2 statcheck results: {len(articles)}")
    print(f"  No stats found: {n_no_stats}")
    print(f"  Failed: {n_failed}")

    if len(articles) < 10:
        print("  Too few articles. Increase --max-articles.")
        return

    # Save extracted data
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    extract_path = DATA_DIR / "pmc_statcheck_extracted.json"
    extract_path.write_text(json.dumps(articles, indent=2), encoding="utf-8")

    # Analysis
    print(f"\n[3/4] Analysis...")
    n_with_errors = sum(1 for a in articles if a["has_error"])
    n_clean = len(articles) - n_with_errors
    error_rates = [a["error_rate"] for a in articles]
    frac_sig = [a["frac_sig"] for a in articles]
    frac_just_below = [a["frac_just_below_05"] for a in articles]

    print(f"  Total articles: {len(articles)}")
    print(f"  With errors (quasi-label=1): {n_with_errors} ({n_with_errors / len(articles):.1%})")
    print(f"  Clean (quasi-label=0): {n_clean} ({n_clean / len(articles):.1%})")
    print(f"  Mean error rate per article: {np.mean(error_rates):.4f}")
    print(f"  Mean fraction significant: {np.mean(frac_sig):.3f}")
    print(f"  Mean fraction just below 0.05: {np.mean(frac_just_below):.4f}")

    # Quasi-supervised classification (if enough balance)
    if n_with_errors >= 5 and n_clean >= 5:
        print(f"\n[4/4] Quasi-supervised classification (error flag as label)...")

        feature_keys = [
            "mean_p",
            "std_p",
            "min_p",
            "frac_sig",
            "frac_just_below_05",
            "frac_01_05",
            "mean_discrepancy",
            "max_discrepancy",
            "volatility",
            "frac_decreasing",
            "n_tests",
        ]
        X = np.array([[a[k] for k in feature_keys] for a in articles])
        y = np.array([1 if a["has_error"] else 0 for a in articles])
        X = np.nan_to_num(X, nan=0.0)

        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import roc_auc_score
        from sklearn.model_selection import StratifiedKFold
        from sklearn.preprocessing import StandardScaler

        n_splits = min(5, min(n_with_errors, n_clean))
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        scaler = StandardScaler()

        for model_name, model_fn in [
            ("LR", lambda: LogisticRegression(max_iter=2000, random_state=42)),
            ("RF", lambda: RandomForestClassifier(n_estimators=100, max_depth=4, random_state=42)),
        ]:
            fold_aucs = []
            for train_idx, test_idx in cv.split(X, y):
                X_tr = scaler.fit_transform(X[train_idx])
                X_te = scaler.transform(X[test_idx])
                model = model_fn()
                model.fit(X_tr, y[train_idx])
                try:
                    y_prob = model.predict_proba(X_te)[:, 1]
                    fold_aucs.append(roc_auc_score(y[test_idx], y_prob))
                except ValueError:
                    continue

            if fold_aucs:
                mean_auc = np.mean(fold_aucs)
                print(f"  {model_name} AUC: {mean_auc:.4f} ± {np.std(fold_aucs):.4f}")

        # Baseline: discrepancy alone
        disc_auc = roc_auc_score(y, [a["mean_discrepancy"] for a in articles])
        print(f"  Baseline (mean_discrepancy) AUC: {disc_auc:.4f}")
    else:
        print(
            f"\n[4/4] Insufficient class balance for classification (errors={n_with_errors}, clean={n_clean})"
        )

    elapsed = time.time() - t0
    print(f"\n  Total time: {elapsed:.1f}s")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "experiment": "H23_pmc_statcheck",
        "n_searched": len(pmc_ids),
        "n_with_statcheck_results": len(articles),
        "n_with_errors": n_with_errors,
        "n_clean": n_clean,
        "mean_error_rate": round(float(np.mean(error_rates)), 4),
        "mean_frac_significant": round(float(np.mean(frac_sig)), 4),
        "mean_frac_just_below_05": round(float(np.mean(frac_just_below)), 4),
        "elapsed_s": round(elapsed, 1),
        "framing": "quasi-supervised: statcheck Error flag as proxy label, NOT ground truth for p-hacking",
    }
    out_path = RESULTS_DIR / "h23_pmc_statcheck.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"  Results saved: {out_path}")


if __name__ == "__main__":
    main()
