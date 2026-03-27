#!/usr/bin/env python3
"""Search Semantic Scholar for papers by conference, keyword, or topic.

Usage:
    python3 search_semantic_scholar.py --config config.yaml --conference NeurIPS --year 2025
    python3 search_semantic_scholar.py --config config.yaml --keywords "large language model"

Output:
    JSON array of paper dicts to stdout (same format as search_arxiv.py).
"""

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from scripts.config_loader import load_config, get_all_keywords

S2_API = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS = "title,abstract,authors,citationCount,venue,year,externalIds,url,publicationDate"
SEARCH_DELAY = 1.0  # seconds between API calls


def search_semantic_scholar(
    conference: str = "",
    year: int | None = None,
    keywords: list[str] | None = None,
    api_key: str = "",
    min_citations: int = 0,
    max_results: int = 100,
) -> list[dict]:
    """Search Semantic Scholar API for papers.

    Args:
        conference: Conference/venue name to filter by (e.g., "NeurIPS").
        year: Publication year filter.
        keywords: Keywords to search for.
        api_key: Semantic Scholar API key (optional).
        min_citations: Minimum citation count filter.
        max_results: Maximum number of results.

    Returns:
        List of paper dicts in the standard format.
    """
    papers = []
    seen_ids = set()

    # Build search queries
    queries = []
    if conference and keywords:
        for kw in keywords[:3]:
            queries.append(f"{kw} {conference}")
    elif conference:
        queries.append(conference)
    elif keywords:
        for kw in keywords[:5]:
            queries.append(kw)
    else:
        print("Warning: No conference or keywords specified.", file=sys.stderr)
        return []

    for query in queries:
        results = _search_papers(query, year, api_key, max_results=max_results // max(len(queries), 1))
        for paper in results:
            paper_id = paper.get("arxiv_id") or paper.get("s2_id", "")
            if paper_id and paper_id not in seen_ids:
                seen_ids.add(paper_id)
                papers.append(paper)
        time.sleep(SEARCH_DELAY)

    # Filter by conference name (fuzzy match)
    if conference:
        conf_lower = conference.lower()
        papers = [p for p in papers if conf_lower in (p.get("conference", "") or "").lower()
                  or conf_lower in (p.get("venue_raw", "") or "").lower()]

    # Filter by year
    if year:
        papers = [p for p in papers if p.get("year") == year]

    # Filter by minimum citations
    if min_citations > 0:
        papers = [p for p in papers if (p.get("citation_count", 0) or 0) >= min_citations]

    # Sort by citation count descending
    papers.sort(key=lambda p: p.get("citation_count", 0) or 0, reverse=True)

    return papers[:max_results]


def _search_papers(query: str, year: int | None, api_key: str, max_results: int = 50) -> list[dict]:
    """Execute a Semantic Scholar paper search query.

    Returns:
        List of paper dicts in the standard format.
    """
    params = {
        "query": query,
        "fields": S2_FIELDS,
        "limit": min(max_results, 100),
    }
    if year:
        params["year"] = str(year)

    url = f"{S2_API}/paper/search?{urllib.parse.urlencode(params)}"

    headers = {
        "User-Agent": "notion-research-flow/1.0",
    }
    if api_key:
        headers["x-api-key"] = api_key

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print(f"Warning: Semantic Scholar rate limited. Waiting 5s...", file=sys.stderr)
            time.sleep(5)
            return _search_papers(query, year, api_key, max_results)
        print(f"Warning: Semantic Scholar query failed ({e.code}): {e.reason}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Warning: Semantic Scholar query failed: {e}", file=sys.stderr)
        return []

    results = data.get("data", [])
    papers = []

    for item in results:
        if not item or not item.get("title"):
            continue

        # Extract arXiv ID from externalIds
        external_ids = item.get("externalIds") or {}
        arxiv_id = external_ids.get("ArXiv", "")
        s2_id = external_ids.get("CorpusId", "")

        # Extract authors
        authors_list = [a.get("name", "") for a in (item.get("authors") or [])]
        authors_str = ", ".join(authors_list[:5])
        if len(authors_list) > 5:
            authors_str += " et al."

        # Extract venue/conference
        venue = item.get("venue", "") or ""

        # Build source URL
        if arxiv_id:
            source_url = f"https://arxiv.org/abs/{arxiv_id}"
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        else:
            source_url = item.get("url", "") or f"https://api.semanticscholar.org/CorpusID:{s2_id}"
            pdf_url = ""

        # Parse publication date
        pub_date = item.get("publicationDate", "") or ""
        if pub_date:
            pub_date = pub_date[:10]  # YYYY-MM-DD

        papers.append({
            "arxiv_id": arxiv_id,
            "s2_id": str(s2_id),
            "title": item.get("title", "").strip(),
            "authors": authors_str,
            "authors_list": authors_list,
            "abstract": (item.get("abstract") or "").strip(),
            "published_date": pub_date,
            "categories": [],
            "pdf_url": pdf_url,
            "source_url": source_url,
            "source": "Semantic Scholar",
            "citation_count": item.get("citationCount", 0) or 0,
            "conference": _normalize_venue(venue),
            "venue_raw": venue,
            "year": item.get("year"),
            "github_stars": 0,
            "twitter_mentions": 0,
        })

    return papers


def _normalize_venue(venue: str) -> str:
    """Normalize venue name to standard conference abbreviation.

    Examples:
        "Neural Information Processing Systems" -> "NeurIPS"
        "ICML 2024" -> "ICML"
    """
    venue_map = {
        "neurips": "NeurIPS",
        "neural information processing": "NeurIPS",
        "nips": "NeurIPS",
        "icml": "ICML",
        "international conference on machine learning": "ICML",
        "iclr": "ICLR",
        "international conference on learning representations": "ICLR",
        "acl": "ACL",
        "association for computational linguistics": "ACL",
        "emnlp": "EMNLP",
        "empirical methods in natural language processing": "EMNLP",
        "cvpr": "CVPR",
        "computer vision and pattern recognition": "CVPR",
        "iccv": "ICCV",
        "international conference on computer vision": "ICCV",
        "eccv": "ECCV",
        "european conference on computer vision": "ECCV",
        "aaai": "AAAI",
        "ijcai": "IJCAI",
        "naacl": "NAACL",
    }

    venue_lower = venue.lower().strip()
    for key, normalized in venue_map.items():
        if key in venue_lower:
            return normalized

    return venue.strip() if venue else ""


def main():
    parser = argparse.ArgumentParser(description="Search Semantic Scholar for papers")
    parser.add_argument("--config", type=str, default=None, help="Path to config.yaml")
    parser.add_argument("--conference", type=str, default="", help="Conference name (e.g., NeurIPS)")
    parser.add_argument("--year", type=int, default=None, help="Publication year")
    parser.add_argument("--keywords", type=str, default="", help="Comma-separated keywords")
    parser.add_argument("--max-results", type=int, default=100, help="Maximum results")
    args = parser.parse_args()

    config = load_config(args.config)
    s2_config = config["sources"].get("semantic_scholar", {})

    api_key = s2_config.get("api_key", "") or ""
    min_citations = s2_config.get("min_citations", 0)

    keywords = None
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",")]
    elif not args.conference:
        # Fall back to config keywords if no args specified
        keywords = get_all_keywords(config)[:5]

    papers = search_semantic_scholar(
        conference=args.conference,
        year=args.year,
        keywords=keywords,
        api_key=api_key,
        min_citations=min_citations,
        max_results=args.max_results,
    )

    print(json.dumps(papers, ensure_ascii=False, indent=2))
    print(f"\n# Found {len(papers)} papers from Semantic Scholar", file=sys.stderr)


if __name__ == "__main__":
    main()
