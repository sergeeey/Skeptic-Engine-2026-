"""H33 — Cross-Modal Consistency Detection.

Detects fabricated datasets by measuring consistency between data modalities
(e.g., proteomics vs transcriptomics for the same biological samples).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats
from sklearn.metrics import adjusted_rand_score

PROJECT_ROOT = Path(__file__).resolve().parents[2]
H33_DIR = Path(__file__).resolve().parent


# ===========================================================================
# Consistency metrics
# ===========================================================================
def gene_protein_correlation(mrna: np.ndarray, protein: np.ndarray) -> float:
    """Spearman correlation between mRNA and protein levels per gene.
    
    Parameters
    ----------
    mrna : np.ndarray of shape (n_samples, n_genes)
    protein : np.ndarray of shape (n_samples, n_genes)
    
    Returns
    -------
    Mean Spearman correlation across samples.
    """
    correlations = []
    for i in range(mrna.shape[0]):
        if mrna[i].std() > 1e-10 and protein[i].std() > 1e-10:
            rho, _ = stats.spearmanr(mrna[i], protein[i])
            correlations.append(rho)
    return float(np.mean(correlations)) if correlations else 0.0


def rank_consistency(mrna: np.ndarray, protein: np.ndarray) -> float:
    """Kendall's tau of gene rankings across modalities.
    
    Higher values indicate more consistent rankings.
    """
    taus = []
    for i in range(mrna.shape[0]):
        if mrna[i].std() > 1e-10 and protein[i].std() > 1e-10:
            tau, _ = stats.kendalltau(
                np.argsort(np.argsort(mrna[i])),
                np.argsort(np.argsort(protein[i])),
            )
            taus.append(tau)
    return float(np.mean(taus)) if taus else 0.0


def pathway_concordance(
    mrna: np.ndarray,
    protein: np.ndarray,
    n_top_genes: int = 50,
) -> float:
    """Jaccard index of top-N genes across modalities.
    
    Uses most variable genes as proxy for pathway enrichment.
    """
    jaccards = []
    for i in range(mrna.shape[0]):
        mrna_top = set(np.argsort(-np.abs(mrna[i] - mrna[i].mean()))[:n_top_genes])
        protein_top = set(np.argsort(-np.abs(protein[i] - protein[i].mean()))[:n_top_genes])
        
        intersection = len(mrna_top & protein_top)
        union = len(mrna_top | protein_top)
        jaccards.append(intersection / union if union > 0 else 0.0)
    return float(np.mean(jaccards))


def sample_clustering_agreement(
    mrna: np.ndarray,
    protein: np.ndarray,
    n_clusters: int = 3,
) -> float:
    """ARI between clusterings from different modalities.
    
    Uses simple k-means-like assignment based on distance to centroids.
    """
    from sklearn.cluster import KMeans
    
    # Cluster each modality separately
    kmeans_mrna = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    kmeans_prot = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    
    labels_mrna = kmeans_mrna.fit_predict(mrna)
    labels_prot = kmeans_prot.fit_predict(protein)
    
    return float(adjusted_rand_score(labels_mrna, labels_prot))


def effect_size_ratio(mrna: np.ndarray, protein: np.ndarray) -> float:
    """Ratio of effect sizes (protein / mRNA variance explained).
    
    Values near 1.0 indicate consistent effect sizes across modalities.
    """
    mrna_var = np.var(mrna, axis=0)
    protein_var = np.var(protein, axis=0)
    
    # Avoid division by zero
    valid = mrna_var > 1e-10
    if not valid.any():
        return 0.0
    
    ratios = protein_var[valid] / mrna_var[valid]
    # Log-transform for symmetry
    log_ratios = np.log1p(ratios)
    return float(np.mean(log_ratios))


# ===========================================================================
# Data generation
# ===========================================================================
def generate_real_like_data(
    n_samples: int = 50,
    n_genes: int = 100,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate realistic paired mRNA-protein data with biological correlation.
    
    Simulates the known moderate correlation (rho ~ 0.4-0.6) between
    transcript and protein levels due to post-transcriptional regulation.
    """
    if rng is None:
        rng = np.random.default_rng(42)
    
    # Generate latent biological signal
    latent = rng.normal(0, 1, size=(n_samples, n_genes))
    
    # mRNA: latent signal + noise
    mrna = latent + rng.normal(0, 0.5, size=(n_samples, n_genes))
    
    # Protein: latent signal + different noise + moderate correlation with mRNA
    protein = 0.5 * latent + 0.3 * mrna + rng.normal(0, 0.4, size=(n_samples, n_genes))
    
    return mrna, protein


