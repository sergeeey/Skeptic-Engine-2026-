# Skeptic Engine — Scientific Data Integrity Research

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19238786.svg)](https://doi.org/10.5281/zenodo.19238786)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Two-branch research portfolio: scientific data integrity screening (primary) + interdisciplinary discovery (supporting).

## Branch 2 — Statistical Artifact Detection (PRIMARY, 70%)

Transferring financial anomaly detection methods to screen scientific datasets for non-physical statistical artifacts, reporting inconsistencies, and structural anomalies.

> **Framing note:** This project detects statistical artifacts and anomalous data patterns — it does not claim to identify deliberate fraud. Flagged datasets require expert review before any conclusions about intent.

### Validated Experiments

| ID | Experiment | Best AUC | Data |
|----|-----------|---------|------|
| H24 | Benford digit forensics on scRNA-seq | 0.978 | PBMC3k, Kang2018 |
| H25 | Banking autoencoder on proteomics/CNA | 1.000 | CPTAC (Bradshaw 2021) |
| H23 | Behavioral p-hacking detection | 0.729 (real) | Reproducibility Project |

### Key Findings

- Digit forensics + structural anomaly fusion detects simulated artifacts in count matrices (AUC 0.86-1.00 within-dataset)
- Autoencoder reconstruction error catches structure-breaking artifacts that digit tests miss (and vice versa)
- Behavioral features screen statistical reporting anomalies better than p-curve baseline (+7.5pp on real replication data)
- scRNA-seq UMI counts do NOT follow Benford distribution — Benford compliance is itself an anomaly signal
- Cross-dataset generalization fails for sophisticated artifact types (honest negative, documented)

### Known Limitations

- All artifact simulations are synthetic — no confirmed real-world fabrication ground truth exists
- Cross-dataset transfer requires retraining for sophisticated artifact types
- Small sample sizes in some experiments (n=59-99); confidence intervals are wide
- Results indicate anomalous patterns, not deliberate fraud — expert review required for interpretation

## Branch 1 — Discovery Lab (SUPPORTING, 30%)

Infrastructure for interdisciplinary hypothesis search. H10 MOF benchmark complete. H4 TDA cancer resistance pending one clean run. Time-boxed: 1 day/week maintenance maximum.

## Repository Layout

```
experiments/              # Standalone experiments with results
├── h24_benford_scrna/    # Branch 2: scRNA-seq fabrication detection
├── h25_banking_ae_lcms/  # Branch 2: proteomics/CNA integrity
├── h23_phacking_behavioral/ # Branch 2: p-hacking detection
└── dashboard.py          # Unified results view

src/discovery_engine/     # Shared pipeline infrastructure
docs/                     # Project rules, roadmap, research contract
REPORT.md                 # Full research report
```

## Quick Start

```powershell
# View all results
python experiments/dashboard.py

# Run individual experiments
python experiments/h24_benford_scrna/run_combined.py
python experiments/h25_banking_ae_lcms/run_h25.py
python experiments/h23_phacking_behavioral/run_h23_real.py

# Pipeline infrastructure
$env:PYTHONPATH='src'; python -m discovery_engine.main pipeline
```

## Docs

- `docs/project-brief.md` — two-branch strategy and success criteria
- `docs/working-contract.md` — day-to-day execution rules
- `docs/research-contract.md` — scientific integrity boundaries
- `REPORT.md` — full research report with all results
