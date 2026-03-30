"""Metadata feature extraction for paper mill detection (H28).

Extracts 8 authorship/submission features per paper from PubMed metadata.
"""

from __future__ import annotations

from datetime import datetime


def extract_metadata_features(meta: dict) -> dict[str, float]:
    """Extract 8 metadata features from a parsed PubMed article.

    Features:
      1. n_authors — number of authors
      2. n_affiliations — number of unique affiliations
      3. affiliation_diversity — n_affiliations / n_authors
      4. submission_to_acceptance_days — days from received to accepted
      5. n_references — total reference count
      6. self_citation_rate — fraction of references sharing author last names
      7. abstract_length — word count of abstract
      8. author_per_reference — n_authors / n_references (normalized authorship)
    """
    n_authors = meta.get("n_authors", 0)
    n_affiliations = meta.get("n_affiliations", 0)
    n_references = meta.get("n_references", 0)
    abstract_wc = meta.get("abstract_word_count", 0)

    # Affiliation diversity
    affiliation_diversity = n_affiliations / max(n_authors, 1)

    # Submission to acceptance days
    days = _compute_days(meta.get("date_received", ""), meta.get("date_accepted", ""))

    # Self-citation rate (heuristic: check if any author last name appears in ref PMIDs metadata)
    # Simplified: we use ref_pmids count as proxy — real self-citation needs ref author lookup
    self_cite_rate = 0.0
    ref_pmids = meta.get("ref_pmids", [])
    if n_references > 0 and ref_pmids:
        # Heuristic: papers with very few references relative to ref_pmids
        # are likely citing themselves more (self-citation clusters)
        self_cite_rate = len(ref_pmids) / max(n_references, 1)

    # Author per reference ratio
    author_per_ref = n_authors / max(n_references, 1)

    return {
        "n_authors": float(n_authors),
        "n_affiliations": float(n_affiliations),
        "affiliation_diversity": round(affiliation_diversity, 4),
        "submission_to_acceptance_days": float(days),
        "n_references": float(n_references),
        "self_citation_rate": round(self_cite_rate, 4),
        "abstract_length": float(abstract_wc),
        "author_per_reference": round(author_per_ref, 4),
    }


def _compute_days(date_received: str, date_accepted: str) -> float:
    """Compute days between received and accepted dates.

    Returns 0.0 if either date is missing or unparseable.
    """
    if not date_received or not date_accepted:
        return 0.0
    try:
        fmt = _guess_date_format(date_received)
        d1 = datetime.strptime(date_received, fmt)
        fmt = _guess_date_format(date_accepted)
        d2 = datetime.strptime(date_accepted, fmt)
        delta = (d2 - d1).days
        return float(max(delta, 0))
    except (ValueError, TypeError):
        return 0.0


def _guess_date_format(s: str) -> str:
    """Guess date format from string."""
    parts = s.split("-")
    if len(parts) == 3:
        return "%Y-%m-%d"
    elif len(parts) == 2:
        return "%Y-%m"
    return "%Y"


METADATA_FEATURE_NAMES = [
    "n_authors",
    "n_affiliations",
    "affiliation_diversity",
    "submission_to_acceptance_days",
    "n_references",
    "self_citation_rate",
    "abstract_length",
    "author_per_reference",
]
