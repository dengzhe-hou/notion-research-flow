#!/usr/bin/env python3
"""Notion MCP helper utilities for notion-research-flow.

This module provides helper functions for generating Notion MCP tool calls.
Since Notion operations are performed via Claude Code's MCP tools (not direct API),
these helpers format data structures and generate instructions for the SKILL.md prompts.
"""

from datetime import datetime


def format_paper_for_notion(paper: dict) -> dict:
    """Format a paper dict into Notion page properties.

    Args:
        paper: Paper dict with keys like title, arxiv_id, authors, abstract,
               domain, tags, scores, etc.

    Returns:
        Dict of Notion property name -> value, ready for notion-create-pages.
    """
    properties = {
        "Title": paper.get("title", "Untitled"),
        "ArXiv ID": paper.get("arxiv_id", ""),
        "Authors": _truncate(paper.get("authors", ""), 2000),
        "Abstract": _truncate(paper.get("abstract", ""), 2000),
        "Composite Score": paper.get("composite_score", 0),
        "Relevance Score": paper.get("relevance_score", 0),
        "Citation Count": paper.get("citation_count", 0),
        "Added Date": datetime.now().strftime("%Y-%m-%d"),
        "PDF URL": paper.get("pdf_url", ""),
        "Source URL": paper.get("source_url", ""),
    }

    if paper.get("domain"):
        properties["Domain"] = paper["domain"]
    if paper.get("tags"):
        properties["Tags"] = paper["tags"]  # list of strings
    if paper.get("conference"):
        properties["Conference"] = paper["conference"]
    if paper.get("year"):
        properties["Year"] = paper["year"]
    if paper.get("published_date"):
        properties["Published Date"] = paper["published_date"]
    if paper.get("source"):
        properties["Source"] = paper["source"]
    if paper.get("social_score"):
        properties["Social Score"] = paper["social_score"]
    if paper.get("github_stars"):
        properties["GitHub Stars"] = paper["github_stars"]
    if paper.get("twitter_mentions"):
        properties["Twitter Mentions"] = paper["twitter_mentions"]

    return properties


def generate_create_pages_markdown(papers: list[dict]) -> str:
    """Generate markdown content for batch creating Notion pages.

    This produces a formatted string that can be used in SKILL.md instructions
    for calling mcp__notion__notion-create-pages.

    Args:
        papers: List of paper dicts (already scored and filtered).

    Returns:
        Markdown-formatted table of papers for display + JSON for MCP call.
    """
    lines = []
    lines.append("| # | Title | Score | Domain | Source |")
    lines.append("|---|-------|-------|--------|--------|")

    for i, paper in enumerate(papers, 1):
        title = _truncate(paper.get("title", ""), 60)
        score = f"{paper.get('composite_score', 0)}/10"
        domain = paper.get("domain", "Other")
        source = paper.get("source", "arXiv")
        lines.append(f"| {i} | {title} | {score} | {domain} | {source} |")

    return "\n".join(lines)


def generate_database_ddl(config: dict) -> str:
    """Generate SQL DDL for creating the paper database via Notion MCP.

    Args:
        config: Full configuration dict.

    Returns:
        SQL DDL string for mcp__notion__notion-create-database.
    """
    notion_config = config.get("notion", {})

    # Build domain SELECT options
    domain_opts = notion_config.get("domain_options", [
        {"name": "LLM", "color": "blue"},
        {"name": "VLM", "color": "purple"},
        {"name": "Other", "color": "gray"},
    ])
    domain_select = ", ".join(f"'{d['name']}':{d['color']}" for d in domain_opts)

    # Build conference SELECT options
    conf_opts = notion_config.get("conference_options", [
        {"name": "NeurIPS", "color": "blue"},
        {"name": "Preprint", "color": "gray"},
    ])
    conf_select = ", ".join(f"'{c['name']}':{c['color']}" for c in conf_opts)

    ddl = f'''CREATE TABLE (
  "Title" TITLE,
  "ArXiv ID" RICH_TEXT COMMENT 'e.g. 2301.07041',
  "Authors" RICH_TEXT,
  "Abstract" RICH_TEXT,
  "Domain" SELECT({domain_select}),
  "Tags" MULTI_SELECT,
  "Composite Score" NUMBER COMMENT '0-10 scale',
  "Relevance Score" NUMBER COMMENT '0-10 scale',
  "Social Score" NUMBER COMMENT '0-10 scale',
  "Citation Count" NUMBER,
  "GitHub Stars" NUMBER,
  "Twitter Mentions" NUMBER,
  "Conference" SELECT({conf_select}),
  "Year" NUMBER,
  "Status" STATUS,
  "Assigned To" PEOPLE,
  "Added Date" DATE,
  "Published Date" DATE,
  "PDF URL" URL,
  "Source URL" URL,
  "Source" SELECT('arXiv':blue, 'Semantic Scholar':green, 'DBLP':orange, 'Manual':gray),
  "Paper ID" UNIQUE_ID PREFIX 'PAP'
)'''
    return ddl


def generate_view_configs() -> list[dict]:
    """Generate view configuration dicts for the 8 preconfigured views.

    Returns:
        List of dicts with 'name', 'type', and 'description' for each view.
    """
    return [
        {
            "name": "All Papers",
            "type": "table",
            "description": "All papers sorted by date added (newest first)",
            "sort": "Added Date DESC",
            "columns": ["Title", "Domain", "Composite Score", "Status", "Conference", "Added Date"],
        },
        {
            "name": "By Score",
            "type": "table",
            "description": "Papers ranked by composite score",
            "sort": "Composite Score DESC",
            "columns": ["Title", "Domain", "Composite Score", "Relevance Score", "Social Score", "Citation Count"],
        },
        {
            "name": "By Domain",
            "type": "board",
            "description": "Papers grouped by research domain",
            "group_by": "Domain",
            "sort": "Composite Score DESC",
        },
        {
            "name": "Reading Status",
            "type": "board",
            "description": "Kanban board for tracking reading progress",
            "group_by": "Status",
            "sort": "Composite Score DESC",
        },
        {
            "name": "Conference Tracker",
            "type": "table",
            "description": "Papers from tracked conferences",
            "filter": "Conference is not empty",
            "sort": "Year DESC",
            "columns": ["Title", "Conference", "Year", "Composite Score", "Authors"],
        },
        {
            "name": "Timeline",
            "type": "calendar",
            "description": "Calendar view by date added",
            "calendar_by": "Added Date",
        },
        {
            "name": "Trending",
            "type": "table",
            "description": "Papers with high social signals",
            "filter": "Social Score > 0",
            "sort": "Social Score DESC",
            "columns": ["Title", "Social Score", "GitHub Stars", "Twitter Mentions", "Citation Count"],
        },
        {
            "name": "Team Assignments",
            "type": "board",
            "description": "Papers grouped by assigned team member",
            "group_by": "Assigned To",
            "sort": "Status ASC",
        },
    ]


def _truncate(text: str, max_length: int) -> str:
    """Truncate text to max_length, adding ellipsis if needed."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
