---
name: conf-papers
description: Track papers from top ML/AI conferences using Semantic Scholar and DBLP. Use when user says "conf papers", "conference papers", "NeurIPS papers", "ICML 2025", "show me [conference] papers", or wants to explore a specific conference's proceedings.
---

# Conference Papers — Track Top Venue Proceedings

Search, score, and add conference papers to your Notion paper library using Semantic Scholar and DBLP.

## Prerequisites

- Workspace must be set up first (`/setup-workspace`)
- `config.yaml` must exist with `sources.semantic_scholar` and `sources.dblp` configured
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
If not, tell the user to run `/setup-workspace` first.

Read the `paper_database_id` from the state file.

### Step 2: Parse User Request

Extract from the user's message:
- **Conference name**: e.g., "NeurIPS", "ICML", "ACL". Must be one of the tracked conferences in `config.yaml` `sources.dblp.conferences`.
- **Year**: e.g., 2025. Default to the current year if not specified.
- **Keywords** (optional): additional filter keywords from the user's message.

If the conference name is not recognized, show the list of tracked conferences and ask the user to choose.

### Step 3: Search DBLP

Run the DBLP search script:

```bash
cd "$REPO_ROOT"
python3 skills/conf-papers/scripts/search_dblp.py --config config.yaml --conference "$CONFERENCE" --year "$YEAR" --keywords "$KEYWORDS"
```

This outputs a JSON array of papers from DBLP. Capture the output as `$DBLP_PAPERS`.

### Step 4: Search Semantic Scholar

Run the Semantic Scholar search script:

```bash
cd "$REPO_ROOT"
python3 skills/conf-papers/scripts/search_semantic_scholar.py --config config.yaml --conference "$CONFERENCE" --year "$YEAR" --keywords "$KEYWORDS"
```

This outputs a JSON array of papers. Capture the output as `$S2_PAPERS`.

### Step 5: Merge & Deduplicate Sources

Merge the two result sets using this logic:

```python
import json

dblp_papers = json.loads(dblp_json)
s2_papers = json.loads(s2_json)

# Index S2 papers by arxiv_id and normalized title
s2_by_arxiv = {p["arxiv_id"]: p for p in s2_papers if p.get("arxiv_id")}
s2_by_title = {p["title"].lower().strip().rstrip("."): p for p in s2_papers}

merged = []
seen = set()

# Start with S2 papers (they have citations + abstracts)
for p in s2_papers:
    key = p.get("arxiv_id") or p["title"].lower().strip()
    if key not in seen:
        seen.add(key)
        merged.append(p)

# Add DBLP papers not in S2, enriching with S2 citation data if available
for p in dblp_papers:
    key = p.get("arxiv_id") or p["title"].lower().strip().rstrip(".")
    if key not in seen:
        # Try to find S2 match for citation count
        s2_match = s2_by_arxiv.get(p.get("arxiv_id")) or s2_by_title.get(p["title"].lower().strip().rstrip("."))
        if s2_match:
            p["citation_count"] = s2_match.get("citation_count", 0)
            p["abstract"] = s2_match.get("abstract") or p.get("abstract", "")
        seen.add(key)
        merged.append(p)
```

### Step 6: Enrich with Social Signals

Pipe merged papers through the social signal enrichment:

```bash
cd "$REPO_ROOT"
echo '$MERGED_JSON' | python3 scripts/fetch_social_signals.py --config config.yaml
```

Capture the enriched output as `$ENRICHED_JSON`.

### Step 7: Score & Rank

Pipe enriched papers through the scoring engine:

```bash
cd "$REPO_ROOT"
echo '$ENRICHED_JSON' | python3 skills/start-my-day/scripts/score_papers.py --config config.yaml
```

This outputs scored papers sorted by composite_score (descending).

### Step 8: Deduplicate Against Notion

Before creating new entries, check for duplicates:

Use `mcp__notion__notion-search` to search the paper database for each paper's arXiv ID or title.