def generate_fabricated_data(
    n_samples: int = 50,
    n_genes: int = 100,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate fabricated data with broken cross-modal relationships.
    
    Simulates independently generated mRNA and protein (no biological coupling).
    """
    if rng is None:
        rng = np.random.default_rng(42)
    
    # Independently generated - no shared latent structure
    mrna = rng.normal(0, 1, size=(n_samples, n_genes))
    protein = rng.normal(0, 1, size=(n_samples, n_genes))
    
    return mrna, protein


def generate_partially_fabricated_data(
    n_samples: int = 50,
    n_genes: int = 100,
    corruption_level: float = 0.5,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate partially fabricated data with weakened cross-modal relationships.
    
    Mix of real biological signal and random noise.
    """
    if rng is None:
        rng = np.random.default_rng(42)
    
    latent = rng.normal(0, 1, size=(n_samples, n_genes))
    
    # mRNA has some real signal
    mrna = latent + rng.normal(0, 0.5, size=(n_samples, n_genes))
    
    # Protein is partially corrupted
    protein = (
        (1 - corruption_level) * (0.5 * latent + 0.3 * mrna)
        + corruption_level * rng.normal(0, 1, size=(n_samples, n_genes))
    )
    
    return mrna, protein


# ===========================================================================
# Main experiment
# ===========================================================================
def compute_consistency_profile(
    mrna: np.ndarray,
    protein: np.ndarray,
) -> dict[str, float]:
    """Compute all consistency metrics for a dataset pair."""
    return {
        "gene_protein_correlation": gene_protein_correlation(mrna, protein),
        "rank_consistency": rank_consistency(mrna, protein),
        "pathway_concordance": pathway_concordance(mrna, protein),
        "sample_clustering_agreement": sample_clustering_agreement(mrna, protein),
        "effect_size_ratio": effect_size_ratio(mrna, protein),
    }


def run_experiment() -> dict[str, Any]:
    """Run H33 cross-modal consistency experiment."""
    print("=" * 60)
    print("H33: Cross-Modal Consistency Detection")
    print("=" * 60)

    rng = np.random.default_rng(42)
    
    # 1. Generate data
    print("\n[1/4] Generating datasets...")
    real_mrna, real_protein = generate_real_like_data(rng=rng)
    fab_mrna, fab_protein = generate_fabricated_data(rng=rng)
    
    # Partially fabricated at different corruption levels
    partial_datasets = []
    for level in [0.2, 0.4, 0.6, 0.8]:
        p_mrna, p_protein = generate_partially_fabricated_data(
            corruption_level=level, rng=rng
        )
        partial_datasets.append((level, p_mrna, p_protein))

    print(f"  Real: {real_mrna.shape}")
    print(f"  Fabricated: {fab_mrna.shape}")
    print(f"  Partial: {len(partial_datasets)} corruption levels")

    # 2. Compute consistency
    print("\n[2/4] Computing consistency metrics...")
    real_profile = compute_consistency_profile(real_mrna, real_protein)
    fab_profile = compute_consistency_profile(fab_mrna, fab_protein)
    partial_profiles = [
        (level, compute_consistency_profile(mrna, protein))
        for level, mrna, protein in partial_datasets
    ]

    print(f"  Real correlation: {real_profile['gene_protein_correlation']:.3f}")
    print(f"  Fabricated correlation: {fab_profile['gene_protein_correlation']:.3f}")

    # 3. Compute separation
    print("\n[3/4] Computing separation scores...")
    metric_names = list(real_profile.keys())
    separations = {}
    for metric in metric_names:
        real_val = real_profile[metric]
        fab_val = fab_profile[metric]
        separation = abs(real_val - fab_val)
        separations[metric] = separation

    # Overall separation (mean across metrics)
    overall_separation = float(np.mean(list(separations.values())))

    print(f"  Overall separation: {overall_separation:.3f}")
    for metric, sep in sorted(separations.items(), key=lambda x: -x[1]):
        print(f"    {metric}: {sep:.3f}")

    # 4. Partial corruption analysis
    print("\n[4/4] Analyzing partial corruption...")
    corruption_trends = {}
    for metric in metric_names:
        values = [profile[metric] for _, profile in partial_profiles]
        levels = [level for level, _, _ in partial_datasets]
        
        if len(levels) >= 3:
            slope, p_val = stats.linregress(levels, values)[:2]
            corruption_trends[metric] = {
                "slope": slope,
                "p_value": p_val,
                "values": values,
            }

    # Classification test
    all_profiles = [
        ("real", real_profile),
        ("fabricated", fab_profile),
    ] + [(f"partial_{lvl}", prof) for lvl, prof in partial_profiles]
    
    # Simple threshold classifier on gene_protein_correlation
    threshold = (real_profile["gene_protein_correlation"] + fab_profile["gene_protein_correlation"]) / 2
    n_correct = 0
    for label, profile in all_profiles:
        predicted_real = profile["gene_protein_correlation"] > threshold
        actual_real = label == "real"
        if predicted_real == actual_real:
            n_correct += 1
    
    accuracy = n_correct / len(all_profiles)

    print(f"  Threshold accuracy: {accuracy:.3f}")
    for metric, trend in corruption_trends.items():
        print(f"    {metric}: slope={trend['slope']:.4f}, p={trend['p_value']:.4f}")

    # Build results
    summary = {
        "n_real_datasets": 1,
        "n_fabricated_datasets": 1,
        "n_partial_levels": len(partial_datasets),
        "overall_separation": overall_separation,
        "separations": separations,
        "classification_accuracy": accuracy,
        "corruption_trends": {
            k: {"slope": v["slope"], "p_value": v["p_value"]}
            for k, v in corruption_trends.items()
        },
        "conclusion": "SUCCESS" if overall_separation > 0.3 else "WEAK",
    }

    dataset_reports = []
    for label, profile in all_profiles:
        dataset_reports.append({
            "dataset_type": label,
            **profile,
        })

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Overall separation: {summary['overall_separation']:.3f}")
    print(f"  Classification accuracy: {summary['classification_accuracy']:.3f}")
    print(f"  Conclusion: {summary['conclusion']}")

    print(f"\nTop separating metrics:")
    for metric, sep in sorted(separations.items(), key=lambda x: -x[1])[:3]:
        print(f"  {metric}: {sep:.3f}")

    return {
        "experiment": "H33",
        "description": "Cross-Modal Consistency Detection",
        "summary": summary,
        "dataset_reports": dataset_reports,
    }


if __name__ == "__main__":
    results = run_experiment()

    # Save results
    out_path = H33_DIR / "results" / "h33_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nResults saved to: {out_path}")
