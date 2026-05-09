# ARCHCODE Governance Lessons For Skeptic Engine

ARCHCODE should inform Skeptic Engine governance, not become a runtime dependency.

## Transferable Patterns

- Canonical claim layers: public, technical, legacy.
- Machine-checkable claim matrix mapping prose claims to structured artifacts.
- Fail-closed release gates.
- Red-flag scans for overclaiming, stale metrics, and synthetic-data ambiguity.
- Falsification suites that compare against simple baselines and negative controls.
- Decision records for PASS, PARTIAL, FAIL, and KILL outcomes.

## Non-Transferable Parts

- ARCHCODE biology-specific runtime code.
- AlphaGenome-specific validator assumptions.
- Chromatin/variant result artifacts.
- `ag-falsifier` as a package dependency.

## Local Adaptation

Skeptic Engine should implement its own claim validator over existing artifacts under:

- `experiments/**/results/*.json`
- `experiments/bootstrap_results/*.json`
- package metadata files
- release and manuscript surfaces

The immediate goal is governance discipline: canon, inventory, claim matrix, validator, red flags, and release gates.
