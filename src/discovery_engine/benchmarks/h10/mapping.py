from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class H10MappingReport:
    route_id: str
    title: str
    target_name: str | None
    output_path: str
    row_count: int
    distinct_structures: int
    available_targets: list[str] = field(default_factory=list)
    target_distribution: list[str] = field(default_factory=list)
    split_distribution: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)


def _normalize_cell(value: object) -> str:
    return str(value or "").strip()


def _expected_path(route: dict[str, object], project_root: Path, file_name: str) -> Path:
    for item in route.get("expected_files", []):
        if not isinstance(item, dict):
            continue
        rel_path = _normalize_cell(item.get("path"))
        if rel_path.endswith(file_name):
            return project_root / rel_path
    raw_root = _normalize_cell(route.get("raw_root"))
    return project_root / raw_root / file_name


def _output_path(route: dict[str, object], project_root: Path) -> Path:
    rel_path = _normalize_cell(route.get("mapped_output"))
    if rel_path:
        return project_root / rel_path
    return project_root / "data" / "benchmarks" / "h10_mapped" / f"{route.get('route_id', 'unknown')}.csv"


def _read_csv_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        return [], []

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return [], []
        fieldnames = [_normalize_cell(name) for name in reader.fieldnames]
        rows: list[dict[str, str]] = []
        for raw_row in reader:
            normalized = {key: _normalize_cell(value) for key, value in raw_row.items()}
            if any(normalized.values()):
                rows.append(normalized)
    return rows, fieldnames


def _select_target_name(
    route: dict[str, object],
    label_rows: list[dict[str, str]],
    requested_target_name: str | None,
    blockers: list[str],
) -> tuple[str | None, list[str]]:
    available_targets = sorted({_normalize_cell(row.get("target_name")) for row in label_rows if _normalize_cell(row.get("target_name"))})

    if requested_target_name:
        if requested_target_name not in available_targets:
            blockers.append(
                f"Requested target '{requested_target_name}' is not present in labels.csv."
            )
            return None, available_targets
        return requested_target_name, available_targets

    route_targets = [
        _normalize_cell(target_name)
        for target_name in route.get("target_options", [])
        if _normalize_cell(target_name)
    ]
    for target_name in route_targets:
        if target_name in available_targets:
            return target_name, available_targets

    if len(available_targets) == 1:
        return available_targets[0], available_targets

    if len(available_targets) > 1:
        blockers.append(
            "Multiple target_name values are present in labels.csv; choose one explicitly for mapping."
        )

    return None, available_targets


