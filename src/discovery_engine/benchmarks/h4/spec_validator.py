from __future__ import annotations

from dataclasses import dataclass, field


_REQUIRED_ROUTE_FIELDS = [
    "id",
    "title",
    "accession",
    "route_status",
    "disease",
    "unit_of_analysis",
    "evaluation_level",
    "label_type",
    "split_unit",
]
_ALLOWED_ROUTE_STATUS = {"scouting", "contract_locked_pending_audit", "ready"}
_ALLOWED_TRACK_STATUS = {"active", "closed_after_kill_criterion", "archived"}


@dataclass(slots=True)
class H4RouteValidationReport:
    route_id: str
    is_default: bool
    route_status: str
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class H4SpecValidationReport:
    candidate_id: str
    route_count: int
    default_route_count: int
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    route_reports: list[H4RouteValidationReport] = field(default_factory=list)


def _validate_label_schema(route: dict[str, object], report: H4RouteValidationReport) -> None:
    label_schema = route.get("label_schema")
    if not isinstance(label_schema, dict) or not label_schema:
        report.errors.append("label_schema must be a non-empty object.")
        return
    task_type = str(label_schema.get("task_type", "")).strip()
    if not task_type:
        report.errors.append("label_schema.task_type is required.")
    positive_label = str(label_schema.get("positive_label", "")).strip()
    if not positive_label:
        report.errors.append("label_schema.positive_label is required.")


def _validate_split_contract(route: dict[str, object], report: H4RouteValidationReport) -> None:
    split_unit = str(route.get("split_unit", "")).strip()
    if not split_unit:
        report.errors.append("split_unit is required.")
    group_keys = route.get("group_keys_for_split", [])
    if not isinstance(group_keys, list) or not [str(item).strip() for item in group_keys]:
        report.errors.append("group_keys_for_split must be a non-empty list.")
    leakage_keys = route.get("leakage_keys", [])
    if not isinstance(leakage_keys, list) or not [str(item).strip() for item in leakage_keys]:
        report.errors.append("leakage_keys must be a non-empty list.")


def _validate_route(route: dict[str, object]) -> H4RouteValidationReport:
    route_id = str(route.get("id", "unknown"))
    report = H4RouteValidationReport(
        route_id=route_id,
        is_default=bool(route.get("default_route")),
        route_status=str(route.get("route_status", "unknown")),
        is_valid=True,
    )

    for field_name in _REQUIRED_ROUTE_FIELDS:
        value = route.get(field_name)
        if not isinstance(value, str) or not value.strip():
            report.errors.append(f"{field_name} is required.")

    if report.route_status not in _ALLOWED_ROUTE_STATUS:
        report.errors.append(
            f"route_status must be one of {sorted(_ALLOWED_ROUTE_STATUS)}, got {report.route_status!r}."
        )

    _validate_label_schema(route, report)
    _validate_split_contract(route, report)

    blocking_issues = route.get("blocking_issues", route.get("blocking_questions", []))
    if not isinstance(blocking_issues, list):
        report.errors.append("blocking_issues must be a list.")
        blocking_issues = []

    evaluation_level = str(route.get("evaluation_level", "")).strip()
    if not evaluation_level:
        report.errors.append("evaluation_level is required.")

    if report.is_default and report.route_status == "scouting":
        report.errors.append("default_route cannot remain in scouting status.")

    if report.route_status == "ready":
        if [str(item).strip() for item in blocking_issues]:
            report.errors.append("ready routes must not have blocking_issues.")
        if not isinstance(route.get("sample_count"), int):
            report.errors.append("ready routes must declare sample_count.")
        if route.get("unit_of_analysis") == "single_cell" and not isinstance(
            route.get("cell_count"), int
        ):
            report.errors.append("ready single-cell routes must declare cell_count.")
    elif report.route_status == "contract_locked_pending_audit":
        if not [str(item).strip() for item in blocking_issues]:
            report.warnings.append(
                "contract_locked_pending_audit route has no blocking_issues; check whether it should be marked ready."
            )

    report.is_valid = not report.errors
    return report


def validate_h4_spec(spec: dict[str, object]) -> H4SpecValidationReport:
    errors: list[str] = []
    warnings: list[str] = []

    candidate_id = str(spec.get("candidate_id", "H4"))
    track_status = str(spec.get("track_status", "active"))
    status_reason = str(spec.get("status_reason", "")).strip()
    dataset_routes = spec.get("dataset_routes", [])
    if not isinstance(dataset_routes, list) or not dataset_routes:
        errors.append("dataset_routes must be a non-empty list.")
        dataset_routes = []

    if not isinstance(spec.get("metrics"), list) or not spec.get("metrics"):
        errors.append("metrics must be a non-empty list.")

    if not isinstance(spec.get("baselines"), list) or not spec.get("baselines"):
        errors.append("baselines must be a non-empty list.")

    if track_status not in _ALLOWED_TRACK_STATUS:
        errors.append(
            f"track_status must be one of {sorted(_ALLOWED_TRACK_STATUS)}, got {track_status!r}."
        )
    if track_status != "active" and not status_reason:
        errors.append("closed or archived H4 specs must declare status_reason.")

    route_reports = [_validate_route(route) for route in dataset_routes if isinstance(route, dict)]
    default_route_count = sum(
        1 for route in dataset_routes if isinstance(route, dict) and route.get("default_route")
    )
    if default_route_count != 1:
        errors.append(f"Exactly one default_route is required, got {default_route_count}.")

    for route_report in route_reports:
        if not route_report.is_valid:
            errors.append(f"Route {route_report.route_id} is invalid.")
        warnings.extend(
            [f"Route {route_report.route_id}: {warning}" for warning in route_report.warnings]
        )

    if track_status == "closed_after_kill_criterion":
        warnings.append(
            "H4 is closed after kill criterion; route metadata is archival until explicitly reopened."
        )

    return H4SpecValidationReport(
        candidate_id=candidate_id,
        route_count=len(route_reports),
        default_route_count=default_route_count,
        is_valid=not errors,
        errors=errors,
        warnings=warnings,
        route_reports=route_reports,
    )
