from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

from discovery_engine.collectors import fetch_semantic_scholar, fetch_zenodo
from discovery_engine.dqops import normalize_sources
from discovery_engine.schemas import HypothesisCard, SourceRecord

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_+-]*")
_TRANSFER_METHOD_RE = re.compile(r"^Transfer\s+(.+?)\s+from\s+", re.IGNORECASE)
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "beyond",
    "by",
    "for",
    "from",
    "if",
    "in",
    "into",
    "is",
    "of",
    "on",
    "or",
    "over",
    "than",
    "that",
    "the",
    "their",
    "then",
    "this",
    "to",
    "use",
    "via",
    "vs",
    "with",
}
_GENERIC_ANCHOR_TOKENS = {
    "analysis",
    "baseline",
    "biology",
    "control",
    "data",
    "dataset",
    "design",
    "discovery",
    "evidence",
    "graph",
    "hypothesis",
    "information",
    "learning",
    "materials",
    "model",
    "models",
    "network",
    "prediction",
    "predictive",
    "problem",
    "problems",
    "properties",
    "property",
    "science",
    "simple",
    "systems",
    "theory",
    "transfer",
}
_DOMAIN_QUERY_TERMS = {
    "biology": "biology",
    "materials_science": "materials science",
    "control_information_theory": "control theory information theory",
    "interdisciplinary": "interdisciplinary science",
}
_DOMAIN_PAIR_QUERY_FRAMES = {
    ("biology", "materials_science"): [
        "{method} materials science benchmark",
        "{method} materials property prediction",
        "bioinspired materials {method}",
    ],
    ("materials_science", "biology"): [
        "{method} biology benchmark",
        "{method} biological networks",
        "materials informed biology {method}",
    ],
    ("biology", "control_information_theory"): [
        "{method} biological systems control",
        "systems biology {method}",
        "{method} state estimation biological data",
    ],
    ("control_information_theory", "biology"): [
        "{method} biological systems benchmark",
        "{method} gene regulatory network",
        "{method} biological state estimation",
    ],
    ("materials_science", "control_information_theory"): [
        "{method} materials science control",
        "{method} materials dynamical systems",
        "{method} materials state estimation",
    ],
    ("control_information_theory", "materials_science"): [
        "{method} materials science benchmark",
        "{method} materials process control",
        "{method} materials uncertainty estimation",
    ],
}
_BRIDGE_TAG_QUERY_TERMS = {
    "control": ["control theory", "dynamical systems", "output feedback"],
    "estimation": ["state estimation", "kalman filter", "observer"],
    "feedback": ["feedback control", "closed loop", "controller"],
    "graph": ["graph neural network", "message passing", "graph learning"],
    "information_theory": [
        "information bottleneck",
        "mutual information",
        "representation learning",
    ],
    "optimization": ["optimization", "bayesian optimization", "active learning"],
    "topology": ["topological data analysis", "persistent homology", "topological descriptors"],
    "surrogates": ["surrogate model", "reduced-order model", "proxy benchmark"],
    "mof": ["metal-organic framework", "MOF benchmark", "reticular chemistry"],
    "stability": ["stability prediction", "degradation benchmark", "phase stability"],
    "single_cell": ["single-cell", "single-cell RNA", "cell state transition"],
    "llps": [
        "liquid-liquid phase separation",
        "condensate dynamics",
        "intrinsically disordered protein",
    ],
    "koopman": ["koopman operator", "slow modes", "dynamical mode decomposition"],
}


