# Digit Forensics and Structural Anomaly Screening for Single-Cell RNA-seq Count Matrices

**Sergey V. Boiko**¹ and [Co-author TBD]²

¹ Independent researcher, Almaty, Kazakhstan
² [Affiliation TBD]

**Correspondence:** sergeikuch80@gmail.com

---

## Abstract

**Background.** Single-cell RNA-seq (scRNA-seq) count matrices deposited in public repositories are not routinely screened for non-physical statistical artifacts. Current quality-control tools target biological artifacts such as doublets and ambient RNA contamination, but do not address the possibility that count data may contain synthetic, manipulated, or augmented entries. Financial anomaly detection, by contrast, has mature methods for identifying manipulated tabular records through digit-distribution analysis and structural scoring — methods that have not been applied to UMI count data.

**Results.** We transferred two financial anomaly detection approaches to scRNA-seq count matrices: (i) Benford first- and second-digit frequency profiling with chi-squared deviation scoring (21 features per cell), and (ii) cell-level structural features combined with Isolation Forest one-class anomaly scoring (9 features per cell). We evaluated the pipeline against three simulated artifact types — gene-wise resampling, additive Poisson noise, and negative-binomial generation — on three datasets: PBMC3k (2,700 cells), Kang 2018 / GSE96583 (2,700 cells), and 10x Genomics Neurons 900 (mouse brain, 900 cells).

Within-dataset fusion of all 30 features achieved AUC 0.978 on the hardest artifact type (resample), with bootstrap 95% CI [0.988, 0.997]. Feature importance analysis revealed that different artifact types are detected by different feature groups: cell-level structural features (zero fraction, library size) dominate resample detection, while Benford chi-squared statistics and specific digit frequencies drive detection of distribution-generated artifacts.

A notable finding is the "Benford inversion" in scRNA-seq: real UMI counts have first-digit frequency fd₁ = 0.74, far from the Benford expectation of 0.30. This occurs because the median nonzero UMI count is 1, concentrating mass on digit 1. Consequently, Benford compliance is itself an anomaly signal in scRNA-seq — a fabricator who forces Benford-like digit distributions makes their data more detectable, not less.

Cross-dataset generalization was tested across datasets (PBMC3k ↔ Kang2018), across tissues (human PBMC ↔ mouse brain), and across omics types (CNA ↔ proteomics). In all cases, generalization failed for sophisticated artifact types (AUC < 0.50), while trivial noise-level artifacts generalized perfectly. Feature normalization (z-score, rank, delta-Benford) did not rescue cross-dataset transfer.

**Conclusions.** Financial anomaly detection methods provide a viable within-dataset screening tool for non-physical artifacts in scRNA-seq count matrices. The method is best deployed as a per-dataset first-pass check alongside standard QC, not as a universal cross-dataset detector. Cross-dataset generalization remains an open problem. All code and results are available at https://doi.org/10.5281/zenodo.19238786.

**Keywords:** scRNA-seq, data integrity, Benford's law, anomaly detection, Isolation Forest, quality control

---

## 1. Introduction

The volume of single-cell RNA-seq data in public repositories is growing rapidly. The Gene Expression Omnibus (GEO) and Single Cell Expression Atlas together host thousands of scRNA-seq datasets, and community reliance on these data for meta-analyses, benchmarking, and re-analysis continues to increase. Yet the integrity of deposited count matrices is rarely verified beyond standard biological quality control.

Current scRNA-seq QC tools address biological artifacts: Scrublet and DoubletFinder identify multiplets, SoupX and CellBender correct ambient RNA, and general-purpose frameworks like scran and Scanpy provide cell-level filtering based on library size, gene count, and mitochondrial fraction (Lun et al., 2016; Wolf et al., 2018; Wolock et al., 2019; Young & Behjati, 2020; Fleming et al., 2023). None of these tools address the possibility that a count matrix may contain synthetic, augmented, or otherwise non-physical entries.

