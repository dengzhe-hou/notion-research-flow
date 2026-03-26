#!/usr/bin/env python3
"""Unit tests for config_loader."""

import json
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.config_loader import (
    _validate_config,
    add_known_arxiv_ids,
    get_all_categories,
    get_all_keywords,
    get_excluded_keywords,
    get_known_arxiv_ids,
    load_state,
    save_state,
)

VALID_CONFIG = {
    "researcher": {"name": "Test"},
    "interests": {
        "domains": [
            {
                "name": "LLM",
                "priority": 8,
                "keywords": ["LLM", "transformer"],
                "arxiv_categories": ["cs.CL", "cs.AI"],
            }
        ],
        "excluded_keywords": ["survey only"],
    },
    "sources": {"arxiv": {"enabled": True}},
    "scoring": {
        "relevance": 35,
        "recency": 15,
        "popularity": 20,
        "social": 20,
        "quality": 10,
    },
    "display": {"daily_top_n": 15},
}


def test_validate_config_valid():
    _validate_config(VALID_CONFIG)  # Should not raise


def test_validate_config_missing_key():
    bad = {k: v for k, v in VALID_CONFIG.items() if k != "scoring"}
    try:
        _validate_config(bad)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "scoring" in str(e)


def test_validate_config_bad_weights():
    bad = {**VALID_CONFIG, "scoring": {"relevance": 50, "recency": 50, "popularity": 0, "social": 0, "quality": 0}}
    _validate_config(bad)  # sums to 100, should pass

    bad2 = {**VALID_CONFIG, "scoring": {"relevance": 50, "recency": 50, "popularity": 1, "social": 0, "quality": 0}}
    try:
        _validate_config(bad2)
        assert False, "Should have raised ValueError for sum != 100"
    except ValueError:
        pass


def test_validate_config_no_domains():
    bad = {**VALID_CONFIG, "interests": {"domains": []}}
    try:
        _validate_config(bad)
        assert False, "Should have raised ValueError for empty domains"
    except ValueError:
        pass


def test_get_all_keywords():
    kws = get_all_keywords(VALID_CONFIG)
    assert "LLM" in kws
    assert "transformer" in kws


def test_get_all_categories():
    cats = get_all_categories(VALID_CONFIG)
    assert "cs.CL" in cats
    assert "cs.AI" in cats


def test_get_excluded_keywords():
    assert get_excluded_keywords(VALID_CONFIG) == ["survey only"]
    assert get_excluded_keywords({"interests": {}}) == []


def test_state_roundtrip():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        # Create marker so find_repo_root won't be needed
        state = {"paper_database_id": "abc123", "setup_complete": True}
        save_state(state, repo_root=tmpdir)
        loaded = load_state(repo_root=tmpdir)
        assert loaded["paper_database_id"] == "abc123"
        assert loaded["setup_complete"] is True


def test_load_state_missing():
    with tempfile.TemporaryDirectory() as tmpdir:
        loaded = load_state(repo_root=Path(tmpdir))
        assert loaded == {}


def test_known_arxiv_ids_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        known = get_known_arxiv_ids(repo_root=Path(tmpdir))
        assert known == set()


def test_add_known_arxiv_ids():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Create initial state file
        save_state({"setup_complete": True}, repo_root=root)

        add_known_arxiv_ids(["2301.07041", "2603.24533"], repo_root=root)
        known = get_known_arxiv_ids(repo_root=root)
        assert "2301.07041" in known
        assert "2603.24533" in known

        # Add more, including a duplicate and empty string
        add_known_arxiv_ids(["2301.07041", "2603.99999", ""], repo_root=root)
        known = get_known_arxiv_ids(repo_root=root)
        assert len(known) == 3  # no duplicates, no empty
        assert "2603.99999" in known


def test_known_arxiv_ids_persists():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        save_state({"paper_database_id": "abc"}, repo_root=root)
        add_known_arxiv_ids(["1234.56789"], repo_root=root)

        # Reload state and check both original keys and cache are preserved
        state = load_state(repo_root=root)
        assert state["paper_database_id"] == "abc"
        assert "1234.56789" in state["known_arxiv_ids"]


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
