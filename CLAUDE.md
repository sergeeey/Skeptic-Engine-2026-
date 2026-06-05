# Skeptic Engine v0.2.0 — Claude Code Project Memory

## PROJECT
- **Stack:** Python 3.11+, numpy/scipy/sklearn, torch (optional), pandas (optional)
- **Goal:** Statistical artifact detection for scientific data integrity (fraud detection methods → science)
- **Status:** v0.2.0 production-ready, Zenodo DOI 10.5281/zenodo.19238786, Apache 2.0
- **Repo:** https://github.com/sergeeey/Skeptic-Engine-2026-.git
- **CLI:** `skeptic-toolkit matrix.mtx`, `skeptic-mrm`, `discovery-engine`
- **Tests:** 360 passing, coverage 24%, mypy clean, ruff clean (3 UP007 warnings)

## ARCHITECTURE

```
src/
├── skeptic_toolkit/        # CLI + syndrome layer (H29)
├── skeptic_mrm/            # Materials Reliability Module (stub/fallback)
└── discovery_engine/       # Original discovery infrastructure (supporting)

experiments/                # 22 directories, 11 documented
├── h24_benford_scrna/      # Benford forensics, AUC 0.978, PBMC3k
├── h25_banking_ae_lcms/    # Autoencoder, AUC 1.000, CPTAC
├── h23_phacking_behavioral/# p-hacking, AUC 0.729, Reproducibility Project ⭐
├── h29_biological_syndromes/# Syndrome detector, MaveDB/ClinVar validation ⭐
└── [h26-h38, mrm_*]/       # Additional experiments (some undocumented)
```

## ALWAYS DO
- Pydantic validation on inputs (if adding new API endpoints)
- Parameterized queries (not applicable — no SQL)
- structlog instead of print() (partially applied)
- Read experiments/*/run_*.py before claiming validation status

## VALIDATION TIERS (IMPORTANT for claims)

| Tier | What | Where | Claim scope |
|---|---|---|---|
| **Tier 1** (strongest) | Real data + real fraud labels | H23 (Reproducibility Project) | Real fraud detection |
| **Tier 2** (strong) | Real data + expert labels | H29 (MaveDB/ClinVar benign vs pathogenic) | Expert-labeled integrity |
| **Tier 3** (medium) | Real data + **simulated** fabrication | H24/H25 (PBMC/CPTAC + synthetic) | Synthetic artifact detection |

**Key distinction:** H24/H25 achieve AUC 0.978-1.000 on **simulated** fabrication (resample/noise/random_nb), NOT real fraud. Ground truth real fraud = H23 only (99 studies).

## FRAMING (NON-NEGOTIABLE)

From `docs/research-contract.md`:
- **NOT** a Nobel-ready discovery claim
- **NOT** a fraud accusation tool
- **IS** a statistical artifact detector requiring expert review
- **IS** transfer of financial fraud methods to science

**Folder name contradiction:** Current folder "nobel premia Boiko - 2026" violates research-contract.md framing. Rename to `skeptic-engine-manuscript` when consolidating.

## NEVER
- Claim "real fraud detection" for H24/H25 (their fabrication is synthetic)
- Count H29 multi-dataset validation as "11 independent experiments" (it's 1 experiment, multiple datasets)
- Hardcode secrets (MP_API_KEY from env ✅)
- Skip README update when adding experiments (11/22 currently documented)

## CURRENT FOCUS (from activeContext.md)

v0.2.0 released (commit 1144fd6). Next: optional external outreach.

**Parked до 2026-06-20:** transfer plan (golden-set harness from VeriFind, ChernoffPy from MarkovChains). Do NOT start before GeoScan blind test deadline.

## QUICK COMMANDS

```bash
# Run main experiments
python experiments/h24_benford_scrna/run_h24.py       # Benford scRNA
python experiments/h25_banking_ae_lcms/run_h25.py     # AE proteomics
python experiments/h23_phacking_behavioral/run_h23_real.py  # p-hacking real data

# CLI
skeptic-toolkit matrix.mtx --mode syndrome --report out.json

# Tests
python -m pytest tests/ -q --tb=short   # 360 passing
python -m ruff check src/ tests/         # 3 UP007 warnings only
python -m mypy src/ --ignore-missing-imports  # clean
```

## DEPENDENCIES

Core: numpy 2.3.5, scipy 1.17.1, scikit-learn 1.7.2  
Optional: torch 2.12.0.dev (⚠️ bleeding edge), pandas 2.3.3

**Risk:** torch on dev version — pin to stable before PyPI release.

## KNOWN ISSUES

1. **Coverage 24%** — low for production. Target ≥60%.
2. **Feature branches stale** — 6 branches on origin/*, possibly dead.
3. **11/22 experiments undocumented** — half of experiments/ not in README.
4. **No PyPI release** — Zenodo only, not pip-installable.
5. **Folder name** — contradicts CONTRACT framing.

## RECONCILIATION HISTORY

**2026-06-05:** activeContext claimed "11 independent, 55K+ real data" vs parked plan "вся валидация синтетическая". Resolved:
- activeContext: overcounted (MaveDB/TCGA/CPTAC = 1 H29 experiment, not 3).
- parked plan: undercounted (missed H23/H29 real labels, only saw H24/H25 synthetic).
- Truth: 3 tiers (Tier 1: H23 real fraud, Tier 2: H29 expert labels, Tier 3: H24/H25 synthetic).
- Scientific validity: **6/10** (not 3, not 9).
