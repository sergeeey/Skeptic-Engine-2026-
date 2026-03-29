# Paper Outline: Statistical Artifact Detection in scRNA-seq Count Matrices

## Working Title

**"Digit Forensics and Structural Anomaly Screening for Single-Cell RNA-seq Count Matrices"**

Alternative: "Detecting Non-Physical Statistical Patterns in scRNA-seq Data Using Financial Anomaly Detection Methods"

> **Framing principle:** The paper claims detection of statistical artifacts, not fraud. All flagged data requires expert review. We do not determine intent.

## Target Journal (ordered by fit)

1. **Bioinformatics** (Oxford) — Application Note (4 pages) or Original Paper
2. **GigaScience** — Data Note / Technical Note
3. **NAR Genomics and Bioinformatics** — Original Article
4. **PLoS Computational Biology** — Research Article

## Authors

- Sergey Boiko (lead — methodology transfer, fraud detection expertise)
- [Bioinformatics collaborator needed — domain validation, biological framing]

## Abstract (250 words)

**Background.** Single-cell RNA-seq count matrices deposited in public repositories are not routinely screened for fabrication. Current quality-control tools target biological artifacts (doublets, ambient RNA) rather than data manipulation. Meanwhile, financial fraud detection relies on digit-distribution analysis and structural anomaly scoring to detect manipulated tabular records — methods that have not been applied to UMI count data.

**Results.** We transferred two fraud detection approaches to scRNA-seq: (i) Benford first- and second-digit frequency profiling with chi-squared deviation scoring (21 features), and (ii) cell-level structural features with Isolation Forest anomaly scoring (9 features). We evaluated three simulated fabrication types — gene-wise resampling, additive Poisson noise, and negative-binomial generation — on two PBMC datasets (PBMC3k, n = 2 700; Kang 2018 / GSE96583, n = 2 700).

Within-dataset Random Forest fusion achieved AUC 0.98 (resample), 1.00 (noise), and 1.00 (random NB). Feature importance analysis revealed that different fabrication types are caught by different feature groups: cell-level structural features (zero fraction, library size) dominate resample detection, while Benford chi-squared and specific digit frequencies (fd_2, fd_4) drive random-NB detection. Cross-dataset evaluation showed that noise-type manipulation generalizes perfectly (AUC = 1.00) because it creates a trivially detectable sparsity shift, whereas resample and NB fabrication signals are dataset-specific and do not transfer (AUC < 0.50). Feature normalization (z-score, rank, delta-Benford) did not rescue cross-dataset generalization.

**Conclusions.** Fraud-inspired digit and structural forensics provide a viable within-dataset fabrication screen for scRNA-seq. Universal cross-dataset deployment requires fabrication-type-aware normalization strategies that remain an open problem.

## Sections

### 1. Introduction

- scRNA-seq data volume growing rapidly; repositories (GEO, SRA) accept data without fabrication checks
- Existing QC (Scrublet, DoubletFinder, SoupX) targets biological artifacts, not deliberate manipulation
- Bradshaw et al. 2021: digit-frequency ML detected CNA fabrication at 82–100% accuracy — but only on copy-number data, not scRNA-seq UMI counts
- Vilenchik & Goldberg 2019: Benford law characterizes scRNA-seq cell types — but was never applied to fabrication detection
- scRNA-seq Bias Detector 2025: uses Isolation Forest for QC anomaly detection — but targets contamination, not fraud
- **Gap**: no tool applies fraud detection methods (Benford digits, structural anomaly scoring) to scRNA-seq UMI count matrices for fabrication detection
- **Our contribution**: systematic transfer of two financial fraud techniques; honest evaluation including negative cross-dataset results

### 2. Methods

#### 2.1 Datasets
- **PBMC3k** (10x Genomics): 2,700 cells × 32,738 genes, standard benchmark
- **Kang 2018 / GSE96583** (Figshare H5): 6,548 ctrl + 7,451 stim PBMC cells; subsampled to 2,700; gene-aligned to 13,537 shared genes

#### 2.2 Simulated Fabrication (adapted from Bradshaw 2021)

| Method | Mechanism | What it preserves | What it destroys |
|--------|-----------|-------------------|------------------|
| **Resample** | Per-gene shuffle across cells | Per-gene marginal distributions | Inter-gene correlation (cell identity) |
| **Noise** | Additive Poisson (λ = 0.15 × value) | Approximate value range | Sparsity structure (nonzero 2.6% → 21.4%) |
| **Random NB** | Per-gene NB(n,p) fitted to real | Per-gene mean/variance | Digit-level distribution; inter-gene structure |

**Honest caveat on noise fabrication**: additive Poisson noise increases nonzero fraction by 8×, creating a trivially detectable sparsity change. We report noise results for completeness but do not claim this as a meaningful detection benchmark.

#### 2.3 Feature Extraction

