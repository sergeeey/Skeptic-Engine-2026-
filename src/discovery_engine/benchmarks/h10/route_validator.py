from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class RouteValidationReport:
    route_id: str
    title: str
    found_required: int
    missing_required: int
    found_optional: int
    missing_optional: int
    missing_paths: list[str] = field(default_factory=list)


def validate_h10_route(route: dict[str, object], project_root: Path) -> RouteValidationReport:
    expected_files = route.get("expected_files", [])
    found_required = 0
    missing_required = 0
    found_optional = 0
    missing_optional = 0
    missing_paths: list[str] = []

    for item in expected_files:
        if not isinstance(item, dict):
            continue
        rel_path = str(item.get("path", ""))
        required = bool(item.get("required", False))
        abs_path = project_root / rel_path

        if abs_path.exists():
            if required:
                found_required += 1
            else:
                found_optional += 1
        else:
            missing_paths.append(rel_path)
            if required:
                missing_required += 1
            else:
                missing_optional += 1

    return RouteValidationReport(
        route_id=str(route.get("route_id", "unknown")),
        title=str(route.get("title", "")),
        found_required=found_required,
        missing_required=missing_required,
        found_optional=found_optional,
        missing_optional=missing_optional,
        missing_paths=missing_paths,
    )
