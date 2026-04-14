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

The "Replication Crisis" has highlighted the fragility of scientific claims. While much focus has been placed on p-hacking and publication bias, the detection of *structural* artifacts—subtle inconsistencies in high-dimensional data (e.g., scRNA-seq count matrices)—remains under-explored.

Current tools (e.g., p-curve, Statcheck) are unimodal: they look at p-values *or* pixels. They do not look at the data *structure*. Furthermore, they rarely provide calibrated uncertainty. A score of "0.8" from a generic anomaly detector is meaningless without knowing: *How likely is a true negative to score 0.8?*

We propose a shift from **Single-Point Detection** to **Calibrated, Adversarial Verification**.

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
This yields not just a point estimate, but a confidence interval based on the local density of calibration data.

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

### 4.2 Limitations
*   **Synthetic Ground Truth:** Most validation relies on simulated fabrications. Real-world confirmed fraud datasets are scarce.
*   **Domain Specificity:** While UAS generalizes better than single detectors, the feature extraction still requires domain knowledge (e.g., knowing what "Benford" means for scRNA-seq vs. proteomics).

### 4.3 Future Work
*   **Knowledge Graph (H38):** Linking anomalies across papers to detect systematic "paper mills."
*   **Real-World Integration:** Deploying Skeptic Engine as a pre-submission check for partner journals.

---

## 5. Conclusion

Skeptic Engine demonstrates that we can move beyond simple statistical checks to a **holistic, calibrated, and explainable** system for data integrity. By combining multi-modal detection with adversarial debate, we provide a tool that doesn't just find errors, but helps us understand them.

---

## References

1.  Bradshaw, C. J. A., et al. (2021). "CNA: Copy Number Alteration detection in cancer." *Nature Methods*.
2.  Benford, F. (1938). "The Law of Anomalous Numbers." *PNAS*.
3.  Nuijten, M. B., et al. (2016). "The prevalence of statistical reporting errors in psychology." *Behavior Research Methods*.
