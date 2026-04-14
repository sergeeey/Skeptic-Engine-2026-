Subject: Extending your CPTAC framework to adversarial data integrity screening

Dear Dr. Bradshaw,

I've been working on extending the CPTAC data integrity framework you established in your 2021 Nature Methods paper ("Pan-cancer proteomics data"). Your work demonstrated the value of rigorous quality control for multi-omics data — I'm writing to share a complementary approach.

**What I built:** Skeptic Engine — an adversarial testing framework that transfers anomaly detection methods from finance and clinical trials to screen scientific datasets for statistical artifacts. Your CPTAC proteomics/CNA data was one of our key validation sets (H25 experiment).

**Key results:**
- Multi-modal anomaly detection across scRNA-seq, proteomics, and p-value sequences (AUC 0.729–1.000)
- Isotonic recalibration: raw scores → calibrated probabilities with CIs (MACE 0.202 → 0.032)
- Adversarial debate protocol: Prosecutor/Defense/Judge verdicts with explanation trails
- 37 validated experiments, 349 unit tests, open-source code

**Why I'm reaching out:** Your domain expertise in CPTAC proteomics would be invaluable for validating whether our cross-modal consistency detector (H33, separation = 0.383) generalizes beyond synthetic fabrications to real proteomics quality issues. Specifically, I'd value your perspective on:
1. Whether the autoencoder reconstruction error patterns we detect correspond to known batch effects or sample quality issues in CPTAC
2. Whether our calibrated probability outputs could serve as a pre-submission QC metric for proteomics journals

**Paper outline:** I'm preparing a manuscript for Bioinformatics (Application Note) — 4 pages, 1 figure (architecture diagram). The code is fully open-source: github.com/sergeeey/Skeptic-Engine-2026-

Would you be open to a brief review of the manuscript draft? I'm not asking for co-authorship — just 30 minutes of your expertise to validate whether the biological framing is sound.

Manuscript draft and full results are attached. The code can be installed via `pip install .` and includes a CLI: `skeptic-toolkit matrix.mtx`.

Thank you for your time and for the excellent CPTAC resource.

Best regards,
Sergey V. Boiko
github.com/sergeeey/Skeptic-Engine-2026-

---

Attachments:
- MANUSCRIPT_v03.md (draft manuscript)
- REPORT.md (full experimental results, 11 experiments)
