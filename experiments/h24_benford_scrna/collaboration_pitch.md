# Collaboration Pitch — Statistical Artifact Detection in scRNA-seq Data

## For: Bioinformatics / Computational Biology researchers

### One-Line Summary

We have working code + results showing that financial anomaly detection methods (Benford digit analysis + Isolation Forest fusion) can screen scRNA-seq count matrices for non-physical statistical artifacts with AUC 0.978 (bootstrap 95% CI: [0.988, 0.997]) — and we need a bioinformatics domain expert to co-author.

> Note: We detect statistical artifacts, not fraud. Flagged data requires expert review.

**Published:** https://doi.org/10.5281/zenodo.19238786 (Zenodo, Apache 2.0)
**Live Demo:** https://colab.research.google.com/drive/1zk1SVyJ_N4uQ4wNryd6svhUj_M26mOKa

### What We Have (completed)

1. **Working pipeline** (Python, numpy/sklearn only):
   - Benford digit frequency extraction (21 features)
   - Cell-level anomaly features (8 features)
   - Isolation Forest anomaly scoring (1 feature)
   - Fusion classifier (30 features, RF)

2. **Results on 2 datasets** (PBMC3k + Kang2018/GSE96583):
   - Within-dataset AUC: 0.86-1.00 (3 fabrication methods)
   - Cross-dataset noise detection: AUC = 1.00
   - Cross-dataset sophisticated fabrication: does not generalize (honest negative)
   - Feature importance analysis showing which feature groups drive each fabrication type

3. **Paper outline** with 5 sections, target journals, figures

4. **Confirmed prior art gap**: Benford on scRNA-seq only for cell typing (Vilenchik 2019), Bradshaw 2021 on CNA only. Nobody did UMI fabrication detection.

### What We Need From You

1. **Domain validation**: Are our fabrication simulations biologically realistic? What manipulations would a real fabricator use?
2. **Biological interpretation**: Why do specific Benford features (fd_2, chi2) discriminate NB-generated data?
3. **Additional datasets**: Access to datasets with known quality issues or from retracted papers
4. **Journal selection guidance**: Which venue best fits this method+application paper?
5. **Co-authorship**: Second author on the paper (we do all computational work)

### What We Bring

- **Fraud detection domain expertise**: 10+ years in financial security, fintech KZ
- **All code and results already produced** — no computation needed from you
- **Paper draft in progress** — you review, comment, add domain framing
- **Open-source release planned** — high visibility tool for the community

### Why This Matters

- scRNA-seq data in GEO/SRA is not routinely checked for fabrication
- Current QC (Scrublet, ambient RNA filters) targets biological artifacts, not fraud
- Bradshaw 2021 showed omics fabrication is a real problem (82-100% detection on CNA)
- This is the first tool targeting UMI count matrix integrity specifically

### Timeline

- Week 1-2: You review methods and suggest improvements
- Week 3: We revise, you write 1-2 paragraphs of biological context in Discussion
- Week 4: Submit to bioRxiv as preprint + journal submission

### Where to Find Potential Co-Authors

**Strategy 1: Authors of adjacent papers**
- Contact authors of Bradshaw et al. 2021 (omics fabrication) — they may want to extend their work
- Contact authors of Vilenchik & Goldberg 2019 (Benford scRNA-seq) — natural extension
- Contact authors of scRNA-seq Bias Detector (2025) — complementary QC tool

**Strategy 2: Bioinformatics groups in KZ/Central Asia**
- Nazarbayev University (NU) bioinformatics department
- Al-Farabi Kazakh National University — computational biology group
- Satbayev University — data science + biology intersection

**Strategy 3: Open collaboration platforms**
- Twitter/X: post results with tag #scRNAseq #DataIntegrity #Bioinformatics
- bioRxiv preprint first (solo), then invite reviewers to co-author extended version
- ResearchGate: message authors of cited papers directly

**Strategy 4: Academic collaboration networks**
- ELIXIR (European bioinformatics network) — open collaboration calls
- GOBLET (Global Organisation for Bioinformatics Learning) — training collaborations
- Galaxy Project community — tool development collaborations

### Email Template

Subject: Collaboration opportunity — Fraud detection methods for scRNA-seq data integrity

Dear [Name],

I'm writing because your work on [their paper] is directly relevant to a project I'm developing. I've built a tool that transfers financial fraud detection methods (Benford digit analysis + Isolation Forest) to detect fabricated scRNA-seq count matrices.

Key results on PBMC3k and Kang2018 datasets:
- Within-dataset detection AUC: 0.86-1.00
- Cross-dataset noise detection: AUC = 1.00
- Full feature importance analysis completed

I have working code, results, and a paper outline, but I need a bioinformatics domain expert to validate the biological framing and co-author the paper.

Would you be interested in a brief call to discuss? I can share the code and results immediately.

Best regards,
Sergey Boiko
[LinkedIn/GitHub]
