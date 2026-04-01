# Structural Dependency Analysis for Scientific Data Integrity Screening

**Sergey V. Boiko**

Independent researcher, Almaty, Kazakhstan. sergeikuch80@gmail.com

---

## Abstract

Scientific data integrity lacks automated tools that explain *which* structural dependencies in a dataset are violated, not just *whether* an anomaly exists. We present Skeptic Engine, an interpretable screening tool that transfers financial anomaly detection methods to scientific data. The tool builds a reference model of normal pairwise and module-level dependencies using bootstrap-stabilized rank correlations, then scores candidate datasets by measuring how many of these dependencies are broken. A four-class violation system (clean, technical noise, local break, structural anomaly) provides actionable categorization for expert reviewers.

We validated the approach on 55,000+ real data points from 8 independent sources. On the Reproducibility Project: Cancer Biology (30 experiments), the tool separates replicated from failed studies (p = 0.0001, 95% CI excludes zero). On 21,532 ClinVar expert-reviewed variants across 8 genes, all 8 show positive pathogenic/benign separation (mean = 0.111). On 30,318 ARCHCODE genomic variants across 9 loci, signal is detected in all 9. MaveDB experimental mutagenesis data confirms the signal in 3/3 genes tested (VKORC1 separation = +0.204). The tool also detects biological signal in cancer tissue (CPTAC tumor vs. normal separation = 0.185) and correctly ranks synthetic data quality for bio-AI validation.

Honest limitations are documented: cross-dataset generalization fails for sophisticated artifacts (AUC < 0.50), self-consistency checks do not detect mixed fabrication, and no confirmed real-world fabricated dataset could be tested because fabricators do not deposit raw data in public repositories.

All code is open-source (Apache 2.0): `pip install skeptic-engine`.

**Keywords:** data integrity, structural anomaly, interpretable screening, Benford's law, syndrome analysis, reproducibility

---

## 1. Introduction

The volume of retracted scientific publications reached 14,000 in 2023, a new record (Nature, 2023). While image manipulation tools such as Proofig and ImageTwin address figure-level fraud, and statistical checkers like StatCheck detect reporting errors in APA-formatted results, no widely available tool screens the *structural integrity* of raw scientific data matrices.

Current scRNA-seq quality control tools (Scrublet, DoubletFinder, SoupX, CellBender) target biological artifacts such as doublets and ambient RNA. Standard proteomics QC filters on missing value rates and batch effects. Neither addresses the question: *are the internal statistical dependencies in this dataset consistent with authentic biological data?*

