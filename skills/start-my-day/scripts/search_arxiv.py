#!/usr/bin/env python3
"""Search arXiv for recent papers matching research interests.

Usage:
    python3 search_arxiv.py --config config.yaml [--max-results 50] [--lookback-days 3]

Output:
    JSON array of paper dicts to stdout.
"""

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

NS = "http://www.w3.org/2005/Atom"
ARXIV_API = "http://export.arxiv.org/api/query"

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from scripts.config_loader import load_config, get_all_categories, get_excluded_keywords


def search_arxiv(
    categories: list[str],
    keywords: list[str],
    max_results: int = 50,
    lookback_days: int = 3,
) -> list[dict]:
    """Search arXiv API for recent papers.

    Args:
        categories: arXiv categories to search (e.g., ["cs.AI", "cs.CL"]).
        keywords: Keywords to search in title/abstract.
        max_results: Maximum number of results per query.
        lookback_days: Only include papers from the last N days.

    Returns:
        List of paper dicts with keys: arxiv_id, title, authors, abstract,
        published_date, categories, pdf_url, source_url, source.
    """
    papers = []
    seen_ids = set()
    cutoff_date = datetime.now() - timedelta(days=lookback_days)

    # Strategy 1: Search by category
    for cat in categories:
        query = f"cat:{cat}"
        new_papers = _query_arxiv(query, max_results=max_results // len(categories) + 5)
        for p in new_papers:
            if p["arxiv_id"] not in seen_ids:
                seen_ids.add(p["arxiv_id"])
                papers.append(p)
        time.sleep(0.5)  # Be nice to arXiv API

    # Strategy 2: Search by keywords (top 5 keywords to avoid too many queries)
    top_keywords = keywords[:5]
    for kw in top_keywords:
        query = f'all:"{kw}"'
        new_papers = _query_arxiv(query, max_results=10)
        for p in new_papers:
            if p["arxiv_id"] not in seen_ids:
                seen_ids.add(p["arxiv_id"])
                papers.append(p)
        time.sleep(0.5)

    # Filter by date
    filtered = []
    for p in papers:
        try:
            pub_date = datetime.strptime(p["published_date"], "%Y-%m-%d")
            if pub_date >= cutoff_date:
                filtered.append(p)
        except (ValueError, TypeError):
            filtered.append(p)  # Keep if date parsing fails

    return filtered


def _query_arxiv(query: str, max_results: int = 50) -> list[dict]:
    """Execute a single arXiv API query.

    Args:
        query: arXiv search query string.
        max_results: Maximum results to return.

    Returns:
        List of paper dicts.
    """
    params = urllib.parse.urlencode({
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    })
    url = f"{ARXIV_API}?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "notion-research-flow/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read()
    except Exception as e:
        print(f"Warning: arXiv query failed for '{query}': {e}", file=sys.stderr)
        return []

    root = ET.fromstring(data)
    papers = []

    for entry in root.findall(f"{{{NS}}}entry"):
        arxiv_id = entry.findtext(f"{{{NS}}}id", "")
        if "/abs/" in arxiv_id:
            arxiv_id = arxiv_id.split("/abs/")[-1]
        arxiv_id = arxiv_id.split("v")[0]  # Remove version

        title = (entry.findtext(f"{{{NS}}}title", "") or "").strip().replace("\n", " ")
        abstract = (entry.findtext(f"{{{NS}}}summary", "") or "").strip().replace("\n", " ")
        authors = [
            a.findtext(f"{{{NS}}}name", "")
            for a in entry.findall(f"{{{NS}}}author")
        ]
        published = (entry.findtext(f"{{{NS}}}published", "") or "")[:10]
        categories = [
            c.get("term", "")
            for c in entry.findall(f"{{{NS}}}category")
            if c.get("term")
        ]

        papers.append({
            "arxiv_id": arxiv_id,
            "title": title,
            "authors": ", ".join(authors[:5]) + (" et al." if len(authors) > 5 else ""),
            "authors_list": authors,
            "abstract": abstract,
            "published_date": published,
            "categories": categories,
            "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
            "source_url": f"https://arxiv.org/abs/{arxiv_id}",
            "source": "arXiv",
            "citation_count": 0,
            "github_stars": 0,
            "twitter_mentions": 0,
        })

    return papers


def main():
    parser = argparse.ArgumentParser(description="Search arXiv for recent papers")
    parser.add_argument("--config", type=str, default=None, help="Path to config.yaml")
    parser.add_argument("--max-results", type=int, default=None, help="Override max results")
    parser.add_argument("--lookback-days", type=int, default=None, help="Override lookback days")
    args = parser.parse_args()

    config = load_config(args.config)

    categories = get_all_categories(config)
    keywords = []
    for domain in config["interests"]["domains"]:
        keywords.extend(domain.get("keywords", []))

    max_results = args.max_results or config["sources"]["arxiv"].get("max_results", 50)
    lookback_days = args.lookback_days or config["sources"]["arxiv"].get("lookback_days", 3)

    papers = search_arxiv(
        categories=categories,
        keywords=keywords,
        max_results=max_results,
        lookback_days=lookback_days,
    )

    # Filter excluded keywords
    excluded = get_excluded_keywords(config)
    if excluded:
        papers = [
            p for p in papers
            if not any(
                ex.lower() in p["title"].lower() or ex.lower() in p["abstract"].lower()
                for ex in excluded
            )
        ]

    print(json.dumps(papers, ensure_ascii=False, indent=2))
    print(f"\n# Found {len(papers)} papers", file=sys.stderr)


if __name__ == "__main__":
    main()
