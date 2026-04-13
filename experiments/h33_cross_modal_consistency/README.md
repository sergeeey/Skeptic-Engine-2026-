# H33 — Cross-Modal Consistency Detection

## Hypothesis
Fabricated or manipulated datasets exhibit **inconsistency across data modalities**
(e.g., proteomics vs transcriptomics, or scRNA-seq vs bulk RNA-seq for the same samples).

Legitimate biological data should show concordant patterns across modalities
(e.g., genes with high mRNA should have detectable protein levels).
Fabricated data often fails to maintain these cross-modal relationships.

## Signals

| Signal | Description |
|---|---|
| `gene_protein_correlation` | Spearman correlation between mRNA and protein levels |
| `rank_consistency` | Kendall's tau of gene rankings across modalities |
| `pathway_concordance` | Jaccard index of enriched pathways |
| `sample_clustering_agreement` | ARI between clusterings from different modalities |
| `effect_size_ratio` | Ratio of effect sizes (proteomics / transcriptomics) |

## Method

1. Collect paired multi-omics datasets (e.g., CPTAC proteomics + transcriptomics)
2. Compute per-sample cross-modal concordance metrics
3. Compare real vs synthetic/fabricated data consistency
4. Flag datasets with anomalously low cross-modal agreement

## Data Sources

- **CPTAC**: Matched proteomics + genomics for cancer samples
- **GEO**: Multi-omics datasets with paired measurements
- **Synthetic**: Fabricated data with broken cross-modal relationships

## Validation

- **Positive control:** CPTAC real data (should show high consistency)
- **Negative control:** Independently fabricated datasets (should show low consistency)
- **Target:** Separation > 0.5 between real and fabricated

## Files

- `run_h33.py` — main experiment script
- `consistency_metrics.py` — cross-modal concordance computation
- `results/h33_results.json` — experiment results