**Benford digit features (21 per cell):**
- First-digit frequencies: 9 features (digits 1–9), computed on nonzero UMI counts per cell
- Second-digit frequencies: 10 features (digits 0–9), computed on counts ≥ 10
- Chi-squared divergence from theoretical Benford distribution: 2 features (first-digit χ², second-digit χ²)
- Manually verified: extracted frequencies match hand-computed values (see Supplementary Audit)

**Cell-level structural features (8 per cell):**
- Total counts (library size), genes detected, zero fraction, mean/variance/CV of nonzero, max count, log1p(total)

**Isolation Forest anomaly score (1 per cell):**
- Trained on real cell-level features only (one-class); anomaly score = decision_function output

**Fusion (30 features):** concatenation of all above

#### 2.4 Classification and Evaluation
- Random Forest (100 trees) and Logistic Regression
- Stratified 80/20 train/test split (verified: zero overlap)
- Shuffle test: AUC = 0.51 on permuted labels (no leakage)
- Metrics: AUC-ROC, Average Precision, F1, Balanced Accuracy

#### 2.5 Cross-Dataset Generalization Protocol
- Train on all PBMC3k (real + fabricated) → test on all Kang2018 (and vice versa)
- Gene sets aligned to 13,537 shared genes before feature extraction
- Four normalization strategies tested: raw, z-score, rank (quantile), delta-Benford

#### 2.6 Feature Importance
- Permutation importance (10 repeats, AUC-ROC scoring) on held-out test set
- Gini importance from Random Forest as complementary measure
- Feature group aggregation: Benford first-digit, Benford second-digit, Benford chi², cell-level, IF score

### 3. Results

#### 3.1 Within-Dataset Detection (Table 1 — Figure 1)

| Fabrication | Benford RF | Cell-Level RF | IF-Only RF | **Fusion RF** |
|-------------|-----------|---------------|------------|---------------|
| Resample | 0.864 | 0.956 | 0.639 | **0.978** |
| Noise* | 1.000 | 1.000 | 1.000 | **1.000** |
| Random NB | 0.989 | 0.997 | 0.843 | **0.999** |

*Noise AUC = 1.00 is expected due to trivial sparsity change (nonzero fraction 2.6% → 21.4%). This result validates the pipeline but does not demonstrate meaningful detection capability.

**Key finding**: Fusion consistently outperforms individual feature sets. The improvement is most meaningful on resample (+0.02 over cell-level, +0.11 over Benford alone).

#### 3.2 Feature Importance Analysis (Table 2 — Figure 2)

**Resample** (AUC = 0.978 fusion):
- Dominant group: **cell-level** (permutation importance 0.078) — especially zero fraction and library size
- Secondary: **Benford chi²** (0.013) — resampling homogenizes cells, reducing inter-cell variance of digit distributions by 4×
- Mechanism: resampling destroys cell identity → each cell becomes a random mix → digit distribution variance collapses

**Noise** (AUC = 1.000):
- All feature groups show zero permutation importance (model is already perfect; removing any single feature does not degrade AUC)
- Gini importance reveals frac_zeros (0.22) and fd_2 (0.13) as primary split features

**Random NB** (AUC = 0.999):
- Top feature: **chi2_first_digit** (0.005) — NB generator fails to reproduce Benford digit distribution
- Secondary: **frac_zeros** (0.004) — NB generation does not reproduce biological dropout patterns
- Individual digit features fd_2, fd_4 contribute — specific digit frequencies carry fabrication signal

**Conclusion for Figure 2**: Different fabrication types are caught by different feature groups. This supports the fusion approach and explains why no single feature set achieves best performance across all methods.

#### 3.3 Cross-Dataset Generalization (Table 3 — Figure 3)

| Fabrication | Within-PBMC | Within-Kang | PBMC→Kang | Kang→PBMC |
|-------------|------------|-------------|-----------|-----------|
| Resample | 0.953 | 0.986 | 0.430 | 0.482 |
| Noise | 1.000 | 1.000 | 1.000 | 1.000 |
| Random NB | 0.995 | 0.994 | 0.186 | 0.764 |

**Noise generalizes trivially** because the sparsity shift is universal.

**Resample and Random NB do not generalize** (AUC ≈ 0.50 or worse). The model learns dataset-specific digit and structural patterns rather than universal fabrication signatures.

#### 3.4 Normalization Does Not Rescue Generalization (Table 4)

| Fabrication | Raw | Z-score | Rank | Delta-Benford |
|-------------|-----|---------|------|---------------|
| Resample | 0.496 | 0.496 | 0.488 | 0.496 |
| Noise | 1.000 | 1.000 | 1.000 | 1.000 |
| Random NB | 0.501 | 0.501 | 0.503 | 0.501 |

Feature normalization (z-score, rank transform, delta-from-Benford-expected) does not improve cross-dataset transfer. The fabrication signal is fundamentally entangled with dataset-specific characteristics.

### 4. Discussion