@dataclass(slots=True)
class SkepticHit:
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
class SkepticReview:
    card_id: str
    title: str
    verdict: str
    original_novelty_score: float
    revised_novelty_score: float
    original_confidence_score: float
    revised_confidence_score: float
    novelty_penalty: float
    confidence_penalty: float
    challenge_summary: str
    live_query: str = ""
    live_records_scanned: int = 0
    providers_scanned: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    top_hits: list[SkepticHit] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "card_id": self.card_id,
            "title": self.title,
            "verdict": self.verdict,
            "original_novelty_score": self.original_novelty_score,
            "revised_novelty_score": self.revised_novelty_score,
            "original_confidence_score": self.original_confidence_score,
            "revised_confidence_score": self.revised_confidence_score,
            "novelty_penalty": self.novelty_penalty,
            "confidence_penalty": self.confidence_penalty,
            "challenge_summary": self.challenge_summary,
            "live_query": self.live_query,
            "live_records_scanned": self.live_records_scanned,
            "providers_scanned": self.providers_scanned,
            "warnings": self.warnings,
            "top_hits": [hit.to_dict() for hit in self.top_hits],
        }


@dataclass(slots=True)
class SkepticRun:
    challenged_cards: list[HypothesisCard]
    reviews: list[SkepticReview]
    prior_art_count: int
    manifests_used: list[str]
    live_fetch_queries: int = 0
    live_records_fetched: int = 0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "challenged_cards": [card.to_dict() for card in self.challenged_cards],
            "reviews": [review.to_dict() for review in self.reviews],
            "prior_art_count": self.prior_art_count,
            "manifests_used": list(self.manifests_used),
            "live_fetch_queries": self.live_fetch_queries,
            "live_records_fetched": self.live_records_fetched,
            "warnings": list(self.warnings),
        }


@dataclass(slots=True)
class LivePriorArtFetch:
    query: str
    records: list[SourceRecord]
    providers_scanned: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def _tokenize(text: str) -> list[str]:
    return [
        token
        for token in _TOKEN_RE.findall(text.lower())
        if len(token) >= 3 and token not in _STOPWORDS
    ]


def _record_terms(record: SourceRecord) -> set[str]:
    payload = " ".join(
        [
            record.title,
            record.abstract,
            " ".join(record.claims),
            " ".join(record.methods),
            " ".join(record.mechanisms),
            " ".join(record.open_questions),
            " ".join(record.bridge_tags),
            " ".join(record.limitations),
            " ".join(f"{key} {value}" for key, value in record.metadata.items()),
        ]
    )
    return set(_tokenize(payload))


def _card_terms(card: HypothesisCard, source_index: dict[str, SourceRecord]) -> set[str]:
    evidence_records = [
        source_index[item] for item in card.evidence_source_ids if item in source_index
    ]
    payload = [
        card.title,
        card.core_mechanism,
        card.inferred_bridge,
        card.speculative_hypothesis,
        card.python_mvp,
        card.first_falsification_test,
        " ".join(card.fields_bridged),
    ]
    for record in evidence_records:
        payload.extend(
            [
                record.title,
                " ".join(record.methods),
                " ".join(record.mechanisms),
                " ".join(record.open_questions),
                " ".join(record.bridge_tags),
            ]
        )
    return set(_tokenize(" ".join(payload)))


def _card_bridge_tags(card: HypothesisCard, source_index: dict[str, SourceRecord]) -> set[str]:
    tags: set[str] = set()
    for source_id in card.evidence_source_ids:
        record = source_index.get(source_id)
        if record is not None:
            tags.update(tag.strip().lower() for tag in record.bridge_tags if tag.strip())
    return tags


def _card_anchor_terms(card: HypothesisCard, source_index: dict[str, SourceRecord]) -> set[str]:
    evidence_records = [
        source_index[item] for item in card.evidence_source_ids if item in source_index
    ]
    anchors = set(_tokenize(card.title))
    for record in evidence_records:
        anchors.update(_tokenize(" ".join(record.methods)))
        anchors.update(_tokenize(" ".join(record.mechanisms)))
        anchors.update(_tokenize(" ".join(record.bridge_tags)))
    return {token for token in anchors if token not in _GENERIC_ANCHOR_TOKENS}


def _transfer_method(card: HypothesisCard) -> str:
    match = _TRANSFER_METHOD_RE.match(card.title.strip())
    if not match:
        return ""
    return match.group(1).strip().replace("_", " ")


