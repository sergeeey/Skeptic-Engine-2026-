from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from discovery_engine.collectors import fetch_semantic_scholar, fetch_zenodo
from discovery_engine.dqops import normalize_sources
from discovery_engine.schemas import CandidateSeed, SourceRecord
from discovery_engine.skeptic.candidate_families import (
    CandidateFamilyProfile,
    get_candidate_family_profile,
)

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_+-]*")
_STOPWORDS = {
    "and",
    "for",
    "from",
    "into",
    "the",
    "with",
    "using",
    "over",
    "than",
    "against",
    "that",
    "this",
    "still",
}


@dataclass(slots=True)
class Top5SkepticHit:
    source_id: str
    title: str
    domain: str
    source_type: str
    match_score: float
    shared_terms: list[str] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class Top5SkepticReview:
    candidate_id: str
    title: str
    verdict: str
    original_score: float
    revised_score: float
    penalty: float
    query_bundle: list[str] = field(default_factory=list)
    providers_scanned: dict[str, int] = field(default_factory=dict)
    live_records_scanned: int = 0
    challenge_summary: str = ""
    warnings: list[str] = field(default_factory=list)
    top_hits: list[Top5SkepticHit] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "title": self.title,
            "verdict": self.verdict,
            "original_score": self.original_score,
            "revised_score": self.revised_score,
            "penalty": self.penalty,
            "query_bundle": self.query_bundle,
            "providers_scanned": self.providers_scanned,
            "live_records_scanned": self.live_records_scanned,
            "challenge_summary": self.challenge_summary,
            "warnings": self.warnings,
            "top_hits": [hit.to_dict() for hit in self.top_hits],
        }


@dataclass(slots=True)
class Top5SkepticRun:
    reviews: list[Top5SkepticReview]
    live_fetch_queries: int
    live_records_fetched: int
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "reviews": [review.to_dict() for review in self.reviews],
            "live_fetch_queries": self.live_fetch_queries,
            "live_records_fetched": self.live_records_fetched,
            "warnings": self.warnings,
        }


def _tokenize(text: str) -> list[str]:
    return [
        token
        for token in _TOKEN_RE.findall(text.lower())
        if len(token) >= 3 and token not in _STOPWORDS
    ]


def _seed_terms(seed: CandidateSeed, profile: CandidateFamilyProfile) -> set[str]:
    payload = " ".join(
        [
            seed.title,
            seed.why_promising,
            seed.minimal_python_route,
            seed.first_falsification_test,
            seed.next_verification_step,
            " ".join(seed.claimed_datasets),
            " ".join(seed.claimed_tools),
            " ".join(profile.anchor_terms),
            " ".join(profile.downgrade_terms),
        ]
    )
    return set(_tokenize(payload))


def _record_terms(record: SourceRecord) -> set[str]:
    payload = " ".join(
        [
            record.title,
            record.abstract,
            " ".join(record.bridge_tags),
            " ".join(record.claims),
            " ".join(record.methods),
            " ".join(f"{key} {value}" for key, value in record.metadata.items()),
        ]
    )
    return set(_tokenize(payload))


def _query_bundle(seed: CandidateSeed, profile: CandidateFamilyProfile) -> list[str]:
    queries = list(profile.query_templates)
    if seed.claimed_datasets:
        queries.append(f"{profile.query_templates[0]} {seed.claimed_datasets[0]}")
    if seed.claimed_tools:
        queries.append(f"{profile.query_templates[0]} {seed.claimed_tools[0]}")
    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        normalized = " ".join(query.lower().split())
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(query)
    return deduped[:4]


