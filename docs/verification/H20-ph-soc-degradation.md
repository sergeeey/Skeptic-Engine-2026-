# H20 Verification Note

## Candidate

`H20` — Persistent-homology-based predictor of solid oxide cell electrode degradation.

## Verification Date

2026-03-25

## Status

`partially_verified`

## Verified Findings

1. A 2023 open-access paper directly applied persistent homology to the microstructure evolution of solid oxide fuel cell anodes before and after aging.
2. A 2025 open-access paper used persistence-image representations plus neural networks to predict SOC electrode polarization curves from microstructure.
3. A 2026 open-access paper used persistent homology with deep learning to predict eight SOC microstructural parameters from synthetic 3D microstructures.
4. At least one open Zenodo dataset exists for a 3D SOC fuel-electrode microstructure, and the 2025 topology-informed ML paper also exposes a Zenodo record with microstructures, persistence diagrams, and a trained model.

## Practical Reading

### What this means

The broad claim "persistent homology for SOC degradation/prediction is untouched" is no longer defensible.

### What still appears open

The narrower claim still looks plausible:

- using early or initial topological signatures to predict later degradation trajectories or failure metrics in a longitudinal setting

This remains an inference from the retrieved sources, not a proven literature gap.

## Novelty Reassessment

- Original seed framing: high novelty
- Revised assessment: medium novelty

Reason:

- SOC + PH is already established for degradation characterization and for related predictive tasks.
- The candidate remains interesting only if reframed around longitudinal early-warning prediction or explicit failure forecasting.

## Recommended Reframe

Replace the old wording:

- "PH predictor of SOC degradation"

With a narrower wording:

- "Early-warning prediction of SOC degradation trajectories from initial persistent-homology signatures"

## Next Verification Steps

1. Verify whether the 2025 Zenodo dataset contains time-separated or only simulated static microstructures.
2. Verify whether any paper already predicts long-term degradation or failure metrics from early PH descriptors.
3. Confirm a benchmark target such as TPB loss, coarsening metric, polarization drift, or remaining useful life.
4. Only keep `H20` in the top-5 queue if the longitudinal prediction gap survives prior-art review.

## Sources

- 2023 Energy and AI: https://www.sciencedirect.com/science/article/pii/S2666546823000289
- 2025 Energy and AI: https://www.sciencedirect.com/science/article/pii/S2666546825000278
- 2025 Zenodo dataset for the 2025 paper: https://zenodo.org/records/13731825
- 2026 Journal of Power Sources: https://www.sciencedirect.com/science/article/pii/S0378775325027119
- 2018 Zenodo SOC tomography dataset: https://zenodo.org/records/1040274
