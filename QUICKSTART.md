# Quick Start / 快速上手

Get up and running in 5 minutes. | 5 分钟快速上手。

---

## Step 1: Install Prerequisites / 安装前提

### Claude Code

```bash
# Requires Node.js 18+ | 需要 Node.js 18+
npm install -g @anthropic-ai/claude-code

# First run will guide you through login | 首次运行会引导登录
claude
```

### Notion MCP Server

```bash
# One-line setup (recommended) | 一键配置（推荐）
claude mcp add notion --transport http --url https://mcp.notion.com/mcp
```

Or manually add to `~/.claude/settings.json`:
```json
{
  "mcpServers": {
    "notion": {
      "type": "http",
      "url": "https://mcp.notion.com/mcp"
    }
  }
}
```

> On first use, Claude Code will open a Notion OAuth page. Grant access and you're set.
>
> 首次使用时会弹出 Notion OAuth 授权页面，授权后即可使用。

### Python 3.9+

```bash
pip install -r requirements.txt
```

---

## Step 2: Clone & Configure / 克隆并配置

```bash
git clone https://github.com/your-username/notion-research-flow.git
cd notion-research-flow
pip install -r requirements.txt

# Create your personal config | 创建个人配置
cp config.example.yaml config.yaml
```

Edit `config.yaml` — the most important section is your research interests:

```yaml
interests:
  domains:
    - name: "Your Research Area"
      priority: 8          # 1-10, higher = more important
      keywords:
        - "keyword1"
        - "keyword2"
      arxiv_categories:
        - "cs.AI"
        - "cs.LG"
```

---

## Step 3: Install Skills / 安装技能

```bash
# Option A: Symlink (recommended — auto-syncs updates)
# 方式 A: 软链接（推荐，自动同步更新）
ln -s $(pwd)/skills/* ~/.claude/skills/

# Option B: Copy
# 方式 B: 复制
cp -r skills/* ~/.claude/skills/
```

---

## Step 4: Use! / 开始使用

Open Claude Code and run:

```
/setup-workspace
```

This creates your Notion paper database with 8 views. You only need to run this once.

Then, every day:

```
/start-my-day
```

This fetches recent papers from arXiv, scores them against your interests, and pushes them to your Notion database.

---

## Daily Workflow / 每日工作流

```
Morning:
  /start-my-day                    # Fetch today's papers | 获取今日论文

When you find an interesting paper:
  /paper-analyze 2301.07041        # Deep analysis | 深度分析

End of week:
  /weekly-digest                   # Weekly summary | 每周摘要

Team reading group:
  /team-sync assign "Paper X" to "Alice"   # Assign papers | 分配论文
```

---

## Using an Existing Notion Database / 使用已有数据库

If you already have a paper database in Notion and want to use it instead of creating a new one:

1. Find your database ID (it's in the Notion URL: `notion.so/[DATABASE_ID]?v=...`)
2. Create `.notion-research-flow.json`:

```json
{
  "paper_database_id": "your-database-id-here",
  "setup_complete": true
}
```

3. Skip `/setup-workspace` and go directly to `/start-my-day`.

> Note: Your existing database should have at least a "Title" property. Other properties will be added as needed.

---

## Troubleshooting / 常见问题

### "No config.yaml found"
```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your interests
```

### "Workspace not set up"
```bash
# Run in Claude Code:
/setup-workspace
```

### "Notion authorization failed"
```bash
# Re-add the MCP server
claude mcp remove notion
claude mcp add notion --transport http --url https://mcp.notion.com/mcp
# Then try again — the OAuth page should open
```

### "arXiv API unreachable"
The arXiv API occasionally has downtime. Wait a few minutes and try again, or check https://status.arxiv.org.

---

## What's Next / 下一步

- Customize `config.yaml` with more research domains
- Adjust scoring weights to match your priorities
- Explore the [full documentation](README.md) for advanced features
