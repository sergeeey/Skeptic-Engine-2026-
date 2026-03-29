# H10 Graph Artifact

- dataset: `2019-ASR`
- source package: `CoRE_MOF`
- artifact: `data\benchmarks\h10_graphs\mofsimplify_asr_graphs.jsonl.gz`
- summary: `data\benchmarks\h10_graphs\mofsimplify_asr_graph_summary.json`
- rows requested: `2179`
- rows built: `2179`
- failures: `0`
- average nodes: `281.43`
- average edges: `291.18`
- max nodes: `5576`
- max edges: `5440`

## What The Artifact Contains

Each JSONL record includes:

- `structure_id`
- `core_mof_id`
- `split`
- `target_name`
- `target_value`
- `formula`
- `num_nodes`
- `num_edges`
- `lattice_matrix`
- `atomic_numbers`
- `frac_coords`
- undirected `edges`

## Construction Rule

The graph is built from the `CoRE_MOF` `2019-ASR` structure matching each
`structure_id` in the mapped `H10` route.

Neighborhood construction uses `MinimumDistanceNN` through `pymatgen`.

## Current Meaning

This artifact makes the graph path reproducible and input-ready.

It does not yet mean that a graph model has been trained or benchmarked.

## Related Docs

- `h10-baseline-matrix.md`
- `h10-benchmark-plan.md`
- `h10-descriptor-baseline.md`
- `h10-descriptor-tree-baseline.md`
