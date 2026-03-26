---
name: setup-workspace
description: One-click Notion workspace initialization for paper research. Creates a paper database with 8 preconfigured views. Use when user says "setup notion", "init workspace", "create paper database", or runs this for the first time.
---

# Setup Notion Research Workspace

Initialize a complete paper research workspace in Notion with one command.

## Safety Guarantee

This skill **only creates new content** in Notion. It will **never modify, overwrite, or delete** any existing pages, databases, or content. All new items are created under a dedicated parent page.

## Workflow

### Step 1: Load Configuration

Read the config file to get domain options and conference options:

```bash
cd "$(python3 -c "
from pathlib import Path
p = Path.cwd()
for d in [p] + list(p.parents):
    if (d / 'config.example.yaml').exists():
        print(d); break
")"
python3 scripts/config_loader.py
```

If `config.yaml` doesn't exist, tell the user to create it first:
```
cp config.example.yaml config.yaml
# Edit config.yaml with your research interests
```

### Step 2: Check for Existing Setup

Check if `.notion-research-flow.json` already exists with a valid database ID:

```bash
cat .notion-research-flow.json 2>/dev/null || echo "{}"
```

If `setup_complete` is `true`, inform the user:
> "Workspace already set up. Database ID: {paper_database_id}. To re-create, delete .notion-research-flow.json and run again."

Also search Notion for an existing "Research Paper Library" database:

Use `mcp__notion__notion-search` with query "Research Paper Library" to check for duplicates.

If found, ask the user:
1. **Reuse existing** — link to the found database (update `.notion-research-flow.json`)
2. **Create new** — create a fresh database alongside it
3. **Cancel** — abort setup

### Step 3: Create Paper Database

Use `mcp__notion__notion-create-database` to create the database.

**Database title**: "Research Paper Library"

**SQL DDL** (generate from config using `scripts/notion_helpers.py`):

```bash
python3 -c "
import yaml
import sys
sys.path.insert(0, '.')
from scripts.notion_helpers import generate_database_ddl
with open('config.yaml') as f:
    config = yaml.safe_load(f)
print(generate_database_ddl(config))
"
```

Use the output DDL with `mcp__notion__notion-create-database`.

**Important**: Note the returned `database_id` and `data_source_id` from the creation response.

### Step 4: Customize Status Options

Use `mcp__notion__notion-update-data-source` to customize the Status property options to:
- Not started → **Unread**
- In progress → **Reading**
- Done → **Read**

Also add custom status groups if the API supports it:
- Noted
- Discussed

### Step 5: Create 8 Preconfigured Views

Create each view using `mcp__notion__notion-create-view` on the database's data_source_id.

**View 1: All Papers** (table)
- Sort by "Added Date" descending
- Show columns: Title, Domain, Composite Score, Status, Conference, Added Date

**View 2: By Score** (table)
- Sort by "Composite Score" descending
- Show columns: Title, Domain, Composite Score, Relevance Score, Social Score, Citation Count

**View 3: By Domain** (board)
- Group by "Domain"
- Sort by "Composite Score" descending

**View 4: Reading Status** (board)
- Group by "Status"
- Sort by "Composite Score" descending

**View 5: Conference Tracker** (table)
- Filter: Conference is not empty
- Sort by "Year" descending
- Show columns: Title, Conference, Year, Composite Score, Authors

**View 6: Timeline** (calendar)
- Calendar by "Added Date"

**View 7: Trending** (table)
- Filter: Social Score > 0
- Sort by "Social Score" descending
- Show columns: Title, Social Score, GitHub Stars, Twitter Mentions, Citation Count

**View 8: Team Assignments** (board)
- Group by "Assigned To"
- Sort by "Status" ascending

### Step 6: Save State

Save the database ID and metadata to `.notion-research-flow.json`:

```python
import json
state = {
    "paper_database_id": "<database_id from Step 3>",
    "paper_data_source_id": "<data_source_id from Step 3>",
    "setup_complete": True,
    "setup_date": "<current ISO datetime>",
    "views_created": 8
}
with open(".notion-research-flow.json", "w") as f:
    json.dump(state, f, indent=2)
```

### Step 7: Report Success

Display a summary:

```
Workspace setup complete!

Database: Research Paper Library
Views created: 8
  - All Papers (table)
  - By Score (table)
  - By Domain (board)
  - Reading Status (board)
  - Conference Tracker (table)
  - Timeline (calendar)
  - Trending (table)
  - Team Assignments (board)

Next steps:
  /start-my-day    — fetch today's recommended papers
```

## Key Rules

- NEVER modify or delete existing Notion content
- Always check for existing setup before creating
- Save state to `.notion-research-flow.json` after successful setup
- If any step fails, report the error clearly and suggest manual fixes
- The database DDL must match config.yaml domain and conference options
