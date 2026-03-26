---
name: team-sync
description: Team paper collaboration — assign papers, view assignments, track reading progress. Use when user says "assign paper", "team sync", "who's reading", "team assignments", "team status", or wants to manage team paper reading.
---

# Team Sync — Paper Assignment & Progress Tracking

Manage team paper reading assignments, view progress, and track who's reading what.

## Prerequisites

- Workspace must be set up first (`/setup-workspace`)
- `.notion-research-flow.json` must contain `paper_database_id`
- `team.enabled: true` in `config.yaml`

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

Check that `team.enabled` is `true` in config. If not, inform the user:
"Team features are disabled. Set `team.enabled: true` in config.yaml to enable."

### Step 2: Discover Team Members

Use `mcp__notion__notion-get-users` to list workspace members.

Cache the user list for the current session (no need to re-fetch for each sub-command).

### Step 3: Parse Command

Detect which sub-command the user wants:

#### Sub-command: `assign [paper] to [person]`

1. **Find the paper**: Search Notion database using `mcp__notion__notion-search` for the paper by title or arXiv ID.
   - If multiple matches, show them and ask the user to choose.
   - If no match, suggest running `/paper-search` first.

2. **Find the person**: Match against the workspace members list.
   - Support partial name matching (e.g., "Alice" matches "Alice Wang").
   - If ambiguous, show candidates and ask.

3. **Assign**: Use `mcp__notion__notion-update-page` to set the `Assigned To` property to the matched person.

4. **Confirm**:
   ```markdown
   Assigned "[Paper Title]" to **[Person Name]**.
   → [Link to paper page]
   ```

#### Sub-command: `status`

1. Query the database for all papers where `Assigned To` is not empty using `mcp__notion__notion-fetch`.

2. Group by person and display:

   ```markdown
   ## Team Reading Status

   ### [Person 1] (N papers)
   | Status | Score | Title |
   |--------|-------|-------|
   | Reading | 8.1/10 | [Paper with link] |
   | Unread | 7.5/10 | [Paper with link] |

   ### [Person 2] (N papers)
   | Status | Score | Title |
   |--------|-------|-------|
   | Read | 7.8/10 | [Paper with link] |
   ...
   ```

#### Sub-command: `unassigned`

1. Query the database for papers where `Assigned To` is empty, sorted by Composite Score descending.

2. Display top papers waiting for assignment:

   ```markdown
   ## Unassigned Papers (top 20 by score)

   | # | Score | Title | Domain | Added |
   |---|-------|-------|--------|-------|
   | 1 | 8.5/10 | [Title] | LLM | 2025-03-27 |
   ...

   Use `/team-sync assign "[title]" to [person]` to assign.
   ```

#### Sub-command: `progress`

1. Query all assigned papers.

2. Compute per-person statistics:

   ```markdown
   ## Team Reading Progress

   | Person | Total | Unread | Reading | Read | Noted | Completion |
   |--------|-------|--------|---------|------|-------|------------|
   | Alice | 8 | 2 | 3 | 2 | 1 | 37.5% |
   | Bob | 5 | 1 | 1 | 3 | 0 | 60.0% |
   | **Team** | **13** | **3** | **4** | **5** | **1** | **46.2%** |

   ### This Week's Activity
   - Papers assigned: N
   - Papers completed (→ Read/Noted): N
   - Most active reader: [Person] (N papers read)
   ```

### Step 4: Handle Edge Cases

If the user's message doesn't match any sub-command, show the help menu:

```markdown
## Team Sync — Commands

- `/team-sync assign "[paper title]" to [person]` — assign a paper
- `/team-sync status` — view all assignments by person
- `/team-sync unassigned` — see papers waiting for assignment
- `/team-sync progress` — team reading statistics

**Team members in workspace**: [list names]
```

## Key Rules

- Only works when `team.enabled: true` in config — check this first
- Never remove existing assignments unless explicitly asked ("unassign" or "remove assignment")
- When assigning, confirm the paper and person before making changes
- Show Notion page links for all papers so users can click through
- If the workspace has only one user, note that team features are more useful with multiple members
- Default sort: Composite Score descending for unassigned, Status for assigned
- The `Assigned To` property is a PEOPLE type — use the person's Notion user ID
