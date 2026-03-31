"""GEO dataset search and download utilities for H26 experiment.

Uses NCBI E-utilities to find scRNA-seq datasets and download count matrices.
"""

from __future__ import annotations

import gzip
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
USER_AGENT = "SkepticEngine/0.1"
NCBI_RATE_LIMIT_SLEEP = 0.35
GEO_FTP_BASE = "https://ftp.ncbi.nlm.nih.gov/geo/series"


def _ncbi_request(url: str) -> bytes:
    """Make an NCBI API request with rate limiting."""
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=60) as resp:
            data = resp.read()
        time.sleep(NCBI_RATE_LIMIT_SLEEP)
        return data
    except (HTTPError, URLError, TimeoutError) as e:
        print(f"    GEO API error: {e}")
        time.sleep(2.0)
        return b""


def search_geo_scrna(max_results: int = 100) -> list[str]:
    """Search GEO for scRNA-seq datasets, return GSE accessions."""
    # WHY: search 2018-2023 range — older datasets more likely to have
    # supplementary count matrices on FTP (newer ones use SRA only)
    query = (
        '"expression profiling by high throughput sequencing"[DataSet Type] '
        'AND "single cell"[Description] '
        'AND "Homo sapiens"[Organism] '
        "AND 2018:2023[PDAT]"
    )
    url = f"{ESEARCH_URL}?db=gds&term={quote(query)}&retmax={max_results}&retmode=json"
    data = _ncbi_request(url)
    if not data:
        return []
    result = json.loads(data)
    gds_ids = result.get("esearchresult", {}).get("idlist", [])

    if not gds_ids:
        return []

    # Fetch summaries to get GSE accessions
    accessions = []
    for batch_start in range(0, len(gds_ids), 50):
        batch = gds_ids[batch_start : batch_start + 50]
        ids_str = ",".join(batch)
        url = f"{ESUMMARY_URL}?db=gds&id={ids_str}&retmode=json"
        data = _ncbi_request(url)
        if not data:
            continue
        summary = json.loads(data)
        for gds_id in batch:
            entry = summary.get("result", {}).get(gds_id, {})
            accession = entry.get("accession", "")
            if accession.startswith("GSE"):
                accessions.append(accession)

    return accessions


def get_supplementary_files(gse: str) -> list[dict]:
    """List supplementary files for a GSE accession.

    Returns list of dicts with 'name' and 'url' keys.
    """
    # Construct FTP directory URL
    gse_prefix = gse[: len(gse) - 3] + "nnn"  # GSE12345 -> GSE12nnn
    base_url = f"{GEO_FTP_BASE}/{gse_prefix}/{gse}/suppl/"

    try:
        req = Request(base_url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        time.sleep(NCBI_RATE_LIMIT_SLEEP)
    except (HTTPError, URLError, TimeoutError):
        return []

    # Parse HTML directory listing for file links
    import re

    files = []
    for match in re.finditer(r'href="([^"]+)"', html):
        fname = match.group(1)
        # Skip navigation links and filelist
        if fname.startswith("/") or fname.startswith("http") or fname == "filelist.txt":
            continue
        # Accept data files: mtx, h5, csv, tsv, txt, tar, gz
        if any(
            ext in fname.lower() for ext in [".mtx", ".h5", ".csv", ".tsv", ".txt", ".tar", ".gz"]
        ):
            files.append(
                {
                    "name": fname,
                    "url": base_url + fname,
                }
            )

    return files


def download_file(url: str, dest: Path) -> bool:
    """Download a file from URL to destination path."""
    if dest.exists():
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=120) as resp:
            with open(dest, "wb") as f:
                f.write(resp.read())
        time.sleep(NCBI_RATE_LIMIT_SLEEP)
        return True
    except (HTTPError, URLError, TimeoutError) as e:
        print(f"    Download error: {e}")
        return False


def find_count_matrix_file(files: list[dict]) -> dict | None:
    """Find the most likely count matrix file from supplementary listing.

    Prefer processed count matrices and avoid metadata / DE / expression-summary files.
    """
    excluded_substrings = [
        "metadata",
        "cellmeta",
        "genemeta",
        "differential",
        "_de_",
        "_de-",
        "marker",
        "annotation",
        ".rds",
        ".rdata",
        "log2tpm",
        "tpm",
        "fpkm",
        "cpm",
        "_tcr",
        "tcr_",
        "vdj",
        "atac",
        "peak",
    ]
    suffix_weights = [
        (".mtx.gz", 140),
        (".mtx", 130),
        (".h5", 110),
        (".hdf5", 110),
        (".csv.gz", 90),
        (".tsv.gz", 85),
        (".txt.gz", 80),
        (".csv", 75),
        (".tsv", 70),
        (".txt", 65),
    ]
    signal_weights = [
        ("filtered_feature_bc_matrix", 60),
        ("filtered_gene_bc_matrices", 60),
        ("rawcounts", 55),
        ("raw_count", 55),
        ("count_matrix", 50),
        ("counts_matrix", 50),
        ("counts", 40),
        ("count", 35),
        ("umi", 25),
        ("matrix", 20),
    ]

    ranked: list[tuple[int, dict]] = []
    for f in files:
        name_lower = f["name"].lower()
        if any(token in name_lower for token in excluded_substrings):
            continue

        score = 0
        for suffix, weight in suffix_weights:
            if name_lower.endswith(suffix):
                score += weight
                break
        for token, weight in signal_weights:
            if token in name_lower:
                score += weight
        if "_raw.tar" in name_lower:
            score -= 200
        elif name_lower.endswith(".tar") or name_lower.endswith(".tar.gz"):
            score -= 80

        if score > 0:
            ranked.append((score, f))

    if ranked:
        ranked.sort(key=lambda item: (-item[0], len(item[1]["name"])))
        return ranked[0][1]

    # Last resort: RAW.tar (large, likely to be skipped by caller)
    for f in files:
        name_lower = f["name"].lower()
        if "_raw.tar" in name_lower or name_lower.endswith(".tar") or name_lower.endswith(".tar.gz"):
            return f

    return None
