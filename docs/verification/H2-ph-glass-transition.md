# H2 Verification Note

## Candidate

`H2` — Persistent homology as predictor of glass transition behavior.

## Verification Date

2026-03-25

## Status

`partially_verified`

## Verified Findings

1. Persistent homology is already an established line of work in glass science, not a fresh import.
2. A 2022 open review explicitly summarizes recent uses of persistent homology in glass science and discusses coupling PH with machine learning.
3. A 2020 Communications Materials paper used computational homology plus machine learning to extract structural changes during glass formation across different cooling rates in metallic glass models.
4. A 2025 Nature Communications paper linked persistent-homology-derived hierarchical structure to mechanical properties in covalent amorphous solids, confirming that PH-to-property prediction in amorphous materials is already active prior art.
5. The cited 2025 Zenodo `Cu–Zr(–Al)` dataset is real and open, but it is organized around quenching conditions, stress-strain responses, and stress-drop statistics rather than a direct Tg-labeled benchmark.

## Practical Reading

### What this means

The broad claim "persistent homology as a predictor of glass transition behavior" is not defensible as a high-novelty idea by itself.

### What still appears open

A narrower candidate may survive:

- testing whether PH descriptors outperform simpler structural descriptors for predicting cooling-rate-dependent stability or deformation-related proxies in metallic glasses
- constructing a benchmark that links PH features to experimentally meaningful transition-adjacent observables instead of only descriptive topology

These remain inferences from the retrieved sources, not proven literature gaps.

## Novelty Reassessment

- Original seed framing: high novelty
- Revised assessment: low-to-medium novelty

Reason:

- Glass science already has a persistent-homology review tradition.
- PH+ML for glass-formation structure analysis is already published.
- PH-to-property work in amorphous materials is already strong and active.

## Recommended Reframe

Replace the old wording:

- "Persistent homology as predictor of glass transition behavior"

With a narrower wording:

- "Benchmarking persistent-homology descriptors against classical structural features for cooling-rate and deformation proxies in metallic glasses"

## Dataset Reassessment

### Confirmed

- The 2025 Zenodo `Cu–Zr(–Al)` metallic-glass dataset is real and open.
- It contains composition, cooling-rate variation, replicate runs, and deformation-response outputs.

### Not yet confirmed

- A clean open benchmark with direct Tg labels matched to atomistic structures
- Whether the available dataset is enough for a scientifically defensible transition-focused benchmark rather than a mechanical-response proxy task

## Next Verification Steps

1. Decide whether cooling rate, stress-drop statistics, or deformation response is an acceptable proxy target for an MVP.
2. Check whether a better open Tg-labeled dataset exists for metallic or oxide glasses.
3. Compare PH descriptors against standard handcrafted descriptors, not just against no baseline.
4. Keep `H2` in the top-5 queue only if a benchmark target can be defended as meaningful and not already saturated by prior work.

## Sources

- 2022 review: https://www.sciencedirect.com/science/article/pii/S2590159122000437
- 2020 Communications Materials: https://www.nature.com/articles/s43246-020-00100-3
- 2025 Nature Communications: https://www.nature.com/articles/s41467-025-63424-z
- 2025 Zenodo dataset: https://zenodo.org/records/17335348
- 2025/2026 related glass-topology work surfaced during search:
  https://www.sciencedirect.com/science/article/pii/S3050475925005809
