---
name: start-my-day
description: Daily paper discovery — fetches recent arXiv papers, scores them, and pushes to your Notion database. Use when user says "start my day", "daily papers", "today's papers", "what's new", or wants paper recommendations.
---

# Start My Day — Daily Paper Discovery

Fetch, score, and push today's recommended papers to your Notion paper library.

## Prerequisites

- Workspace must be set up first (`/setup-workspace`)
- `config.yaml` must exist with research interests configured
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

Read the `paper_database_id` from the state file — this is needed for writing to Notion.

### Step 2: Search arXiv

Run the arXiv search script:

```bash
cd "$REPO_ROOT"
python3 skills/start-my-day/scripts/search_arxiv.py --config config.yaml
```

This outputs a JSON array of papers to stdout. Capture the output.

### Step 3: Score & Rank Papers

Pipe the search results through the scoring engine:

```bash
cd "$REPO_ROOT"
echo '$PAPERS_JSON' | python3 skills/start-my-day/scripts/score_papers.py --config config.yaml
```

This outputs scored papers sorted by composite_score (descending), capped at `daily_top_n`.

### Step 4: Deduplicate Against Notion

Before creating new entries, check for duplicates:

Use `mcp__notion__notion-search` to search the paper database for each paper's arXiv ID.

For any papers already in Notion, skip them and note "already exists".

### Step 5: Push to Notion

For each new (non-duplicate) paper, create a Notion page using `mcp__notion__notion-create-pages`.

Use the `paper_database_id` from Step 1 as the parent.

For each paper, set these properties:
- **Title**: paper title
- **ArXiv ID**: arxiv_id
- **Authors**: authors string
- **Abstract**: abstract (truncated to 2000 chars)
- **Domain**: assigned domain from scoring
- **Composite Score**: composite_score (0-10 scale, e.g. 8.1)
- **Relevance Score**: relevance_score (0-10 scale)
- **Social Score**: social_score (0-10 scale)
- **Citation Count**: citation_count
- **Added Date**: today's date
- **Published Date**: published_date
- **PDF URL**: pdf_url
- **Source URL**: source_url
- **Source**: "arXiv"
- **Status**: "Not started" (default, maps to "Unread")

You can batch multiple pages in a single `notion-create-pages` call for efficiency.

### Step 6: Write Rich Content to Each Paper Page

For EVERY paper pushed to Notion, update the page content (not just properties) with structured analysis using `mcp__notion__notion-update-page` with `replace_content`:

```markdown
## TL;DR
[1-2 sentence summary: what the paper does + key quantitative result]

## Core Contributions
- [Contribution 1 — the main novelty]
- [Contribution 2 — the technical approach]
- [Contribution 3 — key result or insight]

## Key Results
| Metric | Value |
|--------|-------|
| [main benchmark] | [number] |
| [comparison] | [vs baseline] |

## Why It Matters
[1-2 sentences connecting this paper to the user's research interests from config.yaml]

## Links
- [PDF](pdf_url) | [Abstract](source_url) | [Code](github_url if available)
```

### Step 7: Create Daily Digest Page

Create a standalone Notion page (under the Research parent page) as the daily overview:

**Title**: `YYYY-MM-DD Daily Paper Digest`
**Icon**: chart emoji

**Content structure**:
```markdown
## Overview
**N new papers** added today. Domains: [list domains found].

## Research Trends
[3-4 bullet points summarizing themes across today's papers]

## Today's Top 3
### 1. [Title] ([score]/10)
[2-3 sentence summary + why it's #1]
→ [Link to Notion page]

### 2. [Title] ([score]/10)
[2-3 sentence summary]
→ [Link to Notion page]

### 3. [Title] ([score]/10)
[2-3 sentence summary]
→ [Link to Notion page]

## Reading Recommendations
| Priority | Paper | Why Read |
|----------|-------|----------|
| ⭐⭐⭐ | [best paper] | [reason] |
| ⭐⭐ | [next] | [reason] |
| ⭐ | [next] | [reason] |

## Score Distribution (0-10 scale)
- **8.0+**: N papers — [names]
- **7.0-8.0**: N papers — [names]
- **6.0-7.0**: N papers — [names]
```

### Step 8: Present Summary to User

Display the complete results in the conversation:

```markdown
## Daily Paper Recommendations — [today's date]

Found **N** new papers (**M** already in library, skipped).

### Top 3
| # | Score | Title | Domain |
|---|-------|-------|--------|
| 1 | 8.1/10 | ... | LLM |
| 2 | 7.9/10 | ... | VLM |
| 3 | 7.7/10 | ... | LLM |

📊 Daily Digest → [link to digest page]
📚 Paper Library → [link to database]

### Next Steps
- `/paper-analyze [arxiv_id]` — deep-read any paper above
- `/paper-search [keyword]` — search your library
```

## Key Rules

- Always run `/setup-workspace` first if state file is missing
- Deduplicate before creating — never create duplicate entries in Notion
- Respect arXiv API rate limits: 0.5s delay between queries
- Show progress as you work: "Searching arXiv...", "Scoring papers...", "Pushing to Notion..."
- If arXiv API is unreachable, report the error and suggest trying again later
- Cap abstract at 2000 characters to stay within Notion's rich text limits
- Scores use 0-10 scale (not percentage). Phase 1 uses 3 active dimensions (relevance/recency/quality), re-normalized to full range
- EVERY paper page must have rich content (TL;DR, contributions, results, links) — not just database properties
- ALWAYS create a daily digest page with trends, top 3 analysis, and reading recommendations