def _domain_pair(card: HypothesisCard) -> tuple[str, str]:
    if len(card.fields_bridged) >= 2:
        return card.fields_bridged[0], card.fields_bridged[1]
    field = card.fields_bridged[0] if card.fields_bridged else "interdisciplinary"
    return field, field


def _query_terms(card: HypothesisCard, source_index: dict[str, SourceRecord]) -> list[str]:
    terms: list[str] = []
    method = _transfer_method(card)
    if method:
        terms.append(method)
    for field_name in card.fields_bridged:
        if field_name in _DOMAIN_QUERY_TERMS:
            terms.append(_DOMAIN_QUERY_TERMS[field_name])

    evidence_records = [
        source_index[item] for item in card.evidence_source_ids if item in source_index
    ]
    for record in evidence_records:
        if record.methods:
            terms.append(record.methods[0].replace("_", " "))
        if record.bridge_tags:
            terms.extend(tag.replace("_", " ") for tag in record.bridge_tags[:2])
        if record.open_questions:
            terms.extend(_tokenize(record.open_questions[0])[:2])

    anchors = sorted(_card_anchor_terms(card, source_index))
    terms.extend(item.replace("_", " ") for item in anchors[:3])

    deduped: list[str] = []
    seen: set[str] = set()
    for term in terms:
        normalized = " ".join(term.lower().split())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(term)
    return deduped[:8]


def build_targeted_queries(
    card: HypothesisCard, source_index: dict[str, SourceRecord]
) -> list[str]:
    base_terms = _query_terms(card, source_index)
    method = _transfer_method(card) or "computational method"
    domain_a, domain_b = _domain_pair(card)
    evidence_records = [
        source_index[item] for item in card.evidence_source_ids if item in source_index
    ]

    queries: list[str] = []
    if base_terms:
        queries.append(" ".join(base_terms[:8]))

    frames = _DOMAIN_PAIR_QUERY_FRAMES.get((domain_a, domain_b), [])
    tag_terms: list[str] = []
    for record in evidence_records:
        for tag in record.bridge_tags[:3]:
            tag_terms.extend(_BRIDGE_TAG_QUERY_TERMS.get(tag, []))

    dedup_tag_terms: list[str] = []
    seen_tags: set[str] = set()
    for term in tag_terms:
        normalized = " ".join(term.lower().split())
        if normalized in seen_tags:
            continue
        seen_tags.add(normalized)
        dedup_tag_terms.append(term)

    for frame in frames[:2]:
        query = frame.format(method=method)
        if dedup_tag_terms:
            query = f"{query} {dedup_tag_terms[0]}"
        queries.append(query)

    if dedup_tag_terms:
        queries.append(
            " ".join(
                [
                    method,
                    _DOMAIN_QUERY_TERMS.get(domain_b, domain_b.replace("_", " ")),
                    dedup_tag_terms[0],
                    dedup_tag_terms[1] if len(dedup_tag_terms) > 1 else "",
                ]
            ).strip()
        )

    deduped_queries: list[str] = []
    seen_queries: set[str] = set()
    for query in queries:
        normalized = " ".join(query.lower().split())
        if not normalized or normalized in seen_queries:
            continue
        seen_queries.add(normalized)
        deduped_queries.append(query)
    return deduped_queries[:3]


def build_targeted_query(card: HypothesisCard, source_index: dict[str, SourceRecord]) -> str:
    return " || ".join(build_targeted_queries(card, source_index))


def _rationale(
    shared_terms: set[str],
    shared_anchor_terms: set[str],
    shared_bridge_tags: set[str],
    domain_match: bool,
    record: SourceRecord,
) -> list[str]:
    reasons: list[str] = []
    if domain_match:
        reasons.append("domain overlap with candidate fields")
    if shared_anchor_terms:
        reasons.append(f"anchor overlap: {', '.join(sorted(shared_anchor_terms)[:4])}")
    if shared_bridge_tags:
        reasons.append(f"shared bridge tags: {', '.join(sorted(shared_bridge_tags)[:4])}")
    if shared_terms:
        reasons.append(f"shared terms: {', '.join(sorted(shared_terms)[:6])}")
    if record.authority_score >= 0.55:
        reasons.append(f"authority_score={record.authority_score:.2f}")
    return reasons


