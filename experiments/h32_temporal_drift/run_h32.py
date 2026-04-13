"""H32 — Temporal P-Hacking Detection.

Detects authors/labs with suspicious temporal drift in p-value distributions,
indicating potential p-hacking behavior over time.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats
from sklearn.linear_model import LinearRegression

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "experiments"
H32_DIR = Path(__file__).resolve().parent

# ===========================================================================
# Data structures
# ===========================================================================
@dataclass
class AuthorPValueSeries:
    """P-value time series for a single author."""

    author_id: str
    years: list[int]
    p_values: list[list[float]]  # p_values[i] = p-values published in year years[i]

    def n_papers(self) -> int:
        return len(self.years)

    def total_pvalues(self) -> int:
        return sum(len(pvs) for pvs in self.p_values)


@dataclass
class TemporalFeature:
    """A single temporal feature computed from p-value series."""

    name: str
    values: list[float]  # One value per year
    slope: float
    p_value: float  # Significance of slope
    is_significant_drift: bool  # p < 0.01


@dataclass
class DriftDetectionResult:
    """Result of drift detection for an author."""

    author_id: str
    n_papers: int
    n_pvalues: int
    features: list[TemporalFeature]
    drift_detected: bool
    max_drift_p_value: float
    n_significant_drifts: int
    flag: bool  # True if suspicious


# ===========================================================================
# Feature extraction
# ===========================================================================
def compute_frac_just_below_05(p_values: list[float]) -> float:
    """Fraction of p-values in [0.04, 0.05)."""
    if not p_values:
        return 0.0
    count = sum(1 for p in p_values if 0.04 <= p < 0.05)
    return count / len(p_values)


def compute_frac_significant(p_values: list[float]) -> float:
    """Fraction of p-values < 0.05."""
    if not p_values:
        return 0.0
    count = sum(1 for p in p_values if p < 0.05)
    return count / len(p_values)


def compute_mean_p(p_values: list[float]) -> float:
    """Mean p-value."""
    if not p_values:
        return 0.5
    return float(np.mean(p_values))


def compute_pvalue_clustering(p_values: list[float]) -> float:
    """Measure of p-value clustering near 0.05.
    
    Uses the ratio of p-values in [0.04, 0.05) to p-values in [0.01, 0.05).
    Higher values indicate more clustering near the threshold.
    """
    if not p_values:
        return 0.0
    near_threshold = sum(1 for p in p_values if 0.04 <= p < 0.05)
    significant = sum(1 for p in p_values if 0.01 <= p < 0.05)
    if significant == 0:
        return 0.0
    return near_threshold / significant


def compute_yearly_features(series: AuthorPValueSeries) -> dict[str, list[float]]:
    """Compute per-year features for an author's p-value series."""
    n_years = len(series.years)
    frac_below_05 = []
    frac_significant = []
    mean_p = []
    clustering = []

    for pvs in series.p_values:
        frac_below_05.append(compute_frac_just_below_05(pvs))
        frac_significant.append(compute_frac_significant(pvs))
        mean_p.append(compute_mean_p(pvs))
        clustering.append(compute_pvalue_clustering(pvs))

    return {
        "frac_just_below_05": frac_below_05,
        "frac_significant": frac_significant,
        "mean_p": mean_p,
        "pvalue_clustering": clustering,
    }


# ===========================================================================
# Drift detection
# ===========================================================================
def fit_trend(years: list[int], values: list[float]) -> tuple[float, float]:
    """Fit linear trend and return (slope, p_value)."""
    if len(years) < 3:
        return 0.0, 1.0

    X = np.array(years).reshape(-1, 1)
    y = np.array(values)

    model = LinearRegression()
    model.fit(X, y)
    slope = float(model.coef_[0])

    # Compute p-value for slope
    n = len(years)
    y_pred = model.predict(X)
    residuals = y - y_pred
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    
    if ss_tot == 0:
        return slope, 1.0

    r_squared = 1 - ss_res / ss_tot
    # F-test for significance of regression
    if n <= 2:
        return slope, 1.0
    f_stat = (r_squared / (1 - r_squared)) * (n - 2) if r_squared < 1 else float('inf')
    p_value = float(1 - stats.f.cdf(f_stat, 1, n - 2)) if f_stat > 0 else 1.0

    return slope, p_value


def detect_drift(series: AuthorPValueSeries) -> DriftDetectionResult:
    """Detect temporal drift in author's p-value patterns."""
    yearly_features = compute_yearly_features(series)
    years = series.years

    features = []
    for name, values in yearly_features.items():
        slope, p_val = fit_trend(years, values)
        features.append(TemporalFeature(
            name=name,
            values=values,
            slope=slope,
            p_value=p_val,
            is_significant_drift=p_val < 0.01,
        ))

    n_significant = sum(1 for f in features if f.is_significant_drift)
    min_p = min((f.p_value for f in features), default=1.0)

    # Flag if any feature shows significant drift
    drift_detected = n_significant > 0
    flag = drift_detected

    return DriftDetectionResult(
        author_id=series.author_id,
        n_papers=series.n_papers(),
        n_pvalues=series.total_pvalues(),
        features=features,
        drift_detected=drift_detected,
        max_drift_p_value=min_p,
        n_significant_drifts=n_significant,
        flag=flag,
    )


