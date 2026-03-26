---
name: start-my-day
description: Daily paper discovery — fetches recent arXiv papers, scores them, and pushes to your Notion database. Use when user says "start my day", "daily papers", "today's papers", "what's new", or wants paper recommendations.
allowed-tools: Bash(*), Read, Write, mcp__notion__notion-search, mcp__notion__notion-create-pages, mcp__notion__notion-fetch
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
- **Composite Score**: composite_score (as percentage, e.g. 0.75)
- **Relevance Score**: relevance_score (as percentage)
- **Social Score**: social_score (as percentage)
- **Citation Count**: citation_count
- **Added Date**: today's date
- **Published Date**: published_date
- **PDF URL**: pdf_url
- **Source URL**: source_url
- **Source**: "arXiv"
- **Status**: "Not started" (default, maps to "Unread")

You can batch multiple pages in a single `notion-create-pages` call for efficiency.

### Step 6: Generate TL;DR for Top Papers

For the top `deep_analyze_top` papers (default 3):

Read the paper's abstract carefully and generate a brief analysis:

```markdown
### [Rank]. [Title]
**Score**: [composite_score]% | **Domain**: [domain] | **arXiv**: [arxiv_id]

**TL;DR**: [1-2 sentence summary of the key contribution]

**Why it matters**: [1 sentence on relevance to user's research interests]

**PDF**: [pdf_url]
```

### Step 7: Present Summary

Display the complete results:

```markdown
## Daily Paper Recommendations — [today's date]

Found **N** new papers (**M** already in library, skipped).

### Top Recommendations

[TL;DR for top 3 papers from Step 6]

### All Papers

| # | Score | Title | Domain | arXiv ID |
|---|-------|-------|--------|----------|
| 1 | 75%   | ...   | LLM    | 2603.xxxxx |
| 2 | 68%   | ...   | VLM    | 2603.xxxxx |
...

### Next Steps
- `/paper-analyze [arxiv_id]` — deep-read any paper above
- `/paper-search [keyword]` — search your library
- `/conf-papers [conference] [year]` — track conference papers
```

## Key Rules

- Always run `/setup-workspace` first if state file is missing
- Deduplicate before creating — never create duplicate entries in Notion
- Respect arXiv API rate limits: 0.5s delay between queries
- Show progress as you work: "Searching arXiv...", "Scoring papers...", "Pushing to Notion..."
- If arXiv API is unreachable, report the error and suggest trying again later
- Cap abstract at 2000 characters to stay within Notion's rich text limits
- The scoring engine works even without social signals (Phase 1) — social_score will be 0