#### 4.1 What Works and Why
- **Within-dataset fusion AUC 0.98–1.00**: combination of digit forensics and structural features catches all three fabrication types
- **Benford mechanism on resample**: gene-shuffling homogenizes cells, collapsing the inter-cell variance of digit distributions by 4× — this is a genuine, non-trivial signal
- **Benford mechanism on random NB**: fitted NB generators reproduce mean/variance but fail to reproduce the digit-level distribution that real biological processes produce — chi² divergence from Benford expected is the signature
- **Cell-level mechanism**: fabrication methods that change library size, dropout pattern, or CV structure are caught by standard structural features regardless of digit patterns

#### 4.2 What Doesn't Work and Why
- **Cross-dataset generalization fails** for sophisticated fabrication (resample, NB): the digit and structural features are dataset-specific because they encode library preparation, sequencing depth, and biological composition — all of which differ between PBMC3k and Kang2018
- **Normalization does not help**: the dataset-specific information is not a simple location-scale shift; it is embedded in the joint distribution of features
- **Isolation Forest standalone is weak** (AUC 0.64 on resample): one-class anomaly detection without supervision is insufficient; the fabrication direction is specific and needs labeled data

#### 4.3 Honest Limitations
1. **Simulated fabrication ≠ real-world fraud**: we do not know what methods a real fabricator would use; our three methods are standard from Bradshaw 2021 but may not represent sophisticated attacks
2. **Noise fabrication is trivially detectable**: the AUC = 1.00 result reflects a massive sparsity change, not subtle digit forensics; we report it for completeness, not as evidence of method power
3. **No ground-truth fabricated datasets**: there are no publicly known fabricated scRNA-seq count matrices to test against; RetractionWatch does not track data-level fraud at this granularity
4. **Two datasets only**: generalization was tested on PBMC3k ↔ Kang2018 (both PBMC, same species); generalization to non-PBMC tissues and non-human species is untested
5. **Integer UMI counts only**: the method assumes raw counts; normalized, log-transformed, or imputed matrices would require adaptation

#### 4.4 Relationship to Prior Work
- **Extends Bradshaw 2021**: CNA → scRNA-seq UMI, same Benford approach but different data type and additional fabrication methods
- **Complements Vilenchik 2019**: their Benford application was for cell-type classification; ours is for fabrication detection — same mathematical tool, different problem
- **Distinct from scRNA-seq Bias Detector 2025**: they use IF for QC (doublets, contamination); we use IF for fraud detection — same algorithm, different target
- **Novel contribution**: first application of Benford digit forensics + IF fusion to scRNA-seq count matrix integrity

#### 4.5 Practical Recommendations
1. Deploy as **within-dataset first-pass screen** for GEO submissions alongside standard QC
2. **Not sufficient as standalone fraud detector** — must be combined with domain expertise
3. **Most reliable for detecting NB-type synthetic data** (AUC 0.99, Benford chi² is primary driver)
4. **Least reliable for detecting sophisticated resampling** without dataset-specific training data
5. **Future work**: adversarial-aware fabrication (where fabricator knows about Benford) → test H-L09 adversarial robustness extension

### 5. Conclusion

Financial fraud detection methods — Benford digit frequency analysis and Isolation Forest structural anomaly scoring — transfer effectively to within-dataset fabrication detection in scRNA-seq count matrices (fusion AUC 0.98–1.00). Different feature groups detect different fabrication types: cell-level structural features catch correlation-destroying fabrication, while Benford digit statistics catch distribution-generating fabrication. Cross-dataset generalization remains an open problem: fabrication signals are entangled with dataset-specific characteristics that simple normalization cannot remove. We release all code and data as an open tool for the scRNA-seq data integrity community.

## Figures

1. **Figure 1**: Within-dataset AUC comparison (4 methods × 3 fabrication types) — bar chart
2. **Figure 2**: Feature group importance by fabrication type — horizontal bar chart (already generated)
3. **Figure 3**: Cross-dataset generalization matrix — heatmap or paired bar chart
4. **Figure S1**: ROC curves for each method/fabrication combination
5. **Figure S2**: Benford digit distribution shift: real vs fabricated (violin plots)

## Supplementary Materials

- **Audit Report**: Manual verification of feature extraction, shuffle test results, data leakage check
- Full results JSON for all experiments
- ROC curve plots
- Feature importance analysis (permutation + Gini)
- Normalization experiment results
- Code repository link

## Data and Code Availability

- **Code**: GitHub repository (to be created before submission)
- **PBMC3k**: 10x Genomics public dataset
- **Kang2018**: GEO GSE96583 / Figshare (doi:10.6084/m9.figshare.22572694)
- **All experiment outputs**: `experiments/h24_benford_scrna/results/`
- **Reproducibility**: single script `run_combined.py` reproduces all main results

## Timeline to Submission

- Week 1 [DONE]: MVP experiments, cross-validation, feature importance, normalization test, audit
- Week 2: Generate publication-quality figures; write Methods and Results sections
- Week 3: Write Introduction and Discussion; find co-author
- Week 4: Internal review, submit preprint to bioRxiv
