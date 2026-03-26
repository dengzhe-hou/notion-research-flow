#!/usr/bin/env python3
"""Unit tests for the DBLP search module."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "conf-papers" / "scripts"))

from search_dblp import search_dblp, _search_by_query, VENUE_KEYS

MOCK_DBLP_RESPONSE = json.dumps({
    "result": {
        "hits": {
            "hit": [
                {
                    "info": {
                        "title": "Scaling Laws for Neural Language Models.",
                        "authors": {
                            "author": [
                                {"text": "Jared Kaplan"},
                                {"text": "Sam McCandlish"},
                            ]
                        },
                        "year": "2020",
                        "venue": "NeurIPS",
                        "doi": "10.5555/3495724.3496878",
                        "url": "https://dblp.org/rec/conf/nips/KaplanMHBDBS20",
                        "ee": "https://arxiv.org/abs/2001.08361",
                    }
                },
                {
                    "info": {
                        "title": "Language Models are Few-Shot Learners.",
                        "authors": {
                            "author": [
                                {"text": "Tom Brown"},
                                {"text": "Benjamin Mann"},
                            ]
                        },
                        "year": "2020",
                        "venue": "NeurIPS",
                        "doi": "",
                        "url": "https://dblp.org/rec/conf/nips/BrownMRS20",
                        "ee": ["https://arxiv.org/abs/2005.14165", "https://proceedings.neurips.cc/paper/2020/xxx"],
                    }
                },
            ]
        }
    }
}).encode()


def test_venue_keys_exist():
    """All standard conferences should have DBLP venue keys."""
    expected = ["NeurIPS", "ICML", "ICLR", "ACL", "EMNLP", "CVPR", "ICCV", "ECCV", "AAAI", "IJCAI"]
    for conf in expected:
        assert conf in VENUE_KEYS, f"Missing venue key for {conf}"


def test_parse_dblp_response():
    """Verify paper dict format from DBLP response."""
    mock_response = MagicMock()
    mock_response.read.return_value = MOCK_DBLP_RESPONSE
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("search_dblp.urllib.request.urlopen", return_value=mock_response):
        papers = _search_by_query("NeurIPS 2020", max_results=10)

    assert len(papers) == 2

    p0 = papers[0]
    assert p0["title"] == "Scaling Laws for Neural Language Models"
    assert "Jared Kaplan" in p0["authors"]
    assert p0["year"] == 2020
    assert p0["source"] == "DBLP"
    assert p0["github_stars"] == 0
    assert p0["twitter_mentions"] == 0


def test_arxiv_id_extraction_from_ee():
    """arXiv ID should be extracted from DBLP ee links."""
    mock_response = MagicMock()
    mock_response.read.return_value = MOCK_DBLP_RESPONSE
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("search_dblp.urllib.request.urlopen", return_value=mock_response):
        papers = _search_by_query("test", max_results=10)

    # First paper: ee is a string with arxiv URL
    assert papers[0]["arxiv_id"] == "2001.08361"
    # Second paper: ee is a list containing arxiv URL
    assert papers[1]["arxiv_id"] == "2005.14165"


def test_title_deduplication():
    """Duplicate titles should be removed."""
    mock_response = MagicMock()
    dup_response = json.dumps({
        "result": {
            "hits": {
                "hit": [
                    {
                        "info": {
                            "title": "Same Paper Title.",
                            "authors": {"author": [{"text": "Author"}]},
                            "year": "2025",
                            "venue": "NeurIPS",
                            "url": "",
                            "ee": "",
                        }
                    },
                ]
            }
        }
    }).encode()
    mock_response.read.return_value = dup_response
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    # search_dblp deduplicates across venue + keyword searches
    with patch("search_dblp.urllib.request.urlopen", return_value=mock_response):
        with patch("search_dblp.time.sleep"):
            papers = search_dblp(
                conference="NeurIPS",
                year=2025,
                keywords=["test"],
                max_results=10,
            )

    # Should only have 1 unique paper despite multiple queries returning the same title
    titles = [p["title"] for p in papers]
    assert len(titles) == len(set(t.lower() for t in titles)), "Duplicate titles found"


def test_year_filter():
    """Papers outside the year filter should be excluded."""
    mock_response = MagicMock()
    mock_response.read.return_value = MOCK_DBLP_RESPONSE
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("search_dblp.urllib.request.urlopen", return_value=mock_response):
        with patch("search_dblp.time.sleep"):
            papers = search_dblp(conference="NeurIPS", year=2025, max_results=10)

    # Both mock papers are from 2020, so filtering for 2025 should return empty
    assert len(papers) == 0


def test_network_error_returns_empty():
    """Network errors should return empty list."""
    with patch("search_dblp.urllib.request.urlopen", side_effect=Exception("timeout")):
        papers = _search_by_query("test", max_results=10)
    assert papers == []


def test_conference_field_set():
    """Conference field should be set on all returned papers."""
    mock_response = MagicMock()
    mock_response.read.return_value = MOCK_DBLP_RESPONSE
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("search_dblp.urllib.request.urlopen", return_value=mock_response):
        with patch("search_dblp.time.sleep"):
            papers = search_dblp(conference="NeurIPS", year=2020, max_results=10)

    for p in papers:
        assert p["conference"] == "NeurIPS", f"Expected NeurIPS, got {p['conference']}"


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
