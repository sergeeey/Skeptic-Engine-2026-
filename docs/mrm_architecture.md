# SE-MRM Architecture

## Overview

```
┌─────────────────────────────────────────────────────┐
│                  Skeptic Engine                      │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │         SE-MRM (Materials Reliability)       │    │
│  │                                               │    │
│  │  Ingest → Normalize → Screen → Attack        │    │
│  │   → Score → Rank → Promote/Hold/Kill         │    │
│  └─────────────────────────────────────────────┘    │
│                                                      │
│  Branch 2: Scientific Data Integrity (70%)          │
│  Branch 1: Discovery Lab (30%)                       │
│  NEW: SE-MRM — orthogonal module                      │
└─────────────────────────────────────────────────────┘
```

## Pipeline Stages

```
Stage 0: Intake          → normalized candidate manifest
Stage 1: Sanity + Dedup  → valid candidates, rejection report
Stage 2: Cheap screening → heuristics, OOD flags, pre-score
Stage 3: Simulation      → relaxation, energetics, stability
Stage 4: Falsification   → attack suite, failure detection
Stage 5: Adjudication    → composite score + decision
Stage 6: Escalation      → expensive validation queue (future)
Stage 7: Reporting       → candidate card, batch summary
```

## Module Structure

```
src/skeptic_mrm/
├── __init__.py              # Package metadata
├── schemas/
│   ├── material_candidate.py
│   ├── simulation_run.py
│   ├── failure_attack.py
│   └── reliability_decision.py
├── ingest.py                # CIF/JSON/MP-ID loaders
├── normalize.py             # Validation, dedup, fingerprint
├── generator_adapters.py    # IGeneratorAdapter + stubs
├── simulation_backends.py   # ISimulationBackend + stubs
├── falsification.py         # Attack library + orchestrator
├── scoring.py               # Composite reliability score
├── reports.py               # Candidate/batch reports
├── runner.py                # MRMRunner (main orchestrator)
└── cli.py                   # skeptic-mrm CLI
```

## Key Interfaces

### IGeneratorAdapter
```python
class IGeneratorAdapter(ABC):
    def sample(self, constraints: dict, n: int) -> list[dict]: ...
    def metadata(self) -> dict: ...
```

### ISimulationBackend
```python
class ISimulationBackend(ABC):
    def relax(self, candidate, config) -> SimulationRun: ...
    def simulate(self, candidate, scenario) -> SimulationRun: ...
    def supports(self) -> dict: ...
```

### IAttackPolicy
```python
class IAttackPolicy:
    def propose(self, candidate, history, budget) -> list[str]: ...
```

## Backend Strategy

| Backend | Status | Tier |
|---|---|---|
| MatterSim (stub) | Default v0.1 | 1 |
| JaxMD | Experimental (API unstable) | 2 |
| DFT hook | Reserved for future | 2 |

**JaxMD is experimental** — the project itself warns about API-breaking changes.

## Scoring Formula

```
final_reliability_score =
    w1 * thermo_score          (0.25)
  + w2 * dynamic_score         (0.20)
  + w3 * stress_resilience     (0.20)
  + w4 * reproducibility       (0.10)
  + w5 * novelty               (0.05)
  - w6 * uncertainty_penalty   (0.10)
  - w7 * sim_disagreement      (0.05)
  - w8 * compute_risk          (0.05)
```

## Decision Thresholds

| Criterion | Value |
|---|---|
| Kill below | 0.35 |
| Hold below | 0.65 |
| Promote above | 0.65 |
| Min stability | 0.30 |
| Min dynamic | 0.30 |
| Max uncertainty | 0.50 |

## Provenance

Every decision is traceable to:
- Input artifact (CIF/JSON/MP-ID)
- Run ID + config version
- Backend version + random seed
- Simulation outputs
- Scoring policy version
