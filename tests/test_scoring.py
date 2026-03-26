#!/usr/bin/env python3
"""Unit tests for the paper scoring engine."""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "start-my-day" / "scripts"))

from score_papers import (
    score_papers,
    _compute_relevance,
    _compute_recency,
    _compute_popularity,
    _compute_social,
    _compute_quality,
    _assign_domain,
)

# Minimal config for testing
TEST_CONFIG = {
    "scoring": {
        "relevance": 35,
        "recency": 15,
        "popularity": 20,
        "social": 20,
        "quality": 10,
    },
    "interests": {
        "domains": [
            {
                "name": "LLM",
                "priority": 8,
                "keywords": ["large language model", "LLM", "in-context learning"],
                "arxiv_categories": ["cs.CL", "cs.AI"],
            },
            {
                "name": "VLM",
                "priority": 7,
                "keywords": ["vision-language", "multimodal", "CLIP"],
                "arxiv_categories": ["cs.CV"],
            },
        ],
    },
    "display": {
        "score_threshold": 0.0,
        "daily_top_n": 15,
    },
}

SAMPLE_PAPER_LLM = {
    "arxiv_id": "2401.00001",
    "title": "A Novel Large Language Model for In-Context Learning",
    "abstract": "We propose a new LLM architecture that outperforms state-of-the-art on benchmarks. "
                "Our method achieves 92.3% accuracy on SuperGLUE. We present ablation studies.",
    "authors": "Alice, Bob",
    "published_date": datetime.now().strftime("%Y-%m-%d"),
    "categories": ["cs.CL", "cs.AI"],
    "pdf_url": "https://arxiv.org/pdf/2401.00001.pdf",
    "source_url": "https://arxiv.org/abs/2401.00001",
    "source": "arXiv",
    "citation_count": 0,
    "github_stars": 0,
    "twitter_mentions": 0,
}

SAMPLE_PAPER_UNRELATED = {
    "arxiv_id": "2401.00002",
    "title": "Optimal Routing in Sensor Networks",
    "abstract": "This paper studies routing protocols for wireless sensor networks.",
    "authors": "Charlie",
    "published_date": "2026-03-20",
    "categories": ["cs.NI"],
    "pdf_url": "https://arxiv.org/pdf/2401.00002.pdf",
    "source_url": "https://arxiv.org/abs/2401.00002",
    "source": "arXiv",
    "citation_count": 0,
    "github_stars": 0,
    "twitter_mentions": 0,
}


def test_relevance_high_match():
    domains = TEST_CONFIG["interests"]["domains"]
    score = _compute_relevance(SAMPLE_PAPER_LLM, domains)
    assert score > 0.5, f"LLM paper should have high relevance, got {score}"


def test_relevance_low_match():
    domains = TEST_CONFIG["interests"]["domains"]
    score = _compute_relevance(SAMPLE_PAPER_UNRELATED, domains)
    assert score < 0.2, f"Unrelated paper should have low relevance, got {score}"


def test_recency_today():
    today = datetime.now().strftime("%Y-%m-%d")
    paper = {"published_date": today}
    score = _compute_recency(paper)
    assert score > 0.9, f"Today's paper should have recency ~1.0, got {score}"


def test_recency_old():
    paper = {"published_date": "2025-01-01"}
    score = _compute_recency(paper)
    assert score < 0.1, f"Old paper should have low recency, got {score}"


def test_recency_missing():
    score = _compute_recency({})
    assert score == 0.3, f"Missing date should default to 0.3, got {score}"


def test_popularity_no_citations():
    score = _compute_popularity({"citation_count": 0})
    assert score == 0.0


def test_popularity_with_citations():
    score = _compute_popularity({"citation_count": 50})
    assert 0.3 < score < 0.5


def test_popularity_with_venue():
    score = _compute_popularity({"citation_count": 0, "conference": "NeurIPS"})
    assert score == 0.3  # 0.7*0 + 0.3*1.0


def test_social_no_signals():
    score = _compute_social({"github_stars": 0, "twitter_mentions": 0})
    assert score == 0.0


def test_social_with_signals():
    score = _compute_social({"github_stars": 250, "twitter_mentions": 25})
    assert score == 0.5  # 0.5*(250/500) + 0.5*(25/50)


def test_quality_markers():
    paper_good = {"abstract": "We propose a novel method that outperforms state-of-the-art. "
                              "Our approach achieves 95.2% accuracy on the benchmark. "
                              "We present comprehensive ablation studies. " * 3}
    paper_bad = {"abstract": "Short."}
    assert _compute_quality(paper_good) > _compute_quality(paper_bad)


def test_assign_domain():
    domains = TEST_CONFIG["interests"]["domains"]
    assert _assign_domain(SAMPLE_PAPER_LLM, domains) == "LLM"
    assert _assign_domain(SAMPLE_PAPER_UNRELATED, domains) == "Other"


def test_score_papers_sorted():
    papers = [SAMPLE_PAPER_UNRELATED.copy(), SAMPLE_PAPER_LLM.copy()]
    scored = score_papers(papers, TEST_CONFIG)
    assert scored[0]["composite_score"] >= scored[-1]["composite_score"]


def test_score_papers_range():
    papers = [SAMPLE_PAPER_LLM.copy()]
    scored = score_papers(papers, TEST_CONFIG)
    s = scored[0]["composite_score"]
    assert 0 <= s <= 10, f"Composite score should be 0-10, got {s}"


def test_subscores_are_0_10():
    papers = [SAMPLE_PAPER_LLM.copy()]
    scored = score_papers(papers, TEST_CONFIG)
    p = scored[0]
    assert 0 <= p["relevance_score"] <= 10, f"relevance_score out of range: {p['relevance_score']}"
    assert 0 <= p["social_score"] <= 10, f"social_score out of range: {p['social_score']}"


def test_score_papers_threshold():
    config = {**TEST_CONFIG, "display": {"score_threshold": 9.9, "daily_top_n": 15}}
    papers = [SAMPLE_PAPER_UNRELATED.copy()]
    scored = score_papers(papers, config)
    assert len(scored) == 0, "Low-scoring paper should be filtered by high threshold"


def test_weight_renormalization():
    """Phase 1: social/popularity have no data → weights redistribute to relevance+recency+quality."""
    papers = [SAMPLE_PAPER_LLM.copy()]
    scored = score_papers(papers, TEST_CONFIG)
    # With renormalization, a highly relevant today's paper should score well above 5
    assert scored[0]["composite_score"] > 5.0


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"  ERROR {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
    sys.exit(1 if failed else 0)
