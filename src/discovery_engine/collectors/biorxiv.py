"""bioRxiv API collector for preprints."""

from __future__ import annotations

from discovery_engine.collectors._domain_mapper import map_domain
from discovery_engine.collectors._http import RateLimiter, fetch_json
from discovery_engine.collectors._tag_extractor import extract_bridge_tags
from discovery_engine.enums import SourceType
from discovery_engine.schemas import SourceRecord

_BIORXIV_BASE = "https://api.biorxiv.org/details/biorxiv"
_BIORXIV_RATE_LIMITER = RateLimiter(min_interval=0.5)


def _format_authors(authors: str) -> str:
    """Shorten long author lists."""
    parts = [a.strip() for a in authors.split(";") if a.strip()]
    if len(parts) <= 3:
        return "; ".join(parts)
    return f"{parts[0]}; {parts[1]}; ... ({len(parts)} authors)"


def fetch_biorxiv(
    *,
    interval: str = "2025-01-01/2026-03-26",
    subject: str | None = None,
    max_results: int = 100,
) -> list[SourceRecord]:
    """Fetch preprints from bioRxiv API within a date interval.

    Args:
        interval: Date range as ``"YYYY-MM-DD/YYYY-MM-DD"``.
        subject: Optional bioRxiv category filter (e.g. ``"bioinformatics"``).
        max_results: Maximum preprints to return.

    Returns:
        List of SourceRecord objects.
    """
    records: list[SourceRecord] = []
    cursor = 0

    while cursor < max_results:
        url = f"{_BIORXIV_BASE}/{interval}/{cursor}"

        try:
            data = fetch_json(url, rate_limiter=_BIORXIV_RATE_LIMITER)
        except Exception as exc:
            # Partial failure: stop pagination, keep what we have.
            break

        collection = data.get("collection") or []
        if not collection:
            break

        for item in collection:
            if len(records) >= max_results:
                break

            doi = (item.get("doi") or "").strip()
            title = (item.get("title") or "").strip()
            if not doi or not title:
                continue

            category = (item.get("category") or "").strip()
            if subject and category.lower() != subject.lower():
                continue

            abstract = (item.get("abstract") or "").strip()
            published_journal = (item.get("published") or "NA").strip()
            is_published = published_journal != "NA" and published_journal != ""

            records.append(
                SourceRecord(
                    id=f"biorxiv:{doi}",
                    title=title,
                    domain=map_domain([category]),
                    source_type=SourceType.PREPRINT,
                    abstract=abstract,
                    bridge_tags=extract_bridge_tags(abstract),
                    authority_score=0.65 if is_published else 0.4,
                    novelty_factor=0.7,
                    bias_index=0.3,
                    citations=[f"doi:{doi}"],
                    metadata={
                        "doi": doi,
                        "date": item.get("date", ""),
                        "category": category,
                        "authors": _format_authors(item.get("authors", "")),
                        "published_journal": published_journal,
                        "provenance": "biorxiv_api",
                    },
                )
            )

        cursor += len(collection)
        # bioRxiv returns empty collection when no more pages.
        if len(collection) < 30:
            break

    return records
