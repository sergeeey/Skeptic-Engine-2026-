# H10 Data Contract

## Related Docs

- `h10-benchmark-plan.md`
- `h10-baseline-matrix.md`
- `decision-memo-top5.md`
- `working-contract.md`

## Purpose

This document defines what must exist locally before the `H10` benchmark can move from planning to execution.

## Raw Data Principle

Do not start model training until the label route is explicit and the raw files are mapped.

The benchmark should run from a normalized mapped CSV artifact, not directly from
raw route files.

## Supported Routes

### Route 1

`mofsimplify_stability`

Expected assets:

- a structure index or mapping for CoRE-MOF entries
- one or more tables with MOFSimplify-derived stability labels
- a join key that can be matched reproducibly across structures and labels

### Route 2

`free_energy_threshold`

Expected assets:

- a structure list
- a table with free-energy-derived synthesizability proxy labels or thresholds
- documentation describing how the threshold was defined

## Mandatory Questions

Before any benchmark run, answer all of these:

1. What is the exact prediction target?
2. Is it binary, ordinal, or continuous?
3. What is the join key between structures and labels?
4. How many usable rows remain after filtering?
5. What is the baseline class balance?
6. What is the train/validation/test split policy?

## No-Claim Rule

The project must not claim:

- synthesizability prediction
- graph superiority
- scientific novelty

until the raw data contract is satisfied and baselines are run on identical splits.
