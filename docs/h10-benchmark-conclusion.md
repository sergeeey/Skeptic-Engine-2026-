# H10 Benchmark Conclusion

## Date

2026-03-26

## Related Docs

- `h10-benchmark-plan.md`
- `h10-baseline-matrix.md`
- `h10-result-memo.md`
- `h10-descriptor-tree-baseline.md`
- `h10-graph-baseline.md`
- `h10-graph-mpnn-baseline.md`
- `h10-hybrid-baseline.md`

## Verdict

`H10` should currently be framed as a reproducible benchmark-comparison result, not as a graph-win result.

This conclusion is now supported by a fixed split, multiple trained baseline families, and direct comparison on the same proxy target.

## Task

- candidate: `H10`
- title: `Graph-based benchmarking for MOF synthesizability and stability proxies`
- current target: `solvent_removal_stability_binary`
- dataset rows: `2179`
- split: `train=1394`, `val=349`, `test=436`
- primary metric: `average_precision`

## Best Observed Results

| Model | Family | Test AP | Test ROC-AUC | Test Balanced Accuracy |
|---|---|---:|---:|---:|
| `descriptor_hgb_v1` | descriptor | `0.873903` | `0.826238` | `0.739742` |
| `hybrid_hgb_v1` | descriptor + graph-structural | `0.862236` | `0.834634` | `0.751918` |
| `graph_structural_hgb_v1` | graph-structural | `0.834278` | `0.797952` | `0.725214` |
| `descriptor_logreg_v1` | descriptor linear | `0.752156` | `0.674191` | `0.604772` |
| `graph_mpnn_v2` | message passing | `0.736903` | `0.672960` | `0.619431` |
| `graph_mpnn_v3` | message passing | `0.731329` | `0.676191` | `0.608321` |

## What Is Now Supported

- The `H10` route is executable and reproducible.
- The `MOFSimplify` solvent-removal stability proxy is usable as a benchmark target.
- Graph-derived information is not empty:
  - graph-structural features produce a strong baseline
  - the hybrid model improves some secondary metrics over pure descriptor HGB
- The benchmark can already support a real comparison-style result.

## What Is Not Supported

- The claim that graph models win on this task is not supported.
- The claim that message-passing is the best route for this target is not supported.
- The claim that graph signal is necessary for the strongest result is not supported.

## Honest Interpretation

The strongest current model on the primary metric is still the descriptor HGB baseline.

Graph information helps as a comparison layer and may improve some secondary metrics, but it does not currently overturn the main result. The clean scientific output is therefore:

- descriptor baseline is strongest on `average_precision`
- hybrid baseline is competitive and stronger on some secondary metrics
- pure graph and current message-passing routes are weaker

## Benchmark Conclusion

The current benchmark falsifies the simple version of the `H10` graph-advantage hypothesis.

It does **not** falsify the weaker claim that structure-aware graph signals contain useful information. But at the current level of evidence, the correct project framing is:

`H10 is a benchmark-comparison track showing that descriptor models remain the strongest baseline on the chosen MOF stability proxy, while graph and hybrid routes provide informative but non-winning alternatives.`

## Recommended Next Step

1. Freeze the current `H10` comparison result as the repository's benchmark conclusion.
2. Do not continue graph tuning unless there is a sharply specified new hypothesis.
3. Shift primary exploratory effort toward `H4` dataset verification while keeping `H10` as the strongest completed evidence package.
