# H10 Benchmark Plan

## Related Docs

- `decision-memo-top5.md`
- `h10-data-contract.md`
- `h10-baseline-matrix.md`
- `h10-benchmark-conclusion.md`
- `working-contract.md`

## Candidate

`H10` — Graph-based benchmarking for MOF synthesizability and stability proxies

## Goal

Build a reproducible benchmark scaffold that compares:

- descriptor baseline
- sequence or text-like baseline
- graph baseline

on a defensible MOF synthesizability or stability-proxy task.

## MVP Position

This is a benchmark-first project, not yet a discovery claim.

The immediate objective is to prove or disprove:

- whether graph structure adds measurable value over simpler baselines
- whether the target label is scientifically defensible

## Candidate Label Routes

### Route A

`MOFSimplify` solvent-removal stability labels

Why useful:

- real experimental provenance
- linked to CoRE-MOF structures
- likely easiest open route for MVP

Main caveat:

- stability is only a proxy for broader synthesizability

### Route B

Free-energy-based synthesizability threshold

Why useful:

- closer to an explicit synthesizability framing

Main caveat:

- may be harder to reproduce or reuse openly
- threshold may encode prior modeling assumptions

## Benchmark Families

### Descriptor baseline

- simple handcrafted structural descriptors
- composition statistics
- porosity or geometric summary features when available

### Sequence or text-like baseline

- canonicalized formula or tokenized linker/metal descriptors
- bag-of-tokens or simple embedding baseline

### Graph baseline

- graph representation of MOF structure
- start with a graph-ready schema even if the first MVP uses placeholder extraction

## Minimum Artifact Set

- benchmark spec
- dataset card
- label card
- split plan
- baseline matrix
- evaluation protocol

## Success Criteria

The H10 scaffold is useful only if it makes these decisions explicit:

1. what the target actually is
2. what counts as a fair baseline
3. what metrics matter
4. what would falsify the graph advantage claim

## Current Status

The original scaffolding goals in this plan are now materially complete for the `MOFSimplify` route.

The live project question is no longer how to start the benchmark, but how to state its current conclusion honestly.

See `h10-benchmark-conclusion.md` for the current verdict.
