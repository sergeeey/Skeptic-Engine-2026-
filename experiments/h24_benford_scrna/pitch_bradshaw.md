# Pitch: Michael Bradshaw — CNA fabrication extension to scRNA-seq

**To:** Michael Bradshaw (University of Utah / Huntsman Cancer Institute)
**Re:** Extending your omics fabrication detection work to scRNA-seq UMI counts

---

## Email

Subject: Extending your omics fabrication detection framework to scRNA-seq — Collaboration inquiry

Dear Dr. Bradshaw,

Your 2021 PLoS ONE paper on detecting fabricated CNA data using Benford's Law directly inspired the project I'm reaching out about. I built on your framework and extended it from CNA to single-cell RNA-seq UMI count matrices — with an unexpected finding.

**Key results:**

- **Benford Inversion**: scRNA-seq UMI counts do NOT follow Benford's Law (first-digit frequency fd1 = 0.74 vs. expected 0.30). This means Benford compliance is itself a fabrication signal — the opposite of what your CNA framework assumes. This appears to be undocumented in the literature.
- **Fusion AUC 0.978** on PBMC3k (bootstrap 95% CI: [0.988, 0.997]) using 30-feature fusion of Benford digits + cell-level structural features + Isolation Forest anomaly scoring.
- **Cross-omics validation**: We also applied a banking-style autoencoder to your Bradshaw CPTAC proteomics data — AUC 1.000 for random/shuffle fabrication, confirming that reconstruction error captures structural coherence violations.

The full toolkit is open-source on Zenodo:
https://doi.org/10.5281/zenodo.19238786

Interactive demo (runs in browser, no install):
https://colab.research.google.com/drive/1zk1SVyJ_N4uQ4wNryd6svhUj_M26mOKa

I have a paper draft, all code, and results ready. I'm looking for a domain co-author who understands omics data integrity — and given that this directly extends your published work, you're the natural fit. I'm happy to offer senior authorship for the domain framing contribution.

Would you be open to a brief look at the code and results?

Best regards,
Sergey V. Boiko
AI Systems & Security Architect | Almaty, Kazakhstan
GitHub: https://github.com/sergeeey/Skeptic-Engine-2026-

---

## Why Bradshaw

- His 2021 paper is the closest prior art — we literally use his CPTAC data in H25
- Benford Inversion finding is a direct novelty relative to his framework
- He understands the fabrication detection framing — no need to explain "why this matters"
- Co-authorship makes Paper 2 (multi-omics) natural: his CNA + our scRNA-seq + proteomics
