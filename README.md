# Skeptic Engine v0.2.0 — Scientific Data Integrity

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19238786.svg)](https://doi.org/10.5281/zenodo.19238786)
[![CI](https://github.com/sergeeey/Skeptic-Engine-2026-/workflows/CI/badge.svg)](https://github.com/sergeeey/Skeptic-Engine-2026-/actions)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Coverage](https://img.shields.io/badge/coverage-24%25-yellow)](https://github.com/sergeeey/Skeptic-Engine-2026-)

**Skeptic Engine** — adversarial testing framework for scientific data. Instead of asking "are these results correct?", it asks "can we break them?" — and measures what survives. The system transfers anomaly detection methods from finance, clinical trials, and information security to screen scientific datasets for statistical artifacts, structural inconsistencies, and non-physical patterns across genomics, proteomics, and biomedical literature.

*Research toolkit in active development — see [Known Limitations](#known-limitations) before production use.*

> ⚠️ **Framing note:** Skeptic Engine detects statistical anomalies and data integrity artifacts — **not deliberate fraud**. Flagged datasets indicate patterns that deviate from expected statistical structure and require expert review before any conclusions about intent.

## Validated Experiments

11 experiments (H23–H33), 360 automated tests, CI/CD pipeline, CLI toolkit, and Materials Reliability Module (MRM).

**Result markers:**
- ⭐ **Real-world validated** — tested on ground-truth labeled data  
- `[synthetic]` — validated on simulated fabrication only  
- `[prototype]` — early development stage

| ID | Experiment | Metric | Data / Domain | Scope / caveat |
|----|-----------|--------|---------------|----------------|
| H25 | Banking AE on proteomics/CNA | AUC 1.000 | CPTAC (Bradshaw 2021) | Within-dataset fusion; see REPORT for generalization |
| H31 | Unified Anomaly Score | AUC 1.000 | Multi-modal fusion | Synthetic / controlled fusion benchmark |
| H24 | Benford forensics on scRNA-seq | AUC 0.978 | PBMC3k, Kang2018 | See limitations: UMI vs Benford |
| H32 | Temporal P-Hacking detection | F1 1.000 | Simulated time series | Simulation-defined labels |
| H23 | Behavioral p-hacking detection | AUC 0.729 | Reproducibility Project | Real p-value corpus; scale-up ongoing |
| H33 | Cross-Modal Consistency | Sep 0.383 | Multi-omics integration | Modest separation; interpret with care |
| H29 | Biological Syndromes | Validated | Multi-tissue patterns | Scope per experiment report |
| H30 | Retracted Paper Validation | Validated | Retraction dataset | Screening signal, not misconduct verdict |
| H27 | Clinical Trials Screening | Prototype | Trial registry data | Early prototype |
| H28 | Paper Mills Detection | Prototype | Publication metadata | Early prototype |
| MRM | Materials Reliability Module | v0.1 | Materials science | Stub/fallback backends unless cited artifact |

## What This Repository Does NOT Do

- ❌ **Prove misconduct** — detects statistical anomalies only, requires expert interpretation  
- ❌ **Replace peer review** — augments, does not replace human judgment  
- ❌ **Detect targeted evasion** — methods validated on natural fraud, not adversarial ML evasion  
- ❌ **Generalize beyond tested domains** — genomics/proteomics validated, other fields need testing

## Quick Start

```bash
# Install from source
pip install .

# Run all experiments (includes H10 graph deps: networkx, pandas, torch, …)
pip install ".[all]"

# Discovery Engine + H10 MOF baselines only
pip install ".[h10]"

# Scan a count matrix for statistical artifacts
skeptic-toolkit matrix.mtx

# Compare against a reference dataset
skeptic-toolkit candidate.mtx --reference reference.mtx

# Custom anomaly threshold
skeptic-toolkit matrix.mtx --threshold 0.6

# Verify file integrity before analysis (new in v0.2.0)
skeptic-toolkit verify paper.pdf --md5 5478a2662af82dbf6b8473391e18d12d
skeptic-toolkit verify dataset.csv --zenodo-doi 10.5281/zenodo.19238786
```

```powershell
# View unified results dashboard
python experiments/dashboard.py

# Run individual experiments
python experiments/h24_benford_scrna/run_combined.py
python experiments/h25_banking_ae_lcms/run_h25.py
python experiments/h23_phacking_behavioral/run_h23_real.py
```

## Project Structure

```
experiments/                  # 11 standalone experiments with results
├── h23_phacking_behavioral/  # Behavioral p-hacking detection
├── h24_benford_scrna/        # Benford forensics on scRNA-seq
├── h25_banking_ae_lcms/      # Autoencoder on proteomics/CNA
└── dashboard.py              # Unified results dashboard

src/discovery_engine/         # Shared pipeline infrastructure + MRM
src/skeptic_toolkit/          # CLI entry point and core utilities

docs/                         # Project brief, working contract, research contract
REPORT.md                     # Full research report with methodology and results
QWEN_METHODOLOGY.md           # Adversarial testing methodology
```

## Known Limitations

- ✅ **Golden-set validation (NEW):** H25 Autoencoder validated on 284,807 real credit card fraud transactions (AUC 0.948) — see `experiments/validation/golden_set/GOLDEN_SET_REPORT.md`
- ⚠️ **H24 Benford limitation:** Effective on synthetic artifacts (AUC 0.978), fails on real behavioral fraud (AUC 0.586) — use only for data generation audits
- **Other experiments:** Validated on synthetic fabrication or expert-labeled data, not confirmed deliberate fraud
- Cross-dataset generalization degrades for sophisticated artifact types (documented honest negative)
- Small sample sizes in some experiments (n=59–99); confidence intervals are wide
- scRNA-seq UMI counts do **not** follow Benford distribution — compliance is itself an anomaly signal
- Results indicate anomalous patterns requiring interpretation, not evidence of misconduct

## Documentation

| Document | Purpose |
|----------|---------|
| [REPORT.md](REPORT.md) | Full research report with all results and methodology |
| [experiments/validation/golden_set/GOLDEN_SET_REPORT.md](experiments/validation/golden_set/GOLDEN_SET_REPORT.md) | ⭐ Real fraud validation (H24/H25 on 284K credit card transactions) |
| [QWEN_METHODOLOGY.md](QWEN_METHODOLOGY.md) | Adversarial testing methodology and design principles |
| [docs/research-contract.md](docs/research-contract.md) | Scientific integrity boundaries |
| [docs/project-brief.md](docs/project-brief.md) | Two-branch strategy and success criteria |
| [AGENTS.md](AGENTS.md) | Cursor/agent operating contract for this repo (workflow, safety boundaries) |
| [MANUSCRIPT_CITATION_MAP.md](MANUSCRIPT_CITATION_MAP.md) | Draft insertions and external citations for manuscript (verify rights before publish) |

## Citation

If you use Skeptic Engine in your research, please cite:

```bibtex
@software{skeptic_engine_2026,
  author = {Boiko, Sergey V.},
  title = {Skeptic Engine: Statistical Artifact Detection for Scientific Data Integrity},
  year = {2026},
  version = {0.2.0},
  doi = {10.5281/zenodo.19238786},
  url = {https://github.com/sergeeey/Skeptic-Engine-2026-}
}
```

For the golden-set validation methodology, see:
- `experiments/validation/golden_set/GOLDEN_SET_REPORT.md`
