"""H23 Scale-Up — Extract p-values from PubMed open-access psychology papers.

Uses statcheck_python to extract APA-formatted statistical results from
PubMed Central open-access full-text articles, then runs H23 behavioral
analysis on the extracted per-article p-value sequences.

Usage:
    python experiments/h23_phacking_behavioral/run_h23_extract.py [--max-articles 500]
"""

from __future__ import annotations

import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import numpy as np

RESULTS_DIR = Path(__file__).resolve().parent / "results"
DATA_DIR = Path(__file__).resolve().parent / "data"

# PubMed E-utilities
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def search_pubmed(query: str, max_results: int = 500) -> list[str]:
    """Search PubMed and return list of PMC IDs."""
    params = f"db=pmc&term={quote(query)}&retmax={max_results}&retmode=json"
    url = f"{ESEARCH_URL}?{params}"
    req = Request(url, headers={"User-Agent": "SkepticEngine/0.1"})
    with urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data.get("esearchresult", {}).get("idlist", [])


def fetch_pmc_text(pmc_id: str) -> str:
    """Fetch full text from PMC in plain text format."""
    # Try PMC OA API for full text
    url = f"{EFETCH_URL}?db=pmc&id={pmc_id}&rettype=xml&retmode=xml"
    req = Request(url, headers={"User-Agent": "SkepticEngine/0.1"})
    with urlopen(req, timeout=30) as resp:
        xml_text = resp.read().decode("utf-8", errors="replace")

    # Extract text from XML body
    try:
        root = ET.fromstring(xml_text)
        paragraphs = []
        for p in root.iter("p"):
            if p.text:
                paragraphs.append(p.text)
            for child in p:
                if child.tail:
                    paragraphs.append(child.tail)
        return " ".join(paragraphs)
    except ET.ParseError:
        return xml_text


