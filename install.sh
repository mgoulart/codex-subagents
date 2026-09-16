#!/bin/bash

# Codex Subagents Plugin - One-Click Install Script
# Automatically installs the Plugin and MCP server

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Codex Subagents Plugin - One-Click Install${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check dependencies and record missing ones
MISSING_DEPS=()

check_dependency() {
    if ! command -v $1 &> /dev/null; then
        MISSING_DEPS+=("$1")
        echo -e "${RED}✗ Not found: $1${NC}"
        return 1
    else
        echo -e "${GREEN}✓ Installed: $1${NC}"
        return 0
    fi
}

echo -e "${YELLOW}[1/6] Checking dependencies...${NC}"
check_dependency "python3"
check_dependency "uv"
check_dependency "uvx"
check_dependency "codex"
echo ""

# If there are missing dependencies, provide installation guidance
if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}  Missing dependencies found${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    for dep in "${MISSING_DEPS[@]}"; do
        case $dep in
            python3)
                echo -e "${YELLOW}📦 Python 3${NC}"
                echo -e "   Will auto-detect installed Python 3 versions"
                echo -e "   If not found, install with Homebrew:"
                echo -e "   ${GREEN}brew install python3${NC}"
                echo ""
                ;;
            uv|uvx)
                echo -e "${YELLOW}📦 uv (Python package manager)${NC}"
                echo -e "   Will auto-install uv"
                echo ""
                ;;
            codex)
                echo -e "${YELLOW}📦 Codex CLI${NC}"
                echo -e "   Will auto-install Codex CLI"
                echo -e "   Requires npm (Node.js package manager)"
                echo ""
                ;;
        esac
    done

    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Auto-install missing dependencies? (y/n)${NC}"
    read -r response

    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BLUE}  Starting automatic dependency installation${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""

        INSTALL_SUCCESS=true
        NEED_CODEX_LOGIN=false

        for dep in "${MISSING_DEPS[@]}"; do
            case $dep in
                python3)
                    echo -e "${YELLOW}[Python 3] Detecting...${NC}"
                    # Try to find Python 3
                    if command -v python3.11 &> /dev/null; then
                        echo -e "${GREEN}✓ Found Python 3.11${NC}"
                        ln -sf $(which python3.11) /usr/local/bin/python3 2>/dev/null || true
                    elif command -v python3.10 &> /dev/null; then
                        echo -e "${GREEN}✓ Found Python 3.10${NC}"
                        ln -sf $(which python3.10) /usr/local/bin/python3 2>/dev/null || true
                    elif command -v python3.9 &> /dev/null; then
                        echo -e "${GREEN}✓ Found Python 3.9${NC}"
                        ln -sf $(which python3.9) /usr/local/bin/python3 2>/dev/null || true
                    else
                        echo -e "${RED}✗ No Python 3 version found${NC}"
                        echo -e "${YELLOW}Please install with Homebrew:${NC}"
                        echo -e "${GREEN}brew install python3${NC}"
                        INSTALL_SUCCESS=false
                    fi
                    echo ""
                    ;;
                uvx)
                    echo -e "${YELLOW}[uv] Installing...${NC}"
                    if curl -LsSf https://astral.sh/uv/install.sh | sh; then
                        # Reload environment variables
                        export PATH="$HOME/.local/bin:$PATH"

                        # Verify installation
                        if command -v uvx &> /dev/null; then
                            UVX_VERSION=$(uvx --version 2>&1 | head -1)
                            echo -e "${GREEN}✓ uv installed successfully: $UVX_VERSION${NC}"
                        else
                            echo -e "${YELLOW}⚠ uv installed but not in PATH${NC}"
                            echo -e "${YELLOW}Please run: ${GREEN}source ~/.bashrc${NC} or ${GREEN}source ~/.zshrc${NC}"
                            echo -e "${YELLOW}Then re-run this script${NC}"
                            INSTALL_SUCCESS=false
                        fi
                    else
                        echo -e "${RED}✗ uv installation failed${NC}"
                        INSTALL_SUCCESS=false
                    fi
                    echo ""
                    ;;
                codex)
                    echo -e "${YELLOW}[Codex CLI] Installing...${NC}"

                    # Check for npm
                    if ! command -v npm &> /dev/null; then
                        echo -e "${RED}✗ npm not found${NC}"
                        echo -e "${YELLOW}Please install Node.js first:${NC}"
                        echo -e "${GREEN}brew install node${NC}"
                        INSTALL_SUCCESS=false
                    else
                        if npm install -g @openai/codex@latest; then
                            if command -v codex &> /dev/null; then
                                CODEX_VERSION=$(codex --version 2>&1 | head -1)
                                echo -e "${GREEN}✓ Codex CLI installed successfully: $CODEX_VERSION${NC}"
                                NEED_CODEX_LOGIN=true
                            else
                                echo -e "${RED}✗ Codex CLI installation failed${NC}"
                                INSTALL_SUCCESS=false
                            fi
                        else
                            echo -e "${RED}✗ Codex CLI installation failed${NC}"
                            INSTALL_SUCCESS=false
                        fi
                    fi
                    echo ""
                    ;;
            esac
        done

        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

        if [ "$INSTALL_SUCCESS" = true ]; then
            echo -e "${GREEN}✅ All dependencies installed successfully!${NC}"
            echo ""

            if [ "$NEED_CODEX_LOGIN" = true ]; then
                echo -e "${YELLOW}⚠️  Important: Please log in to Codex CLI first:${NC}"
                echo -e "${GREEN}codex login${NC}"
                echo ""
                echo -e "${YELLOW}After logging in, this script will continue installing...${NC}"
                echo ""
                read -p "Press Enter to continue..."
            fi

            echo -e "${BLUE}Continuing Plugin installation...${NC}"
            echo ""
        else
            echo -e "${RED}❌ Some dependencies failed to install${NC}"
            echo -e "${YELLOW}Please manually install the failed dependencies using the instructions above, then re-run this script${NC}"
            exit 1
        fi
    else
        echo ""
        echo -e "${RED}Installation cancelled${NC}"
        echo -e "${YELLOW}Please manually install the dependencies listed above, then re-run this script${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ All dependency checks passed${NC}"
    echo ""
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
PLUGINS_DIR="$CLAUDE_DIR/plugins"

