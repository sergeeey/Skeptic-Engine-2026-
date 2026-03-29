# Documentation Map

## Start Here

1. `project-brief.md` — **two-branch strategy**, success criteria, kill criteria
2. `working-contract.md` — day-to-day execution rules
3. `research-contract.md` — scientific integrity and promotion gates

## Branch 2: Data Integrity (PRIMARY)

Experiment results and analysis are in `experiments/` directory, not in docs.

- `../REPORT.md` — full research report covering H24, H25, H23
- `../experiments/h24_benford_scrna/paper_outline.md` — H24 paper outline
- `../experiments/h24_benford_scrna/collaboration_pitch.md` — co-author strategy
- `toolkit_mvp.md` — H24-inspired fabrication risk scanner CLI

## Branch 1: Discovery Lab (SUPPORTING)

### Decision and Prioritization

- `decision-memo-top5.md` — ranked execution order for hypothesis candidates
- `domain-seed-notes.md` — early domain framing
- `report-ingestion-notes.md` — how report-derived seeds were interpreted

### H10 MOF Benchmark (COMPLETE)

- `h10-benchmark-plan.md` — benchmark framing
- `h10-data-contract.md` — raw-to-mapped data requirements
- `h10-benchmark-conclusion.md` — final benchmark verdict
- `h10-result-memo.md` — result abstract and narrative
- `h10-baseline-matrix.md` — split policy, baseline readiness
- `h10-descriptor-baseline.md` — LogReg descriptor baseline
- `h10-descriptor-tree-baseline.md` — HGB descriptor baseline
- `h10-graph-artifact.md` — graph-ready CoRE-MOF artifact
- `h10-graph-baseline.md` — first graph baseline
- `h10-graph-mpnn-baseline.md` — MPNN graph baseline
- `h10-hybrid-baseline.md` — descriptor+graph comparison

### H4 TDA Cancer Resistance (PENDING)

- `h4-dataset-decision.md` — dataset route choice
- `h4-benchmark-plan.md` — scaffold plan
- `h4-data-contract.md` — required contract fields for GSE164897
- `h4-audit-report.md` — audit-ready metadata summary for the default route

### Verification

- `verification/` — candidate-specific review and prior-art notes
- `verification/skeptic-latest.md` — latest automated prior-art pressure test
- `verification/top5-skeptic-latest.md` — top-5 family skeptic pass

### Other

- `source-manifest-spec.md` — source manifest format
- `mvp-roadmap.md` — staged build plan (original, predates two-branch split)
- `working-contract.md` — execution contract (shared)

## Reading Order for New Session

1. `project-brief.md` (understand the two branches)
2. `../REPORT.md` (see all validated results)
3. `working-contract.md` (execution rules)
4. Then dive into whichever branch is active
