# Skeptic Engine: Calibrated, Adversarial Anomaly Detection for Scientific Data Integrity

**Authors:** Sergey V. Boiko  
**Version:** 0.3 (Internal Draft)  
**Date:** 2026-04-13  

---

## Abstract

Scientific data integrity is traditionally reliant on post-hoc retraction or manual peer review. While statistical tools exist to detect specific artifacts (e.g., p-hacking, image duplication), they often operate in isolation and produce opaque "risk scores" that are difficult for reviewers to interpret.

We present **Skeptic Engine**, an automated, adversarial testing framework that detects statistical artifacts across high-throughput biological data, proteomics, and meta-analyses. Unlike single-method detectors, our system integrates **multi-modal anomaly scores** (Benford digit forensics, autoencoder reconstruction error, behavioral p-hacking detection, and cross-modal consistency) into a **Unified Anomaly Score (UAS)**.

Crucially, we introduce two novelties to make these scores actionable:
1. **Isotonic Recalibration:** We transform raw detector scores into calibrated probabilities with confidence intervals, reducing the Mean Absolute Calibration Error (MACE) from **0.202 to 0.032**.
2. **Debate-Driven Verdicts:** We employ an adversarial protocol (Prosecution vs. Defense agents) to synthesize interpretable verdicts. Instead of a black-box flag, the system outputs a structured summary: *"Prosecutor found 3 anomalies; Defense explained 2; Verdict: SUSPICIOUS (Confidence 0.72)."*

Evaluated across 37 experiments (including synthetic fabrications of scRNA-seq, proteomics, and meta-analyses), our approach achieves **AUC = 1.000** on unified detection while providing the calibrated uncertainty estimates essential for high-stakes editorial decisions.

---

## 1. Introduction

The "Replication Crisis" has highlighted the fragility of scientific claims across disciplines. The Open Science Collaboration's 2015 replication project found that only 36% of social science findings replicated (Open Science Collaboration, 2015), while similar concerns have been raised in preclinical research (Begley & Ellis, 2012) and biomedical literature (Ioannidis, 2005). While much focus has been placed on p-hacking, publication bias, and selective reporting, the detection of *structural* artifacts—subtle inconsistencies in high-dimensional data such as scRNA-seq count matrices, proteomics profiles, and meta-analytic p-value sequences—remains under-explored.

Current statistical integrity tools operate in isolation. P-curve analysis (Simonsohn et al., 2014) examines the distribution of significant p-values but ignores data structure. Statcheck (Nuijten et al., 2016) extracts and recomputes reported test statistics but does not analyze raw data matrices. Image forensics tools detect pixel-level manipulation but are silent on statistical coherence. Each tool answers a narrow question: "Are the p-values suspicious?" or "Does this image look manipulated?" None asks the broader question: "Does this dataset exhibit structural coherence consistent with genuine measurement?"

Furthermore, existing detectors rarely provide calibrated uncertainty. A score of "0.8" from a generic anomaly detector is meaningless without knowing: *How likely is a true negative to score 0.8?* Without calibration, reviewers cannot distinguish between a borderline flag and a confident detection.

We propose a shift from **Single-Point Detection** to **Calibrated, Adversarial Verification**. Our framework, **Skeptic Engine**, transfers anomaly detection methods from financial fraud detection, clinical trial monitoring, and information security to screen scientific datasets across multiple modalities. The system integrates seven specialized detectors into a Unified Anomaly Score (UAS), calibrates raw scores into interpretable probabilities with confidence intervals, and synthesizes findings through an adversarial debate protocol that produces structured, explanation-rich verdicts.

Our contributions are:
1. **Multi-modal anomaly detection** across scRNA-seq, proteomics, p-value sequences, and cross-omics data (AUC 0.729–1.000)
2. **Isotonic recalibration** reducing Mean Absolute Calibration Error from 0.202 to 0.032 (84% improvement)
3. **Adversarial debate protocol** generating interpretable verdicts with evidence trails
4. **37 validated experiments** with open-source code and reproducible pipelines

---

## 2. Methods

### 2.1 The Skeptic Engine Architecture
The system operates in four stages:
1.  **Extraction:** Features are extracted from raw data matrices (Benford digits, p-value sequences, cross-modal correlations).
2.  **Detection:** Multiple specialized detectors (H24–H33) compute raw anomaly scores.
3.  **Calibration (H34):** Raw scores are mapped to calibrated probabilities using **Isotonic Regression** trained on historical experimental data.
4.  **Verdict (H36):** An adversarial **Debate Protocol** generates arguments for and against fabrication, synthesizing a final decision with an explanation trail.

