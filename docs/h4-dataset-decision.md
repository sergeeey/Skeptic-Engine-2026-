# H4 Dataset Decision

## Date

2026-03-26

## Related Docs

- `verification/H4-tda-cancer-resistance.md`
- `decision-memo-top5.md`
- `working-contract.md`

## Candidate

`H4` — TDA for early detection of resistant-state transitions in cancer single-cell data

## Decision

Use `GSE164897` as the first executable benchmark route for `H4`.

Keep `GSE120575` and `scCT-DB` as phase-2 patient-derived follow-up routes.

## Why This Is The Right First Route

- it is open and directly reusable
- it has explicit treatment-state structure rather than only broad cohort metadata
- it is aligned with the narrowed H4 question: resistant-state transitions
- it supports a fast Python-first benchmark path

## Why Not Start With The Patient Route

`GSE120575` is scientifically attractive because it is patient-derived and clinically meaningful, but it is a responder/non-responder benchmark rather than a clean transition benchmark.

`scCT-DB` is even broader and more powerful as a search layer, but it is not a single benchmark by itself and still requires choosing and ingesting one concrete dataset.

## Route Assignment

### Phase 1

- dataset: `GSE164897`
- role: fast executable benchmark
- framing: melanoma targeted-therapy resistance-state detection

### Phase 2

- dataset: `GSE120575`
- role: patient-derived response benchmark
- framing: melanoma checkpoint-immunotherapy response / resistance

### Phase 3

- dataset layer: `scCT-DB`
- role: broader search space for stronger patient-derived longitudinal benchmarks

## Practical Consequence

The H4 blocker is no longer dataset existence.

The new H4 task is:

`Build the first benchmark scaffold around GSE164897 and test whether TDA features add value beyond standard single-cell baselines.`

## Recommended Next Step

1. Define the exact benchmark target for `GSE164897`.
2. Decide what counts as the baseline family:
   - PCA / UMAP + clustering
   - pseudotime
   - velocity-style transition summaries when feasible
3. Build an H4 dataset card and benchmark plan around this route.
