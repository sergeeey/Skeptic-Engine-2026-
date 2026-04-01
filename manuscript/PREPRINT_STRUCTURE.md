# Skeptic Engine — bioRxiv Preprint Structure

## Title
**Structural Dependency Analysis for Scientific Data Integrity: An Interpretable Screening Engine Validated Across 55,000 Real-World Data Points**

## Authors
Sergey V. Boiko (Independent researcher, Almaty, Kazakhstan)

## One-Sentence Thesis
We built an interpretable tool that checks scientific data by finding broken biological dependencies — and validated it on 55,000+ real data points from 8 independent sources.

---

## Structure

### Abstract (250 words)
- Problem: scientific data integrity lacks interpretable automated screening
- Method: syndrome-style constraint analysis (pairwise + module + residual)
- Key results: separation on RPCB (p=0.0001), ClinVar 8/8 genes, MaveDB experimental
- Conclusion: structural dependency analysis provides interpretable, validated integrity screening

### 1. Introduction
- Scientific data integrity crisis (14,000 retractions in 2023)
- Existing tools: StatCheck (reporting errors), ImageTwin (figures) — none for raw data structure
- Gap: no tool explains WHICH dependencies are broken
- Our contribution: interpretable structural screening engine

### 2. Methods
#### 2.1 Constraint Model
- Pairwise rank-correlation with bootstrap stability selection
- Module-level constraints via hierarchical clustering
- Latent reconstruction residuals (optional AE)

#### 2.2 Syndrome Scoring
- Violation vector computation
- 4-class classification: clean / technical_noise / local_break / structural_anomaly
- Aggregation: 0.5*pairwise + 0.3*module + 0.2*residual

#### 2.3 Three-Level Verdict
- CLEAN / UNCERTAIN / FLAGGED
- Configurable uncertainty band

#### 2.4 Datasets
| Source | Type | N |
|--------|------|---|
| CPTAC proteomics | Protein expression | 140 samples |
| PBMC3k scRNA-seq | UMI counts | 2,700 cells |
| ARCHCODE ClinVar | Genomic variants | 30,318 variants |
| MaveDB | Experimental mutagenesis | 12,000+ variants |
| TCGA | Cancer proteomics | 1,808 samples |
| GTEx | Healthy tissue expression | 54 tissues |
| RPCB | Replication outcomes | 30 experiments |

### 3. Results
#### 3.1 Within-Dataset Detection (H24/H25)
- Fusion AUC 0.978 (scRNA-seq), 1.000 (proteomics)
- Statistical robustness: p<0.001, power=1.0, 95% CI [0.970, 0.984]
- QC baseline comparison: fusion +4.2pp vs standard QC

#### 3.2 Syndrome Layer (H29)
- Proteomics: random/shuffle separation=0.594
- scRNA-seq portability: separation=0.534
- Module-breaking: 3/3 targeted breaks detected in top-5

#### 3.3 Real-World Validation
- **ClinVar expert-reviewed**: 8/8 genes, 21,532 variants, mean sep=0.111
- **ARCHCODE 9 loci**: 30,318 variants, 9/9 signal detected
- **MaveDB experimental**: 3/3 genes positive (VKORC1 sep=+0.204)
- **RPCB**: replicated vs failed sep=0.685, p=0.0001
- **GTEx**: 54 healthy tissues CLEAN (reference baseline)
- **TCGA**: 5/5 cancer types CLEAN (sanity check, FPR=0%)
- **Retracted data**: GSE160269 CLEAN (not false-accused)

#### 3.4 Novel Applications
- Biology detector: cancer vs normal separation=0.185 on CPTAC
- Bio-AI validation: correct quality ranking of synthetic data

#### 3.5 Honest Negatives
- Cross-dataset generalization fails (AUC<0.50)
- Self-check does not detect mixed fabrication (injection test)
- Noise 10% not detected by syndrome
- 0/15 confirmed fabricators deposited raw GEO data
- MaveDB Bonferroni-corrected p=0.07 (borderline)

### 4. Discussion
#### 4.1 Structural Integrity vs Fraud Detection
- "anomaly != fraud" — central principle
- Tool produces evidence for expert review, not verdicts

#### 4.2 Limitations
- Supervised detector, not universal screener
- No ground truth for real fabrication (fabricators don't share data)
- Small samples limit stability selection
- Benford features domain-specific (UMI vs continuous)

#### 4.3 Comparison with Existing Tools
| Tool | Scope | Interpretable | Raw data |
|------|-------|---------------|----------|
| StatCheck | Reporting errors | No | No |
| ImageTwin | Figure manipulation | No | No |
| Standard QC | Biological artifacts | Partial | Yes |
| **Skeptic Engine** | **Structural integrity** | **Yes** | **Yes** |

#### 4.4 Future Directions
- Real fraud validation (when data becomes available)
- Cross-dataset domain adaptation
- Integration with journal submission pipelines
- Bio-AI synthetic data quality certification

### 5. Conclusions
3 sentences: tool works, validated on real data, interpretable.

### Data Availability
- Code: https://github.com/sergeeey/Skeptic-Engine-2026-
- Archive: https://doi.org/10.5281/zenodo.19238786
- CLI: `pip install skeptic-engine && skeptic-toolkit matrix.mtx --mode syndrome`

### Supplementary
- S1: Full validation results table
- S2: Syndrome report examples (JSON + Markdown)
- S3: Statistical corrections and p-values
- S4: Module constraint lists per dataset
