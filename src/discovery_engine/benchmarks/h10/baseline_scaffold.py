from __future__ import annotations

import csv
import json
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from discovery_engine.benchmarks.h10.mofsimplify_import import MOFSIMPLIFY_FULL_SSD_PATH


_NON_FEATURE_COLUMNS = {
    "CoRE_name",
    "refcode",
    "doi",
    "assigned_solvent_removal_stability",
    "ANN_predicted_solvent_removal_stability",
    "ANN_prediction_probability",
    "ANN_LSE",
    "partition",
    "explicit_intro_in_paper",
    "number_of_sentences_in_paper",
    "sentence_indices",
    "collapse_keywords",
    "solvent_keywords",
    "stability_keywords",
    "sentences",
    "filename",
}


@dataclass(slots=True)
class H10SplitSummary:
    split: str
    row_count: int
    class_balance: list[str] = field(default_factory=list)


@dataclass(slots=True)
class H10BaselineSpec:
    baseline_id: str
    family: str
    status: str
    input_artifact: str | None = None
    row_count: int = 0
    feature_count: int = 0
    ready_for_training: bool = False
    notes: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)


@dataclass(slots=True)
class H10EvaluationProtocol:
    split_policy: str
    primary_metric: str
    metrics: list[str] = field(default_factory=list)
    positives_label: str = "1"
    falsification_rule: str = ""


@dataclass(slots=True)
class H10BaselineScaffold:
    route_id: str
    target_name: str
    mapped_dataset_path: str
    total_rows: int
    split_summaries: list[H10SplitSummary] = field(default_factory=list)
    baselines: list[H10BaselineSpec] = field(default_factory=list)
    evaluation_protocol: H10EvaluationProtocol | None = None
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "route_id": self.route_id,
            "target_name": self.target_name,
            "mapped_dataset_path": self.mapped_dataset_path,
            "total_rows": self.total_rows,
            "split_summaries": [asdict(item) for item in self.split_summaries],
            "baselines": [asdict(item) for item in self.baselines],
            "evaluation_protocol": asdict(self.evaluation_protocol) if self.evaluation_protocol else None,
            "warnings": self.warnings,
            "blockers": self.blockers,
        }


