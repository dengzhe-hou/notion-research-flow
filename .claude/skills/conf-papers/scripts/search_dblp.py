#!/usr/bin/env python3
"""Search DBLP for conference papers.

Usage:
    python3 search_dblp.py --config config.yaml --conference NeurIPS --year 2025
    python3 search_dblp.py --config config.yaml --conference ICML --year 2025 --keywords "language model"

Output:
    JSON array of paper dicts to stdout (same format as search_arxiv.py).
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from scripts.config_loader import load_config

DBLP_API = "https://dblp.org/search/publ/api"
SEARCH_DELAY = 1.0  # seconds between API calls


# Map common conference abbreviations to DBLP venue keys
VENUE_KEYS = {
    "NeurIPS": "conf/nips",
    "ICML": "conf/icml",
    "ICLR": "conf/iclr",
    "ACL": "conf/acl",
    "EMNLP": "conf/emnlp",
    "NAACL": "conf/naacl",
    "CVPR": "conf/cvpr",
    "ICCV": "conf/iccv",
    "ECCV": "conf/eccv",
    "AAAI": "conf/aaai",
    "IJCAI": "conf/ijcai",
}


def search_dblp(
    conference: str,
    year: int | None = None,
    keywords: list[str] | None = None,
    max_results: int = 100,
) -> list[dict]:
    """Search DBLP API for conference papers.

    Args:
        conference: Conference abbreviation (e.g., "NeurIPS").
        year: Publication year filter.
        keywords: Optional keywords to filter results.
        max_results: Maximum number of results.

    Returns:
        List of paper dicts in the standard format.
    """
    papers = []
    seen_titles = set()

    # Build search query
    venue_key = VENUE_KEYS.get(conference, "")
    if venue_key:
        # Use venue stream for precise results
        venue_papers = _search_by_venue(venue_key, year, max_results)
        papers.extend(venue_papers)
    else:
        # Fall back to text search
        query = f"{conference}"
        if year:
            query += f" {year}"
        search_papers = _search_by_query(query, max_results)
        papers.extend(search_papers)

    # Additional keyword-filtered search within conference
    if keywords:
        for kw in keywords[:3]:
            query = f"{conference} {kw}"
            if year:
                query += f" {year}"
            kw_papers = _search_by_query(query, max_results=30)
            for p in kw_papers:
                title_key = p["title"].lower().strip().rstrip(".")
                if title_key not in seen_titles:
                    seen_titles.add(title_key)
                    papers.append(p)
            time.sleep(SEARCH_DELAY)

    # Deduplicate
    unique_papers = []
    seen = set()
    for p in papers:
        title_key = p["title"].lower().strip().rstrip(".")
        if title_key not in seen:
            seen.add(title_key)
            unique_papers.append(p)

    # Filter by year if specified
    if year:
        unique_papers = [p for p in unique_papers if p.get("year") == year]

    # Set conference name
    for p in unique_papers:
        p["conference"] = conference

    return unique_papers[:max_results]


def _search_by_venue(venue_key: str, year: int | None, max_results: int) -> list[dict]:
    """Search DBLP by venue stream URL.

    Uses: https://dblp.org/search/publ/api?q=stream:streams/{venue_key}:&h=100&format=json
    """
    query = f"stream:streams/{venue_key}:"
    if year:
        query += f" year:{year}:"

    return _search_by_query(query, max_results)


def _search_by_query(query: str, max_results: int = 100) -> list[dict]:
    """Execute a DBLP publication search.

    Returns:
        List of paper dicts.
    """
    params = {
        "q": query,
        "format": "json",
        "h": min(max_results, 1000),
    }
    url = f"{DBLP_API}?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "notion-research-flow/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read())
    except Exception as e:
        print(f"Warning: DBLP query failed for '{query}': {e}", file=sys.stderr)
        return []

    result = data.get("result", {})
    hits = result.get("hits", {}).get("hit", [])

    papers = []
    for hit in hits:
        info = hit.get("info", {})
        if not info.get("title"):
            continue

        title = info.get("title", "").strip().rstrip(".")

        # Extract authors
        authors_info = info.get("authors", {}).get("author", [])
        if isinstance(authors_info, dict):
            authors_info = [authors_info]
        authors_list = []
        for a in authors_info:
            if isinstance(a, dict):
                authors_list.append(a.get("text", ""))
            elif isinstance(a, str):
                authors_list.append(a)

        authors_str = ", ".join(authors_list[:5])
        if len(authors_list) > 5:
            authors_str += " et al."

        # Extract year
        paper_year = int(info.get("year", 0)) if info.get("year") else None

        # Extract DOI and other links
        doi = info.get("doi", "")
        dblp_url = info.get("url", "")
        ee = info.get("ee", "")  # electronic edition URL

        # Try to extract arXiv ID from ee URL
        arxiv_id = ""
        if isinstance(ee, str) and "arxiv.org" in ee:
            match = re.search(r"(\d{4}\.\d{4,5})", ee)
            if match:
                arxiv_id = match.group(1)
        elif isinstance(ee, list):
            for link in ee:
                if isinstance(link, str) and "arxiv.org" in link:
                    match = re.search(r"(\d{4}\.\d{4,5})", link)
                    if match:
                        arxiv_id = match.group(1)
                        break

        # Build URLs
        if arxiv_id:
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            source_url = f"https://arxiv.org/abs/{arxiv_id}"
        elif doi:
            pdf_url = ""
            source_url = f"https://doi.org/{doi}"
        else:
            pdf_url = ""
            source_url = dblp_url or (ee if isinstance(ee, str) else (ee[0] if isinstance(ee, list) and ee else ""))

        venue = info.get("venue", "")

        papers.append({
            "arxiv_id": arxiv_id,
            "title": title,
            "authors": authors_str,
            "authors_list": authors_list,
            "abstract": "",  # DBLP doesn't provide abstracts
            "published_date": f"{paper_year}-01-01" if paper_year else "",
            "categories": [],
            "pdf_url": pdf_url,
            "source_url": source_url,
            "source": "DBLP",
            "citation_count": 0,  # DBLP doesn't provide citation counts
            "conference": "",  # Set by caller
            "venue_raw": venue if isinstance(venue, str) else str(venue),
            "year": paper_year,
            "github_stars": 0,
            "twitter_mentions": 0,
        })

    return papers


def main():
    parser = argparse.ArgumentParser(description="Search DBLP for conference papers")
    parser.add_argument("--config", type=str, default=None, help="Path to config.yaml")
    parser.add_argument("--conference", type=str, required=True, help="Conference name (e.g., NeurIPS)")
    parser.add_argument("--year", type=int, default=None, help="Publication year")
    parser.add_argument("--keywords", type=str, default="", help="Comma-separated keywords to filter")
    parser.add_argument("--max-results", type=int, default=100, help="Maximum results")
    args = parser.parse_args()

    config = load_config(args.config)

    # Validate conference against config
    tracked = config["sources"].get("dblp", {}).get("conferences", [])
    if tracked and args.conference not in tracked:
        print(f"Warning: '{args.conference}' not in tracked conferences: {tracked}", file=sys.stderr)

    keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else None

    papers = search_dblp(
        conference=args.conference,
        year=args.year,
        keywords=keywords,
        max_results=args.max_results,
    )

    print(json.dumps(papers, ensure_ascii=False, indent=2))
    print(f"\n# Found {len(papers)} papers from DBLP for {args.conference}", file=sys.stderr)
    if args.year:
        print(f"# Year filter: {args.year}", file=sys.stderr)


if __name__ == "__main__":
    main()
