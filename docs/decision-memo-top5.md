# Top-5 Decision Memo

## Related Docs

- `working-contract.md`
- `research-contract.md`
- `h10-benchmark-plan.md`
- `h10-benchmark-conclusion.md`

## Date

2026-03-26

## Purpose

Convert the original report-driven `top-5` queue into an evidence-aware working order for MVP execution, then update it after the first family-specific skeptic pass.

## Decision Standard

Candidates are ranked by:

1. surviving novelty after prior-art review
2. data readiness
3. Python-first tractability
4. falsifiability
5. expected value for the project

## Result

### 1. H10

`Graph-based benchmarking for MOF synthesizability and stability proxies`

Why it moves to the top:

- the problem is real
- structure resources are real
- proxy labels are available
- implementation path is already materially built
- family-specific skeptic did not add a strong downgrade
- even if novelty is moderate, it is still the strongest executable benchmark on the board

### 2. H4

`TDA for early detection of resistant-state transitions in cancer single-cell data`

Why it stays high:

- biologically meaningful target
- computationally testable
- potentially high upside
- family-specific skeptic did not materially weaken it

Why it is not first:

- benchmark route is now clearer, but the project still has to choose between a fast open resistance-state benchmark and a stronger patient-derived route
- prior art already exists in oncology TDA

Current route choice:

- `GSE164897` is now the preferred fast executable benchmark route
- `GSE120575` and `scCT-DB` remain the patient-derived follow-up routes

### 3. H20

`Early-warning PH predictor of SOC electrode degradation trajectories`

Why it remains viable:

- good materials-science target
- accessible topology toolchain
- plausible engineering value
- family-specific skeptic did not materially weaken it further

Why it drops:

- prior art is already significant
- novelty survives only in a narrow longitudinal early-warning framing

### 4. H1

`Koopman-style slow-mode analysis for LLPS-relevant IDP trajectory data`

Why it remains interesting:

- conceptually strong
- some possible novelty survives

Why it is not execution-ready:

- no confirmed open LLPS trajectory benchmark yet
- current seed datasets are a poor fit
- family-specific skeptic added another downgrade, so this is now a weaker hold than before

### 5. H2

`Benchmarking persistent-homology descriptors for metallic-glass transition and deformation proxies`

Why it remains on the board:

- easy open-data route
- good baseline-comparison problem

Why it moves down:

- novelty is already low-to-medium
- strongest framing is benchmark-oriented rather than discovery-oriented
- family-specific skeptic added another downgrade

## 2026-03-26 Skeptic Update

The new `skeptic-top5` pass did not change the working order of the top three tracks, but it did change how the bottom of the board should be interpreted.

What changed:

- `H10` remains the lead because execution evidence is now much stronger than the rest of the board.
- `H4` remains second because the main blocker is now benchmark route selection, not novelty collapse.
- `H20` remains third in a narrow longitudinal framing.
- `H1` and `H2` both received family-specific skeptic downgrades and should now be treated as weaker reserve tracks, not near-term promotion candidates.

## 2026-03-26 H10 Baseline Update

The first trainable graph-path baseline for `H10` is now complete.

What it means:

- `H10` remains the execution lead because it has the strongest evidence package in the repository.
- The graph route is now real, not hypothetical.
- But the current graph-path baseline does not beat the strongest descriptor baseline, so the graph-advantage claim is still unproven.

Practical consequence:

- the next `H10` decision is no longer "can we train a graph baseline?"
- it is "do we invest in a true message-passing model, or do we accept a benchmark framing where descriptor models remain stronger?"

## 2026-03-26 H10 MPNN Update

The current true message-passing graph baseline for `H10` is now complete.

What it means:

- the project-local environment issue blocking `torch` use has been worked around by importing `torch` before `sklearn`
- a real MPNN has now been trained on the fixed split with distance-aware message features
- the best message-passing test result so far is still `graph_mpnn_v2`
- a chemistry-aware follow-up `graph_mpnn_v3` improved validation metrics but did not improve the primary test metric `average_precision`
- the message-passing route is still weaker than both `descriptor_hgb_v1` and `graph_structural_hgb_v1`

Practical consequence:

- `H10` still remains the lead benchmark track because the evidence package is strongest
- but the specific claim "graph models should win here" is now weaker than before
- the honest default framing is shifting further toward benchmark comparison rather than graph superiority

## 2026-03-26 H10 Hybrid Update

The first descriptor-plus-graph comparison baseline for `H10` is now complete.

What it means:

- the merged `descriptor + graph-structural` stack improves over pure descriptor HGB on `ROC-AUC` and `balanced_accuracy`
- but it still does not beat `descriptor_hgb_v1` on the primary metric `average_precision`
- this is useful evidence that graph signal is not empty, but it is still not enough to justify a graph-win claim

Practical consequence:

- `H10` is now even more clearly a benchmark-comparison track
- the next graph step should only happen if there is a sharply justified architecture or feature hypothesis
- otherwise the right output is a clean comparison result: descriptor strongest on AP, hybrid stronger on some secondary metrics, message passing still behind

What did not change:

- the board should still optimize for executable evidence, not abstract discovery score alone
- `H10` is still the right MVP lead because it has the most honest path to a real benchmark result

## Working Recommendation

### MVP primary track

- Keep `H10` as the primary completed benchmark-comparison track and package its current conclusion cleanly

### Secondary verification track

- lock the first `H4` benchmark route and start scaffold planning
- continue novelty-gap verification for `H20`

### Hold

- `H1` until a real LLPS trajectory dataset is identified and the novelty pressure improves
- `H2` as fallback benchmark work only if the proxy target remains defensible after another review pass

## Execution Order

1. Freeze `H10` as a benchmark-comparison result unless a sharply justified new graph hypothesis appears
2. In parallel, build the first `H4` benchmark scaffold around `GSE164897`
3. Reassess whether `H20` still deserves top-5 placement after longitudinal-gap review
4. Only if `H10` weakens materially, reopen the race between `H4` and `H20`

## Conclusion

The most honest and executable lead candidate is currently `H10`.

It is not the most romantic hypothesis.
It is the strongest first project for building real evidence, and the first family-specific skeptic pass did not overturn that.
