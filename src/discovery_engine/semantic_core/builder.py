from __future__ import annotations

from dataclasses import dataclass

from discovery_engine.schemas import SourceRecord


@dataclass(frozen=True, slots=True)
class SemanticProfile:
    source_id: str
    domain: str
    methods: tuple[str, ...]
    mechanisms: tuple[str, ...]
    open_questions: tuple[str, ...]
    bridge_tags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CrossDomainLink:
    source_a: str
    source_b: str
    domain_a: str
    domain_b: str
    shared_tags: tuple[str, ...]
    transferable_methods: tuple[str, ...]
    rationale: str
    link_score: float


def _normalized_items(values: list[str]) -> tuple[str, ...]:
    return tuple(sorted({value.strip().lower() for value in values if value.strip()}))


def build_semantic_profiles(records: list[SourceRecord]) -> list[SemanticProfile]:
    profiles: list[SemanticProfile] = []
    for record in records:
        profiles.append(
            SemanticProfile(
                source_id=record.id,
                domain=record.domain,
                methods=_normalized_items(record.methods),
                mechanisms=_normalized_items(record.mechanisms),
                open_questions=_normalized_items(record.open_questions),
                bridge_tags=_normalized_items(record.bridge_tags),
            )
        )
    return profiles


def _shared_terms(profile_a: SemanticProfile, profile_b: SemanticProfile) -> tuple[str, ...]:
    return tuple(sorted(set(profile_a.bridge_tags).intersection(profile_b.bridge_tags)))


def _transferable_methods(profile_a: SemanticProfile, profile_b: SemanticProfile) -> tuple[str, ...]:
    return tuple(sorted(set(profile_a.methods).union(profile_b.methods)))


def find_cross_domain_links(
    profiles: list[SemanticProfile],
    source_index: dict[str, SourceRecord],
) -> list[CrossDomainLink]:
    links: list[CrossDomainLink] = []

    for index, profile_a in enumerate(profiles):
        for profile_b in profiles[index + 1 :]:
            if profile_a.domain == profile_b.domain:
                continue

            shared_tags = _shared_terms(profile_a, profile_b)
            if not shared_tags:
                continue

            record_a = source_index[profile_a.source_id]
            record_b = source_index[profile_b.source_id]
            transferable_methods = _transferable_methods(profile_a, profile_b)
            score = round(
                (
                    len(shared_tags) / max(len(set(profile_a.bridge_tags).union(profile_b.bridge_tags)), 1)
                    + (record_a.novelty_factor + record_b.novelty_factor) / 2
                )
                / 2,
                4,
            )
            rationale = (
                f"Shared tags {', '.join(shared_tags)} suggest that methods from {profile_a.domain} "
                f"may transfer into {profile_b.domain}, or vice versa."
            )
            links.append(
                CrossDomainLink(
                    source_a=profile_a.source_id,
                    source_b=profile_b.source_id,
                    domain_a=profile_a.domain,
                    domain_b=profile_b.domain,
                    shared_tags=shared_tags,
                    transferable_methods=transferable_methods,
                    rationale=rationale,
                    link_score=score,
                )
            )

    return sorted(links, key=lambda item: item.link_score, reverse=True)
