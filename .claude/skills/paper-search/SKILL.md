---
name: paper-search
description: Search your Notion paper library by keyword, domain, score, status, or date range. Use when user says "search papers", "find papers about X", "papers on topic", "show me papers", "paper search", or wants to look up papers in their library.
---

# Paper Search — Query Your Notion Library

Search and filter papers in your Notion paper database using keywords, domains, scores, status, and date ranges.

## Prerequisites

- Workspace must be set up first (`/setup-workspace`)
- `.notion-research-flow.json` must contain `paper_database_id`

## Workflow

### Step 1: Load Config & State

```bash
REPO_ROOT=$(python3 -c "
from pathlib import Path
p = Path.cwd()
for d in [p] + list(p.parents):
    if (d / 'config.example.yaml').exists():
        print(d); break
")
cd "$REPO_ROOT"
```

Check that `.notion-research-flow.json` exists and has `setup_complete: true`.
Read the `paper_database_id` from the state file.

### Step 2: Parse Search Query

Extract search criteria from the user's message. Support these filter types:

- **Keyword** (free text): search in Title and Abstract fields
- **Domain** (select): match against Domain property (e.g., "LLM", "VLM")
- **Score threshold** (number): minimum Composite Score (0-10)
- **Status** (select): "Unread", "Reading", "Read", "Noted"
- **Conference** (select): e.g., "NeurIPS", "ICML"
- **Date range**: "last N days", "this week", "this month", or specific dates
- **Source** (select): "arXiv", "Semantic Scholar", "DBLP", "Manual"

Examples of user queries and how to parse them:
- "papers about attention mechanisms" → keyword: "attention mechanisms"
- "unread LLM papers with score > 7" → status: Unread, domain: LLM, score: > 7
- "NeurIPS 2025 papers" → conference: NeurIPS, year: 2025
- "papers added this week" → date range: last 7 days
- "top 10 papers" → sort by score, limit 10

### Step 3: Query Notion Database

Use `mcp__notion__notion-fetch` to query the paper database with appropriate filters.

The database URL format: `https://www.notion.so/{paper_database_id}`

Build the query by constructing a natural language filter description that Notion MCP will interpret. Examples:

- For keyword search: Search within the database for papers whose Title or Abstract contains the keyword
- For domain filter: Filter where Domain equals the specified domain
- For score threshold: Filter where Composite Score is greater than or equal to the threshold
- For status filter: Filter where Status equals the specified status
- For date range: Filter where Added Date is within the specified range

If the search criteria are complex, break them into multiple queries and intersect results.

### Step 4: Format & Display Results

Present results as a formatted markdown table:

```markdown
## Search Results: "[query]"

Found **N** papers matching your criteria.

| # | Score | Title | Domain | Status | Added |
|---|-------|-------|--------|--------|-------|
| 1 | 8.1/10 | [Title with Notion link] | LLM | Unread | 2025-03-27 |
| 2 | 7.5/10 | [Title with Notion link] | VLM | Reading | 2025-03-26 |
...

### Score Summary
- Average score: X.X/10
- Highest: X.X/10 — [title]
- Domains: LLM (N), VLM (N), ...
```

If no results found, suggest:
- Broadening the search criteria
- Checking available domains with a list
- Running `/start-my-day` to add more papers

### Step 5: Suggest Actions

Based on the search results, offer relevant next actions:

```markdown
### Actions
- `/paper-analyze [arxiv_id]` — deep analysis of any paper above
- `/team-sync assign [title] to [person]` — assign for reading
- Refine: "search [narrower keyword]" or "show only unread"
```

## Key Rules

- Always run `/setup-workspace` first if state file is missing
- Default sort: Composite Score descending (highest first)
- Default limit: 20 papers (user can request more)
- If keyword search returns too many results (>50), suggest narrowing criteria
- Show Notion page links for each paper so user can click through
- Preserve the user's search context — if they refine, build on previous criteria
- Handle empty results gracefully with helpful suggestions