def _project_relative(project_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [{str(key): str(value or "").strip() for key, value in row.items()} for row in reader]


def _is_float_like(value: str) -> bool:
    if value == "":
        return True
    try:
        float(value)
    except ValueError:
        return False
    return True


def _detect_feature_columns(rows: list[dict[str, str]]) -> list[str]:
    if not rows:
        return []

    candidate_columns = [column for column in rows[0] if column not in _NON_FEATURE_COLUMNS]
    feature_columns: list[str] = []
    for column in candidate_columns:
        sample_values = [row.get(column, "") for row in rows[:50]]
        if all(_is_float_like(value) for value in sample_values):
            feature_columns.append(column)
    return feature_columns


def _write_descriptor_feature_artifact(
    archive_path: Path,
    mapped_rows: list[dict[str, str]],
    output_path: Path,
) -> tuple[int, int]:
    mapped_index = {row["structure_id"]: row for row in mapped_rows if row.get("structure_id")}

    with zipfile.ZipFile(archive_path) as archive:
        with archive.open(MOFSIMPLIFY_FULL_SSD_PATH) as handle:
            text_handle = (line.decode("utf-8-sig") for line in handle)
            reader = csv.DictReader(text_handle)
            raw_rows = [{str(key): str(value or "").strip() for key, value in row.items()} for row in reader]

    feature_columns = _detect_feature_columns(raw_rows)
    output_rows: list[dict[str, str]] = []
    for raw_row in raw_rows:
        structure_id = raw_row.get("CoRE_name", "").strip()
        mapped_row = mapped_index.get(structure_id)
        if mapped_row is None:
            continue
        output_row = {
            "structure_id": structure_id,
            "core_mof_id": raw_row.get("refcode", "").strip(),
            "split": mapped_row.get("split", ""),
            "target_value": mapped_row.get("target_value", ""),
        }
        for feature_name in feature_columns:
            output_row[feature_name] = raw_row.get(feature_name, "").strip()
        output_rows.append(output_row)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["structure_id", "core_mof_id", "split", "target_value", *feature_columns]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    return len(output_rows), len(feature_columns)


def _split_summaries(mapped_rows: list[dict[str, str]]) -> list[H10SplitSummary]:
    split_order = ["train", "val", "test"]
    summaries: list[H10SplitSummary] = []
    for split_name in split_order:
        rows = [row for row in mapped_rows if row.get("split") == split_name]
        if not rows:
            continue
        negatives = sum(1 for row in rows if row.get("target_value") == "0")
        positives = sum(1 for row in rows if row.get("target_value") == "1")
        summaries.append(
            H10SplitSummary(
                split=split_name,
                row_count=len(rows),
                class_balance=[f"0={negatives}", f"1={positives}"],
            )
        )
    return summaries


def _formula_coverage(mapped_rows: list[dict[str, str]]) -> int:
    return sum(1 for row in mapped_rows if row.get("formula"))


def _core_mof_coverage(mapped_rows: list[dict[str, str]]) -> int:
    return sum(1 for row in mapped_rows if row.get("core_mof_id"))


def _build_baselines(
    spec: dict[str, object],
    project_root: Path,
    mapped_rows: list[dict[str, str]],
    descriptor_artifact_path: Path,
    descriptor_row_count: int,
    descriptor_feature_count: int,
    graph_artifact_path: Path,
) -> list[H10BaselineSpec]:
    baselines: list[H10BaselineSpec] = []
    formula_coverage = _formula_coverage(mapped_rows)
    core_mof_coverage = _core_mof_coverage(mapped_rows)

    for item in spec.get("baselines", []):
        if not isinstance(item, dict):
            continue
        baseline_id = str(item.get("id", "unknown"))
        family = str(item.get("family", "unknown"))

        if baseline_id == "descriptor_baseline":
            baselines.append(
                H10BaselineSpec(
                    baseline_id=baseline_id,
                    family=family,
                    status="ready",
                    input_artifact=_project_relative(project_root, descriptor_artifact_path),
                    row_count=descriptor_row_count,
                    feature_count=descriptor_feature_count,
                    ready_for_training=descriptor_row_count > 0 and descriptor_feature_count > 0,
                    notes=[
                        "Uses RAC and geometric descriptors extracted from MOFSimplify full_SSD_data.csv.",
                        "Run descriptor baselines only on the fixed MOFSimplify train/val/test split.",
                    ],
                )
            )
            continue

        if baseline_id == "token_baseline":
            ready = formula_coverage == len(mapped_rows) and len(mapped_rows) > 0
            blockers = []
            notes = [
                "Preferred token route is formula or linker/metal tokenization from a structure-derived representation."
            ]
            if not ready:
                blockers.append("Mapped route does not yet provide reliable formula or linker token fields.")
                notes.append("Do not use CoRE refcodes as a proxy tokenization baseline; that would be identifier leakage, not chemistry.")
            baselines.append(
                H10BaselineSpec(
                    baseline_id=baseline_id,
                    family=family,
                    status="blocked" if not ready else "ready",
                    row_count=formula_coverage,
                    feature_count=1 if ready else 0,
                    ready_for_training=ready,
                    notes=notes,
                    blockers=blockers,
                )
            )
            continue

        if baseline_id == "graph_baseline":
            ready = graph_artifact_path.exists()
            blockers = []
            if not ready:
                blockers.append("No local CIF or graph-construction artifact is present yet for the mapped structures.")
            notes = [
                f"core_mof_id coverage is {core_mof_coverage}/{len(mapped_rows)}; schema is ready for later CoRE-MOF structure fetch.",
                "Graph baseline should only start after a reproducible CIF-to-graph extraction path is added.",
            ]
            if ready:
                notes.append(f"Graph artifact is available at {_project_relative(project_root, graph_artifact_path)}.")
            baselines.append(
                H10BaselineSpec(
                    baseline_id=baseline_id,
                    family=family,
                    status="input_ready" if ready else "scaffold_ready",
                    input_artifact=_project_relative(project_root, graph_artifact_path) if ready else None,
                    row_count=core_mof_coverage,
                    feature_count=0,
                    ready_for_training=ready,
                    notes=notes,
                    blockers=blockers,
                )
            )
            continue

        baselines.append(
            H10BaselineSpec(
                baseline_id=baseline_id,
                family=family,
                status="unknown",
            )
        )

    return baselines


def _build_markdown(scaffold: H10BaselineScaffold) -> str:
    lines = [
        "# H10 Baseline Matrix",
        "",
        f"- route: `{scaffold.route_id}`",
        f"- target: `{scaffold.target_name}`",
        f"- mapped dataset: `{scaffold.mapped_dataset_path}`",
        f"- rows: `{scaffold.total_rows}`",
        "",
        "## Split Summary",
        "",
        "| Split | Rows | Class Balance |",
        "|---|---:|---|",
    ]
    for split in scaffold.split_summaries:
        lines.append(f"| {split.split} | {split.row_count} | {', '.join(split.class_balance)} |")

    lines.extend(
        [
            "",
            "## Baseline Matrix",
            "",
            "| Baseline | Family | Status | Train Ready | Rows | Features | Artifact |",
            "|---|---|---|---|---:|---:|---|",
        ]
    )
    for baseline in scaffold.baselines:
        artifact = baseline.input_artifact or "-"
        lines.append(
            f"| {baseline.baseline_id} | {baseline.family} | {baseline.status} | "
            f"{'yes' if baseline.ready_for_training else 'no'} | {baseline.row_count} | "
            f"{baseline.feature_count} | {artifact} |"
        )
        for note in baseline.notes:
            lines.append(f"- {baseline.baseline_id}: {note}")
        for blocker in baseline.blockers:
            lines.append(f"- blocker for {baseline.baseline_id}: {blocker}")

    if scaffold.evaluation_protocol is not None:
        protocol = scaffold.evaluation_protocol
        lines.extend(
            [
                "",
                "## Evaluation Protocol",
                "",
                f"- split policy: {protocol.split_policy}",
                f"- primary metric: `{protocol.primary_metric}`",
                f"- metrics: {', '.join(protocol.metrics)}",
                f"- positive label: `{protocol.positives_label}`",
                f"- falsification rule: {protocol.falsification_rule}",
            ]
        )

    if scaffold.blockers:
        lines.extend(["", "## Project-Level Blockers", ""])
        lines.extend([f"- {item}" for item in scaffold.blockers])

    if scaffold.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend([f"- {item}" for item in scaffold.warnings])

    return "\n".join(lines) + "\n"


def build_h10_baseline_scaffold(
    *,
    project_root: Path,
    spec: dict[str, object],
    mapped_dataset_path: Path,
    archive_path: Path,
    descriptor_output_path: Path,
    graph_artifact_path: Path,
    scaffold_output_path: Path,
    baseline_matrix_doc_path: Path,
) -> H10BaselineScaffold:
    mapped_rows = _load_csv_rows(mapped_dataset_path)
    if not mapped_rows:
        raise ValueError("Mapped H10 dataset is empty; run h10-map before building baseline scaffold.")

    target_names = sorted({row.get("target_name", "") for row in mapped_rows if row.get("target_name")})
    if len(target_names) != 1:
        raise ValueError("Mapped H10 dataset must contain exactly one target_name for baseline scaffold generation.")

    descriptor_row_count, descriptor_feature_count = _write_descriptor_feature_artifact(
        archive_path,
        mapped_rows,
        descriptor_output_path,
    )

    baselines = _build_baselines(
        spec,
        project_root,
        mapped_rows,
        descriptor_output_path,
        descriptor_row_count,
        descriptor_feature_count,
        graph_artifact_path,
    )

    blockers: list[str] = []
    if not any(baseline.baseline_id == "descriptor_baseline" and baseline.ready_for_training for baseline in baselines):
        blockers.append("Descriptor baseline is not train-ready, so no fair benchmark can start yet.")
    if not any(baseline.baseline_id == "graph_baseline" and baseline.ready_for_training for baseline in baselines):
        blockers.append("Graph baseline still needs a reproducible CIF-to-graph ingestion path.")

    scaffold = H10BaselineScaffold(
        route_id=str(mapped_rows[0].get("route_id", "unknown")),
        target_name=target_names[0],
        mapped_dataset_path=_project_relative(project_root, mapped_dataset_path),
        total_rows=len(mapped_rows),
        split_summaries=_split_summaries(mapped_rows),
        baselines=baselines,
        evaluation_protocol=H10EvaluationProtocol(
            split_policy="Use the fixed MOFSimplify train/val/test partition shipped with the source dataset.",
            primary_metric="average_precision",
            metrics=[str(item) for item in spec.get("metrics", [])],
            positives_label="1",
            falsification_rule=str(spec.get("falsification_rule", "")),
        ),
        warnings=[
            "Token baseline remains blocked until chemistry-derived token fields are added.",
            "Do not compare graph models against descriptor baselines on different splits.",
        ],
        blockers=blockers,
    )

    scaffold_output_path.parent.mkdir(parents=True, exist_ok=True)
    scaffold_output_path.write_text(json.dumps(scaffold.to_dict(), indent=2), encoding="utf-8")
    baseline_matrix_doc_path.write_text(_build_markdown(scaffold), encoding="utf-8")
    return scaffold
