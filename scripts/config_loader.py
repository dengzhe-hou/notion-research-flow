#!/usr/bin/env python3
"""Load and validate notion-research-flow configuration."""

import os
import json
import yaml
from pathlib import Path
from typing import Any

# Default config search paths (relative to repo root)
CONFIG_FILENAMES = ["config.yaml", "config.yml"]
STATE_FILENAME = ".notion-research-flow.json"


def find_repo_root() -> Path:
    """Find the repo root by looking for config.example.yaml."""
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / "config.example.yaml").exists():
            return parent
    raise FileNotFoundError(
        "Cannot find repo root. Make sure you're inside the notion-research-flow directory."
    )


def load_config(config_path: str | None = None) -> dict[str, Any]:
    """Load research configuration from YAML file.

    Args:
        config_path: Explicit path to config file. If None, searches default locations.

    Returns:
        Parsed configuration dictionary.

    Raises:
        FileNotFoundError: If no config file found.
    """
    if config_path:
        path = Path(config_path)
    else:
        root = find_repo_root()
        path = None
        for name in CONFIG_FILENAMES:
            candidate = root / name
            if candidate.exists():
                path = candidate
                break
        if path is None:
            raise FileNotFoundError(
                "No config.yaml found. Copy config.example.yaml to config.yaml and customize it:\n"
                "  cp config.example.yaml config.yaml"
            )

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    _validate_config(config)
    return config


def _validate_config(config: dict) -> None:
    """Basic validation of config structure."""
    required_keys = ["researcher", "interests", "sources", "scoring", "display"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required config key: '{key}'")

    # Validate scoring weights sum to 100
    scoring = config["scoring"]
    total = sum(scoring.get(k, 0) for k in ["relevance", "recency", "popularity", "social", "quality"])
    if total != 100:
        raise ValueError(f"Scoring weights must sum to 100, got {total}")

    # Validate at least one domain
    domains = config["interests"].get("domains", [])
    if not domains:
        raise ValueError("At least one research domain must be defined in interests.domains")


def load_state(repo_root: Path | None = None) -> dict[str, Any]:
    """Load local state (Notion database IDs, last run time, etc.).

    Returns:
        State dictionary, or empty dict if no state file exists.
    """
    root = repo_root or find_repo_root()
    state_path = root / STATE_FILENAME
    if not state_path.exists():
        return {}
    with open(state_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict[str, Any], repo_root: Path | None = None) -> None:
    """Save local state to .notion-research-flow.json."""
    root = repo_root or find_repo_root()
    state_path = root / STATE_FILENAME
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def get_all_keywords(config: dict) -> list[str]:
    """Extract all keywords from all research domains."""
    keywords = []
    for domain in config["interests"].get("domains", []):
        keywords.extend(domain.get("keywords", []))
    return keywords


def get_all_categories(config: dict) -> list[str]:
    """Extract all unique arXiv categories from all research domains."""
    categories = set()
    for domain in config["interests"].get("domains", []):
        categories.update(domain.get("arxiv_categories", []))
    return sorted(categories)


def get_excluded_keywords(config: dict) -> list[str]:
    """Get list of excluded keywords."""
    return config["interests"].get("excluded_keywords", [])


def get_known_arxiv_ids(repo_root: Path | None = None) -> set[str]:
    """Load the set of ArXiv IDs already pushed to Notion.

    Uses a local cache in .notion-research-flow.json to avoid relying on
    Notion search (which has indexing delays for newly created pages).
    """
    state = load_state(repo_root)
    return set(state.get("known_arxiv_ids", []))


def add_known_arxiv_ids(new_ids: list[str], repo_root: Path | None = None) -> None:
    """Add ArXiv IDs to the local dedup cache and persist."""
    root = repo_root or find_repo_root()
    state = load_state(root)
    existing = set(state.get("known_arxiv_ids", []))
    existing.update(id_ for id_ in new_ids if id_)
    state["known_arxiv_ids"] = sorted(existing)
    save_state(state, root)


if __name__ == "__main__":
    # Quick test
    try:
        cfg = load_config()
        print(f"Loaded config for: {cfg['researcher']['name']}")
        print(f"Domains: {[d['name'] for d in cfg['interests']['domains']]}")
        print(f"Keywords: {get_all_keywords(cfg)[:5]}...")
        print(f"Categories: {get_all_categories(cfg)}")
    except FileNotFoundError as e:
        print(f"Config not found: {e}")
