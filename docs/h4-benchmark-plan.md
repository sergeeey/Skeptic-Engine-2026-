# H4 Benchmark Plan

## Related Docs

- `h4-dataset-decision.md`
- `verification/H4-tda-cancer-resistance.md`
- `decision-memo-top5.md`
- `working-contract.md`

## Candidate

`H4` — TDA for early detection of resistant-state transitions in cancer single-cell data

## Goal

Build a reproducible single-cell benchmark that tests whether TDA-derived features improve resistance-state detection beyond standard embedding, clustering, or trajectory baselines.

## Default Route

`GSE164897` melanoma targeted-therapy resistance-state benchmark

Why this route is first:

- open and directly reusable
- explicitly structured around resistant states
- fast enough for an executable MVP

## Phase-2 Routes

- `GSE120575` for patient-derived melanoma immunotherapy response
- `scCT-DB` for a broader patient-derived longitudinal search layer

## Benchmark Question

Can TDA features provide measurable value over simpler single-cell state-space baselines on a defensible resistance-related label?

## Planned Baseline Families

### Standard single-cell baseline

- PCA or UMAP embeddings
- clustering or simple state classifiers

### Trajectory baseline

- pseudotime
- transition or progression summaries from standard workflows

### TDA baseline

- persistence-derived features over the single-cell state geometry
- topological summaries designed to capture resistant-state transition structure

## Immediate Build Scope

1. Fix the exact `GSE164897` label definition.
2. Write the H4 dataset card and execution plan from the benchmark spec.
3. Delay ingestion and modeling code until the label contract and split policy are explicit.

## Success Standard

`H4` only survives as a serious execution track if the benchmark makes it possible to answer a clean question:

`Does TDA add signal beyond standard single-cell baselines for resistance-state detection?`
