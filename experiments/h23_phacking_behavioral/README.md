# H23 — Behavioral P-Hacking Detection

## Structure

H23 has two tracks with different evidence strength:

### H23-main (supervised / quasi-supervised — primary evidence)

Uses datasets with known labels or quasi-labels:

| Dataset | n | Label | Best AUC | Script |
|---------|---|-------|---------|--------|
| Simulated p-hacking | 1000 | Controlled simulation | 0.993 | run_h23.py |
| RPP (Reproducibility Project) | 99 | Replication outcome | 0.729 | run_h23_real.py |
| Statcheck meta-analyses | 61 | Statcheck error flag | 0.765 | run_h23_statcheck.py |

### H23-pmc (unsupervised + quasi-supervised — supporting evidence)

Extracts p-values from live PMC articles using statcheck_python.
Quasi-label: statcheck Error flag (reported p ≠ recomputed p).

| Dataset | n | Label | Script |
|---------|---|-------|--------|
| PMC regex extraction | 28 | Unsupervised (IF anomaly) | run_h23_extract.py |
| PMC statcheck extraction | TBD | Quasi-supervised (Error flag) | run_h23_pmc_statcheck.py |

## What H23 proves

- Behavioral features (volatility, threshold clustering, sequence dynamics) consistently beat single-feature baselines by +7.5 to +28.7 pp AUC across all labeled datasets
- The improvement holds on both simulated and real data

## What H23 does NOT prove

- That flagged articles are actually p-hacked (quasi-labels are reporting errors, not confirmed p-hacking)
- That the method generalizes to all scientific fields (tested on psychology only)
- That PMC extraction constitutes ground truth

## Honest framing for paper

Claim: "Behavioral features can screen articles for statistical reporting anomalies"
NOT: "We detect p-hacking with ground truth labels"

## Missing for stronger evidence

- Nuijten 688k dataset (BLOCKED — DANS link rot, status: UNKNOWN)
- Larger labeled replication dataset (Many Labs 2, SCORE project)
- Cross-field validation (not just psychology)
