# SE-MRM Data Contract

## Entity: MaterialCandidate

| Field | Type | Required | Description |
|---|---|---|---|
| candidate_id | str | Yes | Unique identifier (auto-generated if missing) |
| source | str | Yes | "mattergen", "materials_project", "cif_upload", etc. |
| composition | str | Yes | Chemical formula (e.g. "LiFePO4") |
| structure_format | str | Yes | "cif", "poscar", "json", "mp_id" |
| structure_blob | str | Yes | Raw structure data or reference |
| generator_version | str\|None | No | Version of the generator model |
| generator_seed | int\|None | No | Random seed used for generation |
| target_properties | dict | No | Target property constraints |
| novelty_context | dict | No | Nearest neighbors, distance metric |
| created_at | str | No | ISO 8601 timestamp |
| provenance_hash | str | Auto | SHA-256 hash of key fields (first 16 chars) |

## Entity: SimulationRun

| Field | Type | Required | Description |
|---|---|---|---|
| run_id | str | Yes | Unique run identifier |
| candidate_id | str | Yes | Reference to MaterialCandidate |
| backend | str | Yes | "mattersim", "jaxmd", "dft_hook" |
| tier | int | Yes | 0=heuristic, 1=ML, 2=expensive |
| config_version | str | Yes | Backend config version |
| status | str | Yes | "completed", "failed", "timeout", "diverged" |
| metrics | dict | No | Numerical results |
| artifacts | dict | No | URIs to trajectory/log files |

## Entity: FailureAttack

| Field | Type | Required | Description |
|---|---|---|---|
| attack_id | str | Yes | Unique attack identifier |
| candidate_id | str | Yes | Reference to MaterialCandidate |
| attack_type | str | Yes | Type of attack (see taxonomy) |
| params | dict | No | Attack configuration |
| collapsed | bool | No | Whether structure collapsed |
| property_drop | float | No | Fractional property degradation |
| stress_hotspots_detected | bool | No | Whether hotspots were found |
| details | dict | No | Additional attack-specific data |

## Entity: ReliabilityDecision

| Field | Type | Required | Description |
|---|---|---|---|
| decision_id | str | Yes | Unique decision identifier |
| candidate_id | str | Yes | Reference to MaterialCandidate |
| final_score | float | Yes | Composite reliability score [0, 1] |
| status | str | Yes | "promote", "hold", "kill" |
| sub_scores | dict | No | Individual score components |
| reasons | list[str] | No | Decision rationale |
| review_required | bool | No | Whether human review is needed |

## Input Formats

### CIF (.cif)
- Standard Crystallographic Information File
- Must contain at least `_cell_length` or lattice parameters
- Composition extracted from `_chemical_formula_sum`

### POSCAR (.vasp, .poscar)
- VASP structure file
- Must have ≥4 non-empty lines
- Composition from first line (comment)

### JSON / JSONL (.json, .jsonl)
- Array of MaterialCandidate dicts (JSON)
- One dict per line (JSONL)
- Required: candidate_id, source, composition, structure_format, structure_blob

### MP-ID (via API)
- Materials Project identifier string
- Actual data fetched via mp-api (deferred to backend)

## Validation Rules

1. Composition must match chemical formula pattern
2. Structure must pass format-specific sanity checks
3. Duplicate candidates (same fingerprint) are deduplicated
4. Missing fields get defaults or auto-generated values

## Storage

- Metadata: SQLite database (mrm.db) or JSON files
- Artifacts: Local filesystem or S3 (configurable)
- Run manifests: JSON with full provenance
