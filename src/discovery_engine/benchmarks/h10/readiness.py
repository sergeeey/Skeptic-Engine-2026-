from __future__ import annotations

from dataclasses import dataclass, field

from discovery_engine.benchmarks.h10.dataset_card import H10DatasetCard
from discovery_engine.benchmarks.h10.mapping import H10MappingReport
from discovery_engine.benchmarks.h10.route_validator import RouteValidationReport


@dataclass(slots=True)
class H10ReadinessReport:
    route_id: str
    is_ready: bool
    blockers: list[str] = field(default_factory=list)


def build_h10_readiness_report(
    route_validation: RouteValidationReport,
    dataset_card: H10DatasetCard,
    mapping_report: H10MappingReport,
) -> H10ReadinessReport:
    blockers: list[str] = []

    if route_validation.missing_required > 0:
        blockers.append("Required route files are missing.")
    if not dataset_card.ready_for_mapping:
        blockers.append("Raw CSV assets do not yet contain enough rows for reproducible mapping.")
    blockers.extend(mapping_report.blockers)
    if mapping_report.row_count == 0:
        blockers.append(
            "No mapped benchmark rows are available for split planning or baseline training."
        )

    deduped_blockers: list[str] = []
    seen: set[str] = set()
    for blocker in blockers:
        if blocker not in seen:
            deduped_blockers.append(blocker)
            seen.add(blocker)

    return H10ReadinessReport(
        route_id=route_validation.route_id,
        is_ready=not deduped_blockers,
        blockers=deduped_blockers,
    )
