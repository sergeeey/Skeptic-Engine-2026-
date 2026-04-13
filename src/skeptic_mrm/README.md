# Skeptic Engine: Materials Reliability Module (SE-MRM)

> A falsification-first reliability layer for inorganic crystal candidates.
> SE-MRM does not try to prove materials are good.
> It tries to break them early, score their resilience,
> and reduce false-positive promotion before expensive validation.

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)]()
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)]()
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)]()

---

## What is SE-MRM?

SE-MRM is a module within the **Skeptic Engine** project that screens inorganic crystal candidates for reliability before expensive validation (DFT, synthesis).

It implements the **falsification-first** paradigm:
1. **Accept** candidates from generators or external sources
2. **Normalize** and validate structure integrity
3. **Screen** via multi-tier simulation
4. **Attack** with 8 failure-mode types
5. **Score** composite reliability
6. **Decide**: promote / hold / kill

## Why?

Generative models (MatterGen, etc.) produce novel materials, but:
- PhononBench: only 25.83% of generated crystals are dynamically stable
- MatterGen: 41.0% stability rate
- **Novelty ≠ physical viability**

SE-MRM catches fragile candidates **before** they waste DFT/synthesis resources.

## Installation

```bash
# From the project root:
pip install -e ".[mrm]"

# Or without optional crystallography deps:
pip install -e .
```

## Quick Start

### CLI

```bash
# Show help
skeptic-mrm

# Ingest candidates
skeptic-mrm ingest candidates.jsonl

# Run full pipeline
skeptic-mrm run --input candidates.jsonl --out results/batch_001

# View report
skeptic-mrm report results/batch_001/batch_summary.json
```

### Python API

```python
from skeptic_mrm.runner import MRMConfig, MRMRunner

config = MRMConfig(
    mode="standard",
    max_attacks_per_candidate=8,
)
runner = MRMRunner(config=config)
result = runner.run_batch("data/candidates.jsonl")

print(result.summary())
for survivor in result.top_survivors(5):
    print(f"  {survivor.summary()}")
```

## Module Structure

```
src/skeptic_mrm/
├── schemas/           # Data models
├── ingest.py          # CIF/JSON/MP-ID loaders
├── normalize.py       # Validation, dedup, fingerprint
├── generator_adapters.py  # IGeneratorAdapter + stubs
├── simulation_backends.py # ISimulationBackend + stubs
├── falsification.py   # Attack library + orchestrator
├── scoring.py         # Composite reliability score
├── reports.py         # Candidate/batch reports
├── runner.py          # MRMRunner (main orchestrator)
└── cli.py             # skeptic-mrm CLI
```

## Pipeline

```
Candidate → Normalize → Screen → Attack → Score → Rank → Promote/Hold/Kill
```

## Failure Modes (v0.1)

| Attack | Target |
|---|---|
| Lattice perturbation | Structure collapse |
| Atomic displacement | Dynamic instability |
| Temperature ramp | Thermal sensitivity |
| Pressure ramp | Pressure sensitivity |
| Repeated relaxation | Thermodynamic instability |
| Defect injection | Defect sensitivity |
| Property fragility | Property collapse |
| Symmetry perturbation | Symmetry collapse |

## Scoring

```
final = 0.25*thermo + 0.20*dynamic + 0.20*stress + 0.10*reprod + 0.05*novelty
        - 0.10*uncertainty - 0.05*disagreement - 0.05*compute_risk
```

| Decision | Threshold |
|---|---|
| Kill | < 0.35 |
| Hold | 0.35 – 0.65 |
| Promote | > 0.65 |

## Docs

| Document | Path |
|---|---|
| Product Requirements | `docs/mrm_prd.md` |
| Architecture | `docs/mrm_architecture.md` |
| Data Contract | `docs/mrm_data_contract.md` |
| Evaluation Protocol | `docs/mrm_eval_protocol.md` |
| Failure Taxonomy | `docs/mrm_failure_taxonomy.md` |
| CLI Reference | `docs/mrm_cli_reference.md` |
| Negative Results | `docs/mrm_negative_results.md` |

## Research Contract

SE-MRM inherits Skeptic Engine rules:
- Verify before claim
- Falsification route required
- Unknowns marked
- Kill criteria enforced
- Honest negatives reported
- Evidence provenance mandatory

## Limitations (v0.1)

- All simulations are **stubs** — real MatterSim/DFT integration pending
- Scoring weights are **default** — not calibrated on real data
- No real ground truth for stability
- Single backend only (no disagreement detection)
- Inorganic crystals only

## Benchmarks

```bash
# Run stub benchmark
python experiments/mrm_bench_v01/run_bench_v01.py

# Smoke test
python experiments/mrm_bench_v01/run_smoke_test.py
```

## License

Apache 2.0

## Author

Sergey V. Boiko — part of the Skeptic Engine project
