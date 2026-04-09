# Codex Subagents - Claude Code Plugin

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Stars](https://img.shields.io/github/stars/mgoulart/codex-subagents?style=social)](https://github.com/mgoulart/codex-subagents)
[![GitHub Issues](https://img.shields.io/github/issues/mgoulart/codex-subagents)](https://github.com/mgoulart/codex-subagents/issues)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/mgoulart/codex-subagents/pulls)

A Claude Code plugin for orchestrating complex tasks by delegating to multiple parallel Codex agents, then merging and reviewing results.

**Forked from [CoderMageFox/claudecode-codex-subagents](https://github.com/CoderMageFox/claudecode-codex-subagents)** — this fork fixes critical bugs (stdin hang, incorrect MCP registration) and translates all content to English.

## Features

- **Parallel Processing**: Break complex tasks into parallelizable units (max 3 agents per batch)
- **Chain Processing**: Automatic chain batch processing when more than 3 tasks are needed
- **Real-time Progress**: Uses TodoWrite to display task execution progress in real-time
- **Detailed Logging**: All subagent activities logged to `.codex-temp/[timestamp]/` directory
- **Intelligent Delegation**: Automatically delegates to multiple Codex subagents via MCP server
- **Smart Merging**: Automatically detects conflicts and applies optimal merge strategies
- **Quality Validation**: Multiple validation gates including compilation, testing, and code quality checks

## Bugs Fixed in This Fork

### Critical Fix: stdin Hang

The original `codex-as-mcp` server did not pass `stdin=asyncio.subprocess.DEVNULL` when spawning child `codex exec` processes. This caused the child process to inherit the MCP server's stdin (Claude Code's stdio pipe), which caused it to block waiting for input and hang indefinitely.

**Fix:** `stdin=asyncio.subprocess.DEVNULL` is added to the `asyncio.create_subprocess_exec` call. See `codex-as-mcp-patched/server.py` for the full patched version.

### Fix: Incorrect MCP Registration

The original `install.sh` wrote MCP server config to `~/.claude/mcp_settings.json`. Claude Code does **not** read from that file — it reads MCP config from `~/.claude.json` via the `claude mcp add` command.

**Fix:** The install script now uses `claude mcp add --scope user codex-subagent --transport stdio -- uvx codex-as-mcp@latest`.

### Fix: Symlink Install May Fail if Directory Exists

The original install script only checked for `-L` (symlink) before removing the existing install entry, not for regular directories. Using `rm -f` on a directory would fail silently or error.

**Fix:** The check now handles both symlinks and directories, using `rm -rf` to cleanly remove either.

### Fix: Unnecessary Prompt Quoting

The original server wrapped the prompt in `"..."` before passing to `create_subprocess_exec`. Since `create_subprocess_exec` passes args directly to `execvp` (no shell), the literal quote characters were included in the prompt text.

**Fix:** The prompt is passed directly without additional quoting.

## Quick Installation

### Method 1: One-Click Install Script (Recommended)

```bash
git clone https://github.com/mgoulart/codex-subagents.git
cd codex-subagents
./install.sh
```

The installation script automatically:
- Detects and auto-installs missing dependencies (Python 3, uv, Codex CLI)
- Installs the Plugin to `~/.claude/plugins/`
- Copies commands to `~/.claude/commands/` for immediate availability
- Configures the MCP server using `claude mcp add` (correct method)
- Installs both English command variants
- Verifies installation integrity

### Method 2: Manual MCP Registration

If you prefer to configure manually, use the `claude mcp add` command:

```bash
claude mcp add --scope user codex-subagent --transport stdio -- uvx codex-as-mcp@latest
```

Then copy the command files:

```bash
mkdir -p ~/.claude/commands
cp commands/codex-subagents.md ~/.claude/commands/
```

> **Note:** Do NOT manually edit `~/.claude/mcp_settings.json` — Claude Code does not read that file. Always use `claude mcp add` or edit `~/.claude.json` directly.

**Prerequisites:**
- Python 3 (usually pre-installed on macOS, script will auto-detect)
- uv / uvx (script will prompt and auto-install)
- Codex CLI >= 0.46.0 (script will prompt and auto-install)
- Claude Code CLI

After installation, restart Claude Code to use.

## Usage

### Commands

```bash
/codex-subagents <task description>
```

### Examples

**Example 1: Create React Components**
```
/codex-subagents Create a user authentication system with login, registration, and password reset features
```

**Example 2: Refactor Code**
```
/codex-subagents Migrate all React class components to function components and Hooks
```

**Example 3: Add Features**
```
/codex-subagents Add comments, likes, and sharing features to the blog system
```

## How It Works

1. **Task Analysis** (30 seconds): Understand task scope and dependencies
2. **Task Decomposition** (1 minute): Break task into parallel units (max 3 per batch)
3. **Initialize Logging**: Create `.codex-temp/[timestamp]/` directory for logs
4. **Setup Progress Tracking**: Use TodoWrite to create a task list
5. **Chain Execution**:
   - If 3 or fewer agents: Execute directly in parallel
   - If more than 3 agents: Execute in batches of 3
6. **Real-time Progress Updates**: Update TodoWrite and report to user after each batch
7. **Detailed Logging**: Each agent's output recorded to individual log file
8. **Collect Results**: Parse each agent's output and detect conflicts
9. **Apply Merge Strategy**: Direct merge, sequential integration, or conflict resolution
10. **Quality Validation**: Run compilation, lint, type-check, and tests
11. **Generate Report**: Provide comprehensive execution report with log directory path

## Logging

Agent logs are stored in `.codex-temp/[timestamp]/`:

```
.codex-temp/
  └── 20251107_152300/
      ├── user-auth.log
      ├── user-profile.log
      ├── api-endpoints.log
      └── frontend-components.log
```

Add `.codex-temp/` to your project's `.gitignore` to avoid committing temporary files. The plugin commands do this automatically when first run.

## Task Decomposition Strategies

**File-Based**: Independent files, 1 agent per file group
```yaml
agent_1: [UserCard.tsx, UserCard.test.tsx]
agent_2: [ProductCard.tsx, ProductCard.test.tsx]
```

**Feature-Based**: Complete features, 1 agent per feature
```yaml
agent_1: User authentication (DB + API + UI + tests)
agent_2: User profile (DB + API + UI + tests)
```

**Layer-Based**: Architectural layers, 1 agent per layer
```yaml
agent_1: Database models + migrations
agent_2: API endpoints + business logic
agent_3: Frontend components + state
agent_4: Integration tests + E2E
```

## Patched server.py

See `codex-as-mcp-patched/` for a patched version of the MCP server with all critical fixes applied. Refer to the README in that directory for how to use it.

## Best Practices

**Do:**
- Break tasks into atomic, independent units
- Max 3 agents per batch (avoid MCP content overflow)
- Use TodoWrite to track all tasks and batches
- Check detailed logs in `.codex-temp/[timestamp]/`
- Provide clear context to agents

**Do Not:**
- Execute more than 3 agents in a single batch
- Create dependencies between parallel agents
- Skip validation steps
- Ignore test failures

## Contributing

Issues and Pull Requests are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT License

## Credits

Original plugin by [CoderMageFox](https://github.com/CoderMageFox/claudecode-codex-subagents).

This fork adds bug fixes and English translation.

## Links

- [Original Repository](https://github.com/CoderMageFox/claudecode-codex-subagents)
- [This Fork](https://github.com/mgoulart/codex-subagents)
- [Claude Code Documentation](https://docs.claude.com/claude-code)
- [Report Issues](https://github.com/mgoulart/codex-subagents/issues)
