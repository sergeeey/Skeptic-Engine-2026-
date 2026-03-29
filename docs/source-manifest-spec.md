# Source Manifest Spec

This project uses JSON manifests for curated source intake.

## Required fields

- `id`
- `title`
- `domain`
- `source_type`

## Optional fields

- `abstract`
- `claims`
- `methods`
- `mechanisms`
- `open_questions`
- `bridge_tags`
- `limitations`
- `authority_score`
- `bias_index`
- `novelty_factor`
- `citations`
- `metadata`

## Rules

- Scores must stay in the `0.0` to `1.0` range.
- `metadata` should only contain strings.
- `bridge_tags` should be short normalized phrases that help connect domains.
- Source manifests may contain internal seed notes, but those must not be treated as external scientific proof.
- Local files should be referenced via metadata such as `local_path`.

## Current Intake Policy

Until external retrieval is added, manifests are curated manually and treated as the trusted input surface for acquisition.
