# Zenodo Packaging Guide

## What to include in the archive

```
skeptic-engine-v0.1.0/
├── README.md
├── REPORT.md
├── LICENSE                          # ← CREATE THIS (MIT recommended)
├── pyproject.toml
├── demo_colab.ipynb
├── src/
│   ├── discovery_engine/            # Pipeline infrastructure
│   └── skeptic_toolkit/             # Installable CLI toolkit
├── experiments/
│   ├── h24_benford_scrna/           # scRNA-seq artifact detection
│   │   ├── *.py                     # All experiment scripts
│   │   ├── figures/                 # Publication figures
│   │   ├── results/                 # JSON results
│   │   ├── paper_outline.md
│   │   └── collaboration_pitch.md
│   ├── h25_banking_ae_lcms/         # Proteomics/CNA artifact detection
│   │   ├── *.py
│   │   └── results/
│   ├── h23_phacking_behavioral/     # P-hacking behavioral detection
│   │   ├── *.py
│   │   ├── results/
│   │   └── README.md
│   ├── h4_tda_cancer/               # TDA cancer resistance (KILLED)
│   │   ├── run_h4.py
│   │   └── results/
│   ├── dashboard.py
│   └── run_bootstrap_ci.py
├── scripts/
│   └── skeptic_toolkit.py           # CLI wrapper
└── docs/
    ├── project-brief.md
    ├── research-contract.md
    ├── working-contract.md
    ├── toolkit_mvp.md
    └── [other docs]
```

## What to EXCLUDE

- `data/` directories with large downloaded datasets (PBMC3k, Kang2018, CPTAC, GSE164897)
- `_external/` (cloned repos)
- `__pycache__/` directories
- `.git/` directory
- `AGENTS.md` (contains local path)
- `prompts/` (internal prompts)
- `.claude/` (local config)

## Before uploading

1. LICENSE file created (Apache 2.0 — patent protection + enterprise-friendly)
2. Verify no personal paths in code: `grep -r "C:\\Users" src/ experiments/`
3. Verify demo_colab.ipynb references GitHub repo URL correctly
4. Choose Zenodo metadata:
   - Title: "Skeptic Engine: Statistical Artifact Detection for Scientific Data Integrity"
   - Authors: Sergey Boiko
   - Type: Software
   - License: Apache-2.0
   - Keywords: data integrity, statistical artifacts, Benford law, scRNA-seq, anomaly detection

## After uploading

1. Copy the DOI
2. Update demo_colab.ipynb with DOI
3. Update collaboration_pitch.md with DOI
4. Update README.md with DOI badge
