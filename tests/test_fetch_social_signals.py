#!/usr/bin/env python3
"""Unit tests for the social signals enrichment module."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.fetch_social_signals import (
    fetch_social_signals,
    _search_github_stars,
    _github_search_query,
    _estimate_twitter_mentions,
)

TEST_CONFIG = {
    "social": {
        "github": {
            "enabled": True,
            "token": "",
            "min_stars": 10,
        },
        "twitter": {
            "enabled": False,
        },
    },
}

TEST_CONFIG_DISABLED = {
    "social": {
        "github": {"enabled": False},
        "twitter": {"enabled": False},
    },
}

SAMPLE_PAPERS = [
    {
        "arxiv_id": "2301.07041",
        "title": "A Novel Framework for Language Models",
        "github_stars": 0,
        "twitter_mentions": 0,
    },
    {
        "arxiv_id": "2301.07042",
        "title": "Routing in Sensor Networks",
        "github_stars": 0,
        "twitter_mentions": 0,
    },
]

MOCK_GITHUB_RESPONSE = json.dumps({
    "items": [
        {"stargazers_count": 250, "full_name": "user/repo"},
    ]
}).encode()


def test_disabled_config_returns_unchanged():
    """When social signals are disabled, papers should be returned unchanged."""
    papers = [p.copy() for p in SAMPLE_PAPERS]
    result = fetch_social_signals(papers, TEST_CONFIG_DISABLED)
    assert all(p["github_stars"] == 0 for p in result)
    assert all(p["twitter_mentions"] == 0 for p in result)


def test_github_search_with_mock():
    """GitHub search should return star count from API response."""
    mock_response = MagicMock()
    mock_response.read.return_value = MOCK_GITHUB_RESPONSE
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("scripts.fetch_social_signals.urllib.request.urlopen", return_value=mock_response):
        stars = _github_search_query("test query", {"User-Agent": "test"})
        assert stars == 250, f"Expected 250 stars, got {stars}"


def test_github_search_empty_response():
    """GitHub search with no results should return 0."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"items": []}).encode()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("scripts.fetch_social_signals.urllib.request.urlopen", return_value=mock_response):
        stars = _github_search_query("nonexistent paper", {"User-Agent": "test"})
        assert stars == 0


def test_github_search_network_error():
    """GitHub search should return 0 on network errors."""
    with patch("scripts.fetch_social_signals.urllib.request.urlopen", side_effect=Exception("Network error")):
        stars = _github_search_query("test", {"User-Agent": "test"})
        assert stars == 0


def test_min_stars_threshold():
    """Papers below min_stars should get 0."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "items": [{"stargazers_count": 5}]
    }).encode()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("scripts.fetch_social_signals.urllib.request.urlopen", return_value=mock_response):
        stars = _search_github_stars("2301.07041", "Some Paper", "", min_stars=10)
        assert stars == 0, f"Expected 0 (below min_stars), got {stars}"


def test_twitter_no_token_returns_zero():
    """Twitter estimation without bearer token should return 0."""
    mentions = _estimate_twitter_mentions("2301.07041", {"enabled": True})
    assert mentions == 0


def test_fetch_social_signals_enriches_papers():
    """Full pipeline should update github_stars field when GitHub API returns data."""
    mock_response = MagicMock()
    mock_response.read.return_value = MOCK_GITHUB_RESPONSE
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    papers = [SAMPLE_PAPERS[0].copy()]
    with patch("scripts.fetch_social_signals.urllib.request.urlopen", return_value=mock_response):
        with patch("scripts.fetch_social_signals.time.sleep"):  # skip delays
            result = fetch_social_signals(papers, TEST_CONFIG)
            assert result[0]["github_stars"] == 250


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
