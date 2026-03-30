# Pitch: Michele Nuijten — Behavioral p-hacking detection (H23)

**To:** Michele Nuijten (m.b.nuijten@tilburguniversity.edu)
**Re:** Behavioral anomaly detection for statistical reporting — building on statcheck

---

## Email

Subject: Behavioral sequence analysis for replication risk prediction — building on statcheck

Dear Dr. Nuijten,

Your work on statcheck has been foundational for automated statistical error detection. I'm writing because I've built on your framework in an unexpected direction — using the temporal sequence of p-values within a paper as a behavioral signal for replication risk.

**The idea:** Rather than checking individual statistics for errors (as statcheck does), we treat the ordered sequence of p-values in a paper as a behavioral trace — similar to how financial fraud detection analyzes transaction sequences. We extract 18 features capturing clustering near 0.05, terminal significance patterns, volatility, and entropy.

**Results on real data:**
- **Reproducibility Project Psychology (n=99):** AUC 0.729 (vs. p-value-only baseline 0.654, +7.5pp improvement)
- **Statcheck meta-analyses (n=61):** AUC 0.765 (vs. discrepancy baseline 0.522, +24.3pp improvement)
- **Simulated p-hacking (n=2000):** AUC 0.993 (vs. p-curve baseline 0.706)

The approach is complementary to statcheck — it uses the pattern of results across a paper, not the correctness of individual statistics.

All code and data are open-source:
https://doi.org/10.5281/zenodo.19238786

I have a paper outline targeting Research Integrity and Peer Review or Meta-Psychology. Given your deep expertise in this space, I would be honored to collaborate. Your guidance on framing, interpretation, and access to the full statcheck dataset (688k p-values from DANS) would significantly strengthen the work.

Best regards,
Sergey V. Boiko

---

## Why Nuijten

- Statcheck is literally our data source for H23 validation
- She understands p-hacking detection better than anyone
- Access to full 688k statcheck dataset would solve the underpowered problem
- Meta-science community is small and collaborative
- H23 is a SEPARATE paper from H24 — parallel track
