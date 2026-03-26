---
name: paper-analyze
description: Deep analysis of a specific paper — downloads PDF, extracts text, generates detailed summary with methodology breakdown. Use when user says "analyze paper", "deep read", "paper analyze", "read this paper", "tell me about [arxiv_id]", or wants to understand a paper in detail.
---

# Paper Analyze — Deep Paper Analysis

Download, extract, and generate a comprehensive analysis of a specific paper, then write the analysis to its Notion page.

## Prerequisites

- Workspace must be set up first (`/setup-workspace`)
- `.notion-research-flow.json` must contain `paper_database_id`
- PyMuPDF must be installed: `pip install PyMuPDF`

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

### Step 2: Resolve Paper

The user provides one of:
- **arXiv ID** (e.g., `2301.07041`)
- **Paper title** (partial or full)
- **Notion page link** (direct link to a paper in the database)

**If arXiv ID is provided**: Search Notion database for an existing entry with this ArXiv ID using `mcp__notion__notion-search`. If found, use that page. If not found, create a new entry first (search arXiv for metadata).

**If title is provided**: Search Notion database for a matching title. If multiple matches, show them and ask the user to choose.

**If Notion link is provided**: Fetch the page directly.

Record the Notion page ID and arXiv ID for later steps.

### Step 3: Download & Extract PDF

Run the PDF extraction script:

```bash
cd "$REPO_ROOT"
python3 skills/paper-analyze/scripts/extract_pdf.py --arxiv-id "$ARXIV_ID"
```

This outputs a JSON dict with: `full_text`, `page_count`, `sections`.

If the paper has no arXiv ID (e.g., from DBLP), try the `pdf_url` from the Notion page:

```bash
python3 skills/paper-analyze/scripts/extract_pdf.py --url "$PDF_URL"
```

If PDF download fails, fall back to analyzing the abstract only and note the limitation.

### Step 4: Generate Deep Analysis

Read the extracted text (or abstract if PDF unavailable) and generate a comprehensive analysis.

Load the user's research interests from `config.yaml` to personalize the "Relevance" section.

Structure the analysis as follows:

```markdown
## Deep Analysis

### TL;DR
[2-3 sentence executive summary — what was done, how, and the main result]

### Problem Statement
[What problem does this paper address? Why is it important?]

### Methodology
1. **[Step/Component 1]**: [description]
2. **[Step/Component 2]**: [description]
3. **[Step/Component 3]**: [description]
[Include key equations or algorithms if present]

### Key Contributions
- [Contribution 1 — the main novelty]
- [Contribution 2 — technical advance]
- [Contribution 3 — practical impact]

### Experimental Results
| Benchmark | Metric | Result | vs. SOTA |
|-----------|--------|--------|----------|
| [dataset] | [metric] | [value] | [comparison] |

### Strengths
- [Strength 1]
- [Strength 2]

### Limitations & Open Questions
- [Limitation 1]
- [Limitation 2]
- [Open question for future work]

### Relevance to Your Research
[2-3 sentences connecting this paper to the user's research interests from config.yaml domains and keywords. Be specific about which domain it relates to and how it could be applied or extended.]

### Key References
- [Most important cited paper 1] — [why it's important]
- [Most important cited paper 2] — [why it's important]

### Links
- [PDF](pdf_url) | [Abstract](source_url) | [Code](github_url if found)
```

### Step 5: Update Notion Page

Use `mcp__notion__notion-update-page` with `replace_content` to write the deep analysis as the page content.

This replaces any existing content (like the shorter TL;DR from `/start-my-day`) with the full analysis.

### Step 6: Update Status

If the paper's Status is currently "Not started" (Unread), update it to "In progress" (Reading) using `mcp__notion__notion-update-page`.

### Step 7: Present Analysis

Display the full analysis in the conversation, along with:

```markdown
---
Analysis written to Notion → [link to paper page]

### Next Steps
- `/paper-search [related keyword]` — find related papers in your library
- `/paper-analyze [another_arxiv_id]` — analyze another paper
- `/team-sync assign "[title]" to [person]` — assign for discussion
```

## Key Rules

- Always run `/setup-workspace` first if state file is missing
- If PyMuPDF is not installed, provide installation instructions and offer abstract-only analysis
- If PDF download fails (403, timeout, etc.), fall back to abstract-only analysis gracefully
- Clean up downloaded PDF files after extraction (don't leave temp files)
- The analysis should be thorough but focused — aim for 400-800 words
- Personalize the "Relevance to Your Research" section using config.yaml domains
- When creating a new Notion entry for an untracked paper, set all available properties
- If the paper's `display.deep_analyze_top` limit is relevant (auto-analysis mode), respect it
- ALWAYS write the analysis to Notion — the conversation display is supplementary
