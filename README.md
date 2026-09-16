# Codex Subagents - Claude Code Plugin

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Stars](https://img.shields.io/github/stars/mgoulart/codex-subagents?style=social)](https://github.com/mgoulart/codex-subagents)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/mgoulart/codex-subagents/pulls)

Break complex tasks into parallel Codex agents, run them in batches, and merge the results — all from a single Claude Code slash command.

## Install

**Prerequisites:** Python 3, [uv](https://docs.astral.sh/uv/), [Codex CLI](https://github.com/openai/codex), Claude Code CLI

```bash
git clone https://github.com/mgoulart/codex-subagents.git
cd codex-subagents
./install.sh
```

The script auto-detects and installs missing dependencies, registers the MCP server, and copies the command. Restart Claude Code when done.

**Manual install:**
```bash
claude mcp add --scope user codex-subagent --transport stdio -- uvx codex-as-mcp@latest
mkdir -p ~/.claude/commands
cp commands/codex-subagents.md ~/.claude/commands/
```

## Usage

```
/codex-subagents <task description>
```

The orchestrator analyzes your task, splits it into independent units (max 3 agents per batch), runs them in parallel, and merges the results. Tasks needing more than 3 agents run in chained batches automatically.

**Examples:**
```
/codex-subagents Add user authentication with login, registration, and password reset
/codex-subagents Migrate all class components to React hooks
/codex-subagents Add unit tests to the payment module
/codex-subagents using o3, refactor the auth module
/codex-subagents use gpt-4o for all agents — add error handling to the API layer
/codex-subagents agent 1 uses o3 for the DB schema, agent 2 uses gpt-4o for the API
```

## Per-Agent Model and Reasoning Effort

Each agent can use a different model and reasoning effort by adding `"model"` and
`"effort"` keys to its spec:

```javascript
mcp__codex-subagent__spawn_agents_parallel({
  agents: [
    { prompt: "Write the database schema", model: "o3" },
    { prompt: "Audit the parser for bugs",  effort: "high" },
    { prompt: "Write the UI components" }, // model from ~/.codex/config.toml
  ]
})
```

`effort` is one of `minimal`, `low`, `medium`, `high`, `xhigh`. An unrecognised
value is rejected with the list of accepted ones rather than silently ignored.

**Set it explicitly if you care about it.** `codex exec` — which is what this
plugin shells out to — does *not* read `model_reasoning_effort` from
`~/.codex/config.toml`; only the interactive `codex-tui` does. So agents run at
the CLI default no matter what that file says, and nothing surfaces that to the
caller. `model` is not affected: it has always been read from the config file.

To change the default model for all agents:
```bash
# Edit ~/.codex/config.toml
model = "o3"   # applies to agents; model_reasoning_effort does not
```

## Logs

Agent activity is logged to `.codex-temp/[timestamp]/` in your project. Add it to `.gitignore` (the plugin does this automatically on first run).

## How It Works

1. Analyzes task scope and dependencies
2. Splits into atomic, independent units (max 3 per batch)
3. Runs each batch in parallel via `mcp__codex-subagent__spawn_agents_parallel`
4. Chains batches if more than 3 agents are needed
5. Detects conflicts and merges results
6. Runs quality validation (lint, type-check, tests)
7. Reports results with log paths

## Task Decomposition Strategies

| Strategy | When to use | Example |
|----------|-------------|---------|
| **File-based** | Independent files | One agent per component |
| **Feature-based** | Full features | Auth, profile, settings each get an agent |
| **Layer-based** | Architectural layers | DB → API → UI → Tests |

## Patched server.py

`codex-as-mcp-patched/` contains a fixed version of the upstream MCP server with:

- `stdin=DEVNULL` — fixes indefinite hang (critical)
- No prompt quoting — correct `create_subprocess_exec` arg passing
- `os.path.realpath` — macOS `/tmp` symlink compatibility
- Per-agent `model` support — passes `--model` to `codex exec`
- Per-agent `effort` support — passes `-c model_reasoning_effort=<value>`, which
  `codex exec` does not otherwise pick up from `~/.codex/config.toml`

## Bugs Fixed from Original

- **stdin hang** — child `codex exec` inherited the MCP server's stdio pipe and blocked indefinitely waiting for input
- **Wrong MCP config file** — original wrote to `~/.claude/mcp_settings.json` which Claude Code ignores; fixed to use `claude mcp add`
- **Symlink install failure** — `rm -f` on a directory fails silently; fixed to use `rm -rf`
- **Prompt quoting** — wrapping prompt in `"..."` passed literal quote chars to `execvp`; fixed to pass prompt directly

## Contributing

Issues and PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — original plugin by [CoderMageFox](https://github.com/CoderMageFox/claudecode-codex-subagents).