# ===========================================================================
# Synthetic data generation for validation
# ===========================================================================
def generate_synthetic_authors(rng: np.random.Generator) -> list[AuthorPValueSeries]:
    """Generate synthetic authors with known drift patterns.
    
    Creates:
    - 5 clean authors (no drift, uniform p-values)
    - 5 p-hacking authors (increasing frac_just_below_05 over time)
    """
    authors = []
    years = list(range(2010, 2024))
    n_years = len(years)

    # Clean authors
    for i in range(5):
        p_values_per_year = []
        for _ in years:
            # Uniform p-values, no drift
            n_pvals = rng.integers(3, 10)
            pvs = rng.uniform(0, 1, size=n_pvals).tolist()
            p_values_per_year.append(pvs)

        authors.append(AuthorPValueSeries(
            author_id=f"clean_author_{i+1}",
            years=years.copy(),
            p_values=p_values_per_year,
        ))

    # P-hacking authors
    for i in range(5):
        p_values_per_year = []
        for year_idx, year in enumerate(years):
            n_pvals = rng.integers(3, 10)
            # Increasing probability of p-values near 0.05 over time
            t = year_idx / n_years  # 0 to 1
            
            # Mix of uniform and clustered p-values
            n_clustered = int(n_pvals * t * 0.6)  # Increasing clustering
            n_uniform = n_pvals - n_clustered
            
            clustered = rng.uniform(0.04, 0.05, size=n_clustered).tolist()
            uniform = rng.uniform(0, 1, size=n_uniform).tolist()
            
            p_values_per_year.append(clustered + uniform)

        authors.append(AuthorPValueSeries(
            author_id=f"phacking_author_{i+1}",
            years=years.copy(),
            p_values=p_values_per_year,
        ))

    return authors


# ===========================================================================
# Main experiment
# ===========================================================================
def run_experiment() -> dict[str, Any]:
    """Run H32 temporal drift detection experiment."""
    print("=" * 60)
    print("H32: Temporal P-Hacking Detection")
    print("=" * 60)

    # 1. Generate synthetic data
    print("\n[1/4] Generating synthetic authors...")
    rng = np.random.default_rng(42)
    authors = generate_synthetic_authors(rng)
    print(f"  Generated {len(authors)} authors (5 clean, 5 p-hacking)")

    # 2. Detect drift
    print("\n[2/4] Running drift detection...")
    results = []
    for author in authors:
        result = detect_drift(author)
        results.append(result)

    n_flagged = sum(1 for r in results if r.flag)
    n_drift_detected = sum(1 for r in results if r.drift_detected)
    print(f"  Flagged: {n_flagged}/{len(results)}")
    print(f"  Drift detected: {n_drift_detected}/{len(results)}")

    # 3. Validation
    print("\n[3/4] Validating on synthetic ground truth...")
    true_labels = np.array([0] * 5 + [1] * 5)  # 5 clean, 5 p-hacking
    pred_labels = np.array([1 if r.flag else 0 for r in results])

    # Compute metrics
    tp = np.sum((pred_labels == 1) & (true_labels == 1))
    fp = np.sum((pred_labels == 1) & (true_labels == 0))
    tn = np.sum((pred_labels == 0) & (true_labels == 0))
    fn = np.sum((pred_labels == 0) & (true_labels == 1))

    accuracy = (tp + tn) / len(true_labels) if len(true_labels) > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    print(f"  Accuracy: {accuracy:.3f}")
    print(f"  Precision: {precision:.3f}")
    print(f"  Recall: {recall:.3f}")
    print(f"  F1: {f1:.3f}")

    # 4. Feature analysis
    print("\n[4/4] Analyzing drift features...")
    feature_drift_counts = {}
    for r in results:
        for f in r.features:
            if f.is_significant_drift:
                feature_drift_counts[f.name] = feature_drift_counts.get(f.name, 0) + 1

    print("  Significant drift counts by feature:")
    for name, count in sorted(feature_drift_counts.items(), key=lambda x: -x[1]):
        print(f"    {name}: {count}")

    # Build report
    author_reports = []
    for i, r in enumerate(results):
        author_reports.append({
            "author_id": r.author_id,
            "n_papers": r.n_papers,
            "n_pvalues": r.n_pvalues,
            "drift_detected": r.drift_detected,
            "flag": r.flag,
            "max_drift_p_value": r.max_drift_p_value,
            "n_significant_drifts": r.n_significant_drifts,
            "features": [
                {
                    "name": f.name,
                    "slope": f.slope,
                    "p_value": f.p_value,
                    "is_significant": f.is_significant_drift,
                }
                for f in r.features
            ],
            "true_label": "p-hacking" if i >= 5 else "clean",
        })

    # Sort by flag
    author_reports.sort(key=lambda x: (not x["flag"], x["author_id"]))

    summary = {
        "n_authors": len(authors),
        "n_flagged": n_flagged,
        "n_drift_detected": n_drift_detected,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "feature_drift_counts": feature_drift_counts,
    }

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Authors: {summary['n_authors']}")
    print(f"  Flagged: {summary['n_flagged']}")
    print(f"  Accuracy: {summary['accuracy']:.3f}")
    print(f"  F1: {summary['f1']:.3f}")

    print(f"\nFlagged authors:")
    for report in author_reports:
        if report["flag"]:
            print(f"  ⚠️ {report['author_id']}: drift_p={report['max_drift_p_value']:.4f} ({report['true_label']})")

    return {
        "experiment": "H32",
        "description": "Temporal P-Hacking Detection",
        "summary": summary,
        "author_reports": author_reports,
    }


if __name__ == "__main__":
    results = run_experiment()

    # Save results
    out_path = H32_DIR / "results" / "h32_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nResults saved to: {out_path}")
