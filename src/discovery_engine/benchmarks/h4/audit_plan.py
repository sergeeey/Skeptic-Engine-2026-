from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class H4AuditPlan:
    route_id: str
    accession: str
    track_status: str
    status_reason: str
    route_status: str
    unit_of_analysis: str
    evaluation_level: str
    split_unit: str
    group_keys_for_split: list[str] = field(default_factory=list)
    leakage_keys: list[str] = field(default_factory=list)
    blocking_issues: list[str] = field(default_factory=list)
    audit_checks: list[str] = field(default_factory=list)
    raw_ingress_steps: list[str] = field(default_factory=list)


def build_h4_audit_plan(spec: dict[str, object], route_id: str | None = None) -> H4AuditPlan:
    dataset_routes = spec.get("dataset_routes", [])
    selected_route: dict[str, object] | None = None
    track_status = str(spec.get("track_status", "active"))
    status_reason = str(spec.get("status_reason", ""))

    for route in dataset_routes:
        if not isinstance(route, dict):
            continue
        if route_id and str(route.get("id")) == route_id:
            selected_route = route
            break
        if not route_id and route.get("default_route"):
            selected_route = route
            break

    if selected_route is None:
        raise ValueError(f"Could not resolve H4 route {route_id!r}.")

    route_name = str(selected_route.get("id", "unknown"))
    accession = str(selected_route.get("accession", ""))
    split_unit = str(selected_route.get("split_unit", ""))
    group_keys = [str(item) for item in selected_route.get("group_keys_for_split", [])]
    leakage_keys = [str(item) for item in selected_route.get("leakage_keys", [])]
    blocking_issues = [
        str(item)
        for item in selected_route.get(
            "blocking_issues",
            selected_route.get("blocking_questions", []),
        )
    ]

    audit_checks = [
        f"Verify raw files for accession {accession} are locatable and versioned.",
        "Inventory all metadata columns before choosing any split implementation.",
        f"Confirm that split_unit={split_unit} is actually representable from raw metadata.",
        f"Confirm group_keys_for_split are present and non-degenerate: {', '.join(group_keys)}.",
        f"Check leakage-sensitive fields explicitly: {', '.join(leakage_keys)}.",
        "Audit whether the positive and negative labels are cleanly derivable from raw treatment-state metadata.",
        "Record sample, condition, replicate, and cell counts before any model code is written.",
    ]

    if track_status != "active":
        audit_checks.insert(
            0,
            "Track is closed; treat this audit plan as archival context unless H4 is explicitly reopened.",
        )

    raw_ingress_steps = [
        "Locate or download the raw source bundle and write a provenance manifest.",
        "Compute checksum and record source URL or accession metadata.",
        "Extract a raw file inventory with file sizes and candidate metadata tables.",
        "Run schema inspection on cell metadata and expression matrix pointers only.",
        "Write a raw-to-contract field mapping without training any model.",
        "Emit an audit report that either clears or blocks benchmark ingestion.",
    ]

    return H4AuditPlan(
        route_id=route_name,
        accession=accession,
        track_status=track_status,
        status_reason=status_reason,
        route_status=str(selected_route.get("route_status", "")),
        unit_of_analysis=str(selected_route.get("unit_of_analysis", "")),
        evaluation_level=str(selected_route.get("evaluation_level", "")),
        split_unit=split_unit,
        group_keys_for_split=group_keys,
        leakage_keys=leakage_keys,
        blocking_issues=blocking_issues,
        audit_checks=audit_checks,
        raw_ingress_steps=raw_ingress_steps,
    )
