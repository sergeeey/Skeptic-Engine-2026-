"""H23-pmc v2 — Regex extraction + p-value recomputation from PMC articles.

Since statcheck_python fails on XML-extracted text, we use our own:
1. Regex to extract APA-style test results (F, t, r, chi2 with df and p)
2. Recompute p from test statistic + df using scipy
3. Compare reported vs recomputed → Error quasi-label

Usage:
    python experiments/h23_phacking_behavioral/run_h23_pmc_recompute.py [--max-articles 300]
"""

from __future__ import annotations

import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

import numpy as np
from scipy import stats as sp_stats

RESULTS_DIR = Path(__file__).resolve().parent / "results"
DATA_DIR = Path(__file__).resolve().parent / "data"

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def search_pmc(query: str, max_results: int) -> list[str]:
    params = f"db=pmc&term={quote(query)}&retmax={max_results}&retmode=json"
    req = Request(f"{ESEARCH_URL}?{params}", headers={"User-Agent": "SkepticEngine/0.1"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read()).get("esearchresult", {}).get("idlist", [])


def fetch_pmc_fulltext(pmc_id: str) -> str:
    url = f"{EFETCH_URL}?db=pmc&id={pmc_id}&rettype=xml&retmode=xml"
    req = Request(url, headers={"User-Agent": "SkepticEngine/0.1"})
    with urlopen(req, timeout=30) as resp:
        xml_bytes = resp.read()
    root = ET.fromstring(xml_bytes.decode("utf-8", errors="replace"))
    texts = []
    for elem in root.iter():
        if elem.text:
            texts.append(elem.text)
        if elem.tail:
            texts.append(elem.tail)
    return " ".join(texts)


def extract_and_recompute(text: str) -> list[dict]:
    """Extract APA-style stats and recompute p-values."""
    results = []

    patterns = [
        # F(df1, df2) = value, p = reported
        (
            r"[Ff]\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*=\s*([\d.]+)\s*,?\s*[pP]\s*([=<>≤≥])\s*(\.?\d+\.?\d*)",
            "F",
        ),
        # t(df) = value, p = reported
        (r"[tT]\s*\(\s*(\d+)\s*\)\s*=\s*(-?[\d.]+)\s*,?\s*[pP]\s*([=<>≤≥])\s*(\.?\d+\.?\d*)", "t"),
        # r(df) = value, p = reported
        (
            r"[rR]\s*\(\s*(\d+)\s*\)\s*=\s*(-?\.?[\d.]+)\s*,?\s*[pP]\s*([=<>≤≥])\s*(\.?\d+\.?\d*)",
            "r",
        ),
    ]

    for pattern, stat_type in patterns:
        for match in re.finditer(pattern, text):
            try:
                if stat_type == "F":
                    df1 = int(match.group(1))
                    df2 = int(match.group(2))
                    value = float(match.group(3))
                    comparison = match.group(4)
                    reported_p_str = match.group(5)

                    if reported_p_str.startswith("."):
                        reported_p_str = "0" + reported_p_str
                    reported_p = float(reported_p_str)

                    # Recompute
                    recomputed_p = 1.0 - sp_stats.f.cdf(value, df1, df2)

                elif stat_type == "t":
                    df = int(match.group(1))
                    value = abs(float(match.group(2)))
                    comparison = match.group(3)
                    reported_p_str = match.group(4)

                    if reported_p_str.startswith("."):
                        reported_p_str = "0" + reported_p_str
                    reported_p = float(reported_p_str)

                    recomputed_p = 2.0 * (1.0 - sp_stats.t.cdf(value, df))

                elif stat_type == "r":
                    df = int(match.group(1))
                    value = float(match.group(2))
                    comparison = match.group(3)
                    reported_p_str = match.group(4)

                    if reported_p_str.startswith("."):
                        reported_p_str = "0" + reported_p_str
                    reported_p = float(reported_p_str)

                    # r to t transformation
                    if abs(value) < 1.0 and df > 0:
                        t_val = value * np.sqrt(df / (1 - value**2))
                        recomputed_p = 2.0 * (1.0 - sp_stats.t.cdf(abs(t_val), df))
                    else:
                        continue
                else:
                    continue

                if not (0 < reported_p <= 1) or not (0 <= recomputed_p <= 1):
                    continue

                discrepancy = abs(reported_p - recomputed_p)
                # Error: discrepancy > 0.05 (standard statcheck threshold)
                is_error = discrepancy > 0.05
                # Decision error: error that changes significance conclusion
                reported_sig = reported_p < 0.05
                recomputed_sig = recomputed_p < 0.05
                is_decision_error = is_error and (reported_sig != recomputed_sig)

                results.append(
                    {
                        "stat_type": stat_type,
                        "reported_p": round(reported_p, 6),
                        "recomputed_p": round(recomputed_p, 6),
                        "discrepancy": round(discrepancy, 6),
                        "is_error": is_error,
                        "is_decision_error": is_decision_error,
                        "comparison": comparison,
                    }
                )

            except (ValueError, ZeroDivisionError):
                continue

    return results


def article_features(stats: list[dict]) -> dict:
    """Per-article behavioral features from extracted+recomputed stats."""
    n = len(stats)
    reported = np.array([s["reported_p"] for s in stats])
    discrepancies = np.array([s["discrepancy"] for s in stats])
    n_errors = sum(s["is_error"] for s in stats)
    n_decision_errors = sum(s["is_decision_error"] for s in stats)

    return {
        "n_tests": n,
        "n_errors": n_errors,
        "n_decision_errors": n_decision_errors,
        "has_error": n_errors > 0,
        "has_decision_error": n_decision_errors > 0,
        "error_rate": n_errors / n,
        "mean_p": float(np.mean(reported)),
        "std_p": float(np.std(reported)),
        "min_p": float(np.min(reported)),
        "frac_sig": float((reported < 0.05).mean()),
        "frac_just_below_05": float(((reported > 0.04) & (reported < 0.05)).mean()),
        "mean_discrepancy": float(np.mean(discrepancies)),
        "max_discrepancy": float(np.max(discrepancies)),
        "volatility": float(np.std(np.diff(reported))) if n > 1 else 0.0,
        "frac_decreasing": float((np.diff(reported) < 0).mean()) if n > 1 else 0.0,
    }


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
    print(f"H23-pmc v2 — Regex + Recompute on {max_articles} PMC articles")
    print("=" * 70)
    t0 = time.time()

    print("\n[1/4] Searching PMC...")
    query = '("psychological science"[Journal] OR "journal of personality and social psychology"[Journal]) AND open access[filter]'
    pmc_ids = search_pmc(query, max_articles)
    print(f"  Found {len(pmc_ids)} articles")

    print(f"\n[2/4] Extracting + recomputing...")
    articles = []
    n_no_stats = 0
    n_failed = 0

    for i, pmc_id in enumerate(pmc_ids):
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(pmc_ids)} (extracted: {len(articles)}, no stats: {n_no_stats})")

        try:
            time.sleep(0.35)
            text = fetch_pmc_fulltext(pmc_id)
            stats = extract_and_recompute(text)

            if len(stats) >= 3:
                features = article_features(stats)
                features["pmc_id"] = pmc_id
                articles.append(features)
            else:
                n_no_stats += 1
        except Exception:
            n_failed += 1

    print(f"\n  Articles with ≥3 recomputed stats: {len(articles)}")
    print(f"  No stats: {n_no_stats}, Failed: {n_failed}")

    if len(articles) < 10:
        print("  Too few. Try more articles or broader query.")
        # Save what we have anyway
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "pmc_recomputed.json").write_text(
            json.dumps(articles, indent=2, default=str), encoding="utf-8"
        )
        return

    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "pmc_recomputed.json").write_text(
        json.dumps(articles, indent=2, default=str), encoding="utf-8"
    )

    # Analysis
    print(f"\n[3/4] Analysis...")
    n_with_errors = sum(a["has_error"] for a in articles)
    n_clean = len(articles) - n_with_errors

    print(f"  Total: {len(articles)}")
    print(f"  With errors: {n_with_errors} ({n_with_errors / len(articles):.1%})")
    print(f"  Clean: {n_clean} ({n_clean / len(articles):.1%})")
    print(f"  Mean error rate: {np.mean([a['error_rate'] for a in articles]):.4f}")
    print(f"  Mean discrepancy: {np.mean([a['mean_discrepancy'] for a in articles]):.6f}")
    print(f"  Decision errors found: {sum(a['has_decision_error'] for a in articles)}")

    # Classification if balanced
    if n_with_errors >= 5 and n_clean >= 5:
        print(f"\n[4/4] Quasi-supervised classification...")
        feature_keys = [
            "mean_p",
            "std_p",
            "min_p",
            "frac_sig",
            "frac_just_below_05",
            "mean_discrepancy",
            "max_discrepancy",
            "volatility",
            "frac_decreasing",
            "n_tests",
        ]
        X = np.array([[a[k] for k in feature_keys] for a in articles])
        y = np.array([1 if a["has_error"] else 0 for a in articles])
        X = np.nan_to_num(X, nan=0.0)

        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import roc_auc_score
        from sklearn.model_selection import StratifiedKFold
        from sklearn.preprocessing import StandardScaler

        n_splits = min(5, min(n_with_errors, n_clean))
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        scaler = StandardScaler()

        fold_aucs = []
        for train_idx, test_idx in cv.split(X, y):
            model = LogisticRegression(max_iter=2000, random_state=42)
            model.fit(scaler.fit_transform(X[train_idx]), y[train_idx])
            try:
                proba = model.predict_proba(scaler.transform(X[test_idx]))[:, 1]
                fold_aucs.append(roc_auc_score(y[test_idx], proba))
            except ValueError:
                continue

        if fold_aucs:
            print(f"  LR AUC: {np.mean(fold_aucs):.4f} ± {np.std(fold_aucs):.4f}")

        baseline = roc_auc_score(y, [a["mean_discrepancy"] for a in articles])
        print(f"  Baseline (discrepancy) AUC: {baseline:.4f}")
    else:
        print(
            f"\n[4/4] Insufficient balance for classification (errors={n_with_errors}, clean={n_clean})"
        )

    elapsed = time.time() - t0
    print(f"\n  Time: {elapsed:.1f}s")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "experiment": "H23_pmc_recompute",
        "n_searched": len(pmc_ids),
        "n_extracted": len(articles),
        "n_with_errors": n_with_errors,
        "n_clean": n_clean,
        "elapsed_s": round(elapsed, 1),
        "framing": "quasi-supervised: reported≠recomputed as proxy label",
    }
    (RESULTS_DIR / "h23_pmc_recompute.json").write_text(
        json.dumps(output, indent=2, default=str), encoding="utf-8"
    )
    print(f"  Saved: {RESULTS_DIR / 'h23_pmc_recompute.json'}")


if __name__ == "__main__":
    main()
