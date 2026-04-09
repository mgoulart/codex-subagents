# codex-as-mcp-patched

This directory contains a patched version of `server.py` from the `codex-as-mcp` PyPI package, with four critical fixes applied.

## Patches

### Patch 1: stdin=DEVNULL (Critical — fixes indefinite hang)

**Problem:** The original code did not set `stdin` when calling `asyncio.create_subprocess_exec`. This caused the child `codex exec` process to inherit the MCP server's stdin, which is Claude Code's stdio pipe. The child process blocked indefinitely waiting for stdin input that never came.

**Fix:** Added `stdin=asyncio.subprocess.DEVNULL` to `asyncio.create_subprocess_exec`.

```python
# Before (hangs indefinitely):
proc = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    env=_build_child_env(),
)

# After (fixed):
proc = await asyncio.create_subprocess_exec(
    *cmd,
    stdin=asyncio.subprocess.DEVNULL,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    env=_build_child_env(),
)
```

### Patch 2: Remove unnecessary prompt quoting

**Problem:** The original code wrapped the prompt in literal quote characters before passing to `create_subprocess_exec`:

```python
quoted_prompt = '"' + prompt.replace('"', '\\"') + '"'
```

`create_subprocess_exec` passes arguments directly to `execvp` without shell processing, so the literal `"` characters were included in the prompt text sent to the agent.

**Fix:** Pass `prompt` directly without quoting.

### Patch 3: Resolve symlinks in work directory

**Problem:** `os.getcwd()` on macOS may return `/tmp/...` which is a symlink to `/private/tmp/...`. Some tools reject the symlinked path.

**Fix:** Use `os.path.realpath(os.getcwd())` to resolve symlinks before passing to `codex --cd`.

### Patch 4: Remove unused constant

**Problem:** `DEFAULT_TIMEOUT_SECONDS = 8 * 60 * 60` was defined but never used anywhere in the code.

**Fix:** Removed the constant entirely. If a timeout is needed in the future, it should be implemented properly (e.g., passed to `asyncio.wait_for`).

## How to Use This Patched Version

### Option A: Replace via uvx override (recommended)

You can install a local copy of the patched server. First, create a minimal package structure:

```
my-codex-mcp/
  pyproject.toml
  server.py          <- copy this file here
```

Then install and run it with uvx or uv.

### Option B: Patch in place

If you have the codex-as-mcp package installed in a known location (e.g. via `uvx` cache), you can copy `server.py` over the installed version. However, this will be overwritten when the package is updated.

### Option C: Submit upstream

The fixes in this directory have been submitted as a bug report / PR to the original `codex-as-mcp` package. Once merged, the standard `uvx codex-as-mcp@latest` will include the fixes.

## Status

As of this fork (April 2026), the upstream `codex-as-mcp` package (found in the PyPI/uv cache) already includes Patches 1 and 3. Patches 2 and 4 are applied here for completeness and clarity.
