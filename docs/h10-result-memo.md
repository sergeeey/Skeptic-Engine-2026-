# H10 Result Memo

## Date

2026-03-26

## Related Docs

- `h10-benchmark-conclusion.md`
- `h10-baseline-matrix.md`
- `h10-descriptor-tree-baseline.md`
- `h10-graph-baseline.md`
- `h10-graph-mpnn-baseline.md`
- `h10-hybrid-baseline.md`

## One-Line Summary

On the current `MOFSimplify` solvent-removal stability benchmark, descriptor models remain strongest on the primary metric `average_precision`, while graph and hybrid routes provide useful but non-winning alternatives.

## Working Title

`Benchmarking descriptor, graph, and hybrid models for MOF solvent-removal stability prediction`

## Short Abstract

We built a reproducible benchmark for predicting `MOFSimplify` solvent-removal stability labels on `2179` metal-organic frameworks linked to open structure data and evaluated descriptor, graph-structural, message-passing, and descriptor-plus-graph hybrid baselines on a fixed train/validation/test split. The strongest result on the primary metric `average_precision` came from a nonlinear descriptor baseline (`0.873903`), followed by a descriptor-plus-graph hybrid baseline (`0.862236`) and a graph-structural baseline (`0.834278`). Pure message-passing baselines underperformed all stronger non-neural baselines. These results do not support a simple graph-advantage claim on the chosen proxy target, but they do show that graph-derived information is informative and can improve some secondary metrics. The current evidence therefore supports framing `H10` as a benchmark-comparison result rather than a graph-win result.

## Key Results

| Model | Family | Test AP | Test ROC-AUC | Test Balanced Accuracy |
|---|---|---:|---:|---:|
| `descriptor_hgb_v1` | descriptor | `0.873903` | `0.826238` | `0.739742` |
| `hybrid_hgb_v1` | descriptor + graph-structural | `0.862236` | `0.834634` | `0.751918` |
| `graph_structural_hgb_v1` | graph-structural | `0.834278` | `0.797952` | `0.725214` |
| `graph_mpnn_v2` | message passing | `0.736903` | `0.672960` | `0.619431` |
| `graph_mpnn_v3` | message passing | `0.731329` | `0.676191` | `0.608321` |

## Claim Status

Supported:

- the `H10` route is executable and benchmark-ready
- the chosen proxy label supports a real comparison task
- graph-derived signals are informative
- hybrid modeling can improve some secondary metrics

Not supported:

- graph models are best on this benchmark
- message passing is the strongest route on this target
- graph information is required for the strongest current result

## Clean Interpretation

The strongest current story is not "graphs win for MOF stability proxies." The strongest current story is:

`On this benchmark, carefully engineered descriptor models remain hardest to beat on the primary metric, while graph and hybrid models provide informative comparison baselines that clarify what graph signal does and does not add.`

## Reusable Project Summary

`H10` is now the project's most complete evidence package: open-data route, fixed split, multiple baseline families, skeptic pressure, and a clear negative result against the simplest graph-superiority claim.

## Recommended Use

- use this memo as the short narrative summary for the current `H10` state
- use `h10-benchmark-conclusion.md` as the stricter evidence document
- do not continue graph tuning unless there is a sharply specified next hypothesis
