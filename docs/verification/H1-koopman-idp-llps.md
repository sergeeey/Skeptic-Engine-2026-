# H1 Verification Note

## Candidate

`H1` — Koopman spectral fingerprints of IDP phase separation.

## Verification Date

2026-03-25

## Status

`partially_verified`

## Verified Findings

1. IDP / LLPS dynamics is a real and active scientific area, not a fabricated target.
2. Koopman-style and variational molecular-kinetics methods are real and well established for extracting slow collective variables from molecular dynamics trajectories.
3. The retrieved sources did not confirm a direct, standard prior-art line applying Koopman operator methods specifically to LLPS dynamics of intrinsically disordered proteins.
4. The seed report's proposed datasets are a weak fit for the actual task:
   - `MISATO` is a protein-ligand MD dataset for structure-based drug discovery, not an LLPS-focused condensate dynamics benchmark.
   - `OpenProteinSet` is a large structural-biology training corpus centered on sequence/MSA coverage, not LLPS dynamics.
   - `AlphaFold DB` provides predicted structures, not the time-resolved condensate trajectories needed for Koopman slow-mode analysis.

## Practical Reading

### What this means

The conceptual bridge "Koopman methods for LLPS/IDP slow dynamics" remains interesting.

However, the current data route from the seed report is not defensible.

### What still appears open

A narrower candidate may survive:

- applying Koopman-style slow-mode analysis to actual LLPS-relevant MD trajectories or experimentally informed condensate simulations for IDPs

This remains an inference from the retrieved sources, not a proven literature gap.

## Novelty Reassessment

- Original seed framing: high novelty
- Revised assessment: medium novelty, low readiness

Reason:

- The method side is mature.
- The biology target is real.
- But the benchmark route is currently weak because the cited datasets do not match the required dynamics task.

## Recommended Reframe

Replace the old wording:

- "Koopman spectral fingerprints of IDP phase separation"

With a narrower wording:

- "Koopman-style slow-mode analysis for LLPS-relevant IDP trajectory data"

## Dataset Reassessment

### Confirmed

- MISATO, OpenProteinSet, and AlphaFold DB are real datasets/resources.

### Not yet confirmed

- A clean open benchmark of LLPS-relevant IDP trajectories suitable for Koopman / MSM / VAMP-style analysis
- Whether an openly reusable condensate-simulation dataset exists with enough temporal depth and task relevance

## Next Verification Steps

1. Search for genuine LLPS trajectory datasets or open condensate MD benchmarks instead of general protein datasets.
2. Check whether published LLPS MD studies expose reusable trajectories or only figures and summary statistics.
3. Keep `H1` in the top-5 queue only if a defensible data route is found.

## Sources

- Koopman / variational molecular kinetics background: https://arxiv.org/abs/1610.06773
- MISATO dataset paper: https://www.nature.com/articles/s43588-024-00627-2
- OpenProteinSet dataset paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC10441447/
- AlphaFold DB 2024 paper: https://academic.oup.com/nar/advance-article-abstract/doi/10.1093/nar/gkad1011/7337620
- Example LLPS / IDP dynamics study: https://pubs.acs.org/doi/10.1021/jacs.2c13647
