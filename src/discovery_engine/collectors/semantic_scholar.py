"""Semantic Scholar API collector — the KEY external source (citation counts)."""

from __future__ import annotations

import math
from urllib.parse import quote, urlencode

from discovery_engine.collectors._domain_mapper import map_domain
from discovery_engine.collectors._http import RateLimiter, fetch_json
from discovery_engine.collectors._tag_extractor import extract_bridge_tags
from discovery_engine.enums import SourceType
from discovery_engine.schemas import SourceRecord

_S2_BASE = "https://api.semanticscholar.org/graph/v1/paper/search"
_S2_FIELDS = (
    "paperId,title,abstract,authors,year,citationCount,fieldsOfStudy,tldr,openAccessPdf,externalIds"
)
_S2_RATE_LIMITER = RateLimiter(min_interval=1.1)


def _citation_authority(citation_count: int) -> float:
    """Logarithmic mapping: 0→0.1, 10→0.3, 100→0.5, 1000→0.7, 10000+→0.9."""
    if citation_count <= 0:
        return 0.1
    raw = 0.1 + 0.2 * math.log10(max(citation_count, 1))
    return round(min(raw, 0.95), 3)


def _year_novelty(year: int | None) -> float:
    """Recent papers score higher. 2026→0.9, 2024→0.7, 2020→0.4, <2015→0.2."""
    if year is None:
        return 0.3
    age = max(0, 2026 - year)
    return round(max(0.1, min(0.9, 0.9 - age * 0.1)), 2)


def _format_authors(authors: list[dict[str, str]]) -> str:
    names = [a.get("name", "") for a in (authors or []) if a.get("name")]
    if len(names) <= 3:
        return "; ".join(names)
    return f"{names[0]}; {names[1]}; ... ({len(names)} authors)"


def fetch_semantic_scholar(
    *,
    query: str,
    max_results: int = 100,
    year_range: str | None = None,
) -> list[SourceRecord]:
    """Fetch papers from Semantic Scholar graph API.

    Args:
        query: Search query string.
        max_results: Maximum papers to return (API caps at 1000).
        year_range: Optional year filter, e.g. ``"2020-2026"``.

    Returns:
        List of SourceRecord objects.
    """
    records: list[SourceRecord] = []
    offset = 0
    warnings: list[str] = []

    while offset < max_results:
        limit = min(100, max_results - offset)
        params: dict[str, str | int] = {
            "query": query,
            "limit": limit,
            "offset": offset,
            "fields": _S2_FIELDS,
        }
        if year_range:
            params["year"] = year_range

        url = f"{_S2_BASE}?{urlencode(params, quote_via=quote)}"

        try:
            data = fetch_json(url, rate_limiter=_S2_RATE_LIMITER)
        except Exception as exc:
            warnings.append(f"Semantic Scholar page offset={offset} failed: {exc}")
            break

        papers = data.get("data") or []
        if not papers:
            break

        for paper in papers:
            paper_id = paper.get("paperId", "")
            title = (paper.get("title") or "").strip()
            if not paper_id or not title:
                continue

            abstract = paper.get("abstract") or ""
            tldr = (paper.get("tldr") or {}).get("text", "")
            best_abstract = abstract if abstract else tldr

            fields_of_study = paper.get("fieldsOfStudy") or []
            citation_count = paper.get("citationCount") or 0
            year = paper.get("year")
            external_ids = paper.get("externalIds") or {}
            doi = external_ids.get("DOI", "")
            pdf_url = (paper.get("openAccessPdf") or {}).get("url", "")

            records.append(
                SourceRecord(
                    id=f"s2:{paper_id}",
                    title=title,
                    domain=map_domain(fields_of_study),
                    source_type=SourceType.PAPER,
                    abstract=best_abstract,
                    bridge_tags=extract_bridge_tags(best_abstract, extra_keywords=fields_of_study),
                    authority_score=_citation_authority(citation_count),
                    novelty_factor=_year_novelty(year),
                    bias_index=0.15,
                    citations=[doi] if doi else [],
                    metadata={
                        "paperId": paper_id,
                        "doi": doi,
                        "year": str(year or ""),
                        "citationCount": str(citation_count),
                        "authors": _format_authors(paper.get("authors", [])),
                        "openAccessPdf": pdf_url,
                        "fieldsOfStudy": ", ".join(fields_of_study),
                        "provenance": "semantic_scholar_api",
                    },
                )
            )

        offset += len(papers)
        if data.get("next") is None:
            break

    return records
