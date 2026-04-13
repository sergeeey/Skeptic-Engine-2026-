"""H32 Real Data Validation — Run temporal drift detection on PubMed data.

Fetches abstracts from PubMed, extracts p-values, and runs temporal
drift detection on real author publication histories.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import numpy as np
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parents[2]
H32_DIR = PROJECT_ROOT / "experiments" / "h32_temporal_drift"

NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def pubmed_search(query: str, retmax: int = 100) -> list[str]:
    """Search PubMed and return list of PMIDs."""
    url = f"{NCBI_BASE}/esearch.fcgi?db=pubmed&term={query}&retmax={retmax}&retmode=json"
    req = Request(url, headers={"User-Agent": "SkepticEngine/1.0"})
    with urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data.get("esearchresult", {}).get("idlist", [])


def pubmed_fetch_batch(pmids: list[str]) -> list[dict[str, Any]]:
    """Fetch abstracts for a batch of PMIDs."""
    id_str = ",".join(pmids)
    url = f"{NCBI_BASE}/efetch.fcgi?db=pubmed&id={id_str}&retmode=json"
    req = Request(url, headers={"User-Agent": "SkepticEngine/1.0"})
    with urlopen(req, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    
    results = []
    for article in data.get("result", []):
        if article.get("uid") in ("uids",):
            continue
        results.append({
            "pmid": article.get("uid", ""),
            "pub_date": article.get("pubdate", ""),
            "authors": article.get("authors", []),
            "title": article.get("title", ""),
            "abstract": article.get("abstract", ""),
        })
    
    return results


def extract_pvalues_from_text(text: str) -> list[float]:
    """Extract p-values from text using regex patterns."""
    import re
    
    patterns = [
        r"p\s*[<>=]\s*\.?(\d+(?:\.\d+)?)",  # p < 0.001, p = .023
        r"p\s*[<>=]\s*(\d+\.\d+)",  # p < 0.05
    ]
    
    pvalues = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                # Handle leading dot: .023 → 0.023
                val = float(match) if match.startswith(("0", "1")) else float("0" + match)
                if 0 <= val <= 1:
                    pvalues.append(val)
            except ValueError:
                pass
    
    return pvalues


def run_h32_on_pubmed_data(
    query: str = "cancer+biosmark",
    n_articles: int = 200,
) -> dict[str, Any]:
    """Run H32 temporal drift detection on PubMed data."""
    print("=" * 60)
    print("H32: Real Data Validation — PubMed")
    print("=" * 60)

    # 1. Search PubMed
    print(f"\n[1/4] Searching PubMed for: {query.replace('+', ' ')}")
    pmids = pubmed_search(query, retmax=n_articles)
    print(f"  Found {len(pmids)} articles")

    if not pmids:
        return {"status": "no_results", "query": query}

    # 2. Fetch abstracts
    print("\n[2/4] Fetching abstracts...")
    articles = []
    batch_size = 50
    for i in range(0, len(pmids), batch_size):
        batch_pmids = pmids[i:i+batch_size]
        batch_articles = pubmed_fetch_batch(batch_pmids)
        articles.extend(batch_articles)
        time.sleep(0.5)  # Rate limiting
        print(f"  Fetched {len(articles)}/{len(pmids)} articles")

    # 3. Extract p-values
    print("\n[3/4] Extracting p-values...")
    pvalue_data = []
    for article in articles:
        abstract = article.get("abstract", "")
        title = article.get("title", "")
        text = f"{title} {abstract}"
        
        pvalues = extract_pvalues_from_text(text)
        pub_date = article.get("pub_date", "")
        year = int(pub_date[:4]) if pub_date and pub_date[:4].isdigit() else None
        
        if pvalues and year:
            pvalue_data.append({
                "pmid": article.get("pmid", ""),
                "year": year,
                "n_pvalues": len(pvalues),
                "pvalues": pvalues,
            })

    print(f"  Articles with p-values: {len(pvalue_data)}")
    
    if len(pvalue_data) < 10:
        return {
            "status": "insufficient_data",
            "n_articles_with_pvalues": len(pvalue_data),
        }

    # 4. Temporal analysis
    print("\n[4/4] Running temporal analysis...")
    years = sorted(set(d["year"] for d in pvalue_data))
    year_to_pvalues = {}
    for d in pvalue_data:
        year_to_pvalues.setdefault(d["year"], []).extend(d["pvalues"])

    # Compute yearly features
    yearly_features = {}
    for year in years:
        pvs = year_to_pvalues.get(year, [])
        if len(pvs) >= 3:
            frac_below_05 = sum(1 for p in pvs if 0.04 <= p < 0.05) / len(pvs)
            frac_sig = sum(1 for p in pvs if p < 0.05) / len(pvs)
            mean_p = np.mean(pvs)
            yearly_features[year] = {
                "frac_just_below_05": frac_below_05,
                "frac_significant": frac_sig,
                "mean_p": mean_p,
                "n_pvalues": len(pvs),
            }

    # Trend analysis
    trend_years = [y for y in years if y in yearly_features]
    if len(trend_years) >= 5:
        from sklearn.linear_model import LinearRegression
        
        X = np.array(trend_years).reshape(-1, 1)
        
        trends = {}
        for feature in ["frac_just_below_05", "frac_significant", "mean_p"]:
            y_vals = np.array([yearly_features[y][feature] for y in trend_years])
            model = LinearRegression()
            model.fit(X, y_vals)
            slope = model.coef_[0]
            
            # p-value
            y_pred = model.predict(X)
            residuals = y_vals - y_pred
            ss_res = np.sum(residuals ** 2)
            ss_tot = np.sum((y_vals - np.mean(y_vals)) ** 2)
            r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            n = len(trend_years)
            f_stat = (r_squared / (1 - r_squared)) * (n - 2) if r_squared < 1 and r_squared > 0 else 0
            p_val = 1 - stats.f.cdf(f_stat, 1, n - 2) if f_stat > 0 else 1.0
            
            trends[feature] = {
                "slope": slope,
                "p_value": p_val,
                "significant": p_val < 0.01,
            }
    else:
        trends = {}

    # Summary
    n_significant_trends = sum(
        1 for t in trends.values() if t.get("significant", False)
    )
    drift_detected = n_significant_trends > 0

    summary = {
        "n_pmids_searched": len(pmids),
        "n_articles_fetched": len(articles),
        "n_articles_with_pvalues": len(pvalue_data),
        "n_years_with_data": len(yearly_features),
        "drift_detected": drift_detected,
        "n_significant_trends": n_significant_trends,
        "trends": trends,
        "yearly_summary": {
            str(y): {k: v for k, v in feat.items() if k != "pvalues"}
            for y, feat in yearly_features.items()
        },
    }

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"  PMIDs searched: {summary['n_pmids_searched']}")
    print(f"  Articles with p-values: {summary['n_articles_with_pvalues']}")
    print(f"  Years with data: {summary['n_years_with_data']}")
    print(f"  Drift detected: {drift_detected}")
    print(f"  Significant trends: {n_significant_trends}")

    if trends:
        print(f"\nTrend analysis:")
        for feature, trend in trends.items():
            sig = "⚠️ SIGNIFICANT" if trend.get("significant") else ""
            print(f"  {feature}: slope={trend['slope']:.4f}, p={trend['p_value']:.4f} {sig}")

    return {
        "experiment": "H32_real_pubmed",
        "description": "Temporal drift detection on PubMed data",
        "query": query,
        "summary": summary,
    }


if __name__ == "__main__":
    results = run_h32_on_pubmed_data(query="cancer+biomarker", n_articles=200)

    # Save results
    out_path = H32_DIR / "results" / "h32_real_pubmed_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nResults saved to: {out_path}")
