#!/usr/bin/env python3
"""Enrich papers with social signals (GitHub stars, Twitter mentions).

Usage:
    echo '[...papers...]' | python3 fetch_social_signals.py --config config.yaml

Output:
    JSON array of papers with github_stars and twitter_mentions populated, to stdout.

Gracefully degrades: if APIs are unavailable or rate-limited, returns 0 for missing signals.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.config_loader import load_config


GITHUB_API = "https://api.github.com"
GITHUB_SEARCH_DELAY = 1.0  # seconds between GitHub API calls


def fetch_social_signals(papers: list[dict], config: dict) -> list[dict]:
    """Enrich papers with GitHub stars and Twitter mention estimates.

    Args:
        papers: List of paper dicts (must have arxiv_id and title).
        config: Full configuration dict.

    Returns:
        Same papers list with github_stars and twitter_mentions updated.
    """
    social_config = config.get("social", {})
    github_config = social_config.get("github", {})
    twitter_config = social_config.get("twitter", {})

    github_enabled = github_config.get("enabled", False)
    twitter_enabled = twitter_config.get("enabled", False)

    if not github_enabled and not twitter_enabled:
        print("Social signals disabled in config, skipping.", file=sys.stderr)
        return papers

    github_token = github_config.get("token", "") or os.environ.get("GITHUB_TOKEN", "")
    min_stars = github_config.get("min_stars", 10)

    for i, paper in enumerate(papers):
        arxiv_id = paper.get("arxiv_id", "")
        title = paper.get("title", "")

        # GitHub stars
        if github_enabled and (arxiv_id or title):
            stars = _search_github_stars(arxiv_id, title, github_token, min_stars)
            paper["github_stars"] = stars
            if i < len(papers) - 1:
                time.sleep(GITHUB_SEARCH_DELAY)

        # Twitter mentions (best-effort estimate)
        if twitter_enabled and arxiv_id:
            mentions = _estimate_twitter_mentions(arxiv_id, twitter_config)
            paper["twitter_mentions"] = mentions

        if (i + 1) % 5 == 0:
            print(f"# Enriched {i + 1}/{len(papers)} papers", file=sys.stderr)

    total_with_github = sum(1 for p in papers if p.get("github_stars", 0) > 0)
    total_with_twitter = sum(1 for p in papers if p.get("twitter_mentions", 0) > 0)
    print(f"# Social signals: {total_with_github} papers with GitHub stars, "
          f"{total_with_twitter} with Twitter mentions", file=sys.stderr)

    return papers


def _search_github_stars(arxiv_id: str, title: str, token: str, min_stars: int) -> int:
    """Search GitHub for a repository matching the paper.

    Strategy:
    1. Search by arXiv ID (most precise)
    2. If no result, search by paper title keywords

    Returns:
        Number of stars for the best-matching repo, or 0 if not found.
    """
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "notion-research-flow/1.0",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    # Strategy 1: Search by arXiv ID
    if arxiv_id:
        stars = _github_search_query(arxiv_id, headers)
        if stars >= min_stars:
            return stars

    # Strategy 2: Search by title keywords (take first 5 significant words)
    if title:
        # Remove common stop words for better search
        stop_words = {"a", "an", "the", "of", "for", "in", "on", "with", "and", "or", "to", "is", "are", "by"}
        words = [w for w in title.split() if w.lower() not in stop_words and len(w) > 2]
        query = " ".join(words[:5])
        if query:
            stars = _github_search_query(query, headers)
            if stars >= min_stars:
                return stars

    return 0


def _github_search_query(query: str, headers: dict) -> int:
    """Execute a GitHub repository search query.

    Returns:
        Stars of the best-matching repo, or 0.
    """
    encoded_q = urllib.parse.quote(f"{query} in:readme,description")
    url = f"{GITHUB_API}/search/repositories?q={encoded_q}&sort=stars&order=desc&per_page=3"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())

        items = data.get("items", [])
        if items:
            return items[0].get("stargazers_count", 0)
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print(f"Warning: GitHub API rate limited. Skipping remaining searches.", file=sys.stderr)
        else:
            print(f"Warning: GitHub search failed ({e.code}): {e.reason}", file=sys.stderr)
    except Exception as e:
        print(f"Warning: GitHub search error: {e}", file=sys.stderr)

    return 0


def _estimate_twitter_mentions(arxiv_id: str, twitter_config: dict) -> int:
    """Estimate Twitter/X mentions for a paper.

    Uses a simple heuristic: searches for the arXiv ID on the web.
    This is a best-effort estimate and may not be accurate.

    Returns:
        Estimated number of mentions, or 0.
    """
    # For now, return 0 as a placeholder.
    # Phase 2 enhancement: use X API v2 if bearer_token is configured,
    # or use a web search API to estimate mentions.
    bearer_token = twitter_config.get("bearer_token", "")
    if not bearer_token:
        return 0

    # X API v2 search (requires elevated access)
    url = f"https://api.twitter.com/2/tweets/search/recent?query={arxiv_id}&max_results=10"
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "User-Agent": "notion-research-flow/1.0",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
        return data.get("meta", {}).get("result_count", 0)
    except Exception as e:
        print(f"Warning: Twitter search failed: {e}", file=sys.stderr)
        return 0


def main():
    parser = argparse.ArgumentParser(description="Enrich papers with social signals")
    parser.add_argument("--config", type=str, default=None, help="Path to config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)

    papers_json = sys.stdin.read()
    papers = json.loads(papers_json)

    enriched = fetch_social_signals(papers, config)

    print(json.dumps(enriched, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
