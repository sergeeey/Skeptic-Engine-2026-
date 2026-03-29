# H10 Descriptor Tree Baseline

- model: `descriptor_hgb_v1`
- target: `solvent_removal_stability_binary`
- input artifact: `data\benchmarks\h10_features\mofsimplify_descriptor_features.csv`
- rows: train=`1394`, val=`349`, test=`436`
- features: `174`
- selected params: `{"learning_rate": 0.1, "max_depth": 8, "max_iter": 400, "min_samples_leaf": 10}`

## Validation Metrics

- average_precision: `0.877886`
- roc_auc: `0.842919`
- balanced_accuracy: `0.756292`
- threshold: `0.460251`

## Test Metrics

- average_precision: `0.873903`
- roc_auc: `0.826238`
- balanced_accuracy: `0.739742`
- threshold: `0.460251`

## Notes

- This is a nonlinear descriptor sanity baseline on the same fixed split as descriptor_logreg_v1.
- Hyperparameter selection is performed on validation only.

## Artifacts

- report: `data\benchmarks\h10_results\descriptor_hgb_v1.json`
- predictions: `data\benchmarks\h10_results\descriptor_hgb_v1_test_predictions.csv`
