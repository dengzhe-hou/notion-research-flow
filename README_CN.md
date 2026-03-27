# notion-research-flow

**Claude Code + Notion MCP 全流程论文研究助手 —— 从每日 arXiv 到团队论文库。**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skills-blueviolet)](https://docs.anthropic.com/en/docs/claude-code)
[![Notion MCP](https://img.shields.io/badge/Notion-MCP-black)](https://www.notion.com/)

> 首个将 Notion 变成全功能论文管理系统的 Claude Code 技能套件 —— 智能评分、多源聚合、团队协作。

[English](README.md) | [快速上手](QUICKSTART.md)

---

## 为什么选择 notion-research-flow？

| 特性 | evil-read-arxiv | n8n+Notion | ArxivDigest | **notion-research-flow** |
|------|----------------|------------|-------------|--------------------------|
| 存储 | Obsidian (文件) | Notion | Email/GitHub | **Notion** |
| 多维筛选 | 手动文件搜索 | 基础 | 无 | **8 种数据库视图** |
| 评分 | 4 维 | 无 | GPT 评分 | **5 维 (+社交信号)** |
| 社交信号 | 无 | 无 | 无 | **GitHub + Twitter** |
| 团队协作 | 无 | 无 | 无 | **分配/评论/看板** |
| 初始化 | 手动配置 | 手动 | 手动 | **一键 setup** |
| 会议追踪 | DBLP | 无 | 无 | **DBLP + 专属视图** |
| 每周摘要 | 无 | 无 | 无 | **自动生成** |

## 功能特性

### 初始化 & 每日发现
- `/setup-workspace` —— 一键创建 Notion 数据库 + 8 个预配置视图
- `/start-my-day` —— 每日 arXiv 论文发现 + 5D 评分 + 社交信号增强
- 自动去重（不重复入库）
- Top-N 论文由 Claude 自动生成 TL;DR

### 多源聚合 & 会议追踪
- `/conf-papers` —— 通过 Semantic Scholar + DBLP 追踪会议论文
- 5D 评分：相关性 + 新近度 + 流行度（引用量）+ 社交信号（GitHub stars、Twitter）+ 质量
- 会议名称自动标准化（全称 → 缩写）

### 深度分析 & 搜索
- `/paper-analyze` —— 深度论文分析 + PDF 文本提取（PyMuPDF）
- `/paper-search` —— 按关键词、领域、评分、状态、日期搜索 Notion 论文库

### 团队协作 & 报告
- `/team-sync` —— 分配论文、查看分配、追踪团队阅读进度
- `/weekly-digest` —— 自动生成每周摘要：趋势分析、Top 论文、领域分布

## 5D 评分引擎

| 维度 | 权重 | 计算方式 |
|------|------|----------|
| 相关性 | 35% | 关键词 + arXiv 分类匹配 |
| 新近度 | 15% | 指数衰减 exp(-0.1 * 天数) |
| 流行度 | 20% | 引用数 + 会议等级 |
| **社交信号** | **20%** | **GitHub stars + Twitter 热度（新增！）** |
| 质量 | 10% | 作者 h-index 代理 + 摘要质量 |

## Notion 数据库视图

你的论文库自带 8 个预配置视图：

| 视图 | 类型 | 用途 |
|------|------|------|
| All Papers | 表格 | 按日期浏览所有论文 |
| By Score | 表格 | 按综合评分排序 |
| By Domain | 看板 | 按研究领域分组 |
| Reading Status | 看板 | 阅读进度：未读/阅读中/已读/已笔记 |
| Conference Tracker | 表格 | 按会议和年份筛选 |
| Timeline | 日历 | 可视化论文时间线 |
| Trending | 表格 | 高社交信号论文 |
| Team Assignments | 看板 | 团队成员分配 |

## 前提条件

### 1. 安装 Claude Code

```bash
# 需要 Node.js 18+
npm install -g @anthropic-ai/claude-code
claude  # 首次运行会引导登录
```

### 2. 配置 Notion MCP Server

```bash
# 一键添加（推荐）
claude mcp add notion --transport http --url https://mcp.notion.com/mcp

# 或手动编辑 ~/.claude/settings.json
```

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

首次使用 Notion 工具时会自动弹出 OAuth 授权页面，授权后即可使用。

### 3. Python 3.9+

```bash
pip install -r requirements.txt
```

## 快速上手

```bash
# 1. 克隆并配置
git clone https://github.com/dengzhe-hou/notion-research-flow.git
cd notion-research-flow
pip install -r requirements.txt
cp config.example.yaml config.yaml
# 编辑 config.yaml，填入你的研究方向

# 2. 安装 skills 到 Claude Code（项目级）
mkdir -p .claude/skills
ln -s $(pwd)/skills/* .claude/skills/

# 3. 在 Claude Code 中使用
```

在 Claude Code 中：

```
/setup-workspace          # 创建 Notion 论文数据库（仅需一次）
/start-my-day             # 获取今日推荐论文
/paper-analyze 2301.07041 # 深度分析指定论文
/conf-papers NeurIPS 2025 # 追踪会议论文
/paper-search transformer # 搜索论文库
/weekly-digest            # 生成本周摘要
```

## 配置说明

复制 `config.example.yaml` 为 `config.yaml` 并自定义：

```yaml
interests:
  domains:
    - name: "大语言模型"
      priority: 8
      keywords: ["LLM", "in-context learning", "RLHF"]
      arxiv_categories: ["cs.CL", "cs.AI"]

scoring:
  relevance: 35   # 相关性
  recency: 15     # 新近度
  popularity: 20  # 流行度
  social: 20      # 社交信号
  quality: 10     # 质量
```

详见 [config.example.yaml](config.example.yaml)。

## 自动化每日运行

### 方式 1：手动（最简单）
每天在 Claude Code 中输入 `/start-my-day`。

### 方式 2：macOS 定时任务
```bash
# 添加到 crontab（每天早上 8 点运行）
crontab -e
0 8 * * * cd /path/to/notion-research-flow && claude --print "/start-my-day"
```

### 方式 3：Claude Code 循环
```
/loop 24h /start-my-day
```

## 常见问题

**Q: 会影响我 Notion 中已有的内容吗？**
A: 不会。`/setup-workspace` 只创建新的独立页面和数据库，不会修改或删除任何已有内容。

**Q: 可以用已有的 Notion 数据库吗？**
A: 可以。手动编辑 `.notion-research-flow.json`，填入你的数据库 ID，跳过 `/setup-workspace`。

**Q: 需要付费 API 吗？**
A: 不需要。arXiv、Semantic Scholar、DBLP 都是免费 API。社交信号使用免费的网页搜索获取。

**Q: 和 evil-read-arxiv 有什么区别？**
A: 我们使用 Notion（而非 Obsidian）作为后端，支持数据库视图、团队协作和更丰富的筛选体验。另外新增了社交信号评分（GitHub + Twitter）作为第 5 个评分维度。

## 项目结构

```
notion-research-flow/
├── config.example.yaml          # 配置模板（5D 评分、多源、团队）
├── scripts/                     # 共享工具
│   ├── config_loader.py         # 配置加载与验证
│   ├── notion_helpers.py        # Notion DDL、视图、格式化
│   └── fetch_social_signals.py  # GitHub stars + Twitter 信号增强
├── skills/
│   ├── setup-workspace/         # 一键 Notion 初始化
│   ├── start-my-day/            # 每日 arXiv 发现 + 5D 评分
│   │   └── scripts/             # search_arxiv.py + score_papers.py
│   ├── conf-papers/             # 会议论文追踪
│   │   └── scripts/             # search_semantic_scholar.py + search_dblp.py
│   ├── paper-analyze/           # 深度论文分析
│   │   └── scripts/             # extract_pdf.py（PyMuPDF）
│   ├── paper-search/            # Notion 论文库搜索
│   ├── team-sync/               # 团队分配与进度
│   └── weekly-digest/           # 每周研究摘要
└── tests/                       # 58 个单元测试（评分、搜索、提取）
```

## 贡献

欢迎贡献！请提交 Issue 或 Pull Request。

## 致谢

受 [evil-read-arxiv](https://github.com/Mengyanz/evil-read-arxiv) 和 [ArxivDigest](https://github.com/AutoLLM/ArxivDigest) 启发，它们是自动化 arXiv 论文评分与发现工作流的先驱。

## 许可证

[MIT](LICENSE)
