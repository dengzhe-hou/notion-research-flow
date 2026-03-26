#!/usr/bin/env python3
"""Score and rank papers using the multi-dimensional scoring engine.

Phase 1 (MVP): 3D scoring — relevance + recency + quality
Phase 2: Upgrades to 5D — adds popularity (citations) + social signals

Usage:
    echo '[...papers...]' | python3 score_papers.py --config config.yaml

Output:
    JSON array of scored papers (sorted by composite_score DESC) to stdout.
"""

import argparse
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from scripts.config_loader import load_config


def score_papers(papers: list[dict], config: dict) -> list[dict]:
    """Score a list of papers using the configured scoring weights.

    Args:
        papers: List of paper dicts (from search_arxiv.py or other sources).
        config: Full configuration dict.

    Returns:
        Papers with added score fields, sorted by composite_score descending.
    """
    weights = config["scoring"]
    domains = config["interests"].get("domains", [])
    threshold = config["display"].get("score_threshold", 0.0)

    for paper in papers:
        # 1. Relevance score (0-1)
        relevance = _compute_relevance(paper, domains)
        paper["relevance_score"] = round(relevance, 3)

        # 2. Recency score (0-1)
        recency = _compute_recency(paper)

        # 3. Popularity score (0-1) — citations + venue
        popularity = _compute_popularity(paper)

        # 4. Social score (0-1) — GitHub + Twitter
        social = _compute_social(paper)
        paper["social_score"] = round(social, 3)

        # 5. Quality score (0-1) — author proxy + abstract quality
        quality = _compute_quality(paper)

        # Composite score (weighted sum / 100)
        composite = (
            weights.get("relevance", 35) * relevance
            + weights.get("recency", 15) * recency
            + weights.get("popularity", 20) * popularity
            + weights.get("social", 20) * social
            + weights.get("quality", 10) * quality
        ) / 100.0

        paper["composite_score"] = round(composite, 3)

        # Assign best-matching domain
        paper["domain"] = _assign_domain(paper, domains)

    # Sort by composite score descending
    papers.sort(key=lambda p: p["composite_score"], reverse=True)

    # Filter by threshold
    papers = [p for p in papers if p["composite_score"] >= threshold]

    return papers


def _compute_relevance(paper: dict, domains: list[dict]) -> float:
    """Compute relevance score based on keyword and category matching.

    Considers both keyword presence and domain priority weights.
    """
    title = paper.get("title", "").lower()
    abstract = paper.get("abstract", "").lower()
    paper_cats = set(paper.get("categories", []))
    text = f"{title} {abstract}"

    max_score = 0.0

    for domain in domains:
        priority = domain.get("priority", 5) / 10.0  # normalize to 0-1
        keywords = domain.get("keywords", [])
        domain_cats = set(domain.get("arxiv_categories", []))

        # Keyword matching (0-1): fraction of domain keywords found
        if keywords:
            matches = sum(1 for kw in keywords if kw.lower() in text)
            keyword_score = min(matches / max(len(keywords) * 0.3, 1), 1.0)
        else:
            keyword_score = 0.0

        # Category matching (0 or 0.3): bonus for matching arXiv category
        cat_score = 0.3 if paper_cats & domain_cats else 0.0

        # Combined, weighted by priority
        domain_score = (0.7 * keyword_score + cat_score) * priority
        max_score = max(max_score, domain_score)

    return min(max_score, 1.0)


def _compute_recency(paper: dict) -> float:
    """Compute recency score using exponential decay.

    Returns 1.0 for today, ~0.5 at 7 days, ~0.05 at 30 days.
    """
    published = paper.get("published_date", "")
    if not published:
        return 0.3  # default for unknown dates

    try:
        pub_date = datetime.strptime(published, "%Y-%m-%d")
        days_old = (datetime.now() - pub_date).days
        return math.exp(-0.1 * max(days_old, 0))
    except (ValueError, TypeError):
        return 0.3


