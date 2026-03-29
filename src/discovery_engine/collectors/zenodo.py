"""Zenodo API collector for datasets, software, and publications."""

from __future__ import annotations

import re
from urllib.parse import quote, urlencode

from discovery_engine.collectors._domain_mapper import map_domain
from discovery_engine.collectors._http import RateLimiter, fetch_json
from discovery_engine.collectors._tag_extractor import extract_bridge_tags
from discovery_engine.enums import SourceType
from discovery_engine.schemas import SourceRecord

_ZENODO_BASE = "https://zenodo.org/api/records"
_ZENODO_RATE_LIMITER = RateLimiter(min_interval=0.5)

_HTML_TAG_RE = re.compile(r"<[^>]+>")

_TYPE_MAP: dict[str, SourceType] = {
    "dataset": SourceType.DATASET,
    "software": SourceType.REPOSITORY,
    "publication": SourceType.PAPER,
    "poster": SourceType.REPORT,
    "presentation": SourceType.REPORT,
    "lesson": SourceType.REPORT,
    "image": SourceType.REPORT,
    "video": SourceType.REPORT,
}


def _strip_html(text: str) -> str:
    return _HTML_TAG_RE.sub("", text).strip()


def _format_creators(creators: list[dict[str, str]]) -> str:
    names = [c.get("name", "") for c in (creators or []) if c.get("name")]
    if len(names) <= 3:
        return "; ".join(names)
    return f"{names[0]}; {names[1]}; ... ({len(names)} creators)"


def fetch_zenodo(
    *,
    query: str,
    resource_type: str | None = None,
    max_results: int = 100,
) -> list[SourceRecord]:
    """Fetch records from Zenodo API.

    Args:
        query: Search query string.
        resource_type: Optional filter (``"dataset"``, ``"publication"``, ``"software"``).
        max_results: Maximum records to return.

    Returns:
        List of SourceRecord objects.
    """
    records: list[SourceRecord] = []
    page = 1

    while len(records) < max_results:
        size = min(100, max_results - len(records))
        params: dict[str, str | int] = {
            "q": query,
            "size": size,
            "page": page,
            "sort": "mostrecent",
        }
        if resource_type:
            params["type"] = resource_type

        url = f"{_ZENODO_BASE}?{urlencode(params, quote_via=quote)}"

        try:
            data = fetch_json(url, rate_limiter=_ZENODO_RATE_LIMITER)
        except Exception:
            break

        hits = (data.get("hits") or {}).get("hits") or []
        if not hits:
            break

        for hit in hits:
            if len(records) >= max_results:
                break

            record_id = str(hit.get("id", ""))
            meta = hit.get("metadata") or {}
            title = (meta.get("title") or "").strip()
            if not record_id or not title:
                continue

            description = _strip_html(meta.get("description") or "")
            keywords = meta.get("keywords") or []
            creators = meta.get("creators") or []
            doi = (meta.get("doi") or "").strip()

            rt = (meta.get("resource_type") or {}).get("type", "")
            source_type = _TYPE_MAP.get(rt, SourceType.REPORT)

            # Zenodo datasets get slightly lower authority; peer-reviewed pubs get more.
            authority = 0.55 if source_type == SourceType.PAPER else 0.45

            records.append(
                SourceRecord(
                    id=f"zenodo:{record_id}",
                    title=title,
                    domain=map_domain(keywords),
                    source_type=source_type,
                    abstract=description[:2000],
                    bridge_tags=extract_bridge_tags(description, extra_keywords=keywords),
                    authority_score=authority,
                    novelty_factor=0.5,
                    bias_index=0.2,
                    citations=[f"doi:{doi}"] if doi else [],
                    metadata={
                        "zenodo_id": record_id,
                        "doi": doi,
                        "resource_type": rt,
                        "keywords": ", ".join(keywords),
                        "creators": _format_creators(creators),
                        "access_right": meta.get("access_right", ""),
                        "provenance": "zenodo_api",
                    },
                )
            )

        # Check for next page.
        links = data.get("links") or {}
        if not links.get("next"):
            break
        page += 1

    return records