For any papers already in Notion:
- If the existing entry has **lower** citation_count or missing conference, **update** it via `mcp__notion__notion-update-page` with the new data.
- Otherwise, skip and note "already exists".

### Step 9: Push to Notion

For each new (non-duplicate) paper, create a Notion page using `mcp__notion__notion-create-pages`.

Use the `paper_database_id` from Step 1 as the parent.

Set these properties:
- **Title**: paper title
- **ArXiv ID**: arxiv_id (if available)
- **Authors**: authors string
- **Abstract**: abstract (truncated to 2000 chars)
- **Domain**: assigned domain from scoring
- **Composite Score**: composite_score (0-10 scale)
- **Relevance Score**: relevance_score (0-10 scale)
- **Social Score**: social_score (0-10 scale)
- **Citation Count**: citation_count
- **GitHub Stars**: github_stars
- **Twitter Mentions**: twitter_mentions
- **Conference**: conference name (e.g., "NeurIPS")
- **Year**: publication year
- **Added Date**: today's date
- **Published Date**: published_date
- **PDF URL**: pdf_url
- **Source URL**: source_url
- **Source**: "Semantic Scholar" or "DBLP" (whichever provided the primary data)
- **Status**: "Not started" (default, maps to "Unread")

Batch multiple pages in a single `notion-create-pages` call for efficiency.

### Step 10: Write Rich Content to Each Paper Page

For EVERY paper pushed to Notion, update the page content using `mcp__notion__notion-update-page` with `replace_content`:

```markdown
## TL;DR
[1-2 sentence summary: what the paper does + key quantitative result]

## Core Contributions
- [Contribution 1 — the main novelty]
- [Contribution 2 — the technical approach]
- [Contribution 3 — key result or insight]

## Conference Info
- **Venue**: [Conference Year] (e.g., NeurIPS 2025)
- **Citations**: [count] | **GitHub Stars**: [count]

## Why It Matters
[1-2 sentences connecting this paper to the user's research interests from config.yaml]

## Links
- [PDF](pdf_url) | [Abstract](source_url) | [Code](github_url if available)
```

If abstract is empty (common for DBLP-only papers), generate the TL;DR from the title only and note "Abstract not available — consider running `/paper-analyze` for a full analysis."

### Step 11: Present Summary to User

Display the complete results in the conversation:

```markdown
## Conference Papers — [Conference] [Year]

Found **N** new papers (**M** already in library).
Sources: DBLP (X papers) + Semantic Scholar (Y papers).

### Top 5 by Score
| # | Score | Citations | Title | Domain |
|---|-------|-----------|-------|--------|
| 1 | 8.1/10 | 42 | ... | LLM |
| 2 | 7.9/10 | 38 | ... | VLM |
...

### Citation Leaders
| # | Citations | Title |
|---|-----------|-------|
| 1 | 156 | ... |
...

📊 Conference Tracker → [link to Conference Tracker view]
📚 Paper Library → [link to database]

### Next Steps
- `/paper-analyze [arxiv_id]` — deep-read any paper above
- `/conf-papers [other conference] [year]` — explore another conference
- `/paper-search [keyword]` — search your library
```

## Key Rules

- Always run `/setup-workspace` first if state file is missing
- Deduplicate before creating — never create duplicate entries in Notion
- If a paper already exists but has new data (higher citations, added conference), UPDATE it
- Respect API rate limits: 1s between Semantic Scholar calls, 1s between DBLP calls
- Show progress as you work: "Searching DBLP...", "Searching Semantic Scholar...", "Scoring papers..."
- DBLP often lacks abstracts — note this and suggest `/paper-analyze` for detailed analysis
- Prefer Semantic Scholar data when both sources provide the same paper (richer metadata)
- Scores use 0-10 scale. With citation data available, popularity dimension is active (5D scoring)
- Set Conference and Year properties on every paper page
- EVERY paper page must have rich content — not just database properties
