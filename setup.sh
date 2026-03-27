#!/bin/bash
# notion-research-flow setup script
# Installs dependencies, configures Notion MCP, and prepares skills for Claude Code.

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}=== notion-research-flow setup ===${NC}"
echo ""

# 1. Check Python
echo -e "${CYAN}[1/4] Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 not found. Please install Python 3.9+.${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "  Found Python ${PYTHON_VERSION}"

# 2. Install dependencies
echo -e "${CYAN}[2/4] Installing Python dependencies...${NC}"
pip install -r requirements.txt -q
echo -e "  ${GREEN}Done${NC}"

# 3. Config file
echo -e "${CYAN}[3/4] Checking config...${NC}"
if [ ! -f config.yaml ]; then
    cp config.example.yaml config.yaml
    echo -e "  ${YELLOW}Created config.yaml from template. Edit it with your research interests.${NC}"
else
    echo -e "  config.yaml already exists"
fi

# 4. Notion MCP
echo -e "${CYAN}[4/4] Configuring Notion MCP...${NC}"
if command -v claude &> /dev/null; then
    # Check if notion MCP is already configured
    if claude mcp list 2>&1 | grep -q "notion.*Connected"; then
        echo -e "  ${GREEN}Notion MCP already connected${NC}"
    elif claude mcp list 2>&1 | grep -q "notion"; then
        echo -e "  ${YELLOW}Notion MCP configured but needs authentication.${NC}"
        echo -e "  ${YELLOW}Run 'claude' and use any Notion command to trigger OAuth.${NC}"
    else
        claude mcp add notion --transport http --url https://mcp.notion.com/mcp 2>/dev/null
        echo -e "  ${GREEN}Notion MCP added${NC}"
        echo -e "  ${YELLOW}First use will prompt for OAuth authorization in browser.${NC}"
    fi
else
    echo -e "  ${YELLOW}Claude Code not found. Install with: npm install -g @anthropic-ai/claude-code${NC}"
    echo -e "  ${YELLOW}Then run: claude mcp add notion --transport http --url https://mcp.notion.com/mcp${NC}"
fi

echo ""
echo -e "${GREEN}=== Setup complete ===${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit config.yaml with your research interests"
echo "  2. Run 'claude' in this directory"
echo "  3. Type /setup-workspace to create your Notion database"
echo "  4. Type /start-my-day to fetch today's papers"
echo ""
