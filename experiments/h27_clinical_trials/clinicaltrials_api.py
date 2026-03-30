"""ClinicalTrials.gov API v2 wrapper for H27 experiment.

Fetches completed trials with posted results and extracts p-values
from structured outcome measures.

API docs: https://clinicaltrials.gov/data-api/api
"""

from __future__ import annotations

import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_BASE = "https://clinicaltrials.gov/api/v2/studies"
USER_AGENT = "SkepticEngine/0.1"
RATE_LIMIT_SLEEP = 0.5


def _api_request(params: dict) -> dict:
    """Make a single API request with rate limiting and error handling."""
    url = f"{API_BASE}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        time.sleep(RATE_LIMIT_SLEEP)
        return data
    except (HTTPError, URLError, TimeoutError) as e:
        print(f"    API error: {e}")
        time.sleep(2.0)
        return {}


def search_trials_with_results(
    max_results: int = 500,
    condition: str = "",
) -> list[dict]:
    """Search for completed trials that have posted results.

    Returns list of study dicts with protocolSection and resultsSection.
    """
    all_studies: list[dict] = []
    page_token = None

    # WHY: do NOT use fields= parameter — it excludes resultsSection which contains p-values
    while len(all_studies) < max_results:
        params: dict = {
            "query.term": condition if condition else "",
            "filter.overallStatus": "COMPLETED",
            "filter.advanced": "AREA[HasResults]true",
            "pageSize": min(20, max_results - len(all_studies)),
            "format": "json",
        }
        if page_token:
            params["pageToken"] = page_token

        data = _api_request(params)
        if not data:
            break

        studies = data.get("studies", [])
        if not studies:
            break

        all_studies.extend(studies)
        page_token = data.get("nextPageToken")
        if not page_token:
            break

        print(f"    Fetched {len(all_studies)} studies...")

    return all_studies[:max_results]


def fetch_trial_results(nct_id: str) -> dict:
    """Fetch full study record including results for a single trial."""
    params = {
        "query.id": nct_id,
        "format": "json",
    }
    data = _api_request(params)
    studies = data.get("studies", [])
    return studies[0] if studies else {}


def extract_pvalues_from_trial(study: dict) -> list[float]:
    """Extract p-values from structured outcome measure analyses.

    Handles formats: "0.023", "<0.001", ">0.05", "NS", "p=0.012"
    """
    p_values: list[float] = []

    results_section = study.get("resultsSection", {})
    outcome_module = results_section.get("outcomeMeasuresModule", {})
    outcomes = outcome_module.get("outcomeMeasures", [])

    for outcome in outcomes:
        analyses = outcome.get("analyses", [])
        for analysis in analyses:
            p_str = analysis.get("pValue", "")
            p = _parse_pvalue_string(p_str)
            if p is not None:
                p_values.append(p)

    return p_values


def _parse_pvalue_string(s: str) -> float | None:
    """Parse a p-value string into a float.

    Handles: "0.023", "<0.001", "< 0.001", ">0.05", "NS", "p=0.012",
    "0.04 (one-sided)", "not significant"
    """
    if not s or not s.strip():
        return None

    s = s.strip().lower()

    # Skip non-numeric markers
    if s in ("ns", "not significant", "na", "n/a", "--", ""):
        return None

    # Remove "p=" or "p =" prefix
    s = re.sub(r"^p\s*[=:]\s*", "", s)

    # Remove parenthetical notes
    s = re.sub(r"\s*\(.*?\)\s*$", "", s)

    # Handle inequality: "<0.001" → 0.0005, ">0.05" → 0.10
    if s.startswith("<"):
        val = _try_float(s[1:].strip())
        if val is not None:
            return val / 2.0  # Conservative estimate
        return None

    if s.startswith(">"):
        val = _try_float(s[1:].strip())
        if val is not None:
            return min(val * 2.0, 1.0)
        return None

    # Handle "≤" and "≥"
    if s.startswith(("≤", "<=", "le ")):
        cleaned = re.sub(r"^(≤|<=|le\s+)", "", s).strip()
        return _try_float(cleaned)

    if s.startswith(("≥", ">=", "ge ")):
        cleaned = re.sub(r"^(≥|>=|ge\s+)", "", s).strip()
        val = _try_float(cleaned)
        if val is not None:
            return min(val * 1.5, 1.0)
        return None

    # Direct float
    val = _try_float(s)
    if val is not None and 0 < val <= 1:
        return val

    return None


def _try_float(s: str) -> float | None:
    """Try to parse string as float, return None on failure."""
    try:
        val = float(s)
        if 0 <= val <= 1:
            return val
        return None
    except (ValueError, TypeError):
        return None


def extract_trial_metadata(study: dict) -> dict:
    """Extract metadata features from a trial study record."""
    protocol = study.get("protocolSection", {})
    ident = protocol.get("identificationModule", {})
    status = protocol.get("statusModule", {})
    design = protocol.get("designModule", {})
    outcomes_module = protocol.get("outcomesModule", {})

    results_section = study.get("resultsSection", {})
    outcome_measures = results_section.get("outcomeMeasuresModule", {}).get("outcomeMeasures", [])

    # Count outcome measures
    n_outcomes = len(outcome_measures)
    n_primary = sum(1 for o in outcome_measures if o.get("type", "").upper() == "PRIMARY")

    # Count significant primary outcomes
    n_primary_sig = 0
    for o in outcome_measures:
        if o.get("type", "").upper() == "PRIMARY":
            for analysis in o.get("analyses", []):
                p = _parse_pvalue_string(analysis.get("pValue", ""))
                if p is not None and p < 0.05:
                    n_primary_sig += 1

    # Enrollment
    enrollment = design.get("enrollmentInfo", {})
    n_enrolled = enrollment.get("count", 0) if isinstance(enrollment, dict) else 0

    # Phase
    phases = design.get("phases", [])
    phase_str = phases[0] if phases else "NA"

    return {
        "nct_id": ident.get("nctId", ""),
        "title": ident.get("briefTitle", ""),
        "status": status.get("overallStatus", ""),
        "n_outcome_measures": n_outcomes,
        "n_primary_outcomes": n_primary,
        "frac_primary_significant": n_primary_sig / max(n_primary, 1),
        "n_enrolled": n_enrolled,
        "phase": phase_str,
    }