# Create required directories
echo -e "${YELLOW}[2/6] Creating directory structure...${NC}"
mkdir -p "$PLUGINS_DIR"
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Install Plugin (symlink)
echo -e "${YELLOW}[3/6] Installing Plugin...${NC}"
if [ -L "$PLUGINS_DIR/codex-subagents" ] || [ -d "$PLUGINS_DIR/codex-subagents" ]; then
    echo -e "${YELLOW}  Existing installation found, removing old version...${NC}"
    rm -rf "$PLUGINS_DIR/codex-subagents"
fi
ln -s "$SCRIPT_DIR" "$PLUGINS_DIR/codex-subagents"
echo -e "${GREEN}✓ Plugin installed to: $PLUGINS_DIR/codex-subagents${NC}"
echo ""

# Copy commands to global commands directory
echo -e "${YELLOW}[3.5/6] Installing commands to global directory...${NC}"
COMMANDS_DIR="$CLAUDE_DIR/commands"
mkdir -p "$COMMANDS_DIR"

# Copy command files
cp "$SCRIPT_DIR/commands/codex-subagents.md" "$COMMANDS_DIR/"
echo -e "${GREEN}✓ Commands copied to: $COMMANDS_DIR${NC}"
echo ""

# Configure MCP server using claude mcp add
# NOTE: Claude Code reads MCP config from ~/.claude.json via 'claude mcp add',
# NOT from ~/.claude/mcp_settings.json. Using the CLI ensures correct registration.
echo -e "${YELLOW}[4/6] Configuring MCP server...${NC}"
# Register the PATCHED server shipped in this repo, not upstream codex-as-mcp.
# This previously pointed at `uvx codex-as-mcp@latest`, which meant none of the
# fixes in codex-as-mcp-patched/ were ever active: agents ran without the
# sandbox bypass and with no way to set reasoning effort, silently inheriting
# the Codex CLI default. The symlink above puts this repo at a stable path, so
# SCRIPT_DIR is safe to bake into the registration.
UV_PATH="$(which uv 2>/dev/null || echo "$HOME/.local/bin/uv")"
PATCHED_SERVER="$SCRIPT_DIR/codex-as-mcp-patched/server.py"
if [ ! -f "$PATCHED_SERVER" ]; then
    echo -e "${RED}✗ Patched server not found at $PATCHED_SERVER${NC}"
    exit 1
fi
# Re-running the installer must not fail on an existing registration.
claude mcp remove --scope user codex-subagent >/dev/null 2>&1 || true
claude mcp add --scope user codex-subagent --transport stdio -- \
    "$UV_PATH" run --quiet --with "mcp<2" python "$PATCHED_SERVER"
echo -e "${GREEN}✓ MCP server configured${NC}"
echo ""

# Note: The orchestrator creates .codex-temp/ logs in your project directory.
# Add this to your project's .gitignore to avoid committing temporary files:
#   .codex-temp/
# The plugin commands (codex-subagents.md / codex-subagents-en.md) automatically
# add .codex-temp/ to .gitignore when you first run them.

# Verify installation
echo -e "${YELLOW}[5/6] Verifying installation...${NC}"

# Check Plugin structure
if [ -f "$PLUGINS_DIR/codex-subagents/.claude-plugin/plugin.json" ]; then
    echo -e "${GREEN}✓ Plugin structure valid${NC}"
else
    echo -e "${RED}✗ Plugin structure invalid${NC}"
    exit 1
fi

# Check command files
if [ -f "$PLUGINS_DIR/codex-subagents/commands/codex-subagents.md" ]; then
    echo -e "${GREEN}✓ Command files present${NC}"
else
    echo -e "${RED}✗ Command files missing${NC}"
    exit 1
fi

# Check MCP configuration
if claude mcp list | grep -q "codex-subagent"; then
    echo -e "${GREEN}✓ MCP server registered${NC}"
else
    echo -e "${RED}✗ MCP configuration error${NC}"
    exit 1
fi

# Registered is not the same as registered to the right thing -- the bug this
# replaced was a working registration that pointed at the wrong server.
if claude mcp list | grep -q "codex-as-mcp-patched"; then
    echo -e "${GREEN}✓ Using the patched server${NC}"
else
    echo -e "${RED}✗ Registered server is not the patched one${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Installation complete!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}📦 Installation locations:${NC}"
echo -e "   Plugin: $PLUGINS_DIR/codex-subagents"
echo -e "   MCP Config: registered via 'claude mcp add' (stored in ~/.claude.json)"
echo ""
echo -e "${YELLOW}🎯 Usage:${NC}"
echo -e "   ${GREEN}/codex-subagents${NC} <task description>"
echo ""
echo -e "${YELLOW}💡 Tips:${NC}"
echo -e "   - MCP server is the patched build in codex-as-mcp-patched/, run via uv"
echo -e "   - Python dependencies are fetched by uv on first use"
echo -e "   - Make sure Codex CLI is logged in: ${GREEN}codex login${NC}"
echo -e "   - Add .codex-temp/ to your project's .gitignore (plugin does this automatically)"
echo -e "   - Restart Claude Code to load the Plugin"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