### 2.2 Unified Anomaly Score (UAS)
Instead of relying on one metric, we compute a weighted ensemble:
$$ UAS = \sum_{i} w_i \cdot S_i $$
where $S_i$ are normalized scores from $N$ detectors (Benford, Autoencoder, Behavioral, etc.).

### 2.3 Isotonic Recalibration
To address the "Black Box" problem of raw scores, we train a non-decreasing isotonic regression model $f_{iso}$ on historical ground-truth data (real vs. fabricated):
$$ P(\text{Anomaly} | x) \approx f_{iso}(\text{Raw Score}(x)) $$
This yields not just a point estimate, but a confidence interval based on the local density of calibration data. We use 16,224 calibration samples from 6 detectors across H24, H31, H32, and H33 experiments.

### 2.4 Adversarial Debate Protocol (H36)
The debate protocol involves three agents:
- **Prosecutor:** Generates arguments for fabrication based on detected anomalies (Benford deviation, p-value clustering, temporal drift, cross-modal inconsistency)
- **Defense:** Generates arguments for natural variation (large sample size, Benford compliance, no temporal drift, high cross-modal consistency)
- **Judge:** Synthesizes arguments, identifies conflicting evidence categories, and renders a structured verdict (CLEAN/SUSPICIOUS/ANOMALOUS) with confidence score and explanation trail.

### 2.5 Datasets
We evaluate across four data modalities:

**scRNA-seq:** PBMC3k (10x Genomics, 2,700 cells × 32,738 genes) and Kang2018/GSE96583 (stimulated vs control PBMCs). Raw UMI count matrices with integer values.

**Proteomics/CNA:** CPTAC pan-cancer data from Bradshaw et al. (2021), including proteomics (140 samples × 9,585 proteins) and copy number alteration (100 samples × 17,156 genes).

**P-value sequences:** (a) Reproducibility Project: Psychology (99 studies with known replication outcomes), (b) Statcheck meta-analyses dataset (61 articles, 506 extracted tests), and (c) ClinicalTrials.gov API (200 trials, 42 with extractable p-values).

**Cross-omics:** Matched mRNA-protein pairs from CPTAC for cross-modal consistency analysis (H33).

All fabrication methods (resampling, noise injection, negative binomial generation, permutation) are documented and reproducible. Code is available at github.com/sergeeey/Skeptic-Engine-2026-.

---

## 3. Results

### 3.1 Single-Modal Baselines (H23–H25)
We first established strong baselines using individual detectors on specific data types.

| Experiment | Domain | Metric | Result |
| :--- | :--- | :--- | :--- |
| **H24** | scRNA-seq (Benford) | AUC | **0.978** |
| **H25** | Proteomics (Autoencoder) | AUC | **1.000** |
| **H23** | Behavioral (P-Hacking) | AUC | **0.729** |

*Table 1: Individual detector performance. While strong, these detectors are domain-specific.*

### 3.2 Unified Detection (H31)
By combining signals into the **Unified Anomaly Score (UAS)**, we achieve perfect discrimination on synthetic benchmarks.

| Method | AUC | Precision | Recall |
| :--- | :--- | :--- | :--- |
| Benford Only | 0.843 | 0.78 | 0.75 |
| AE Only | 0.989 | 0.92 | 0.90 |
| **UAS (H31)** | **1.000** | **1.00** | **1.00** |

*Table 2: UAS outperforms single modalities by leveraging complementary error profiles.*

### 3.3 Calibrated Uncertainty (H34)
The critical advancement of v0.3 is calibration. We measured the **Mean Absolute Calibration Error (MACE)** before and after isotonic regression.

*   **Baseline MACE (Raw Scores):** 0.202
*   **Calibrated MACE (Isotonic):** 0.032
*   **Improvement:** 84% reduction in calibration error.

*Result:* A raw score of 0.7 now reliably maps to a probability of 0.994 (95% CI [0.946, 1.000]), giving users actionable confidence.

### 3.4 Adversarial Verdicts (H36)
We tested the Debate Protocol on edge cases where raw scores were ambiguous (e.g., Calibrated Score ≈ 0.5).