def extract_pvalues_regex(text: str) -> list[dict]:
    """Fast regex extraction of p-values from text (no statcheck dependency for speed)."""
    results = []

    # APA-style patterns: p = .XXX, p < .XXX, p > .XXX
    patterns = [
        # p = 0.XXX or p = .XXX
        r"[pP]\s*[=<>≤≥]\s*(\.?\d+\.?\d*(?:[eE][+-]?\d+)?)",
        # F(df1, df2) = X.XX, p = .XXX
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
                    results.append(
                        {
                            "p_value": p_val,
                            "context": text[max(0, match.start() - 20) : match.end() + 20],
                        }
                    )
            except (ValueError, IndexError):
                continue

    return results


def extract_behavioral_features_from_pvalues(p_values: list[float]) -> np.ndarray:
    """Same 18 features as run_h23.py but from raw p-value list."""
    n = len(p_values)
    if n == 0:
        return np.zeros(18)

    p = np.clip(np.array(p_values), 1e-15, 1.0)
    features = []

    # 1-3: Basic stats
    features.append(np.mean(p))
    features.append(np.std(p) if n > 1 else 0)
    features.append(np.min(p))

    # 4-6: Threshold clustering
    features.append((p < 0.05).sum() / n)
    features.append(((p > 0.04) & (p < 0.05)).sum() / n)
    features.append(((p > 0.01) & (p < 0.05)).sum() / n)

    # 7-9: Sequence dynamics
    if n > 1:
        diffs = np.diff(p)
        features.append(np.mean(diffs))
        features.append(np.std(diffs))
        features.append((diffs < 0).sum() / len(diffs))
    else:
        features.extend([0, 0, 0])

    # 10-12: Terminal behavior
    features.append(p[-1])
    features.append(1.0 if p[-1] < 0.05 else 0.0)
    features.append(p[-1] - p[0] if n > 1 else 0)

    # 13-15: Entropy and volume
    hist, _ = np.histogram(p, bins=10, range=(0, 1))
    hist_norm = hist / max(hist.sum(), 1)
    entropy = -np.sum(hist_norm[hist_norm > 0] * np.log2(hist_norm[hist_norm > 0]))
    features.append(entropy)
    features.append(n)
    features.append(np.log1p(n))

    # 16-18: Patterns
    features.append(
        np.sum(np.abs(np.diff(np.sign(np.diff(p)))) > 0) / max(n - 2, 1) if n > 2 else 0
    )
    features.append(np.max(np.abs(np.diff(p))) if n > 1 else 0)
    features.append(np.corrcoef(np.arange(n), p)[0, 1] if n > 2 else 0)

    return np.array(features[:18])


def main() -> None:
    # WHY: positional int parse crashed on --max-articles flag; support both forms
    max_articles = 200
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
    print(f"H23 Scale-Up — Extracting p-values from {max_articles} PMC articles")
    print("=" * 70)
    t0 = time.time()

    # Search for psychology papers with statistical tests
    print("\n[1/4] Searching PubMed Central...")
    query = '("psychology"[Journal] OR "psychological"[Title]) AND ("p < " OR "p = " OR "F(" OR "t(") AND open access[filter]'
    pmc_ids = search_pubmed(query, max_results=max_articles)
    print(f"  Found {len(pmc_ids)} PMC articles")

    # Extract p-values from each article
    print(f"\n[2/4] Extracting p-values from articles...")
    articles = []
    failed = 0

    for i, pmc_id in enumerate(pmc_ids):
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(pmc_ids)}...")

        try:
            time.sleep(0.35)  # NCBI rate limit: 3 req/sec
            text = fetch_pmc_text(pmc_id)
            pvals = extract_pvalues_regex(text)

            if len(pvals) >= 3:  # Need at least 3 p-values for sequence features
                articles.append(
                    {
                        "pmc_id": pmc_id,
                        "n_pvalues": len(pvals),
                        "p_values": [p["p_value"] for p in pvals],
                    }
                )
        except Exception:
            failed += 1
            continue

    print(f"  Articles with ≥3 p-values: {len(articles)}")
    print(f"  Failed to fetch: {failed}")

    if len(articles) < 20:
        print("  Too few articles for meaningful analysis. Try increasing --max-articles.")
        return

    # Save extracted data
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    extract_path = DATA_DIR / "pmc_extracted_pvalues.json"
    extract_path.write_text(json.dumps(articles, indent=2), encoding="utf-8")
    print(f"  Saved: {extract_path}")

    # Extract features
    print(f"\n[3/4] Extracting behavioral features...")
    X = np.array([extract_behavioral_features_from_pvalues(a["p_values"]) for a in articles])
    X = np.nan_to_num(X, nan=0.0, posinf=10.0, neginf=-10.0)

    # Descriptive statistics
    n_pvals_per_article = [a["n_pvalues"] for a in articles]
    frac_sig_per_article = [np.mean(np.array(a["p_values"]) < 0.05) for a in articles]
    frac_just_below = [
        np.mean((np.array(a["p_values"]) > 0.04) & (np.array(a["p_values"]) < 0.05))
        for a in articles
    ]

    print(f"\n[4/4] Descriptive statistics...")
    print(f"  Articles: {len(articles)}")
    print(f"  Median p-values per article: {np.median(n_pvals_per_article):.0f}")
    print(f"  Mean fraction significant: {np.mean(frac_sig_per_article):.3f}")
    print(f"  Mean fraction just below 0.05: {np.mean(frac_just_below):.4f}")

    # Anomaly detection: flag articles with suspicious patterns
    from sklearn.ensemble import IsolationForest

    iso = IsolationForest(n_estimators=200, contamination=0.1, random_state=42)
    iso.fit(X)
    anomaly_scores = -iso.decision_function(X)  # higher = more anomalous
    anomaly_labels = iso.predict(X)  # -1 = anomaly, 1 = normal

    n_flagged = (anomaly_labels == -1).sum()
    print(
        f"\n  Isolation Forest flagged: {n_flagged}/{len(articles)} articles ({n_flagged / len(articles):.1%})"
    )

    # Show top-5 most anomalous
    top_anomalous = np.argsort(anomaly_scores)[-5:][::-1]
    print(f"\n  Top-5 most anomalous articles:")
    for idx in top_anomalous:
        a = articles[idx]
        pvals = a["p_values"]
        just_below = sum(0.04 < p < 0.05 for p in pvals)
        print(
            f"    PMC{a['pmc_id']}: {a['n_pvalues']} p-values, "
            f"{sum(p < 0.05 for p in pvals)} sig, "
            f"{just_below} just-below-0.05, "
            f"score={anomaly_scores[idx]:.3f}"
        )

    elapsed = time.time() - t0
    print(f"\n  Total time: {elapsed:.1f}s")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "experiment": "H23_pmc_extraction",
        "n_searched": len(pmc_ids),
        "n_articles_with_pvalues": len(articles),
        "n_failed": failed,
        "median_pvalues_per_article": round(float(np.median(n_pvals_per_article)), 1),
        "mean_frac_significant": round(float(np.mean(frac_sig_per_article)), 4),
        "mean_frac_just_below_05": round(float(np.mean(frac_just_below)), 4),
        "n_if_flagged": int(n_flagged),
        "frac_if_flagged": round(float(n_flagged / len(articles)), 4),
        "top5_anomalous": [
            {
                "pmc_id": articles[idx]["pmc_id"],
                "n_pvalues": articles[idx]["n_pvalues"],
                "anomaly_score": round(float(anomaly_scores[idx]), 4),
            }
            for idx in top_anomalous
        ],
        "elapsed_s": round(elapsed, 1),
    }
    out_path = RESULTS_DIR / "h23_pmc_extraction.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"  Results saved: {out_path}")


if __name__ == "__main__":
    main()
