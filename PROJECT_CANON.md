# Skeptic Engine Canon

Canonical routing and claim policy for Skeptic Engine release-facing material.

## Positioning

Skeptic Engine is an adversarial statistical artifact detection framework for scientific data integrity screening.

It is:

- a research toolkit for detecting statistical artifacts and structural anomalies
- a falsification-first validation framework for scientific datasets
- a source of interpretable screening signals for expert review

It is not:

- a fraud accusation tool
- a clinical or editorial decision system
- a universal detector validated across all datasets and modalities
- a Nobel-ready discovery claim

## Public Canonical Layer

Audience:

- reviewers
- collaborators
- release readers
- users evaluating the current package

Purpose:

- the narrowest defensible current project identity

Allowed default framing:

- "scientific data integrity screening"
- "statistical artifact and anomaly detection"
- "flags requiring expert review"
- "falsification-first research toolkit"

Primary public claims must route through:

- `claims/publication_canonical_index.v0.2.0.json`
- `claims/publication_claim_matrix.v0.2.0.json`
- `scripts/validate_publication_claims.py`

Active public surfaces:

- `README.md`
- `REPORT.md`
- `RELEASE_CHECKLIST.md`
- `manuscript/manuscript.tex`
- `manuscript/PREPRINT_v01.md`
- `manuscript/PREPRINT_STRUCTURE.md`

## Technical Layer

Audience:

- technical collaborators
- maintainers
- readers inspecting the research program in detail

Allowed content:

- H23-H38 experiment details
- synthetic fabrication benchmarks
- calibration and debate experiments
- MRM materials reliability module
- discovery-engine infrastructure
- failed experiments and honest negatives

Rules:

- synthetic-only results must be labeled as synthetic or simulated
- perfect metrics such as `AUC 1.000` or `F1 1.000` must carry scope caveats
- underpowered real-data findings must remain suggestive unless confidence intervals exclude random
- MRM claims must disclose stub/fallback backends unless a real backend artifact is cited

## Legacy And Supporting Layer

Audience:

- provenance and historical continuity

Content:

- original Nobel-oriented interdisciplinary discovery framing
- early top-5 hypothesis generation
- deprioritized materials-science benchmarks
- superseded preprint drafts and exploratory notes

Rules:

- legacy/supporting material must not become the default public identity
- Nobel framing must stay historical or aspirational, never evidentiary
- old claims must be retired or mapped to current evidence before reuse

## Banned Or Restricted Public Claims

The following claims are not allowed on release-facing surfaces unless the claim matrix explicitly verifies them and supplies required caveats:

- "fraud detector" or equivalent intent attribution
- "proves fraud" or "detects misconduct"
- "universal detector"
- "generalizes across datasets" where cross-generalization failures are documented
- "validated" for synthetic-only results without saying synthetic-only
- "READY FOR PUBLISHING" unless all release gates are green in the current run
- "ruff + mypy green" unless the current commands have passed
- "tests passing" without distinguishing pytest tests from adversarial/scientific tests
- "Nobel-ready", "Nobel-class proven", or equivalent award claims

## Claim Promotion Gate

Before promoting any public claim:

1. Identify the public surface and exact claim text.
2. Add or identify a structured evidence artifact.
3. Add the artifact to `claims/publication_canonical_index.v0.2.0.json`.
4. Add a field-level mapping to `claims/publication_claim_matrix.v0.2.0.json`.
5. Run `python scripts/validate_publication_claims.py`.
6. Run `python scripts/check_redflags.py`.
7. Record verification status in `RELEASE_CHECKLIST.md` or a task report.

If a claim cannot pass these steps, it remains `UNVERIFIED`, `PARTIAL`, or `RETIRED`.
