# SE-MRM Product Requirements Document (PRD)

## Metadata

| Field | Value |
|---|---|
| **Module** | Skeptic Engine: Materials Reliability Module |
| **Abbreviation** | SE-MRM |
| **Version** | 0.1.0 |
| **Domain** | Inorganic crystalline materials |
| **Author** | Sergey V. Boiko |
| **Date** | 2026-04-06 |
| **Status** | Draft — v0.1 |

---

## 1. Problem Statement

Generative models for inorganic materials (e.g., MatterGen) can produce novel candidates with desirable target properties. However, **novelty ≠ physical viability**. PhononBench shows average dynamical-stability rate of only 25.83% across generated crystals (MatterGen: 41.0%).

There is no standardized **reliability screening layer** between generation and expensive validation (DFT, synthesis).

## 2. Solution

SE-MRM is a **falsification-first reliability filter** that:
1. Accepts material candidates from generators or external sources
2. Normalizes and validates structure integrity
3. Runs multi-tier simulation screening
4. Executes adversarial failure-mode attacks
5. Computes composite reliability scores
6. Makes promote/hold/kill decisions

**SE-MRM does not prove materials are good. It tries to break them early.**

## 3. Scope (v0.1)

### In-scope
- Inorganic crystalline materials only
- CIF / POSCAR / JSON / MP-ID ingestion
- MatterSim (stub) and JaxMD (experimental) backends
- 8 failure-mode attack types
- Composite reliability scoring
- Promote/hold/kill decisions with audit trail
- CLI + Python API

### Out-of-scope
- Pharmaceuticals / organic molecules
- Autonomous lab integration
- RL self-play policies
- Real-time synchrotron / DTCS integration
- Production-grade robotics loops
- Cross-domain expansion

## 4. Users

| Role | Use case |
|---|---|
| Materials ML researcher | Screen generated candidates before DFT |
| Computational scientist | Stress-test known structures |
| Reliability engineer | Batch-screen candidate pools |
| PI / tech lead | Review reliability reports |

## 5. Success Criteria (90 days)

- [ ] Module ingests CIF/JSON/MP-ID batches
- [ ] Working MatterSim adapter (stub → real)
- [ ] ≥5 failure attacks implemented
- [ ] Composite reliability score calibrated
- [ ] Benchmark vs baseline filter
- [ ] Documented negative cases
- [ ] Reproducible run manifests

## 6. North-Star Metric

**Reduction in false-positive promoted candidates relative to baseline.**

## 7. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Sim-to-real gap | High | Uncertainty penalty, escalation hooks |
| Backend API instability | Medium | Abstraction layer |
| Overfitting to simulator | High | Backend disagreement checks |
| Scope creep | Medium | Hard lock to inorganic crystals |
| False confidence | High | Uncertainty reporting in all outputs |

## 8. Relation to Skeptic Engine

SE-MRM inherits the Skeptic Engine research contract:
- Verify before claim
- Falsification route required
- Unknowns marked
- Kill criteria enforced
- Honest negatives reported
- Evidence provenance mandatory