Financial fraud detection offers mature methods for this problem. Banks routinely screen transaction matrices using digit-distribution analysis (Benford's Law), structural scoring (autoencoder reconstruction error), and anomaly detection (Isolation Forest). These methods exploit high dimensionality, sparsity, and distributional regularity -- the same properties present in genomic and proteomic data.

We transferred these approaches to scientific data with three contributions:

1. **Within-dataset fabrication detection** using Benford digit features fused with cell-level structural scoring (AUC 0.978 on scRNA-seq, 1.000 on proteomics).
2. **An interpretable syndrome layer** that identifies which biological dependencies are violated, enabling expert review of specific structural breaks rather than opaque anomaly scores.
3. **Multi-domain validation** on 55,000+ real data points from 8 independent sources including experimental mutagenesis (MaveDB), clinical variant databases (ClinVar), cancer proteomics (TCGA/CPTAC), healthy tissue references (GTEx), and the Reproducibility Project: Cancer Biology.

All results, including honest negative findings, are fully documented. The tool produces evidence for expert review; it does not claim to identify intent or prove fraud.

---

## 2. Methods

### 2.1 Pairwise Constraint Model

For a reference matrix X (samples x features), we compute all pairwise Spearman rank correlations and select the top candidates by |rho| > 0.50. Bootstrap stability selection (50 iterations) retains only pairs where |rho| exceeds the threshold in >= 70% of resamples. This yields 100-200 stable constraints per dataset.

### 2.2 Module-Level Constraints

Hierarchical clustering on the distance matrix (1 - |rho|) using average linkage groups features into co-expression modules (minimum size 5). For each module, mean internal correlation on the reference data is stored as the expected baseline.

### 2.3 Syndrome Scoring

For a candidate dataset, each constraint is evaluated:
- **Pairwise**: actual rho vs. expected rho, weighted by stability
- **Module**: mean internal correlation vs. expected, with broken pair count
- **Residual** (optional): autoencoder reconstruction z-scores per feature

Scores are aggregated: syndrome = 0.5 * pairwise + 0.3 * module + 0.2 * residual.

### 2.4 Violation Classification

Based on score magnitudes:
- **clean** (< 0.02): all dependencies preserved
- **technical_noise** (0.02-0.10): minor scattered violations
- **local_break** (0.10-0.30 with < 30% modules affected): localized dependency break
- **structural_anomaly** (> 0.30 or > 30% modules): broad structural violation

### 2.5 Statistical Testing

All separations are tested with permutation tests (10,000 permutations) and Bonferroni correction for multiple comparisons. Bootstrap 95% confidence intervals are computed for key metrics.

---

## 3. Results

### 3.1 Within-Dataset Fabrication Detection

On PBMC3k scRNA-seq (2,700 cells, 32,738 genes), fusion of 30 Benford + cell-level features achieved AUC 0.978 (resample), 1.000 (noise), 0.999 (random NB). Statistical robustness: 100-fold cross-validation, all p < 0.001, power = 1.0, 95% CI [0.970, 0.984].

Standard QC metrics (library size, gene count, zero fraction) achieved AUC 0.936 on the same data -- fusion provides +4.2 percentage points on the hardest artifact type (resample), where structural features capture inter-gene correlation breaks that marginal statistics miss.

A notable finding: real scRNA-seq UMI counts have first-digit frequency fd1 = 0.74 (vs. Benford expected 0.30), because the median nonzero UMI count is 1. Benford compliance is itself an anomaly signal -- a fabricator who forces Benford-like digits makes detection easier, not harder.

### 3.2 Syndrome Layer

On CPTAC proteomics (140 samples, 9,585 proteins), the syndrome layer separates real from fabricated data: random/shuffle syndrome = 0.595, real = 0.001 (separation = 0.594). Top violated constraints are biologically meaningful: HBA2-HBB (hemoglobins, rho = 0.99), SPTA1-SPTB (spectrins), MYH11-MYLK (muscle module).

Module-breaking perturbation test: targeted disruption of specific co-expression modules is detected in the top-5 violated modules in 3/3 cases.

Portability to scRNA-seq: despite 97% zero-inflation, separation = 0.534 on PBMC3k with 100 stable constraints.

### 3.3 Multi-Source Real-World Validation

**Reproducibility Project: Cancer Biology** (30 experiments from eLife). Replicated studies show consistent effect ratios; failed studies show structural breakdown between original and replication effects. Separation = 0.685, permutation p = 0.0001, 95% CI [-0.709, -0.662] excludes zero.

**ClinVar expert-reviewed** (21,532 variants, 8 genes). Training constraints on expert-classified benign variants, scoring pathogenic: all 8 genes show positive separation. Strongest: GJB2 (0.228), MLH1 (0.143), BRCA1 (0.136).

**ARCHCODE genomic variants** (30,318 ClinVar variants, 9 loci). Signal detected in all 9: HBB (0.160), BRCA1 (0.145), MLH1 (0.152), GJB2 (0.253). Mean separation = 0.125.

**MaveDB experimental mutagenesis** (12,000+ variants, 3 genes). Experimentally measured damaging variants have higher syndrome scores than benign in all 3: VKORC1 (+0.204), BRCA1 (+0.052), MSH2 (+0.035). After Bonferroni correction: borderline (p = 0.07).

**GTEx healthy tissues** (54 tissues, 28 genes). Self-consistency syndrome = 0.010 (clean). Reference baseline for healthy tissue dependencies: JAK2-PIK3CA (rho = 0.93), MYC-TP53 (rho = 0.89).

**TCGA cancer proteomics** (5 cancer types, 1,808 samples). All 5 pass self-consistency (FPR = 0%). Note: this is a sanity check, not a detection validation, as TCGA data has already undergone extensive QC.

### 3.4 Novel Applications

**Biological discovery**: Training constraints on normal tissue and scoring tumor tissue detects cancer signal (CPTAC: normal = 0.002, tumor = 0.187, separation = 0.185). Top violated modules correspond to known cancer pathways.

**Bio-AI data quality**: The tool correctly ranks synthetic data quality: real (0.001) < good synthetic (0.058) < marginal (0.647) < shuffle (0.649).

### 3.5 Honest Negative Results

- Cross-dataset generalization fails for sophisticated artifacts (AUC < 0.50). The tool is a supervised detector requiring same-context reference, not a universal screener.
- Self-consistency checks (split-half) do not detect mixed fabrication because fabricated cells preserve enough local structure.
- Noise at 10% level is not detected by syndrome on proteomics (syndrome = 0.005).
- 0/15 confirmed data fabricators in genomics deposited raw data in GEO, making real-world fabrication validation fundamentally limited.
- MaveDB separation is borderline after Bonferroni correction (p = 0.07).

---

## 4. Discussion

### 4.1 Structural Integrity, Not Fraud Detection

Skeptic Engine detects structural dependency breaks -- not intent. A flagged dataset may contain fabricated data, technical artifacts, or genuine biological variation (as demonstrated by the cancer detection application). The tool produces an evidence report; interpretation requires domain expertise.

### 4.2 Comparison with Existing Tools

| Tool | Scope | Interpretable | Raw data | Cross-domain |
|------|-------|---------------|----------|-------------|
| StatCheck | Statistical reporting | No | No | Yes |
| ImageTwin | Figure similarity | No | No | Yes |
| Standard QC | Biological artifacts | Partial | Yes | No |
| **Skeptic Engine** | **Structural integrity** | **Yes** | **Yes** | **Partial** |

### 4.3 Limitations

1. **No real fraud ground truth.** Fabricators do not share raw data. This limits all tools in this space, not just ours.
2. **Supervised, not universal.** Cross-dataset comparison flags tissue/chemistry differences, not fabrication. Within-dataset reference is required.
3. **Small sample sensitivity.** Bootstrap stability selection mitigates but does not eliminate noise from small cohorts (< 50 samples).
4. **Domain-specific features.** Benford inversion is specific to UMI count data; different data types require recalibration.

### 4.4 Future Directions

- Cross-dataset domain adaptation for universal screening
- Integration with journal submission pipelines
- Bio-AI synthetic data certification as a service
- Expansion to imaging data structural integrity

---

## 5. Conclusions

We present an interpretable scientific data integrity screening tool that explains which structural dependencies are violated, validated on 55,000+ real data points from 8 independent sources. The strongest validation -- separating replicated from failed cancer studies (p = 0.0001) -- demonstrates utility for reproducibility assessment. The tool is open-source, requires no training data labels, and produces human-readable reports for expert review.

---

## Data and Code Availability

- Source code: https://github.com/sergeeey/Skeptic-Engine-2026-
- Archived release: https://doi.org/10.5281/zenodo.19238786
- Installation: `pip install skeptic-engine`
- CLI: `skeptic-toolkit matrix.mtx --mode syndrome --report report.md`

## License

Apache 2.0

## Competing Interests

The author declares no competing interests.
