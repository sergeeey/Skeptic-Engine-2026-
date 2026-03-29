from __future__ import annotations

from pathlib import Path


def _default_content(path: Path) -> str:
    name = path.name.lower()
    if name == "structures.csv":
        return "structure_id,core_mof_id,formula,source_note\n"
    if name == "labels.csv":
        return "label_id,structure_id,target_name,target_value,target_units,source_note\n"
    if name == "join_keys.csv":
        return "structure_id,label_id,join_key,notes\n"
    if name == "threshold_notes.md":
        return (
            "# Threshold Notes\n\n"
            "Document the threshold definition, provenance, and assumptions here.\n"
        )
    if name == "readme.md":
        return (
            f"# {path.parent.name}\n\n"
            "Document provenance, download date, file names, and preprocessing decisions here.\n"
        )
    return ""


def initialize_route_templates(route: dict[str, object], project_root: Path) -> list[Path]:
    created: list[Path] = []
    for item in route.get("expected_files", []):
        if not isinstance(item, dict):
            continue
        rel_path = str(item.get("path", ""))
        if not rel_path:
            continue
        abs_path = project_root / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        if abs_path.exists():
            continue
        abs_path.write_text(_default_content(abs_path), encoding="utf-8")
        created.append(abs_path)
    return created