def build_h10_mapped_dataset(
    route: dict[str, object],
    project_root: Path,
    *,
    target_name: str | None = None,
    write_output: bool = True,
) -> H10MappingReport:
    route_id = _normalize_cell(route.get("route_id")) or "unknown"
    title = _normalize_cell(route.get("title"))
    blockers: list[str] = []
    warnings: list[str] = []

    structures_path = _expected_path(route, project_root, "structures.csv")
    labels_path = _expected_path(route, project_root, "labels.csv")
    join_keys_path = _expected_path(route, project_root, "join_keys.csv")
    output_path = _output_path(route, project_root)

    structure_rows, structure_columns = _read_csv_rows(structures_path)
    label_rows, label_columns = _read_csv_rows(labels_path)
    join_rows, join_columns = _read_csv_rows(join_keys_path)

    if not structure_rows:
        blockers.append("structures.csv has no usable data rows.")
    if not label_rows:
        blockers.append("labels.csv has no usable data rows.")

    if structure_rows and "structure_id" not in structure_columns:
        blockers.append("structures.csv must contain a structure_id column.")
    if label_rows and "target_name" not in label_columns:
        blockers.append("labels.csv must contain a target_name column.")
    if label_rows and "target_value" not in label_columns:
        blockers.append("labels.csv must contain a target_value column.")

    selected_target, available_targets = _select_target_name(route, label_rows, target_name, blockers)

    structures_by_id = {
        row["structure_id"]: row
        for row in structure_rows
        if row.get("structure_id")
    }

    join_by_label_id = {
        row["label_id"]: row
        for row in join_rows
        if row.get("label_id") and row.get("structure_id")
    }
    if join_rows and "label_id" not in join_columns:
        warnings.append("join_keys.csv is present but does not include label_id; it cannot help with label joins.")

    mapped_rows: list[dict[str, str]] = []
    unresolved_labels = 0
    missing_structures = 0

    if selected_target:
        filtered_labels = [row for row in label_rows if row.get("target_name") == selected_target]
        if not filtered_labels:
            blockers.append(f"No label rows remain after filtering for target '{selected_target}'.")
        for label_row in filtered_labels:
            structure_id = _normalize_cell(label_row.get("structure_id"))
            join_method = "direct"

            if not structure_id:
                label_id = _normalize_cell(label_row.get("label_id"))
                join_row = join_by_label_id.get(label_id)
                if join_row is not None:
                    structure_id = _normalize_cell(join_row.get("structure_id"))
                    join_method = "join_keys"

            if not structure_id:
                unresolved_labels += 1
                continue

            structure_row = structures_by_id.get(structure_id)
            if structure_row is None:
                missing_structures += 1
                continue

            mapped_rows.append(
                {
                    "route_id": route_id,
                    "target_name": selected_target,
                    "structure_id": structure_id,
                    "core_mof_id": _normalize_cell(structure_row.get("core_mof_id")),
                    "formula": _normalize_cell(structure_row.get("formula")),
                    "label_id": _normalize_cell(label_row.get("label_id")),
                    "target_value": _normalize_cell(label_row.get("target_value")),
                    "target_units": _normalize_cell(label_row.get("target_units")),
                    "split": _normalize_cell(label_row.get("split")),
                    "doi": _normalize_cell(label_row.get("doi")),
                    "ann_prediction_probability": _normalize_cell(label_row.get("ann_prediction_probability")),
                    "ann_predicted_target_value": _normalize_cell(label_row.get("ann_predicted_target_value")),
                    "latent_space_entropy": _normalize_cell(label_row.get("latent_space_entropy")),
                    "join_method": join_method,
                    "structure_source_note": _normalize_cell(structure_row.get("source_note")),
                    "label_source_note": _normalize_cell(label_row.get("source_note")),
                }
            )

    if unresolved_labels:
        warnings.append(
            f"{unresolved_labels} label rows could not be mapped to a structure_id."
        )
    if missing_structures:
        warnings.append(
            f"{missing_structures} mapped labels referenced structure_ids absent from structures.csv."
        )

    distinct_target_values = sorted({_normalize_cell(row.get("target_value")) for row in mapped_rows if _normalize_cell(row.get("target_value"))})
    if mapped_rows and len(distinct_target_values) < 2:
        blockers.append("Mapped target contains fewer than two distinct target values.")

    output_columns = [
        "route_id",
        "target_name",
        "structure_id",
        "core_mof_id",
        "formula",
        "label_id",
        "target_value",
        "target_units",
        "split",
        "doi",
        "ann_prediction_probability",
        "ann_predicted_target_value",
        "latent_space_entropy",
        "join_method",
        "structure_source_note",
        "label_source_note",
    ]
    if write_output:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=output_columns)
            writer.writeheader()
            writer.writerows(mapped_rows)

    distribution = Counter(row["target_value"] for row in mapped_rows if row.get("target_value"))
    split_distribution = Counter(row["split"] for row in mapped_rows if row.get("split"))
    return H10MappingReport(
        route_id=route_id,
        title=title,
        target_name=selected_target,
        output_path=str(output_path),
        row_count=len(mapped_rows),
        distinct_structures=len({row["structure_id"] for row in mapped_rows}),
        available_targets=available_targets,
        target_distribution=[
            f"{target_value}={count}"
            for target_value, count in sorted(distribution.items())
        ],
        split_distribution=[
            f"{split_name}={count}"
            for split_name, count in sorted(split_distribution.items())
        ],
        warnings=warnings,
        blockers=blockers,
    )
