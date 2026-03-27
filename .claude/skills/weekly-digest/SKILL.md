---
name: weekly-digest
description: Generate a weekly summary of papers added to your Notion library — trends, top papers, domain breakdown, and reading progress. Use when user says "weekly digest", "weekly summary", "this week's papers", "week in review", "research roundup", or wants a periodic summary.
---

# Weekly Digest — Research Summary

Generate a comprehensive weekly summary of papers in your Notion library, create a digest page, and identify research trends.

## Prerequisites

- Workspace must be set up first (`/setup-workspace`)
- `.notion-research-flow.json` must contain `paper_database_id`
- At least some papers should exist in the database (otherwise, suggest `/start-my-day`)

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

### Step 2: Query Last 7 Days

Use `mcp__notion__notion-fetch` to query the paper database for papers where `Added Date` is within the last 7 days.

Fetch all properties: Title, Domain, Composite Score, Relevance Score, Social Score, Citation Count, GitHub Stars, Status, Conference, Source, ArXiv ID, Authors, Added Date.

If the user specifies a different time range (e.g., "last 2 weeks", "this month"), adjust accordingly.

### Step 3: Analyze & Group

Process the fetched papers:

1. **Group by domain**: Count papers per domain.
2. **Sort within groups**: By Composite Score descending.
3. **Identify top papers**: Top 5 overall by score.
4. **Reading progress**: Count by Status (Unread, Reading, Read, Noted).
5. **Source distribution**: Count by Source (arXiv, Semantic Scholar, DBLP).
6. **Score statistics**: Mean, median, max, min.

### Step 4: Generate Trends Analysis

Using Claude's understanding of the papers' titles, domains, and abstracts (if available from page content), generate:

- **3-5 trend bullet points**: What themes dominated this week?
- **Emerging topics**: Any new keywords or areas appearing?
- **Cross-domain connections**: Papers that bridge multiple domains.
- **Suggested reading order**: Based on score, domain priority, and reading status.

### Step 5: Create Digest Page

Use `mcp__notion__notion-create-pages` to create a standalone page with today's date as the title.

**Title**: `YYYY-MM-DD Weekly Research Digest`
**Icon**: chart emoji

**Content** (use `mcp__notion__notion-update-page` with `replace_content`):

```markdown
## Week of [start date] — [end date]

**N papers** added across **M domains** from **K sources**.

---

## Key Trends
- [Trend 1: describe what's hot this week]
- [Trend 2: emerging theme or shift]
- [Trend 3: cross-domain connection]
- [Trend 4: notable gap or opportunity]

## Top 5 Papers This Week

### 1. [Title] (Score: X.X/10, Domain: [domain])
[1-2 sentence summary — what makes this the top paper]
→ [Link to Notion page]

### 2. [Title] (Score: X.X/10, Domain: [domain])
[1-2 sentence summary]
→ [Link to Notion page]

### 3. [Title] (Score: X.X/10, Domain: [domain])
[1-2 sentence summary]
→ [Link to Notion page]

### 4. [Title] (Score: X.X/10, Domain: [domain])
[Summary]
→ [Link to Notion page]

### 5. [Title] (Score: X.X/10, Domain: [domain])
[Summary]
→ [Link to Notion page]

## By Domain

### [Domain 1] (N papers)
| Score | Title | Status | Source |
|-------|-------|--------|--------|
| 8.1 | [Title] | Unread | arXiv |
| 7.5 | [Title] | Reading | S2 |

### [Domain 2] (N papers)
| Score | Title | Status | Source |
|-------|-------|--------|--------|
...

## Score Distribution
- **8.0+**: N papers
- **6.0–8.0**: N papers
- **4.0–6.0**: N papers
- **< 4.0**: N papers
- **Average**: X.X/10

## Reading Progress
| Status | Count | % |
|--------|-------|---|
| Unread | N | X% |
| Reading | N | X% |
| Read | N | X% |
| Noted | N | X% |

## Action Items
- [ ] [N unread high-score papers to prioritize — list top 3 by name]
- [ ] [Any papers assigned but not started]
- [ ] [Suggested: run `/conf-papers [conference]` if a relevant deadline is approaching]

## Sources
- arXiv: N papers
- Semantic Scholar: N papers
- DBLP: N papers
- Manual: N papers
```

### Step 6: Present Digest to User

Display a concise summary in the conversation:

```markdown
## Weekly Research Digest — [date range]

**N papers** this week across **M domains**.

### Highlights
- Top paper: [Title] (X.X/10)
- Most active domain: [Domain] (N papers)
- Reading progress: X% completed

### Key Trends
[3 bullet points from Step 4]

📊 Full Digest → [link to digest page]
📚 Paper Library → [link to database]

### Next Steps
- `/start-my-day` — fetch today's new papers
- `/paper-analyze [arxiv_id]` — deep-read a top paper
- `/paper-search [keyword]` — search your library
```

## Key Rules

- Always run `/setup-workspace` first if state file is missing
- If no papers found in the date range, report this and suggest running `/start-my-day`
- Default time range: 7 days. Allow user to customize.
- Place the digest page in the same parent as daily digest pages
- Don't duplicate digest pages — if a weekly digest for the same week already exists, offer to update it
- Trends analysis should be specific and actionable, not generic
- Sort papers by Composite Score within each domain section
- Include all papers in the domain breakdown, not just the top ones
- The reading progress section should motivate — highlight what's been accomplished
