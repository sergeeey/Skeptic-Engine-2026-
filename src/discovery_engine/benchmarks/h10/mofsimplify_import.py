from __future__ import annotations

import csv
import zipfile
from dataclasses import dataclass, field
from pathlib import Path


MOFSIMPLIFY_FULL_SSD_PATH = "SciData/separate_files/solvent_removal_stability/full_SSD_data.csv"


@dataclass(slots=True)
class MOFSimplifyImportReport:
    archive_path: str
    route_id: str
    rows_written: int
    structures_path: str
    labels_path: str
    join_keys_path: str
    available_targets: list[str] = field(default_factory=list)
    class_balance: list[str] = field(default_factory=list)


def _raw_route_root(route: dict[str, object], project_root: Path) -> Path:
    raw_root = str(route.get("raw_root", "")).strip()
    if not raw_root:
        raise ValueError("Route is missing raw_root.")
    return project_root / raw_root


def _expected_csv_path(route: dict[str, object], project_root: Path, file_name: str) -> Path:
    for item in route.get("expected_files", []):
        if not isinstance(item, dict):
            continue
        rel_path = str(item.get("path", "")).strip()
        if rel_path.endswith(file_name):
            return project_root / rel_path
    return _raw_route_root(route, project_root) / file_name


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _build_source_note(row: dict[str, str]) -> str:
    doi = row.get("doi", "").strip()
    partition = row.get("partition", "").strip()
    probability = row.get("ANN_prediction_probability", "").strip()
    return f"doi={doi}; partition={partition}; ann_probability={probability}"


def import_mofsimplify_solvent_route(
    archive_path: str | Path,
    route: dict[str, object],
    project_root: Path,
) -> MOFSimplifyImportReport:
    zip_path = Path(archive_path)
    if not zip_path.exists():
        raise FileNotFoundError(f"Archive not found: {zip_path}")

    raw_root = _raw_route_root(route, project_root)
    structures_path = _expected_csv_path(route, project_root, "structures.csv")
    labels_path = _expected_csv_path(route, project_root, "labels.csv")
    join_keys_path = _expected_csv_path(route, project_root, "join_keys.csv")
    readme_path = raw_root / "README.md"

    with zipfile.ZipFile(zip_path) as archive:
        with archive.open(MOFSIMPLIFY_FULL_SSD_PATH) as handle:
            text_handle = (line.decode("utf-8-sig") for line in handle)
            reader = csv.DictReader(text_handle)
            imported_rows = [
                {str(key): str(value or "").strip() for key, value in row.items()}
                for row in reader
            ]

    target_name = "solvent_removal_stability_binary"
    structures_rows: list[dict[str, str]] = []
    label_rows: list[dict[str, str]] = []
    join_rows: list[dict[str, str]] = []
    class_counts: dict[str, int] = {}

    for index, row in enumerate(imported_rows, start=1):
        structure_id = row.get("CoRE_name", "").strip() or row.get("refcode", "").strip()
        core_mof_id = row.get("refcode", "").strip()
        label_value = row.get("assigned_solvent_removal_stability", "").strip()
        label_id = f"{core_mof_id or structure_id}:{index}"

        if not structure_id or not label_value:
            continue

        source_note = _build_source_note(row)
        structures_rows.append(
            {
                "structure_id": structure_id,
                "core_mof_id": core_mof_id,
                "formula": "",
                "source_note": source_note,
            }
        )
        label_rows.append(
            {
                "label_id": label_id,
                "structure_id": structure_id,
                "target_name": target_name,
                "target_value": label_value,
                "target_units": "binary",
                "split": row.get("partition", "").strip(),
                "doi": row.get("doi", "").strip(),
                "ann_prediction_probability": row.get("ANN_prediction_probability", "").strip(),
                "ann_predicted_target_value": row.get("ANN_predicted_solvent_removal_stability", "").strip(),
                "latent_space_entropy": row.get("ANN_LSE", "").strip(),
                "source_note": source_note,
            }
        )
        join_rows.append(
            {
                "structure_id": structure_id,
                "label_id": label_id,
                "join_key": structure_id,
                "notes": "Direct join via CoRE_name from MOFSimplify full_SSD_data.csv",
            }
        )
        class_counts[label_value] = class_counts.get(label_value, 0) + 1

    _write_csv(
        structures_path,
        ["structure_id", "core_mof_id", "formula", "source_note"],
        structures_rows,
    )
    _write_csv(
        labels_path,
        [
            "label_id",
            "structure_id",
            "target_name",
            "target_value",
            "target_units",
            "split",
            "doi",
            "ann_prediction_probability",
            "ann_predicted_target_value",
            "latent_space_entropy",
            "source_note",
        ],
        label_rows,
    )
    _write_csv(
        join_keys_path,
        ["structure_id", "label_id", "join_key", "notes"],
        join_rows,
    )

    readme_lines = [
        "# H10 Raw Data: MOFSimplify Stability Route",
        "",
        "Imported from the MOFSimplify Scientific Data Zenodo archive.",
        "",
        f"- archive: `{zip_path.name}`",
        f"- source path in archive: `{MOFSIMPLIFY_FULL_SSD_PATH}`",
        "- primary paper: `https://www.nature.com/articles/s41597-022-01181-0`",
        "- access route: `https://zenodo.org/records/5736562/files/SciData.zip?download=1`",
        f"- imported rows: `{len(label_rows)}`",
        f"- target_name: `{target_name}`",
        "- join assumption: `labels.structure_id == structures.structure_id == CoRE_name`",
        "- note: `formula` is left blank because full_SSD_data.csv does not expose it directly.",
        "",
        "No manual relabeling has been applied at this stage.",
    ]
    readme_path.write_text("\n".join(readme_lines) + "\n", encoding="utf-8")

    return MOFSimplifyImportReport(
        archive_path=str(zip_path),
        route_id=str(route.get("route_id", "unknown")),
        rows_written=len(label_rows),
        structures_path=str(structures_path),
        labels_path=str(labels_path),
        join_keys_path=str(join_keys_path),
        available_targets=[target_name],
        class_balance=[
            f"{label_value}={count}"
            for label_value, count in sorted(class_counts.items())
        ],
    )
