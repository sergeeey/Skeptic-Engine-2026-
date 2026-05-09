# Release Checklist - v0.2.0

Release status is fail-closed. A release is `READY` only when every required gate below has current passing evidence.

## Current Verdict

`READY FOR LOCAL PACKAGE RELEASE`

Public/external release remains gated on manual `.env` and artifact secret review. Automated local gates now pass: pytest, ruff, mypy, governance checks, package build, twine check, CLI smoke, and MRM smoke.

## Required Release Gates

| Gate | Command | Current status | Evidence |
|---|---|---|---|
| Project canon exists | `Test-Path PROJECT_CANON.md` | PASS | Canon file added |
| Claim contract validates | `python scripts/validate_publication_claims.py` | PASS | `PUBLICATION CLAIMS PASSED.` |
| Red-flag scan | `python scripts/check_redflags.py` | PASS with warnings | 0 errors, 1 warning: local `.env` exists |
| Unit tests | `pytest -q` | PASS | Latest observed: 349 passed, 1 warning |
| Ruff | `ruff check src tests scripts` | PASS | `All checks passed!` |
| Mypy | `mypy src` | PASS | `Success: no issues found in 94 source files` |
| Package build | `python -m build` | PASS | Wheel + sdist built without setuptools license deprecation warnings |
| Twine check | `twine check dist/*` | PASS | Existing v0.1.1 and v0.2.0 artifacts passed |
| CLI smoke | `skeptic-toolkit --help`; `skeptic-mrm --help` | PASS | Both commands print help |
| MRM smoke | `python experiments/mrm_bench_v01/run_smoke_test.py` | PASS | 2 candidates processed; both held |
| Secret scan | `python scripts/check_redflags.py` plus manual `.env` review | PARTIAL | `.env` is ignored by Git, but local contents still require manual review before any public release |

## Package Metadata

| Item | Expected | Current status |
|---|---|---|
| `pyproject.toml` version | `0.2.0` | Covered by claim matrix |
| `src/skeptic_toolkit/__init__.py` version | `0.2.0` | Covered by claim matrix |
| `src/skeptic_mrm/__init__.py` version | `0.2.0` | Covered by claim matrix |
| Changelog entry | present | NOT VERIFIED |

## Public Claim Gates

Before release-facing text changes are promoted:

1. Update `PROJECT_CANON.md` if the public identity changes.
2. Add or update evidence in `claims/artifact_inventory.v0.2.0.json`.
3. Add or update field-level checks in `claims/publication_claim_matrix.v0.2.0.json`.
4. Run `python scripts/validate_publication_claims.py`.
5. Run `python scripts/check_redflags.py`.

## External Release Actions

These require all gates above to be green first:

- PyPI upload
- Zenodo v0.2 upload
- bioRxiv/preprint submission
- Git tag and GitHub release
- Outreach using release claims

## Notes

- `302 adversarial tests` and `349 pytest tests` are different claim types. Do not collapse them into one "tests passing" statement.
- Perfect metrics such as `AUC 1.000` and `F1 1.000` require synthetic/limited-scope caveats.
- `validated` must be scoped: real-data, synthetic-only, within-dataset, or underpowered.