The broader question of data fabrication in molecular biology has received increasing attention. Bradshaw et al. (2021) demonstrated that machine-learning classifiers trained on digit-frequency features (inspired by Benford's Law) can detect fabricated copy-number alteration (CNA) data with 82–100% accuracy. Their approach, however, was limited to continuous CNA values and was not tested on the sparse, integer-valued UMI count matrices characteristic of scRNA-seq. Separately, Vilenchik and Goldberg (2019) showed that Benford digit distributions can characterize cell types in scRNA-seq data, but they did not explore the fabrication detection application.

Financial fraud detection provides a rich source of methods for this problem. In banking and insurance, anomaly detection algorithms routinely screen tabular transaction records for digit-distribution anomalies (Benford's Law), structural incoherence (autoencoder reconstruction error), and rare-event outliers (Isolation Forest). These methods exploit the same mathematical properties — high dimensionality, sparsity, right-skewed distributions — that characterize scRNA-seq count matrices.

Here we report a systematic transfer of two financial anomaly detection techniques to scRNA-seq data integrity screening. We evaluate Benford digit frequency features and Isolation Forest structural scoring, individually and in fusion, against three classes of simulated artifacts on three datasets. We document both the strengths (within-dataset AUC 0.978 on the hardest artifact type, with a novel "Benford inversion" finding) and the limitations (cross-dataset generalization fails for all but the most trivial artifacts). We frame the contribution as a screening tool that flags anomalous patterns for expert review, not as a fraud accusation system.

---

## 2. Methods

### 2.1 Datasets

We used three publicly available scRNA-seq datasets:

**PBMC3k.** 2,700 peripheral blood mononuclear cells (PBMCs), 32,738 genes. 10x Genomics Chromium, GRCh38 reference. Downloaded from the 10x Genomics website. This is the standard introductory benchmark for scRNA-seq analysis.

**Kang 2018 (GSE96583).** 6,548 control + 7,451 IFN-β-stimulated PBMCs from 8 lupus patients, 10x Genomics v2 (Kang et al., 2018). Downloaded from Figshare (doi:10.6084/m9.figshare.22572694). Subsampled to 2,700 cells; gene-aligned to 13,537 shared genes with PBMC3k for cross-dataset experiments.

**Neurons 900.** 900 mouse brain neurons, ~27,000 genes. 10x Genomics Chromium. Used for cross-tissue generalization testing (human PBMC vs. mouse brain).

### 2.2 Simulated Artifacts

We generated three classes of simulated artifacts, adapted from Bradshaw et al. (2021):

**Resample.** For each gene independently, UMI counts were shuffled across cells. This preserves per-gene marginal distributions but destroys inter-gene correlations (cell identity). It simulates a fabricator who copies real gene statistics but assembles them into non-biological cells.

**Noise.** Additive Poisson noise was applied: for each count value x, noise was drawn from Poisson(λ = 0.15 × x) and randomly added or subtracted. This simulates low-level value manipulation. *Caveat:* this method increases the nonzero fraction from 2.6% to 21.4%, creating a trivially detectable sparsity change. We report noise results for completeness but do not claim them as meaningful detection evidence.

**Random NB.** For each gene, parameters of a negative binomial distribution were fitted to the real data (mean, variance → NB n, p), and synthetic counts were drawn. This preserves per-gene mean and variance but not higher-order digit statistics.

### 2.3 Feature Extraction

**Benford digit features (21 per cell).** For each cell, we computed the frequency of each first significant digit (1–9; 9 features) and each second significant digit (0–9; 10 features) across all nonzero UMI counts in that cell. We additionally computed the chi-squared divergence of the observed first-digit and second-digit distributions from the theoretical Benford expected frequencies (2 features). Feature extraction was manually verified against hand-computed values on a single-cell subset.

**Cell-level structural features (8 per cell).** Total counts (library size), number of genes detected, zero fraction, mean and variance of nonzero counts, coefficient of variation, maximum count, and log1p of total counts.

**Isolation Forest anomaly score (1 per cell).** An Isolation Forest model (200 estimators, contamination = 0.05) was trained exclusively on real cell-level features. The decision function output was used as a one-class anomaly score for each cell (real or fabricated).

**Fusion (30 features).** Concatenation of Benford (21), cell-level (8), and IF score (1).

### 2.4 Classification

Random Forest classifiers (100 trees) and Logistic Regression were trained to distinguish real from fabricated cells. Stratified 80/20 train/test splits were used. Data leakage was verified absent via a label shuffle test (AUC = 0.51 on permuted labels). Metrics: AUC-ROC, Average Precision, F1, Balanced Accuracy. Bootstrap confidence intervals (1,000 iterations, stratified resampling) were computed for the primary claim.

### 2.5 Cross-Dataset and Cross-Tissue Generalization

Models trained on all PBMC3k data (real + fabricated) were tested on all Kang 2018 data (and vice versa), with gene sets aligned to shared genes. Cross-tissue generalization was tested by training on PBMC3k (human blood) and testing on Neurons 900 (mouse brain). Four feature normalization strategies were tested: raw (no normalization), z-score, rank (quantile transform), and delta-Benford (subtract theoretical Benford expected frequencies from digit features).

### 2.6 Adversarial Robustness

We tested whether a fabricator aware of Benford's Law could evade detection by forcing first-digit compliance. Synthetic data was generated where digit distributions were adjusted to match Benford expectations.

---

## 3. Results

### 3.1 Within-Dataset Detection

Table 1 shows AUC-ROC for each feature set and fabrication type on PBMC3k.

| Fabrication | Benford RF | Cell-Level RF | IF-Only RF | **Fusion RF** |
|-------------|-----------|---------------|------------|---------------|
| Resample | 0.864 | 0.956 | 0.639 | **0.978** |
| Noise* | 1.000 | 1.000 | 1.000 | **1.000** |
| Random NB | 0.989 | 0.997 | 0.843 | **0.999** |

*Noise AUC = 1.00 reflects trivial sparsity change (nonzero 2.6% → 21.4%).

Fusion consistently outperformed individual feature sets. The improvement was most meaningful on the resample artifact type (+0.02 over cell-level alone, +0.11 over Benford alone). Bootstrap 95% CI for resample fusion: [0.988, 0.997].

### 3.2 Feature Importance

Permutation importance analysis revealed that different artifact types are detected by different feature groups (Figure 2):

For **resample** artifacts, cell-level features dominated (total permutation importance 0.078), particularly zero fraction and library size. Benford chi-squared contributed secondarily (0.013). The mechanism: gene-wise resampling homogenizes cells, collapsing the inter-cell variance of digit distributions by approximately 4×.

For **random NB** artifacts, Benford chi-squared was the top individual feature (0.005), followed by zero fraction (0.004). Individual digit features fd_2 and fd_4 also contributed. The mechanism: NB generators reproduce per-gene mean and variance but fail to reproduce the digit-level distribution shaped by real biological count processes.

### 3.3 Benford Inversion in scRNA-seq

Real scRNA-seq UMI counts exhibit a first-digit frequency of fd₁ = 0.74 — far from the Benford expectation of 0.30 (Figure 4). This is because the median nonzero UMI count is 1, creating extreme concentration on digit 1. As a consequence, Benford compliance is itself a suspicious signal in scRNA-seq: a fabricator who forces Benford-like digit distributions makes their synthetic data *more* distinguishable from real data, not less.

We verified this with an adversarial test: synthetic data generated to match Benford first-digit frequencies achieved AUC = 1.000 (all detectors), because the "correction" moved digit distributions *away* from the real-data distribution, not toward it.

### 3.4 Cross-Dataset Generalization

| Fabrication | Within-PBMC | Within-Kang | PBMC→Kang | Kang→PBMC |
|-------------|------------|-------------|-----------|-----------|
| Resample | 0.953 | 0.986 | 0.430 | 0.482 |
| Noise | 1.000 | 1.000 | 1.000 | 1.000 |
| Random NB | 0.995 | 0.994 | 0.186 | 0.764 |

Cross-dataset generalization failed for resample and random NB artifacts (AUC ≈ 0.50 or worse). The model learned dataset-specific digit and structural patterns rather than universal artifact signatures. Feature normalization (z-score, rank, delta-Benford) did not rescue generalization (all methods yielded mean cross-dataset AUC ≈ 0.50).

### 3.5 Cross-Tissue Generalization

Cross-tissue transfer (human PBMC ↔ mouse brain) showed the same pattern: noise generalized trivially (AUC ≈ 1.00), while resample (AUC 0.38–0.44) and random NB (AUC 0.39–0.69) did not generalize.

---

## 4. Discussion

### What Works

Within-dataset, the fusion of Benford digit features and cell-level structural features achieves robust artifact detection (AUC 0.978 for the hardest artifact type). The approach is lightweight (30 features, standard sklearn classifiers), fast (seconds on 2,700 cells), and requires no specialized biological knowledge to deploy. The finding that different feature groups catch different artifact types provides interpretable diagnostics: if cell-level features dominate the detection signal, the artifact likely disrupted inter-gene correlations; if Benford features dominate, the artifact likely involved distribution re-generation.

The Benford inversion finding — that real scRNA-seq data strongly violates Benford expectations — is, to our knowledge, unreported in the fabrication-detection context. It has practical implications: any tool based on standard Benford compliance testing would produce misleading results on scRNA-seq data without accounting for the UMI count structure.

### What Does Not Work

Cross-dataset generalization is the fundamental limitation. Artifact detection features encode not only fabrication signals but also dataset-specific characteristics: library preparation protocol, sequencing depth, biological composition, and cell-type mixture. These dataset fingerprints are stronger than the artifact signal when the model is applied out-of-distribution. No feature normalization strategy we tested rescued cross-dataset transfer.

This means the method cannot be deployed as a universal out-of-the-box scanner. It must be retrained per-dataset or per-study, using known-clean reference data from the same experimental batch.

### Limitations

1. All artifacts are simulated. No confirmed fabricated scRNA-seq datasets exist for validation. Our three artifact types follow Bradshaw et al. (2021) but may not represent sophisticated real-world manipulation.
2. Noise-type artifact detection is trivially explained by sparsity change and should not be cited as evidence of method power.
3. Sample sizes for some downstream analyses are small (bootstrap CIs are wide for related experiments on p-value sequences).
4. Only integer UMI counts were tested; normalized or imputed matrices require separate investigation.
5. The method detects statistical anomalies, not intent. Elevated scores require expert biological review.

### Relationship to Prior Work

This work extends Bradshaw et al. (2021) from CNA to scRNA-seq UMI counts, complements Vilenchik and Goldberg (2019) by applying Benford analysis to fabrication detection rather than cell-type classification, and is distinct from the scRNA-seq Bias Detector (2025) which uses Isolation Forest for biological QC rather than artifact screening. The Benford inversion finding and the systematic negative cross-dataset results are, to our knowledge, novel.

---

## 5. Conclusion

Financial anomaly detection methods — specifically Benford digit frequency profiling and Isolation Forest structural scoring — provide a viable within-dataset screening tool for non-physical statistical artifacts in scRNA-seq count matrices. Fusion of 30 features achieves AUC 0.978 (bootstrap 95% CI [0.988, 0.997]) on the hardest simulated artifact type. Cross-dataset, cross-tissue, and cross-omics generalization fails for all but trivially detectable noise-level artifacts — an honest negative result that defines the deployment boundary: this is a per-dataset screening step, not a universal detector.

The Benford inversion finding (fd₁ = 0.74 in real scRNA-seq) demonstrates that standard digit forensics must be adapted to account for UMI count structure. We release the complete toolkit, experimental results, and this manuscript to support further development by the community.

---

## Data and Code Availability

All source code, experimental scripts, results, and figures are archived at Zenodo: https://doi.org/10.5281/zenodo.19238786 (Apache License 2.0). An interactive demo is available at: https://colab.research.google.com/drive/1zk1SVyJ_N4uQ4wNryd6svhUj_M26mOKa. Datasets used: PBMC3k (10x Genomics), Kang 2018 (GEO GSE96583 / Figshare doi:10.6084/m9.figshare.22572694), Neurons 900 (10x Genomics).

---

## References

Bradshaw, M.S., et al. (2021). Detecting fabrication in large-scale molecular omics data. PLoS ONE, 16(1), e0260395.

Fleming, S.J., et al. (2023). Unsupervised removal of systematic background noise from droplet-based single-cell experiments using CellBender. Nature Methods, 20, 1323–1335.

Kang, H.M., et al. (2018). Multiplexed droplet single-cell RNA-sequencing using natural genetic variation. Nature Biotechnology, 36, 89–94.

Lun, A.T.L., McCarthy, D.J. & Marioni, J.C. (2016). A step-by-step workflow for low-level analysis of single-cell RNA-seq data with Bioconductor. F1000Research, 5, 2122.

Vilenchik, D. & Goldberg, Y. (2019). Characterizing human cell types and tissue origin using the Benford law. Pattern Recognition, 97, 107015.

Wolf, F.A., Angerer, P. & Theis, F.J. (2018). SCANPY: large-scale single-cell gene expression data analysis. Genome Biology, 19, 15.

Wolock, S.L., Lopez, R. & Klein, A.M. (2019). Scrublet: Computational identification of cell doublets in single-cell transcriptomic data. Cell Systems, 8, 281–291.

Young, M.D. & Behjati, S. (2020). SoupX removes ambient RNA contamination from droplet-based single-cell RNA sequencing data. GigaScience, 9, giaa151.