*   **Case:** Mixed signals (High Benford deviation, but high Cross-Modal consistency).
*   **Outcome:**
    *   **Prosecutor:** Flagged digit deviation (Weight 0.6).
    *   **Defense:** Flagged strong biological coherence (Weight 0.8).
    *   **Judge:** Verdict **CLEAN** (Confidence 0.60). Explanation: *"Strong defense evidence overrides weak prosecution signal."*

---

## 4. Discussion

### 4.1 From "Flagging" to "Explaining"
The primary bottleneck in scientific integrity is not the lack of detectors, but the lack of *trust* in them. By using the **Debate-Driven Verdict**, we provide an audit trail. Reviewers don't just see "Anomalous"; they see *why* (e.g., "p-value clustering is suspicious, but sample size is robust").

### 4.2 Comparison with Existing Tools
Compared to single-method detectors, Skeptic Engine's multi-modal approach captures complementary error profiles. Benford analysis detects digit-level anomalies that autoencoders miss; autoencoders catch structural incoherence that Benford analysis misses; behavioral features identify p-hacking patterns invisible to both. Calibration transforms these opaque scores into interpretable probabilities, addressing a critical gap in current tools.

### 4.3 Limitations
*   **Synthetic Ground Truth:** Most validation relies on simulated fabrications. Real-world confirmed fraud datasets are scarce, limiting our ability to measure real-world precision.
*   **Domain Specificity:** While UAS generalizes better than single detectors, the feature extraction still requires domain knowledge (e.g., knowing what "Benford" means for scRNA-seq vs. proteomics). Cross-dataset generalization fails for sophisticated artifact types (AUC near random).
*   **Computational Cost:** Full pipeline execution (7 detectors + calibration + debate) requires more compute than single-method tools, though individual modules run in under 30 seconds on standard hardware.

### 4.4 Practical Implications
Skeptic Engine is designed as a pre-submission screening tool for journals, preprint servers, and funding agencies. The calibrated probability output enables risk-based triage: scores below 0.3 require no action, scores between 0.3–0.7 warrant expert review, and scores above 0.7 trigger detailed investigation. The debate protocol provides reviewers with structured evidence rather than binary flags.

### 4.5 Future Work
*   **Knowledge Graph (H38):** Linking anomalies across papers to detect systematic "paper mills" and coordinated fabrication.
*   **Real-World Integration:** Deploying Skeptic Engine as a pre-submission check for partner journals.
*   **Adaptive Thresholds (H35):** Domain-specific optimal thresholds using the Mpemba sweet spot pattern.
*   **Instinct Memory (H37):** Self-improving detection through pattern learning from past analyses.

---

## 5. Conclusion

Skeptic Engine demonstrates that we can move beyond simple statistical checks to a **holistic, calibrated, and explainable** system for data integrity. By combining multi-modal detection with adversarial debate, we provide a tool that doesn't just find errors, but helps us understand them.

---

## References

1.  Begley, C. G., & Ellis, L. M. (2012). Drug development: Raise standards for preclinical cancer research. *Nature*, 483(7391), 531-533.
2.  Benford, F. (1938). The law of anomalous numbers. *Proceedings of the American Philosophical Society*, 78(4), 551-572.
3.  Bradshaw, C. J. A., et al. (2021). CPTAC pan-cancer proteomics data. *Nature Methods*, 18, 1017-1026.
4.  Ioannidis, J. P. A. (2005). Why most published research findings are false. *PLoS Medicine*, 2(8), e124.
5.  Nuijten, M. B., Hartgerink, C. H., van Assen, M. A., Epskamp, S., & Wicherts, J. M. (2016). The prevalence of statistical reporting errors in psychology (1985–2013). *Behavior Research Methods*, 48(4), 1205-1226.
6.  Open Science Collaboration. (2015). Estimating the reproducibility of psychological science. *Science*, 349(6251), aac4716.
7.  Simonsohn, U., Nelson, L. D., & Simmons, J. P. (2014). P-curve: A key to the file-drawer problem. *Journal of Experimental Psychology: General*, 143(2), 534-547.
8.  Head, M. L., Holman, L., Lanfear, R., Kahn, A. T., & Jennions, M. D. (2015). The extent and consequences of p-hacking in science. *PLoS Biology*, 13(3), e1002106.
9.  Stigler, S. M. (1980). Gauss and the invention of least squares. *The Annals of Statistics*, 8(3), 465-474.
10. Hartgerink, C. H. J., van Aert, R. C. M., van Rooij, M., & Wicherts, J. M. (2017). Too good to be false: Nonsignificant results revisited. *Collabra: Psychology*, 3(1), 8.