def _score_hit(
    card: HypothesisCard,
    card_terms: set[str],
    card_anchor_terms: set[str],
    card_bridge_tags: set[str],
    record: SourceRecord,
) -> SkepticHit | None:
    record_terms = _record_terms(record)
    if not record_terms:
        return None

    shared_terms = card_terms.intersection(record_terms)
    shared_anchor_terms = card_anchor_terms.intersection(record_terms)
    shared_bridge_tags = card_bridge_tags.intersection(
        {tag.strip().lower() for tag in record.bridge_tags if tag.strip()}
    )
    domain_match = record.domain in {field.lower() for field in card.fields_bridged}

    if not shared_anchor_terms and not shared_bridge_tags:
        return None

    term_overlap = len(shared_terms) / max(min(len(card_terms), 24), 1)
    anchor_overlap = (
        len(shared_anchor_terms) / max(len(card_anchor_terms), 1) if card_anchor_terms else 0.0
    )
    bridge_overlap = (
        len(shared_bridge_tags) / max(len(card_bridge_tags), 1) if card_bridge_tags else 0.0
    )
    domain_bonus = 1.0 if domain_match else 0.35 if record.domain == "interdisciplinary" else 0.0
    authority_bonus = record.authority_score

    match_score = round(
        min(
            1.0,
            0.45 * anchor_overlap
            + 0.2 * term_overlap
            + 0.2 * bridge_overlap
            + 0.05 * domain_bonus
            + 0.1 * authority_bonus,
        ),
        4,
    )
    if match_score < 0.16:
        return None

    return SkepticHit(
        source_id=record.id,
        title=record.title,
        domain=record.domain,
        source_type=record.source_type.value,
        match_score=match_score,
        shared_terms=sorted(shared_terms)[:8],
        rationale=_rationale(
            shared_terms,
            shared_anchor_terms,
            shared_bridge_tags,
            domain_match,
            record,
        ),
    )


