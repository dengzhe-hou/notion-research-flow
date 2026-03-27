---
name: paper-graph
description: Visualize citation relationships for a paper as a Connected Papers-style graph. Use when user says "paper graph", "citation graph", "connected papers", "show relationships", "paper connections", "引用图谱", or wants to see how a paper relates to other work.
---

# Paper Graph — Citation Relationship Visualization

Build and display a Connected Papers-style citation graph for any paper using Semantic Scholar data.

## Prerequisites

- Internet access for Semantic Scholar API
- Workspace setup is optional (graph works standalone)

## Workflow

### Step 1: Resolve Paper Identifier

The user provides one of:
- arXiv ID (e.g., `2301.07041`)
- Paper title (e.g., "Attention Is All You Need")
- DOI or Semantic Scholar ID

If the user provides a vague description, search for the paper first.

### Step 2: Build Citation Graph

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

Run the citation graph builder:

```bash
cd "$REPO_ROOT"
python3 skills/paper-graph/scripts/build_citation_graph.py "$PAPER_ID" --max-refs 10 --max-cites 10 --depth 1 --format json
```

Capture the JSON output.

If the user wants a deeper graph, use `--depth 2` (fetches 2nd-degree references for top-cited papers).

### Step 3: Generate Mermaid Diagram

Run with mermaid output:

```bash
cd "$REPO_ROOT"
python3 skills/paper-graph/scripts/build_citation_graph.py "$PAPER_ID" --max-refs 10 --max-cites 10 --depth 1 --format mermaid
```

### Step 4: Push Graph to Notion (Optional)

If workspace is set up and the paper exists in the Notion library, update the paper's page with the citation graph using `mcp__notion__notion-update-page`:

Append to the page content:

```markdown
## Citation Graph

### Legend
- 🔴 **Seed paper** (this paper)
- 🔵 **References** (papers this paper cites)
- 🟢 **Citations** (papers that cite this paper)

### Graph
\`\`\`mermaid
[MERMAID_DIAGRAM_HERE]
\`\`\`

### Key References (by citation count)
| # | Paper | Year | Citations |
|---|-------|------|-----------|
| 1 | [title] | [year] | [count] |
| 2 | [title] | [year] | [count] |
| ... | | | |

### Key Citing Papers
| # | Paper | Year | Citations |
|---|-------|------|-----------|
| 1 | [title] | [year] | [count] |
| 2 | [title] | [year] | [count] |
| ... | | | |
```

### Step 5: Present to User

Display the results:

```markdown
## Citation Graph — [Paper Title]

**[N] references** ← 🔴 **Seed Paper** → **[M] citations**

### Mermaid Diagram

\`\`\`mermaid
[MERMAID OUTPUT]
\`\`\`

### Top References (this paper cites)
| # | Paper | Year | Citations | ArXiv |
|---|-------|------|-----------|-------|
| 1 | ... | ... | ... | ... |

### Top Citing Papers (cite this paper)
| # | Paper | Year | Citations | ArXiv |
|---|-------|------|-----------|-------|
| 1 | ... | ... | ... | ... |

### Insights
- [1-2 sentences about the research lineage]
- [Key research clusters/themes in the graph]
- [Notable highly-cited connections]

### Next Steps
- `/paper-analyze [arxiv_id]` — deep-read any connected paper
- `/paper-graph [arxiv_id] --depth 2` — expand the graph
- `/start-my-day` — discover new papers in related areas
```

## Key Rules

- Respect Semantic Scholar rate limits: 1s delay between API calls
- Default to depth 1 (seed + direct references/citations). Only use depth 2 if explicitly requested.
- Cap at 10 references + 10 citations by default to keep the graph readable
- If a paper is not found, suggest alternative identifiers (try title search)
- Mermaid node colors: red=seed, blue=references, green=citations
- Sort reference/citation tables by citation count descending
- If the paper exists in the Notion library, offer to update its page with the graph
