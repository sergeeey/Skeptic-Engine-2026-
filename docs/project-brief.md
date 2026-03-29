# Project Brief

## Related Docs

- `working-contract.md`
- `research-contract.md`
- `mvp-roadmap.md`

## Project Structure

This repository contains **two research branches** with different goals, metrics, and resource allocation.

```
Branch 2 (Primary): Scientific Data Integrity    — 70% of effort
Branch 1 (Supporting): Discovery Lab              — 30% of effort
```

---

## Branch 2: Financial Anomaly Detection → Scientific Data Integrity Screening (PRIMARY)

### Goal

Transfer financial anomaly detection methods to scientific data integrity screening: detecting non-physical statistical artifacts, reporting inconsistencies, and structural anomalies in published datasets.

> **Framing:** We detect artifacts, not intent. Flagged data requires expert review.

### Why This Is Primary

- **Operator edge:** direct reuse of 10+ years fraud detection expertise
- **Validated results:** 3 experiments with positive AUC (H24, H25, H23)
- **Confirmed prior-art gaps:** verified via PubMed/Semantic Scholar
- **Clear publication path:** 2-3 papers in 3-6 months
- **Novel scientific observations:** Benford inversion in scRNA-seq, feature group complementarity

### Active Experiments

| ID | Title | Best AUC | Status |
|----|-------|---------|--------|
| H24 | Benford digit forensics on scRNA-seq | 0.978 fusion | Validated, paper outline ready |
| H25 | Banking autoencoder on proteomics/CNA | 1.000 fusion | Validated |
| H23 | Behavioral p-hacking detection | 0.729 real data | Validated, needs scale-up |

### Deliverables

1. Publication-grade research package for H24 (nearest to submission)
2. Scaled validation of H23 on statcheck 688k p-values
3. Cross-omics generalization test for H25
4. Open-source integrity screening toolkit (longer term)

### Success Criteria (90 days)

- [ ] H24 paper submitted or preprinted
- [ ] H23 validated on 10k+ real studies
- [ ] 1 domain co-author onboarded
- [ ] Toolkit MVP working (local count-matrix checker)

---

## Branch 1: Interdisciplinary Discovery Lab (SUPPORTING)

### Goal

Maintain the hypothesis discovery infrastructure and execute one clean benchmark to preserve optionality for future interdisciplinary research.

### Why This Is Supporting

- Operator has no materials science or biology lab expertise
- MOF benchmark field is saturated (Princeton 97% F1, MOFGen, 2025 Nobel)
- Original top-5 hypotheses had low surviving novelty after prior-art review
- Infrastructure value is real but research output requires domain collaborators

### Status

| ID | Title | Status |
|----|-------|--------|
| H10 | MOF stability benchmark | Complete (AP=0.87 descriptor, graph-ready) |
| H4 | TDA cancer resistance | **CLOSED** — TDA AUC=0.50 (random), kill criterion triggered |
| H20 | SOC electrode early-warning | Narrowed, on hold |
| H1 | Koopman LLPS | Blocked on data |
| H2 | PH metallic glass | Fallback, low novelty |

### Time Budget

1 day per week maximum on maintenance. No new infrastructure unless sharp justification.

### Kill Criterion for H4

If after one clean benchmark run: AUC < 0.75 on resistance-labeled dataset, OR dataset not validated within 4 weeks → close track, redirect remaining time to Branch 2.

### Success Criteria (90 days)

- [x] H4 benchmark: one clean result — **KILLED** (TDA AUC=0.50, PCA=0.9998 trivial batch effect)
- [ ] Infrastructure stable, no feature creep
- [ ] Explicit decision: continue or close

---

## Shared Infrastructure

Both branches share:

- `src/discovery_engine/` — pipeline, schemas, collectors
- External source collectors (Semantic Scholar, bioRxiv, Zenodo)
- Skeptic stage for prior-art challenge
- DQOps for source quality scoring
- Working contract and research integrity rules

---

## Research Standard (applies to both branches)

- No fabricated novelty claims
- No fabricated prior-art claims
- No source-free confidence
- No promotion without falsification path
- All results audited: data authenticity, leakage tests, feature verification
- Honest negatives reported (cross-dataset failure, normalization failure, etc.)

---

## End-State Standard

The immediate aim is validated research results with honest limitations documented.

Publication is downstream and must not drive evidence standards.
Recognition is further downstream and must not drive publication framing.