def fetch_targeted_prior_art(
    card: HypothesisCard,
    *,
    source_index: dict[str, SourceRecord],
    max_results_per_source: int = 4,
) -> LivePriorArtFetch:
    queries = build_targeted_queries(card, source_index)
    query = " || ".join(queries)
    providers_scanned: dict[str, int] = {}
    warnings: list[str] = []
    fetched: list[SourceRecord] = []

    if not queries:
        return LivePriorArtFetch(
            query="",
            records=[],
            providers_scanned=providers_scanned,
            warnings=["Could not build a targeted query for this card."],
        )

    query_count = max(len(queries), 1)
    base_budget = max(max_results_per_source // query_count, 1)
    remainder = max_results_per_source % query_count

    for index, query_variant in enumerate(queries):
        query_budget = base_budget + (1 if index < remainder else 0)
        try:
            scholar_records = fetch_semantic_scholar(
                query=query_variant,
                max_results=query_budget,
                year_range="2016-2026",
            )
            providers_scanned["semantic_scholar"] = providers_scanned.get(
                "semantic_scholar", 0
            ) + len(scholar_records)
            fetched.extend(scholar_records)
        except Exception as exc:
            warnings.append(f"semantic_scholar failed for '{query_variant}': {exc}")

        try:
            zenodo_records = fetch_zenodo(query=query_variant, max_results=query_budget)
            providers_scanned["zenodo"] = providers_scanned.get("zenodo", 0) + len(zenodo_records)
            fetched.extend(zenodo_records)
        except Exception as exc:
            warnings.append(f"zenodo failed for '{query_variant}': {exc}")

    normalized, _ = normalize_sources(fetched)
    return LivePriorArtFetch(
        query=query,
        records=normalized,
        providers_scanned=providers_scanned,
        warnings=warnings,
    )


def _review_from_hits(
    card: HypothesisCard,
    hits: list[SkepticHit],
    *,
    live_query: str = "",
    live_records_scanned: int = 0,
    providers_scanned: dict[str, int] | None = None,
    fetch_warnings: list[str] | None = None,
) -> SkepticReview:
    strong_hits = [hit for hit in hits if hit.match_score >= 0.28]
    strongest = strong_hits[0].match_score if strong_hits else 0.0

    if strongest >= 0.5 or len(strong_hits) >= 4:
        verdict = "likely_known"
    elif strong_hits:
        verdict = "needs_review"
    else:
        verdict = "survives_initial_skeptic_pass"

    novelty_penalty = 0.0
    confidence_penalty = 0.0
    if verdict == "needs_review":
        novelty_penalty = min(0.3, 0.08 + 0.25 * strongest + 0.03 * max(len(strong_hits) - 1, 0))
        confidence_penalty = min(0.18, 0.05 + 0.15 * strongest)
    if verdict == "likely_known":
        novelty_penalty = min(0.55, 0.2 + 0.35 * strongest + 0.04 * max(len(strong_hits) - 1, 0))
        confidence_penalty = min(0.28, 0.08 + 0.2 * strongest)

    revised_novelty = round(max(0.05, card.novelty_score - novelty_penalty), 2)
    revised_confidence = round(max(0.05, card.confidence_score - confidence_penalty), 2)

    if strong_hits:
        summary = (
            f"Skeptic found {len(strong_hits)} prior-art hits; strongest overlap score "
            f"{strongest:.2f}. Novelty downgraded by {novelty_penalty:.2f}."
        )
    else:
        summary = "No strong prior-art hits were found in the available local or targeted sources."

    return SkepticReview(
        card_id=card.id,
        title=card.title,
        verdict=verdict,
        original_novelty_score=card.novelty_score,
        revised_novelty_score=revised_novelty,
        original_confidence_score=card.confidence_score,
        revised_confidence_score=revised_confidence,
        novelty_penalty=round(novelty_penalty, 4),
        confidence_penalty=round(confidence_penalty, 4),
        challenge_summary=summary,
        live_query=live_query,
        live_records_scanned=live_records_scanned,
        providers_scanned=dict(providers_scanned or {}),
        warnings=list(fetch_warnings or []),
        top_hits=strong_hits[:5],
    )


def challenge_hypotheses(
    cards: list[HypothesisCard],
    *,
    source_index: dict[str, SourceRecord],
    prior_art_records: list[SourceRecord],
    manifests_used: list[str] | None = None,
    max_live_results_per_source: int = 4,
    use_live_fetch: bool = True,
) -> SkepticRun:
    challenged_cards: list[HypothesisCard] = []
    reviews: list[SkepticReview] = []
    warnings: list[str] = []
    manifests_used = manifests_used or []
    live_fetch_queries = 0
    live_records_fetched = 0

    if not prior_art_records:
        warnings.append("No prior-art manifests were available; skeptic pass is shallow.")
    if prior_art_records and len(prior_art_records) < 50:
        warnings.append(
            f"Only {len(prior_art_records)} prior-art records were available; coverage is shallow."
        )

    for card in cards:
        card_terms = _card_terms(card, source_index)
        anchor_terms = _card_anchor_terms(card, source_index)
        bridge_tags = _card_bridge_tags(card, source_index)
        query = ""
        live_fetch = LivePriorArtFetch(query="", records=[])
        if use_live_fetch:
            query = build_targeted_query(card, source_index)
            live_fetch = fetch_targeted_prior_art(
                card,
                source_index=source_index,
                max_results_per_source=max_live_results_per_source,
            )
            live_fetch_queries += 1
            live_records_fetched += len(live_fetch.records)

        hits: list[SkepticHit] = []
        combined_records: list[SourceRecord] = []
        seen_record_ids: set[str] = set()
        for record in [*prior_art_records, *live_fetch.records]:
            if record.id in seen_record_ids:
                continue
            seen_record_ids.add(record.id)
            combined_records.append(record)

        for record in combined_records:
            if record.id in card.evidence_source_ids:
                continue
            hit = _score_hit(card, card_terms, anchor_terms, bridge_tags, record)
            if hit is not None:
                hits.append(hit)

        hits.sort(key=lambda item: item.match_score, reverse=True)
        review = _review_from_hits(
            card,
            hits,
            live_query=live_fetch.query,
            live_records_scanned=len(live_fetch.records),
            providers_scanned=live_fetch.providers_scanned,
            fetch_warnings=live_fetch.warnings,
        )
        reviews.append(review)

        objections = list(card.objections)
        objections.append(f"Skeptic review: {review.challenge_summary}")
        if review.live_query:
            objections.append(
                f"Skeptic targeted query: {review.live_query} (records={review.live_records_scanned})."
            )
        for fetch_warning in review.warnings[:2]:
            objections.append(f"Skeptic fetch warning: {fetch_warning}.")
        for hit in review.top_hits[:2]:
            objections.append(
                f"Potential prior art: {hit.title} ({hit.source_id}, score={hit.match_score:.2f})."
            )

        challenged_cards.append(
            replace(
                card,
                novelty_score=review.revised_novelty_score,
                confidence_score=review.revised_confidence_score,
                objections=objections,
            )
        )

    if reviews and not any(review.top_hits for review in reviews):
        warnings.append(
            "No strong prior-art hits were found for any candidate in the available local or targeted sources."
        )
    if not any(review.providers_scanned.get("semantic_scholar", 0) > 0 for review in reviews):
        warnings.append(
            "Semantic Scholar prior-art evidence is missing; novelty pressure test is incomplete."
        )

    return SkepticRun(
        challenged_cards=challenged_cards,
        reviews=reviews,
        prior_art_count=len(prior_art_records),
        manifests_used=manifests_used,
        live_fetch_queries=live_fetch_queries,
        live_records_fetched=live_records_fetched,
        warnings=warnings,
    )


def write_skeptic_outputs(
    run: SkepticRun,
    *,
    review_output_path: Path,
    challenged_cards_output_path: Path,
    markdown_output_path: Path,
) -> None:
    review_output_path.parent.mkdir(parents=True, exist_ok=True)
    challenged_cards_output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)

    review_output_path.write_text(
        json.dumps(
            {
                "prior_art_count": run.prior_art_count,
                "manifests_used": run.manifests_used,
                "live_fetch_queries": run.live_fetch_queries,
                "live_records_fetched": run.live_records_fetched,
                "warnings": run.warnings,
                "reviews": [review.to_dict() for review in run.reviews],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    challenged_cards_output_path.write_text(
        json.dumps([card.to_dict() for card in run.challenged_cards], indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Skeptic Latest",
        "",
        "## Summary",
        "",
        f"- prior-art records scanned: {run.prior_art_count}",
        f"- manifests used: {', '.join(run.manifests_used) or 'none'}",
        f"- live targeted queries executed: {run.live_fetch_queries}",
        f"- live records fetched: {run.live_records_fetched}",
    ]
    if run.warnings:
        lines.extend(["- warnings:"] + [f"  - {warning}" for warning in run.warnings])

    lines.extend(["", "## Top Reviews", ""])
    ordered_reviews = sorted(
        run.reviews,
        key=lambda item: (item.novelty_penalty, item.confidence_penalty),
        reverse=True,
    )
    for review in ordered_reviews[:10]:
        lines.extend(
            [
                f"### {review.card_id}",
                "",
                f"- title: {review.title}",
                f"- verdict: `{review.verdict}`",
                (
                    f"- novelty: {review.original_novelty_score:.2f} -> "
                    f"{review.revised_novelty_score:.2f}"
                ),
                (
                    f"- confidence: {review.original_confidence_score:.2f} -> "
                    f"{review.revised_confidence_score:.2f}"
                ),
                f"- live query: {review.live_query or 'none'}",
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
                reason = "; ".join(hit.rationale)
                lines.append(
                    f"  - {hit.source_id} | score={hit.match_score:.2f} | {hit.title} | {reason}"
                )
        lines.append("")

    markdown_output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
