from __future__ import annotations

from dataclasses import dataclass, field

from discovery_engine.schemas import SourceRecord


def _canonical_title(title: str) -> str:
    return " ".join(title.lower().split())


@dataclass(slots=True)
class DQOpsReport:
    total_input: int
    kept: int
    deduplicated: int
    duplicates: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def normalize_sources(records: list[SourceRecord]) -> tuple[list[SourceRecord], DQOpsReport]:
    seen_titles: dict[str, str] = {}
    normalized: list[SourceRecord] = []
    duplicates: list[str] = []
    warnings: list[str] = []

    for record in records:
        canonical = _canonical_title(record.title)
        if canonical in seen_titles:
            duplicates.append(record.id)
            continue

        seen_titles[canonical] = record.id

        if record.authority_score < 0.4:
            warnings.append(f"{record.id}: low authority score")
        if record.bias_index > 0.6:
            warnings.append(f"{record.id}: elevated bias index")
        if record.metadata.get("provenance") == "user_requirements":
            warnings.append(f"{record.id}: internal planning source, not external evidence")
        if record.metadata.get("provenance") == "local_seed_document":
            warnings.append(
                f"{record.id}: local seed document requires source-level verification later"
            )
        if record.metadata.get("provenance") == "seed_domain_note":
            warnings.append(
                f"{record.id}: domain seed note is a planning scaffold, not external evidence"
            )

        normalized.append(record)

    report = DQOpsReport(
        total_input=len(records),
        kept=len(normalized),
        deduplicated=len(duplicates),
        duplicates=duplicates,
        warnings=warnings,
    )
    return normalized, report
