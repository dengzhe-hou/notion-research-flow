#!/usr/bin/env python3
"""Unit tests for the Semantic Scholar search module."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "conf-papers" / "scripts"))

from search_semantic_scholar import (
    search_semantic_scholar,
    _search_papers,
    _normalize_venue,
)

MOCK_S2_RESPONSE = json.dumps({
    "data": [
        {
            "title": "Attention Is All You Need",
            "abstract": "We propose a new architecture based solely on attention mechanisms.",
            "authors": [{"name": "Ashish Vaswani"}, {"name": "Noam Shazeer"}],
            "citationCount": 90000,
            "venue": "Neural Information Processing Systems",
            "year": 2017,
            "externalIds": {"ArXiv": "1706.03762", "CorpusId": "215416146"},
            "url": "https://www.semanticscholar.org/paper/xxx",
            "publicationDate": "2017-06-12",
        },
        {
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "abstract": "We introduce BERT, a new language representation model.",
            "authors": [{"name": "Jacob Devlin"}],
            "citationCount": 70000,
            "venue": "NAACL",
            "year": 2019,
            "externalIds": {"ArXiv": "1810.04805", "CorpusId": "52967399"},
            "url": "https://www.semanticscholar.org/paper/yyy",
            "publicationDate": "2019-06-01",
        },
    ]
}).encode()


def test_normalize_venue_neurips():
    assert _normalize_venue("Neural Information Processing Systems") == "NeurIPS"
    assert _normalize_venue("NeurIPS 2024") == "NeurIPS"
    assert _normalize_venue("nips") == "NeurIPS"


def test_normalize_venue_others():
    assert _normalize_venue("ICML") == "ICML"
    assert _normalize_venue("International Conference on Machine Learning") == "ICML"
    assert _normalize_venue("ACL 2025") == "ACL"
    assert _normalize_venue("CVPR") == "CVPR"


def test_normalize_venue_unknown():
    assert _normalize_venue("Some Workshop") == "Some Workshop"
    assert _normalize_venue("") == ""


def test_parse_s2_response():
    """Verify paper dict format from S2 API response."""
    mock_response = MagicMock()
    mock_response.read.return_value = MOCK_S2_RESPONSE
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("search_semantic_scholar.urllib.request.urlopen", return_value=mock_response):
        papers = _search_papers("attention", year=None, api_key="", max_results=10)

    assert len(papers) == 2

    p = papers[0]
    assert p["arxiv_id"] == "1706.03762"
    assert p["title"] == "Attention Is All You Need"
    assert p["citation_count"] == 90000
    assert p["conference"] == "NeurIPS"
    assert p["source"] == "Semantic Scholar"
    assert p["year"] == 2017
    assert p["pdf_url"] == "https://arxiv.org/pdf/1706.03762.pdf"
    assert p["github_stars"] == 0
    assert p["twitter_mentions"] == 0


def test_min_citations_filter():
    """Papers below min_citations should be filtered out."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "data": [
            {
                "title": "Low Cited Paper",
                "abstract": "Not cited much.",
                "authors": [{"name": "Nobody"}],
                "citationCount": 2,
                "venue": "",
                "year": 2025,
                "externalIds": {"ArXiv": "2501.00001"},
                "url": "",
                "publicationDate": "2025-01-01",
            },
        ]
    }).encode()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("search_semantic_scholar.urllib.request.urlopen", return_value=mock_response):
        with patch("search_semantic_scholar.time.sleep"):
            papers = search_semantic_scholar(
                keywords=["test"], min_citations=10, max_results=10
            )
    assert len(papers) == 0, "Low-cited paper should be filtered by min_citations"


def test_year_filter():
    """Papers outside the year range should be filtered."""
    mock_response = MagicMock()
    mock_response.read.return_value = MOCK_S2_RESPONSE
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("search_semantic_scholar.urllib.request.urlopen", return_value=mock_response):
        with patch("search_semantic_scholar.time.sleep"):
            papers = search_semantic_scholar(
                keywords=["attention"], year=2017, max_results=10
            )
    # Only the 2017 paper should pass
    assert all(p["year"] == 2017 for p in papers)


def test_network_error_returns_empty():
    """Network errors should return empty list, not crash."""
    with patch("search_semantic_scholar.urllib.request.urlopen", side_effect=Exception("timeout")):
        papers = _search_papers("test", year=None, api_key="", max_results=10)
    assert papers == []


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