def _fetch_records(
    queries: list[str], max_results_per_source: int
) -> tuple[list[SourceRecord], dict[str, int], list[str]]:
    fetched: list[SourceRecord] = []
    providers: dict[str, int] = {}
    warnings: list[str] = []
    per_query_budget = max(max_results_per_source // max(len(queries), 1), 1)
    for query in queries:
        try:
            scholar = fetch_semantic_scholar(
                query=query,
                max_results=per_query_budget,
                year_range="2016-2026",
            )
            fetched.extend(scholar)
            providers["semantic_scholar"] = providers.get("semantic_scholar", 0) + len(scholar)
        except Exception as exc:
            warnings.append(f"semantic_scholar failed for '{query}': {exc}")
        try:
            zenodo = fetch_zenodo(query=query, max_results=per_query_budget)
            fetched.extend(zenodo)
            providers["zenodo"] = providers.get("zenodo", 0) + len(zenodo)
        except Exception as exc:
            warnings.append(f"zenodo failed for '{query}': {exc}")
    normalized, _ = normalize_sources(fetched)
    return normalized, providers, warnings


def _score_hits(
    seed: CandidateSeed,
    profile: CandidateFamilyProfile,
    records: list[SourceRecord],
) -> list[Top5SkepticHit]:
    seed_terms = _seed_terms(seed, profile)
    anchor_terms = {token for token in _tokenize(" ".join(profile.anchor_terms))}
    downgrade_terms = {token for token in _tokenize(" ".join(profile.downgrade_terms))}
    hits: list[Top5SkepticHit] = []
    for record in records:
        record_terms = _record_terms(record)
        shared_anchor = anchor_terms.intersection(record_terms)
        if not shared_anchor:
            continue
        shared_terms = seed_terms.intersection(record_terms)
        downgrade_overlap = downgrade_terms.intersection(record_terms)
        match_score = round(
            min(
                1.0,
                0.45 * (len(shared_anchor) / max(len(anchor_terms), 1))
                + 0.25 * (len(shared_terms) / max(min(len(seed_terms), 24), 1))
                + 0.15
                * (
                    len(downgrade_overlap) / max(len(downgrade_terms), 1)
                    if downgrade_terms
                    else 0.0
                )
                + 0.15 * record.authority_score,
            ),
            4,
        )
        if match_score < 0.2:
            continue
        rationale: list[str] = []
        if shared_anchor:
            rationale.append(f"anchor overlap: {', '.join(sorted(shared_anchor)[:5])}")
        if downgrade_overlap:
            rationale.append(f"downgrade overlap: {', '.join(sorted(downgrade_overlap)[:4])}")
        if shared_terms:
            rationale.append(f"shared terms: {', '.join(sorted(shared_terms)[:6])}")
        if record.authority_score >= 0.55:
            rationale.append(f"authority_score={record.authority_score:.2f}")
        hits.append(
            Top5SkepticHit(
                source_id=record.id,
                title=record.title,
                domain=record.domain,
                source_type=record.source_type.value,
                match_score=match_score,
                shared_terms=sorted(shared_terms)[:8],
                rationale=rationale,
            )
        )
    return sorted(hits, key=lambda item: item.match_score, reverse=True)


def review_top5_candidates(
    seeds: list[CandidateSeed],
    *,
    max_live_results_per_source: int = 6,
) -> Top5SkepticRun:
    reviews: list[Top5SkepticReview] = []
    warnings: list[str] = []
    live_fetch_queries = 0
    live_records_fetched = 0

    for seed in seeds:
        profile = get_candidate_family_profile(seed.id)
        if profile is None:
            reviews.append(
                Top5SkepticReview(
                    candidate_id=seed.id,
                    title=seed.title,
                    verdict="no_family_profile",
                    original_score=seed.claimed_discovery_score,
                    revised_score=seed.claimed_discovery_score,
                    penalty=0.0,
                    challenge_summary="No candidate-family skeptic profile exists for this seed.",
                    warnings=["missing family profile"],
                )
            )
            continue

        queries = _query_bundle(seed, profile)
        live_fetch_queries += len(queries)
        records, providers, fetch_warnings = _fetch_records(queries, max_live_results_per_source)
        live_records_fetched += len(records)
        hits = _score_hits(seed, profile, records)
        strong_hits = [hit for hit in hits if hit.match_score >= 0.28]
        strongest = strong_hits[0].match_score if strong_hits else 0.0

        if strongest >= 0.45 or len(strong_hits) >= 4:
            verdict = "likely_known"
        elif strong_hits:
            verdict = "needs_review"
        else:
            verdict = "survives_initial_skeptic_pass"

        penalty = 0.0
        if verdict == "needs_review":
            penalty = min(1.4, 0.4 + 1.6 * strongest + 0.1 * max(len(strong_hits) - 1, 0))
        if verdict == "likely_known":
            penalty = min(2.5, 1.0 + 2.0 * strongest + 0.15 * max(len(strong_hits) - 1, 0))
        revised_score = round(max(0.5, seed.claimed_discovery_score - penalty), 2)

        if strong_hits:
            summary = (
                f"Skeptic found {len(strong_hits)} family-level prior-art hits; strongest overlap "
                f"{strongest:.2f}. Score downgraded by {penalty:.2f}."
            )
        else:
            summary = "No strong family-level prior-art hits were found in the targeted sources."

        reviews.append(
            Top5SkepticReview(
                candidate_id=seed.id,
                title=seed.title,
                verdict=verdict,
                original_score=seed.claimed_discovery_score,
                revised_score=revised_score,
                penalty=round(penalty, 4),
                query_bundle=queries,
                providers_scanned=providers,
                live_records_scanned=len(records),
                challenge_summary=summary,
                warnings=fetch_warnings,
                top_hits=strong_hits[:5],
            )
        )

    if live_records_fetched < 20:
        warnings.append(
            "Top5 skeptic coverage is still shallow; too few live records were fetched."
        )

    return Top5SkepticRun(
        reviews=reviews,
        live_fetch_queries=live_fetch_queries,
        live_records_fetched=live_records_fetched,
        warnings=warnings,
    )


def write_top5_skeptic_outputs(
    run: Top5SkepticRun,
    *,
    review_output_path: Path,
    markdown_output_path: Path,
) -> None:
    review_output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
    review_output_path.write_text(json.dumps(run.to_dict(), indent=2), encoding="utf-8")

    lines = [
        "# Top-5 Skeptic Latest",
        "",
        "## Summary",
        "",
        f"- live targeted queries executed: {run.live_fetch_queries}",
        f"- live records fetched: {run.live_records_fetched}",
    ]
    if run.warnings:
        lines.extend(["- warnings:"] + [f"  - {warning}" for warning in run.warnings])

    lines.extend(["", "## Reviews", ""])
    ordered = sorted(
        run.reviews, key=lambda item: (item.penalty, item.original_score), reverse=True
    )
    for review in ordered:
        lines.extend(
            [
                f"### {review.candidate_id}",
                "",
                f"- title: {review.title}",
                f"- verdict: `{review.verdict}`",
                f"- score: {review.original_score:.2f} -> {review.revised_score:.2f}",
                f"- queries: {' || '.join(review.query_bundle) or 'none'}",
                (
                    f"- live records scanned: {review.live_records_scanned} | "
                    f"providers: {review.providers_scanned or {}}"
                ),
                f"- summary: {review.challenge_summary}",
            ]
        )
        if review.warnings:
            lines.append("- fetch warnings:")
            for warning in review.warnings[:3]:
                lines.append(f"  - {warning}")
        if review.top_hits:
            lines.append("- top hits:")
            for hit in review.top_hits[:3]:
                lines.append(
                    f"  - {hit.source_id} | score={hit.match_score:.2f} | {hit.title} | {'; '.join(hit.rationale)}"
                )
        lines.append("")

    markdown_output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