def _compute_popularity(paper: dict) -> float:
    """Compute popularity score from citations and venue.

    Phase 1: Only citation count (if available).
    Phase 2: Add venue tier scoring.
    """
    citations = paper.get("citation_count", 0) or 0
    citation_score = min(citations / 100.0, 1.0)

    # Venue tier bonus (Phase 2: will be enriched with conference data)
    venue_tiers = {
        "NeurIPS": 1.0, "ICML": 1.0, "ICLR": 1.0,
        "ACL": 0.9, "EMNLP": 0.85, "NAACL": 0.8,
        "CVPR": 0.9, "ICCV": 0.85, "ECCV": 0.8,
        "AAAI": 0.8, "IJCAI": 0.75,
    }
    conference = paper.get("conference", "")
    venue_score = venue_tiers.get(conference, 0.0)

    return 0.7 * citation_score + 0.3 * venue_score


def _compute_social(paper: dict) -> float:
    """Compute social signal score from GitHub stars and Twitter mentions.

    Phase 1: Returns 0 (social signals not yet collected).
    Phase 2: Populated by social_signals.py.
    """
    github_stars = paper.get("github_stars", 0) or 0
    twitter_mentions = paper.get("twitter_mentions", 0) or 0

    github_score = min(github_stars / 500.0, 1.0)
    twitter_score = min(twitter_mentions / 50.0, 1.0)

    if github_stars == 0 and twitter_mentions == 0:
        return 0.0

    return 0.5 * github_score + 0.5 * twitter_score


def _compute_quality(paper: dict) -> float:
    """Compute quality score as a proxy from abstract characteristics.

    Heuristic: papers with methodology indicators, quantitative results,
    and proper structure tend to be higher quality.
    """
    abstract = paper.get("abstract", "").lower()

    score = 0.3  # base score

    # Methodology markers
    method_markers = [
        "we propose", "we introduce", "we present", "our method",
        "our approach", "we design", "novel", "state-of-the-art",
        "outperform", "benchmark", "ablation",
    ]
    method_count = sum(1 for m in method_markers if m in abstract)
    score += min(method_count * 0.1, 0.3)

    # Quantitative results markers
    if re.search(r"\d+\.?\d*%", abstract):
        score += 0.15
    if re.search(r"(?:accuracy|f1|bleu|rouge|auc|map)\s", abstract):
        score += 0.1

    # Length as quality proxy (very short abstracts are often lower quality)
    word_count = len(abstract.split())
    if word_count > 150:
        score += 0.1
    elif word_count < 50:
        score -= 0.1

    return max(min(score, 1.0), 0.0)


def _assign_domain(paper: dict, domains: list[dict]) -> str:
    """Assign the best-matching domain name to a paper."""
    title = paper.get("title", "").lower()
    abstract = paper.get("abstract", "").lower()
    paper_cats = set(paper.get("categories", []))
    text = f"{title} {abstract}"

    best_domain = "Other"
    best_score = 0.0

    for domain in domains:
        keywords = domain.get("keywords", [])
        domain_cats = set(domain.get("arxiv_categories", []))

        kw_score = sum(1 for kw in keywords if kw.lower() in text)
        cat_score = 2 if paper_cats & domain_cats else 0
        total = kw_score + cat_score

        if total > best_score:
            best_score = total
            best_domain = domain["name"]

    return best_domain


def main():
    parser = argparse.ArgumentParser(description="Score and rank papers")
    parser.add_argument("--config", type=str, default=None, help="Path to config.yaml")
    parser.add_argument("--top-n", type=int, default=None, help="Override daily_top_n")
    args = parser.parse_args()

    config = load_config(args.config)

    # Read papers from stdin
    papers_json = sys.stdin.read()
    papers = json.loads(papers_json)

    scored = score_papers(papers, config)

    top_n = args.top_n or config["display"].get("daily_top_n", 15)
    scored = scored[:top_n]

    print(json.dumps(scored, ensure_ascii=False, indent=2))

    # Summary to stderr
    print(f"\n# Scored {len(scored)} papers (threshold: {config['display'].get('score_threshold', 0)})", file=sys.stderr)
    if scored:
        print(f"# Top score: {scored[0]['composite_score']:.1%} — {scored[0]['title'][:60]}", file=sys.stderr)
        print(f"# Bottom score: {scored[-1]['composite_score']:.1%}", file=sys.stderr)


if __name__ == "__main__":
    main()
