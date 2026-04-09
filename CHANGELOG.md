# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.0.0] - 2026-04-09 (mgoulart fork)

### Fixed
- Critical: add `stdin=asyncio.subprocess.DEVNULL` to prevent codex subprocess from
  inheriting the MCP server's stdio pipe and blocking indefinitely (stdin hang bug)
- Fix incorrect prompt quoting in subprocess exec call — `create_subprocess_exec`
  passes args directly to execvp, so literal quote chars were included in the prompt
- Fix MCP registration: use `claude mcp add` instead of writing to `mcp_settings.json`
  (Claude Code does not read from `~/.claude/mcp_settings.json`)
- Fix symlink install: use `rm -rf` to handle both symlinks and existing directories
- Resolve symlinks in working directory path using `os.path.realpath()` for macOS compatibility
- Remove unused `DEFAULT_TIMEOUT_SECONDS` constant

### Added
- `codex-as-mcp-patched/` directory with patched server.py and explanation of all fixes
- `.gitignore` at repo root covering `.codex-temp/`, `*.log`, `.DS_Store`

### Changed
- Translate all Chinese content to English (install.sh, README.md, CHANGELOG.md,
  CONTRIBUTING.md, CODE_OF_CONDUCT.md)
- README.md is now a clean English document; Chinese content preserved in README-zh.md

## [2.0.0] - 2025-11-07

### Changed (Breaking)
- Refactored to standard Claude Code Plugin format
- Project structure reorganized:
  - Added `.claude-plugin/plugin.json` metadata file
  - Moved command files to `commands/` directory
  - Supports installation via `/plugin install`
- Installation method updated:
  - Plugin installation method is now recommended
  - Manual installation kept as alternative
  - Updated all README documentation for new install instructions

### Added
- Plugin management support:
  - Install via `/plugin install CoderMageFox/claudecode-codex-subagents`
  - Manage via `/plugin enable/disable`
  - Validate structure via `/plugin validate`
- Standardized Plugin metadata (`plugin.json`)
  - Includes version, author, license information
  - Declares MCP server dependencies
  - Defines required permissions
- Auto-install of both Chinese and English command variants

## [1.0.0] - 2025-11-07

### Added
- Initial release of Codex Subagents plugin
- Parallel agent orchestration with max 3 agents per batch
- Chain processing for more than 3 agents with automatic batching
- Comprehensive logging system to `.codex-temp/[timestamp]/`
- Real-time progress tracking via TodoWrite integration
- Full i18n support (Chinese and English)
  - `codex-subagents.md` - Default Chinese version
  - `codex-subagents-en.md` - English version
- Complete documentation
  - README.md (Chinese with language switcher)
  - README-en.md (English)
  - README-zh.md (Chinese)
- Quality validation gates
  - Pre-merge checks
  - Compilation validation
  - Static analysis (lint, type-check)
  - Test execution
  - Code quality checks
- Multiple task decomposition strategies
  - File-based decomposition
  - Feature-based decomposition
  - Layer-based decomposition
- Intelligent merge strategies
  - Direct merge (no conflicts)
  - Sequential integration (with dependencies)
  - Conflict resolution (overlapping changes)
  - Incremental validation (high-risk scenarios)
- Detailed agent logging with timestamps and function names
- Batch execution progress reporting
- Error handling and retry mechanisms

### Documentation
- Installation guide with multiple methods
- Usage examples and best practices
- Workflow documentation
- Troubleshooting guide
- Performance optimization tips
- Contributing guidelines (CONTRIBUTING.md)
- Code of Conduct (CODE_OF_CONDUCT.md)

### Infrastructure
- MIT License
- .gitignore for temporary files and logs
- GitHub badges (License, Stars, Issues, PRs Welcome)

[Unreleased]: https://github.com/mgoulart/codex-subagents/compare/v3.0.0...HEAD
[3.0.0]: https://github.com/mgoulart/codex-subagents/releases/tag/v3.0.0
[2.0.0]: https://github.com/CoderMageFox/claudecode-codex-subagents/releases/tag/v2.0.0
[1.0.0]: https://github.com/CoderMageFox/claudecode-codex-subagents/releases/tag/v1.0.0
