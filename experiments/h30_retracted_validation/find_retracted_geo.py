"""Find retracted papers with GEO (GSE) accessions via PubMed.

Strategy: search PubMed for retracted publications mentioning GSE,
extract accessions, check if GEO data is accessible.

Usage:
    python experiments/h30_retracted_validation/find_retracted_geo.py
"""
from __future__ import annotations
import json, re, time, xml.etree.ElementTree as ET
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

RESULTS_DIR = Path(__file__).resolve().parent / "results"
ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
GEO_FTP = "https://ftp.ncbi.nlm.nih.gov/geo/series"
UA = "SkepticEngine/0.1"

def _fetch(url):
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=30) as r: data = r.read()
        time.sleep(0.4)
        return data
    except (HTTPError, URLError, TimeoutError) as e:
        print(f"  API error: {e}"); time.sleep(2); return b""

def search_retracted(max_results=200):
    queries = [
        '"Retracted Publication"[pt] AND ("RNA-seq"[tiab] OR "single-cell"[tiab] OR "scRNA"[tiab]) AND "GSE"[tiab]',
        '"Retracted Publication"[pt] AND ("gene expression"[tiab] OR "sequencing"[tiab]) AND "GSE"[tiab]',
        '"Retracted Publication"[pt] AND ("GEO"[tiab] OR "Gene Expression Omnibus"[tiab])',
    ]
    pmids = set()
    for q in queries:
        url = f"{ESEARCH}?db=pubmed&term={quote(q)}&retmax={max_results}&retmode=json"
        data = _fetch(url)
        if data:
            ids = json.loads(data).get("esearchresult", {}).get("idlist", [])
            pmids.update(ids)
            print(f"  Query found {len(ids)} PMIDs")
    return list(pmids)

def fetch_abstracts(pmids):
    articles = []
    for i in range(0, len(pmids), 50):
        batch = pmids[i:i+50]
        url = f"{EFETCH}?db=pubmed&id={','.join(batch)}&rettype=xml&retmode=xml"
        data = _fetch(url)
        if not data: continue
        try:
            root = ET.fromstring(data)
            for art in root.iter("PubmedArticle"):
                pmid = (art.findtext(".//PMID") or "")
                title = (art.findtext(".//ArticleTitle") or "")
                abstract = (art.findtext(".//AbstractText") or "")
                journal = (art.findtext(".//Journal/Title") or "")
                year = (art.findtext(".//PubDate/Year") or "")
                articles.append({"pmid": pmid, "title": title, "journal": journal,
                                 "year": year, "text": f"{title} {abstract}"})
        except ET.ParseError: continue
    return articles

def check_geo(gse):
    prefix = gse[:len(gse)-3] + "nnn"
    url = f"{GEO_FTP}/{prefix}/{gse}/suppl/"
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=15) as r: html = r.read().decode("utf-8", errors="replace")
        time.sleep(0.4)
        files = re.findall(r'href="([^"]+\.(mtx|csv|tsv|h5|txt|tar)\.?g?z?)"', html, re.I)
        return {"gse": gse, "accessible": True, "n_files": len(files), "files": [f[0] for f in files[:10]]}
    except Exception:
        return {"gse": gse, "accessible": False, "n_files": 0, "files": []}

def main():
    print("=" * 70)
    print("H30 -- Find Retracted Papers with GEO Data")
    print("=" * 70)
    print("\n[1/4] Searching PubMed for retracted genomics papers...")
    pmids = search_retracted()
    print(f"  Total unique PMIDs: {len(pmids)}")
    if not pmids: print("  None found."); return

    print(f"\n[2/4] Fetching abstracts...")
    articles = fetch_abstracts(pmids)
    print(f"  Fetched {len(articles)} articles")

    print("\n[3/4] Extracting GSE accessions...")
    papers_with_gse = []
    for a in articles:
        gses = list(set(re.findall(r"GSE\d{4,8}", a["text"])))
        if gses:
            a["gse_accessions"] = gses
            papers_with_gse.append(a)
            print(f"  PMID {a['pmid']}: {gses} -- {a['title'][:60]}...")
    print(f"  Papers with GSE: {len(papers_with_gse)}")

    print("\n[4/4] Checking GEO accessibility...")
    all_gses = set()
    for p in papers_with_gse: all_gses.update(p["gse_accessions"])
    geo = {}
    for gse in sorted(all_gses):
        s = check_geo(gse); geo[gse] = s
        flag = "OK" if s["accessible"] and s["n_files"] > 0 else "NO"
        print(f"  {gse}: {flag} ({s['n_files']} files)")

    accessible = [g for g, s in geo.items() if s["accessible"] and s["n_files"] > 0]
    print(f"\n{'='*70}\nSUMMARY\n{'='*70}")
    print(f"  Retracted papers: {len(pmids)}")
    print(f"  With GSE: {len(papers_with_gse)}")
    print(f"  Unique GSE: {len(all_gses)}")
    print(f"  Accessible: {len(accessible)}")
    if accessible:
        print("\n  ACCESSIBLE RETRACTED DATASETS:")
        for gse in accessible:
            paper = next((p for p in papers_with_gse if gse in p.get("gse_accessions",[])), None)
            t = paper["title"][:50] if paper else "?"
            print(f"    {gse}: {geo[gse]['n_files']} files -- {t}...")

    out = {"experiment": "H30", "n_papers": len(pmids), "n_with_gse": len(papers_with_gse),
           "n_gse": len(all_gses), "n_accessible": len(accessible),
           "accessible": [geo[g] for g in accessible],
           "papers": [{k:v for k,v in p.items() if k != "text"} for p in papers_with_gse]}
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "h30_retracted_geo_scan.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\n  Saved: {RESULTS_DIR / 'h30_retracted_geo_scan.json'}")

if __name__ == "__main__": main()
