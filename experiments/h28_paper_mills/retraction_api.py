"""PubMed retraction search and metadata extraction for H28 experiment.

Finds retracted papers and matched controls via NCBI E-utilities.
"""

from __future__ import annotations

import json
import re
import time
import xml.etree.ElementTree as ET
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
USER_AGENT = "SkepticEngine/0.1"
NCBI_RATE_LIMIT_SLEEP = 0.35


def _ncbi_request(url: str) -> bytes:
    """Make an NCBI API request with rate limiting."""
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=30) as resp:
            data = resp.read()
        time.sleep(NCBI_RATE_LIMIT_SLEEP)
        return data
    except (HTTPError, URLError, TimeoutError) as e:
        print(f"    NCBI error: {e}")
        time.sleep(2.0)
        return b""


def search_pubmed(query: str, max_results: int = 500) -> list[str]:
    """Search PubMed and return list of PMIDs."""
    url = f"{ESEARCH_URL}?db=pubmed&term={quote(query)}&retmax={max_results}&retmode=json"
    data = _ncbi_request(url)
    if not data:
        return []
    result = json.loads(data)
    return result.get("esearchresult", {}).get("idlist", [])


def search_retracted_papers(max_results: int = 300) -> list[str]:
    """Find PMIDs of retracted publications."""
    query = '"Retracted Publication"[pt]'
    return search_pubmed(query, max_results)


def search_controls(journal: str, year: int, max_results: int = 5) -> list[str]:
    """Find non-retracted papers from the same journal and year."""
    query = f'"{journal}"[Journal] AND {year}[dp] NOT "Retracted Publication"[pt]'
    return search_pubmed(query, max_results)


def fetch_pubmed_xml(pmids: list[str]) -> str:
    """Batch-fetch PubMed XML for up to 200 PMIDs."""
    if not pmids:
        return ""
    ids = ",".join(pmids[:200])
    url = f"{EFETCH_URL}?db=pubmed&id={ids}&retmode=xml"
    data = _ncbi_request(url)
    return data.decode("utf-8", errors="replace") if data else ""


def parse_article_metadata(xml_text: str) -> list[dict]:
    """Parse PubMed XML into structured article metadata."""
    articles = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return articles

    for article_elem in root.findall(".//PubmedArticle"):
        try:
            meta = _parse_single_article(article_elem)
            if meta:
                articles.append(meta)
        except Exception:
            continue

    return articles


def _parse_single_article(article_elem) -> dict | None:
    """Parse a single PubmedArticle element."""
    medline = article_elem.find("MedlineCitation")
    if medline is None:
        return None

    pmid_elem = medline.find("PMID")
    pmid = pmid_elem.text if pmid_elem is not None else ""

    article = medline.find("Article")
    if article is None:
        return None

    # Title
    title_elem = article.find("ArticleTitle")
    title = title_elem.text if title_elem is not None else ""

    # Journal
    journal_elem = article.find(".//Journal/Title")
    journal = journal_elem.text if journal_elem is not None else ""

    # Year
    year_elem = article.find(".//PubDate/Year")
    year = int(year_elem.text) if year_elem is not None and year_elem.text else 0

    # Authors
    authors = []
    affiliations = set()
    for author in article.findall(".//AuthorList/Author"):
        last = author.find("LastName")
        fore = author.find("ForeName")
        name = ""
        if last is not None and last.text:
            name = last.text
            if fore is not None and fore.text:
                name = f"{fore.text} {last.text}"
        if name:
            authors.append(name)

        for aff in author.findall(".//AffiliationInfo/Affiliation"):
            if aff.text:
                affiliations.add(aff.text.strip()[:200])

    # Abstract
    abstract_parts = []
    for abs_elem in article.findall(".//Abstract/AbstractText"):
        if abs_elem.text:
            abstract_parts.append(abs_elem.text)
    abstract = " ".join(abstract_parts)

    # References
    ref_list = article_elem.findall(".//ReferenceList/Reference")
    n_references = len(ref_list)

    # Reference PMIDs (for self-citation analysis)
    ref_pmids = []
    for ref in ref_list:
        for artid in ref.findall(".//ArticleIdList/ArticleId"):
            if artid.get("IdType") == "pubmed" and artid.text:
                ref_pmids.append(artid.text)

    # Dates
    received = _find_date(article, "received")
    accepted = _find_date(article, "accepted")

    return {
        "pmid": pmid,
        "title": title[:200] if title else "",
        "journal": journal[:100] if journal else "",
        "year": year,
        "authors": authors,
        "n_authors": len(authors),
        "affiliations": list(affiliations),
        "n_affiliations": len(affiliations),
        "abstract": abstract,
        "abstract_word_count": len(abstract.split()) if abstract else 0,
        "n_references": n_references,
        "ref_pmids": ref_pmids,
        "date_received": received,
        "date_accepted": accepted,
    }


def _find_date(article, date_type: str) -> str:
    """Find a specific date type (received/accepted) in article history."""
    for hist in article.findall(".//History/PubMedPubDate"):
        if hist.get("PubStatus") == date_type:
            year = hist.find("Year")
            month = hist.find("Month")
            day = hist.find("Day")
            if year is not None and year.text:
                parts = [year.text]
                if month is not None and month.text:
                    parts.append(month.text.zfill(2))
                if day is not None and day.text:
                    parts.append(day.text.zfill(2))
                return "-".join(parts)
    return ""


def fetch_pmc_fulltext(pmid: str) -> str:
    """Try to fetch full text from PMC for a given PubMed ID."""
    # First find PMC ID
    url = f"{ESEARCH_URL}?db=pmc&term={pmid}[pmid]&retmode=json"
    data = _ncbi_request(url)
    if not data:
        return ""
    result = json.loads(data)
    pmc_ids = result.get("esearchresult", {}).get("idlist", [])
    if not pmc_ids:
        return ""

    # Fetch full text XML
    pmc_id = pmc_ids[0]
    url = f"{EFETCH_URL}?db=pmc&id={pmc_id}&rettype=xml&retmode=xml"
    data = _ncbi_request(url)
    if not data:
        return ""

    xml_text = data.decode("utf-8", errors="replace")
    try:
        root = ET.fromstring(xml_text)
        paragraphs = []
        for p in root.iter("p"):
            if p.text:
                paragraphs.append(p.text)
            for child in p:
                if child.tail:
                    paragraphs.append(child.tail)
        return " ".join(paragraphs)
    except ET.ParseError:
        return xml_text[:10000]
