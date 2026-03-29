# H10 Descriptor Baseline

- model: `descriptor_logreg_v1`
- target: `solvent_removal_stability_binary`
- input artifact: `data\benchmarks\h10_features\mofsimplify_descriptor_features.csv`
- rows: train=`1394`, val=`349`, test=`436`
- features: `174`
- selected params: `{"C": 3.0, "class_weight": "balanced"}`

## Validation Metrics

- average_precision: `0.722658`
- roc_auc: `0.669362`
- balanced_accuracy: `0.628473`
- threshold: `0.606261`

## Test Metrics

- average_precision: `0.752156`
- roc_auc: `0.674191`
- balanced_accuracy: `0.604772`
- threshold: `0.606261`

## Notes

- Hyperparameter selection is performed on the fixed validation split only.
- Test metrics are reported once using the threshold selected on validation.
- This is the first trainable descriptor baseline, not the final benchmark claim.

## Artifacts

- report: `data\benchmarks\h10_results\descriptor_logreg_v1.json`
- predictions: `data\benchmarks\h10_results\descriptor_logreg_v1_test_predictions.csv`
