# SE-MRM Evaluation Protocol

## 1. Benchmark Strategy

### Baseline Comparisons

| Baseline | Description |
|---|---|
| A. Generator + property filter | Simple threshold on target properties |
| B. Generator + MatterSim (no falsification) | ML screening without attacks |
| C. Generator + MRM full | Full pipeline with falsification |

### Benchmark Sets

| Set | Description | Size |
|---|---|---|
| A. Reference materials | Known stable inorganic crystals | ~50-200 |
| B. Generated candidates | MatterGen outputs | Variable |
| C. Unstable set | Known unstable / hypothetical structures | ~20-50 |
| D. Adversarial | Perturbed versions of A | Same as A |

## 2. Metrics

### Product Metrics
- % candidates successfully ingested
- % candidates successfully normalized
- Average runtime per candidate
- Cost per promoted candidate
- % candidates with complete provenance
- % candidates with reproducible rerun

### Research Metrics
- Promotion precision on reference benchmark
- False positive rate
- False negative rate
- Calibration quality (Brier score)
- Incremental value over baseline filter
- Failure-mode coverage

### North-Star Metric
**Reduction in false-positive promoted candidates relative to baseline A.**

## 3. Acceptance Criteria for MVP v0.1

- [x] Module ingests CIF/JSON/MP-ID batches
- [x] Working adapter for MatterGen inputs (stub)
- [x] Working backend for MatterSim (stub)
- [x] ≥5 failure attacks implemented (8 implemented)
- [x] Composite reliability score
- [x] Promote/hold/kill decisions
- [x] Reproducible manifests
- [x] Candidate and batch reports
- [ ] Benchmark run against baseline (stub complete, real pending)
- [x] Documented negative cases

### MVP is NOT ready if:
- Only pretty demos exist
- No baseline comparison
- No explicit kill criteria
- No audit trail
- Failed candidates not honestly saved

## 4. Calibration Procedure

1. Run MRM on reference set A (known stable)
2. Run MRM on set C (known unstable)
3. Measure:
   - True positive rate (stable → promote/hold)
   - True negative rate (unstable → kill)
   - Brier score for score calibration
4. Adjust weights/thresholds to optimize north-star metric

## 5. Reproducibility

Every run must log:
- Code version (skeptic_mrm.__version__)
- Config version (MRMConfig)
- Backend versions
- Random seeds
- Run manifest (JSON)

Identical config + seed + backends → identical run manifest.
