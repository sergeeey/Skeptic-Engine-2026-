from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, balanced_accuracy_score, roc_auc_score


_ID_COLUMNS = {"structure_id", "core_mof_id", "split", "target_value"}


@dataclass(slots=True)
class H10TreeMetricSet:
    average_precision: float
    roc_auc: float
    balanced_accuracy: float
    threshold: float


@dataclass(slots=True)
class H10TreeBaselineRun:
    model_id: str
    target_name: str
    input_artifact: str
    train_rows: int
    val_rows: int
    test_rows: int
    feature_count: int
    selected_params: dict[str, object]
    val_metrics: H10TreeMetricSet
    test_metrics: H10TreeMetricSet
    output_predictions_path: str
    output_report_path: str

    def to_dict(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "target_name": self.target_name,
            "input_artifact": self.input_artifact,
            "train_rows": self.train_rows,
            "val_rows": self.val_rows,
            "test_rows": self.test_rows,
            "feature_count": self.feature_count,
            "selected_params": self.selected_params,
            "val_metrics": asdict(self.val_metrics),
            "test_metrics": asdict(self.test_metrics),
            "output_predictions_path": self.output_predictions_path,
            "output_report_path": self.output_report_path,
        }


def _relative(project_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


def _metric_set(y_true: pd.Series, probabilities: pd.Series, threshold: float) -> H10TreeMetricSet:
    predictions = (probabilities >= threshold).astype(int)
    return H10TreeMetricSet(
        average_precision=float(average_precision_score(y_true, probabilities)),
        roc_auc=float(roc_auc_score(y_true, probabilities)),
        balanced_accuracy=float(balanced_accuracy_score(y_true, predictions)),
        threshold=float(threshold),
    )


def _candidate_thresholds(probabilities: pd.Series) -> list[float]:
    values = sorted({round(float(value), 6) for value in probabilities.tolist()})
    if 0.5 not in values:
        values.append(0.5)
    return sorted(set(values))


def _best_threshold(y_true: pd.Series, probabilities: pd.Series) -> float:
    best_threshold = 0.5
    best_score = float("-inf")
    for threshold in _candidate_thresholds(probabilities):
        predictions = (probabilities >= threshold).astype(int)
        score = float(balanced_accuracy_score(y_true, predictions))
        if score > best_score:
            best_score = score
            best_threshold = threshold
    return best_threshold


def _build_markdown(run: H10TreeBaselineRun) -> str:
    return "\n".join(
        [
            "# H10 Descriptor Tree Baseline",
            "",
            f"- model: `{run.model_id}`",
            f"- target: `{run.target_name}`",
            f"- input artifact: `{run.input_artifact}`",
            f"- rows: train=`{run.train_rows}`, val=`{run.val_rows}`, test=`{run.test_rows}`",
            f"- features: `{run.feature_count}`",
            f"- selected params: `{json.dumps(run.selected_params, ensure_ascii=True)}`",
            "",
            "## Validation Metrics",
            "",
            f"- average_precision: `{run.val_metrics.average_precision:.6f}`",
            f"- roc_auc: `{run.val_metrics.roc_auc:.6f}`",
            f"- balanced_accuracy: `{run.val_metrics.balanced_accuracy:.6f}`",
            f"- threshold: `{run.val_metrics.threshold:.6f}`",
            "",
            "## Test Metrics",
            "",
            f"- average_precision: `{run.test_metrics.average_precision:.6f}`",
            f"- roc_auc: `{run.test_metrics.roc_auc:.6f}`",
            f"- balanced_accuracy: `{run.test_metrics.balanced_accuracy:.6f}`",
            f"- threshold: `{run.test_metrics.threshold:.6f}`",
            "",
            "## Notes",
            "",
            "- This is a nonlinear descriptor sanity baseline on the same fixed split as descriptor_logreg_v1.",
            "- Hyperparameter selection is performed on validation only.",
            "",
            "## Artifacts",
            "",
            f"- report: `{run.output_report_path}`",
            f"- predictions: `{run.output_predictions_path}`",
        ]
    ) + "\n"


def run_h10_descriptor_tree_baseline(
    *,
    project_root: Path,
    descriptor_feature_path: Path,
    report_output_path: Path,
    predictions_output_path: Path,
    markdown_output_path: Path,
) -> H10TreeBaselineRun:
    df = pd.read_csv(descriptor_feature_path)
    if df.empty:
        raise ValueError("Descriptor feature artifact is empty.")

    feature_columns = [column for column in df.columns if column not in _ID_COLUMNS]
    if not feature_columns:
        raise ValueError("Descriptor feature artifact contains no feature columns.")

    train_df = df[df["split"] == "train"].copy()
    val_df = df[df["split"] == "val"].copy()
    test_df = df[df["split"] == "test"].copy()

    x_train = train_df[feature_columns]
    y_train = train_df["target_value"].astype(int)
    x_val = val_df[feature_columns]
    y_val = val_df["target_value"].astype(int)
    x_test = test_df[feature_columns]
    y_test = test_df["target_value"].astype(int)

    imputer = SimpleImputer(strategy="median")
    x_train_imp = imputer.fit_transform(x_train)
    x_val_imp = imputer.transform(x_val)
    x_test_imp = imputer.transform(x_test)

    search_space = [
        {"learning_rate": 0.05, "max_depth": 4, "max_iter": 200, "min_samples_leaf": 20},
        {"learning_rate": 0.05, "max_depth": 6, "max_iter": 300, "min_samples_leaf": 20},
        {"learning_rate": 0.1, "max_depth": 6, "max_iter": 300, "min_samples_leaf": 20},
        {"learning_rate": 0.1, "max_depth": 8, "max_iter": 400, "min_samples_leaf": 10},
    ]

    best_model: HistGradientBoostingClassifier | None = None
    best_params: dict[str, object] | None = None
    best_val_probabilities: pd.Series | None = None
    best_score = float("-inf")

    for params in search_space:
        model = HistGradientBoostingClassifier(
            learning_rate=float(params["learning_rate"]),
            max_depth=int(params["max_depth"]),
            max_iter=int(params["max_iter"]),
            min_samples_leaf=int(params["min_samples_leaf"]),
            random_state=42,
        )
        model.fit(x_train_imp, y_train)
        val_probabilities = pd.Series(model.predict_proba(x_val_imp)[:, 1], index=val_df.index)
        score = float(average_precision_score(y_val, val_probabilities))
        if score > best_score:
            best_score = score
            best_model = model
            best_params = dict(params)
            best_val_probabilities = val_probabilities

    if best_model is None or best_params is None or best_val_probabilities is None:
        raise RuntimeError("Tree baseline search failed to produce a model.")

    threshold = _best_threshold(y_val, best_val_probabilities)
    val_metrics = _metric_set(y_val, best_val_probabilities, threshold)
    test_probabilities = pd.Series(best_model.predict_proba(x_test_imp)[:, 1], index=test_df.index)
    test_metrics = _metric_set(y_test, test_probabilities, threshold)

    predictions = test_df[["structure_id", "core_mof_id", "split", "target_value"]].copy()
    predictions["predicted_probability"] = test_probabilities.to_numpy()
    predictions["predicted_label"] = (test_probabilities >= threshold).astype(int).to_numpy()

    predictions_output_path.parent.mkdir(parents=True, exist_ok=True)
    report_output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(predictions_output_path, index=False)

    run = H10TreeBaselineRun(
        model_id="descriptor_hgb_v1",
        target_name="solvent_removal_stability_binary",
        input_artifact=_relative(project_root, descriptor_feature_path),
        train_rows=len(train_df),
        val_rows=len(val_df),
        test_rows=len(test_df),
        feature_count=len(feature_columns),
        selected_params=best_params,
        val_metrics=val_metrics,
        test_metrics=test_metrics,
        output_predictions_path=_relative(project_root, predictions_output_path),
        output_report_path=_relative(project_root, report_output_path),
    )

    report_output_path.write_text(json.dumps(run.to_dict(), indent=2), encoding="utf-8")
    markdown_output_path.write_text(_build_markdown(run), encoding="utf-8")
    return run
