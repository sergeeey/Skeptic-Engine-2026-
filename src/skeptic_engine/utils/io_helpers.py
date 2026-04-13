"""I/O helpers for data loading, API requests, and result persistence.

Consolidates common patterns from H24, H26, H28 for:
- NCBI API requests with rate limiting
- File downloads with User-Agent
- PMC fulltext extraction
- JSON result file saving
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

__all__ = [
    "ncbi_request",
    "fetch_pmc_fulltext",
    "download_file",
    "save_json_results",
    "parse_pvalue_string",
]

# Default user agent for all requests
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "Skeptic-Engine/0.1.1 (+https://github.com/sergeeey/Skeptic-Engine-2026-)"
)

# NCBI requires email for high-volume access
NCBI_EMAIL = "sergeikuch80@gmail.com"


def ncbi_request(url: str, rate_limit: float = 0.35, max_retries: int = 3) -> str | None:
    """Make HTTP request to NCBI E-utilities with rate limiting and retries.

    Parameters
    ----------
    url : str
        NCBI E-utilities URL.
    rate_limit : float
        Seconds to wait between requests (default 0.35s).
    max_retries : int
        Number of retry attempts on failure.

    Returns
    -------
    str | None
        Response text, or None on failure.

    Notes
    -----
    Implements exponential backoff on retries.
    """
    time.sleep(rate_limit)  # Rate limiting

    for attempt in range(max_retries):
        try:
            req = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
            with urlopen(req, timeout=30) as response:
                return response.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError) as e:
            if attempt == max_retries - 1:
                print(f"NCBI request failed after {max_retries} attempts: {e}")
                return None
            wait_time = 2**attempt  # Exponential backoff
            time.sleep(wait_time)

    return None


def fetch_pmc_fulltext(pmc_id: str) -> str | None:
    """Fetch full text from PMC XML using E-utilities.

    Parameters
    ----------
    pmc_id : str
        PMC ID (e.g., "PMC1234567" or just "1234567").

    Returns
    -------
    str | None
        Extracted full text (concatenated <p> tags), or None on failure.

    Notes
    -----
    Strips XML tags and concatenates paragraph content.
    """
    # Ensure PMC ID has prefix
    if not pmc_id.startswith("PMC"):
        pmc_id = f"PMC{pmc_id}"

    url = (
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?"
        f"db=pmc&id={pmc_id}&retmode=xml&tool=SkepticEngine&email={NCBI_EMAIL}"
    )

    xml_text = ncbi_request(url)
    if xml_text is None:
        return None

    # Simple XML parsing: extract content between <p> tags
    import re

    # Match <p>...</p> tags
    p_tags = re.findall(r"<p[^>]*>(.*?)</p>", xml_text, re.DOTALL)

    # Strip nested tags
    paragraphs = []
    for p in p_tags:
        # Remove any nested XML tags
        clean_p = re.sub(r"<[^>]+>", "", p)
        clean_p = clean_p.strip()
        if clean_p:
            paragraphs.append(clean_p)

    return "\n\n".join(paragraphs) if paragraphs else None


def download_file(
    url: str,
    dest: Path | str,
    user_agent: str = DEFAULT_USER_AGENT,
    chunk_size: int = 8192,
) -> Path:
    """Download file from URL with User-Agent header.

    Parameters
    ----------
    url : str
        Source URL.
    dest : Path | str
        Destination file path.
    user_agent : str
        User-Agent header value.
    chunk_size : int
        Chunk size for streaming download.

    Returns
    -------
    Path
        Path to downloaded file.

    Raises
    ------
    HTTPError
        If download fails.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    req = Request(url, headers={"User-Agent": user_agent})
    with urlopen(req, timeout=120) as response:  # noqa: SIM117
        with dest.open("wb") as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)

    return dest


def save_json_results(
    data: dict[str, Any],
    results_dir: Path | str,
    filename: str = "results.json",
) -> Path:
    """Save results to JSON file with standard formatting.

    Parameters
    ----------
    data : dict[str, Any]
        Results dictionary to save.
    results_dir : Path | str
        Directory to save results in.
    filename : str
        Output filename.

    Returns
    -------
    Path
        Path to saved JSON file.

    Notes
    -----
    Creates directory if it doesn't exist.
    Uses 2-space indentation for readability.
    """
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    out_path = results_dir / filename

    out_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return out_path


def parse_pvalue_string(s: str) -> float | None:
    """Parse p-value from string representation (e.g., "<0.001", "NS", "p=0.012").

    Parameters
    ----------
    s : str
        P-value string from paper or database.

    Returns
    -------
    float | None
        Parsed p-value, or None if unparseable.

    Examples
    --------
    >>> parse_pvalue_string("p = 0.023")
    0.023
    >>> parse_pvalue_string("<0.001")
    0.001
    >>> parse_pvalue_string("NS")
    None
    """
    import re

    s = s.strip()

    # "NS" or "not significant"
    if s.upper() in ("NS", "NOT SIGNIFICANT", "N.S."):
        return None

    # Extract numeric value
    match = re.search(r"([<>=]?\s*)(\d+(?:\.\d+)?)", s)
    if match:
        return float(match.group(2))

    return None
