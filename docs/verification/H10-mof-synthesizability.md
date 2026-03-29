# H10 Verification Note

## Candidate

`H10` — GNN prediction of MOF synthesizability.

## Verification Date

2026-03-25

## Status

`partially_verified`

## Verified Findings

1. Synthesizability or synthetic accessibility is a real MOF bottleneck, not a fabricated problem.
2. CoRE MOF 2019 is a real and accessible structure resource, available through a maintained Python package and Zenodo-backed releases.
3. MOFSimplify provides experimentally extracted solvent-removal stability and thermal-stability labels for thousands of MOFs mapped to CoRE MOF 2019 structures.
4. A 2025 JACS paper reports machine-learning prediction of MOF free energy and uses an empirical free-energy-based synthesizability threshold with very strong reported classification performance.
5. A 2025 Nature Communications paper benchmarks CGCNN and MOFormer for MOF property prediction, confirming that graph-based models are already standard tools in MOF structure-property learning.

## Practical Reading

### What this means

The broad claim "MOF synthesizability prediction via machine learning is untouched" is not defensible.

### What still appears open

A narrower candidate remains plausible:

- benchmarking whether graph-based structural learning adds value over descriptor-based or sequence-based baselines for MOF synthesizability or stability proxies
- building a MOF-specific synthesizability benchmark that is cleaner than generic free-energy thresholds or loosely defined stability proxies

These remain inferences from the retrieved sources, not proven literature gaps.

## Novelty Reassessment

- Original seed framing: high novelty
- Revised assessment: medium novelty

Reason:

- Synthesizability prediction is already an active area in MOFs.
- Strong adjacent prior art exists with non-GNN models and with graph models for MOF property prediction.
- Direct primary-source evidence for a settled, standard MOF-specific GNN synthesizability benchmark was not confirmed in this pass.

## Recommended Reframe

Replace the old wording:

- "GNN prediction of MOF synthesizability"

With a narrower wording:

- "Benchmarking graph-based models for MOF synthesizability and stability proxies against descriptor and sequence baselines"

## Dataset Reassessment

### Confirmed

- CoRE MOF 2019 is accessible and package-backed.
- MOFSimplify offers labeled solvent-removal stability and thermal-stability datasets linked to CoRE MOF structures.

### Not yet confirmed

- A clean, community-standard "synthesizable vs nonsynthesizable" MOF benchmark with rigorous negatives
- Whether the 2025 JACS free-energy threshold setup is easily reusable as an open benchmark
- Whether existing graph-based approaches already dominate on the best available MOF synthesizability proxy tasks

## Next Verification Steps

1. Confirm whether MOFSimplify labels are the best proxy target for an MVP benchmark or whether a better synthesizability target exists.
2. Check whether the 2025 JACS dataset or code is openly reusable.
3. Build a minimal benchmark plan:
   - descriptor baseline
   - sequence/text baseline
   - graph baseline
4. Keep `H10` in the top-5 queue only if the benchmark target is scientifically defensible and not already saturated.

## Sources

- CoRE-MOF package and dataset links: https://github.com/coudertlab/CoRE-MOF
- MOFSimplify Scientific Data paper: https://www.nature.com/articles/s41597-022-01181-0
- JACS 2025 MOF free-energy / synthesizability paper summary: https://collaborate.princeton.edu/en/publications/highly-accurate-and-fast-prediction-of-mof-free-energy-via-machin/
- Nature Communications 2025 MOF multimodal ML paper: https://www.nature.com/articles/s41467-025-60796-0
