# SE-MRM Negative Results

## Principle

Per the Skeptic Engine research contract, **honest negatives are mandatory**.
This document tracks all failed experiments, killed candidates, and known limitations.

## Known Limitations (v0.1)

### L-01: All simulations are stubs
- **Status:** Known
- **Impact:** Scores are synthetic, not physical
- **Resolution:** Replace stubs with real MatterSim/DFT backends

### L-02: No real ground truth for stability
- **Status:** Known
- **Impact:** Cannot validate true positive/negative rates
- **Resolution:** Use PhononBench dynamical stability labels as proxy

### L-03: Cross-dataset generalization untested
- **Status:** Not attempted in v0.1
- **Impact:** Unknown if scoring transfers across material classes
- **Resolution:** Run benchmarks on multiple material families

### L-04: Single backend (no disagreement detection)
- **Status:** v0.1 limitation
- **Impact:** Cannot detect simulator-specific artifacts
- **Resolution:** Add second backend (DFT hook or JaxMD production)

### L-05: Scoring weights not calibrated
- **Status:** Default weights
- **Impact:** Relative importance of components is heuristic
- **Resolution:** Optimize weights on reference benchmark

### L-06: No uncertainty quantification
- **Status:** v0.1 uses proxy penalties
- **Impact:** Uncertainty is estimated, not measured
- **Resolution:** Add ensemble or Bayesian uncertainty

## Killed Candidates

_No real candidates killed yet (v0.1 uses synthetic data)._

When real candidates are processed, killed entries will be recorded here with:
- candidate_id
- composition
- failure modes triggered
- decision rationale
- score breakdown

## Failed Experiments

### FE-01: Cross-structure dedup via fingerprint only
- **Issue:** Hash-based fingerprint catches exact duplicates but not structurally similar candidates
- **Impact:** Near-duplicates may pass dedup
- **Resolution:** Add RDF/SOAP-based structural similarity metric

### FE-02: Property extraction from CIF
- **Issue:** Only _chemical_formula_sum extracted; other properties ignored
- **Impact:** Rich CIF data not utilized
- **Resolution:** Full CIF parser in future version

## Sim-to-Real Disclaimer

SE-MRM v0.1 outputs **computational risk assessments**, not physical guarantees.
A "promoted" candidate may still fail in DFT or synthesis.
The module's goal is **risk reduction**, not risk elimination.

All reports must include:
- Uncertainty penalty value
- Evidence completeness score
- "This is a computational screening — experimental validation required" notice
