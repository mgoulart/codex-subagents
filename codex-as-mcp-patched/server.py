"""
MCP server exposing tools for spawning and monitoring Codex CLI agents.

Tools:
  spawn_agent(prompt) -> str                    — single blocking agent
  spawn_agents_parallel(agents) -> dict         — multiple blocking agents
  spawn_agents_async(agents) -> dict            — launch agents, return immediately
  check_agents_status(job_id) -> dict           — poll running/completed agents

Command executed per agent:
    codex e --cd {os.path.realpath(os.getcwd())} --skip-git-repo-check
        --dangerously-bypass-approvals-and-sandbox
        --output-last-message {temp_output} {prompt}

Patches applied vs original CoderMageFox version:
  1. stdin=asyncio.subprocess.DEVNULL — prevents codex subprocess from inheriting
     the MCP server's stdio pipe (Claude Code's stdio), which caused an indefinite
     stdin-read block / hang.
  2. No prompt quoting — create_subprocess_exec passes args directly to execvp
     without shell processing, so wrapping the prompt in literal '"...' caused
     those quote characters to appear in the prompt text.
  3. os.path.realpath(work_directory) — resolves symlinks (e.g. macOS /tmp ->
     /private/tmp) before passing the path to codex --cd.
  4. Removed unused DEFAULT_TIMEOUT_SECONDS constant.
  5. Real-time log streaming — each agent streams stdout/stderr to a log file
     in .codex-temp/<timestamp>/ so you can `tail -f` for live visibility.
     Partial output is preserved even if agents are killed.
  6. Per-agent progress identity — progress notifications include agent index
     and a short label extracted from the prompt, plus elapsed time.
  7. Async launch + polling — spawn_agents_async returns immediately, caller
     polls with check_agents_status to get live progress from log files.
"""

import asyncio
import json
import os
import re
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP, Context


mcp = FastMCP("codex-subagent")


_DEFAULT_CHILD_ENV_OVERRIDES: dict[str, str] = {}

# Registry of async jobs: job_id -> job metadata
_async_jobs: dict[str, dict[str, Any]] = {}


def set_default_child_env(overrides: dict[str, str]) -> None:
    """Set default env overrides for spawned Codex CLI processes.

    Values set here apply to every spawned agent, and can be overridden per-call
    by the tool-level `env` argument.
    """
    _DEFAULT_CHILD_ENV_OVERRIDES.clear()
    _DEFAULT_CHILD_ENV_OVERRIDES.update(overrides)


def _build_child_env() -> dict[str, str]:
    merged = dict(os.environ)
    merged.update(_DEFAULT_CHILD_ENV_OVERRIDES)
    return merged


def _extract_label(prompt: str, max_len: int = 40) -> str:
    """Extract a short label from the prompt for progress messages."""
    # Take first line, strip markdown/formatting
    first_line = prompt.strip().split("\n")[0]
    first_line = re.sub(r"[*#`_\[\]]", "", first_line).strip()
    if len(first_line) > max_len:
        first_line = first_line[:max_len].rsplit(" ", 1)[0] + "..."
    return first_line or "agent"


def _make_log_dir(base_dir: str | None = None) -> Path:
    """Create and return a timestamped log directory."""
    if base_dir:
        log_dir = Path(base_dir)
    else:
        work_dir = os.path.realpath(os.getcwd())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = Path(work_dir) / ".codex-temp" / timestamp
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _format_elapsed(seconds: float) -> str:
    """Format elapsed seconds as a human-readable string."""
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m{secs:02d}s"


def _resolve_codex_executable() -> str:
    """Resolve the `codex` executable path or raise a clear error.

    Returns:
        str: Absolute path to the `codex` executable.

    Raises:
        FileNotFoundError: If the executable cannot be found in PATH.
    """
    codex = shutil.which("codex")
    if not codex:
        raise FileNotFoundError(
            "Codex CLI not found in PATH. Please install it (e.g. `npm i -g @openai/codex`) "
            "and ensure your shell PATH includes the npm global bin."
        )
    return codex


@mcp.tool()
async def spawn_agent(
    ctx: Context,
    prompt: str,
    model: str = "",
    log_file: str = "",
    agent_label: str = "",
) -> str:
    """Spawn a Codex agent to work inside the current working directory.

    The server resolves the working directory via ``os.path.realpath(os.getcwd())``
    to handle macOS /tmp -> /private/tmp symlinks and similar cases.

    Args:
        prompt: All instructions/context the agent needs for the task.
        model: Optional model override (e.g. "o3", "gpt-4o"). Uses the Codex
               CLI default model from ~/.codex/config.toml when not specified.
        log_file: Optional path to stream stdout/stderr to in real-time.
                  Enables `tail -f <log_file>` for live visibility.
        agent_label: Optional short label for progress messages (auto-extracted
                     from prompt if not provided).

    Returns:
        The agent's final response (clean output from Codex CLI).
    """
    # Basic validation to avoid confusing UI errors
    if not isinstance(prompt, str):
        return "Error: 'prompt' must be a string."
    if not prompt.strip():
        return "Error: 'prompt' is required and cannot be empty."

    try:
        codex_exec = _resolve_codex_executable()
    except FileNotFoundError as e:
        return f"Error: {e}"

    label = agent_label or _extract_label(prompt)

    # Patch 3: resolve symlinks so codex gets the real path (macOS /tmp fix)
    work_directory = os.path.realpath(os.getcwd())

    with tempfile.TemporaryDirectory(prefix="codex_output_") as temp_dir:
        output_path = Path(temp_dir) / "last_message.md"
        output_path.touch()

        # Patch 2: pass prompt directly — no quoting needed for create_subprocess_exec
        cmd = [
            codex_exec,
            "e",
            "--cd",
            work_directory,
            "--skip-git-repo-check",
            "--dangerously-bypass-approvals-and-sandbox",
            "--output-last-message",
            str(output_path),
        ]
        if model and isinstance(model, str) and model.strip():
            cmd += ["--model", model.strip()]
        cmd.append(prompt)

        # Prepare log file handle if requested
        log_fh = None
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_fh = open(log_path, "w", encoding="utf-8", buffering=1)  # line-buffered
            log_fh.write(f"=== Agent: {label} ===\n")
            log_fh.write(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_fh.write(f"Prompt: {prompt[:200]}{'...' if len(prompt) > 200 else ''}\n")
            log_fh.write(f"{'=' * 60}\n\n")
            log_fh.flush()

        # Initial progress ping
        try:
            await ctx.report_progress(0, None, f"[{label}] Launching...")
        except Exception:
            pass

        start_time = time.monotonic()

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                # Patch 1: DEVNULL prevents the child from inheriting the MCP
                # server's stdin (Claude Code's stdio pipe), which would cause
                # the child to block indefinitely waiting for input.
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=_build_child_env(),
            )
        except Exception as e:
            if log_fh:
                log_fh.write(f"\n!!! Launch failed: {e}\n")
                log_fh.close()
            return f"Error: Failed to launch Codex agent: {e}"

        # Stream stdout/stderr to log file in real-time while collecting full output
        stdout_chunks: list[bytes] = []
        stderr_chunks: list[bytes] = []

        async def _stream_reader(
            stream: asyncio.StreamReader | None,
            chunks: list[bytes],
            prefix: str,
        ) -> None:
            """Read stream line-by-line, appending to chunks and writing to log."""
            if not stream:
                return
            while True:
                line = await stream.readline()
                if not line:
                    break
                chunks.append(line)
                if log_fh:
                    decoded = line.decode(errors="replace")
                    log_fh.write(f"{prefix}{decoded}")
                    log_fh.flush()

        stdout_reader = asyncio.create_task(
            _stream_reader(proc.stdout, stdout_chunks, "")
        )
        stderr_reader = asyncio.create_task(
            _stream_reader(proc.stderr, stderr_chunks, "[stderr] ")
        )

        # Send periodic heartbeats with elapsed time while process runs
        last_ping = time.monotonic()
        while True:
            try:
                returncode = await asyncio.wait_for(proc.wait(), timeout=5.0)
                break
            except asyncio.TimeoutError:
                now = time.monotonic()
                elapsed = _format_elapsed(now - start_time)
                if now - last_ping >= 5.0:
                    last_ping = now
                    try:
                        await ctx.report_progress(
                            1, None, f"[{label}] Running... ({elapsed})"
                        )
                    except Exception:
                        pass

        # Wait for stream readers to finish
        await stdout_reader
        await stderr_reader

        elapsed = _format_elapsed(time.monotonic() - start_time)

        stdout = b"".join(stdout_chunks).decode(errors="replace")
        stderr = b"".join(stderr_chunks).decode(errors="replace")

        output = output_path.read_text(encoding="utf-8").strip()

        # Write completion to log
        if log_fh:
            log_fh.write(f"\n{'=' * 60}\n")
            log_fh.write(f"Exit code: {returncode}\n")
            log_fh.write(f"Duration: {elapsed}\n")
            log_fh.write(f"End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if output:
                log_fh.write(f"\n--- Final Output ---\n{output}\n")
            log_fh.close()

        if returncode != 0:
            details = [
                "Error: Codex agent exited with a non-zero status.",
                f"Command: {' '.join(cmd)}",
                f"Exit Code: {returncode}",
                f"Duration: {elapsed}",
            ]
            if stderr:
                details.append(f"Stderr: {stderr}")
            if stdout:
                details.append(f"Stdout: {stdout}")
            if output:
                details.append(f"Captured Output: {output}")
            if log_file:
                details.append(f"Log: {log_file}")
            return "\n".join(details)

        return output


@mcp.tool()
async def spawn_agents_parallel(
    ctx: Context,
    agents: list[dict],
    log_dir: str = "",
) -> dict:
    """Spawn multiple Codex agents in parallel.

    Each spawned agent reuses the server's current working directory
    (``os.path.realpath(os.getcwd())``).

    Real-time visibility: each agent streams its output to a log file.
    Use ``tail -f <log_dir>/*.log`` to watch all agents live.

    Args:
        agents: List of agent specs, each with a 'prompt' entry and optional
                'label' for identification.
                Example: [
                    {"prompt": "Create math.md", "label": "math"},
                    {"prompt": "Create story.md", "label": "story"}
                ]
        log_dir: Optional directory for agent log files. Defaults to
                 ``.codex-temp/<timestamp>/`` in the working directory.

    Returns:
        Dict with 'log_dir', 'summary', and 'results' (list of per-agent
        dicts with 'index', 'label', 'output'/'error', 'log_file', 'duration').
    """
    if not isinstance(agents, list):
        return {"error": "Error: 'agents' must be a list of agent specs."}

    if not agents:
        return {"error": "Error: 'agents' list cannot be empty."}

    # Create log directory
    resolved_log_dir = _make_log_dir(log_dir if log_dir else None)

    # Write a manifest so you know what's running
    manifest_path = resolved_log_dir / "manifest.txt"
    with open(manifest_path, "w", encoding="utf-8") as mf:
        mf.write(f"Codex Subagents Run — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        mf.write(f"Agents: {len(agents)}\n")
        mf.write(f"Log dir: {resolved_log_dir}\n\n")
        for i, spec in enumerate(agents):
            label = spec.get("label", "") or _extract_label(spec.get("prompt", ""))
            mf.write(f"  [{i}] {label}\n")
        mf.write(f"\nTail all: tail -f {resolved_log_dir}/*.log\n")

    batch_start = time.monotonic()

    try:
        await ctx.report_progress(
            0,
            len(agents),
            f"Launching {len(agents)} agents — logs at {resolved_log_dir}/",
        )
    except Exception:
        pass

    async def run_one(index: int, spec: dict) -> dict:
        """Run a single agent and return result with index."""
        try:
            if not isinstance(spec, dict):
                return {
                    "index": str(index),
                    "label": f"agent-{index}",
                    "error": f"Agent {index}: spec must be a dictionary with a 'prompt' field.",
                }

            prompt = spec.get("prompt", "")
            model = spec.get("model", "")
            label = spec.get("label", "") or _extract_label(prompt)

            # Create per-agent log file
            safe_label = re.sub(r"[^a-zA-Z0-9_-]", "_", label)[:30]
            log_file = str(resolved_log_dir / f"agent-{index}-{safe_label}.log")

            try:
                await ctx.report_progress(
                    index,
                    len(agents),
                    f"[{index+1}/{len(agents)}] Starting: {label}",
                )
            except Exception:
                pass

            agent_start = time.monotonic()

            output = await spawn_agent(
                ctx, prompt, model, log_file=log_file, agent_label=label
            )

            duration = _format_elapsed(time.monotonic() - agent_start)

            # Report completion
            try:
                await ctx.report_progress(
                    index + 1,
                    len(agents),
                    f"[{index+1}/{len(agents)}] Done: {label} ({duration})",
                )
            except Exception:
                pass

            if output.startswith("Error:"):
                return {
                    "index": str(index),
                    "label": label,
                    "error": output,
                    "log_file": log_file,
                    "duration": duration,
                }

            return {
                "index": str(index),
                "label": label,
                "output": output,
                "log_file": log_file,
                "duration": duration,
            }

        except Exception as e:
            return {
                "index": str(index),
                "label": spec.get("label", f"agent-{index}"),
                "error": f"Agent {index}: {str(e)}",
            }

    # Run all agents concurrently
    tasks = [run_one(i, agent) for i, agent in enumerate(agents)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle any exceptions that weren't caught
    final_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            final_results.append({
                "index": str(i),
                "label": f"agent-{i}",
                "error": f"Unexpected error: {str(result)}",
            })
        else:
            final_results.append(result)

    batch_duration = _format_elapsed(time.monotonic() - batch_start)

    # Write summary to log dir
    summary_path = resolved_log_dir / "summary.txt"
    succeeded = sum(1 for r in final_results if "output" in r)
    failed = sum(1 for r in final_results if "error" in r)
    with open(summary_path, "w", encoding="utf-8") as sf:
        sf.write(f"Batch complete: {batch_duration}\n")
        sf.write(f"Succeeded: {succeeded}/{len(agents)}\n")
        sf.write(f"Failed: {failed}/{len(agents)}\n\n")
        for r in final_results:
            status = "OK" if "output" in r else "FAIL"
            sf.write(f"  [{r['index']}] {r.get('label', '?')} — {status}")
            if "duration" in r:
                sf.write(f" ({r['duration']})")
            sf.write("\n")

    return {
        "log_dir": str(resolved_log_dir),
        "tail_command": f"tail -f {resolved_log_dir}/*.log",
        "summary": f"{succeeded}/{len(agents)} succeeded in {batch_duration}",
        "result": final_results,
    }


@mcp.tool()
async def spawn_agents_async(
    ctx: Context,
    agents: list[dict],
    log_dir: str = "",
) -> dict:
    """Launch multiple Codex agents and return immediately without waiting.

    Use ``check_agents_status(job_id)`` to poll for progress and results.
    Each agent streams output to a log file for real-time visibility.

    Args:
        agents: List of agent specs, each with a 'prompt' and optional 'label'.
        log_dir: Optional directory for log files. Defaults to
                 ``.codex-temp/<timestamp>/``.

    Returns:
        Dict with 'job_id', 'log_dir', 'tail_command', and 'agents' list
        showing index/label/log_file for each launched agent.
    """
    if not isinstance(agents, list) or not agents:
        return {"error": "Error: 'agents' must be a non-empty list of agent specs."}

    # Create log directory and job ID
    resolved_log_dir = _make_log_dir(log_dir if log_dir else None)
    job_id = resolved_log_dir.name  # timestamp or user-provided dirname

    # Build agent metadata and write manifest
    agent_metas: list[dict] = []
    for i, spec in enumerate(agents):
        label = spec.get("label", "") or _extract_label(spec.get("prompt", ""))
        safe_label = re.sub(r"[^a-zA-Z0-9_-]", "_", label)[:30]
        log_file = str(resolved_log_dir / f"agent-{i}-{safe_label}.log")
        agent_metas.append({
            "index": i,
            "label": label,
            "log_file": log_file,
            "prompt": spec.get("prompt", ""),
            "model": spec.get("model", ""),
        })

    manifest_path = resolved_log_dir / "manifest.txt"
    with open(manifest_path, "w", encoding="utf-8") as mf:
        mf.write(f"Codex Subagents Run — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        mf.write(f"Job ID: {job_id}\n")
        mf.write(f"Agents: {len(agents)}\n")
        mf.write(f"Log dir: {resolved_log_dir}\n\n")
        for am in agent_metas:
            mf.write(f"  [{am['index']}] {am['label']}\n")
        mf.write(f"\nTail all: tail -f {resolved_log_dir}/*.log\n")

    # Register the job
    job = {
        "job_id": job_id,
        "log_dir": str(resolved_log_dir),
        "start_time": time.monotonic(),
        "started_at": datetime.now().isoformat(),
        "agents": agent_metas,
        "tasks": {},       # index -> asyncio.Task
        "results": {},     # index -> result dict
        "output_paths": {},  # index -> temp output path
    }
    _async_jobs[job_id] = job

    # Launch each agent as a background asyncio task
    async def _run_agent(meta: dict) -> None:
        idx = meta["index"]
        label = meta["label"]
        log_file = meta["log_file"]
        prompt = meta["prompt"]
        model = meta["model"]
        agent_start = time.monotonic()

        try:
            output = await spawn_agent(
                ctx, prompt, model, log_file=log_file, agent_label=label
            )
            duration = _format_elapsed(time.monotonic() - agent_start)

            if output.startswith("Error:"):
                job["results"][idx] = {
                    "status": "error",
                    "label": label,
                    "error": output,
                    "duration": duration,
                }
            else:
                job["results"][idx] = {
                    "status": "completed",
                    "label": label,
                    "output": output,
                    "duration": duration,
                }
        except Exception as e:
            duration = _format_elapsed(time.monotonic() - agent_start)
            job["results"][idx] = {
                "status": "error",
                "label": label,
                "error": str(e),
                "duration": duration,
            }

    for meta in agent_metas:
        task = asyncio.create_task(_run_agent(meta))
        job["tasks"][meta["index"]] = task

    return {
        "job_id": job_id,
        "log_dir": str(resolved_log_dir),
        "tail_command": f"tail -f {resolved_log_dir}/*.log",
        "agents": [
            {"index": am["index"], "label": am["label"], "log_file": am["log_file"]}
            for am in agent_metas
        ],
    }


@mcp.tool()
async def check_agents_status(
    ctx: Context,
    job_id: str,
    tail_lines: int = 15,
) -> dict:
    """Check the status of agents launched by spawn_agents_async.

    Reads live log files to show what each agent is currently doing.

    Args:
        job_id: The job_id returned by spawn_agents_async.
        tail_lines: Number of recent log lines to include per agent (default 15).

    Returns:
        Dict with overall status, elapsed time, and per-agent status including
        recent log output.
    """
    if job_id not in _async_jobs:
        # Check if it looks like a log_dir path
        available = list(_async_jobs.keys())
        return {
            "error": f"Unknown job_id: {job_id}",
            "available_jobs": available,
        }

    job = _async_jobs[job_id]
    elapsed = _format_elapsed(time.monotonic() - job["start_time"])

    agent_statuses = []
    for meta in job["agents"]:
        idx = meta["index"]
        label = meta["label"]
        log_file = meta["log_file"]

        # Check if this agent has finished
        if idx in job["results"]:
            result = job["results"][idx]
            agent_statuses.append({
                "index": idx,
                "label": label,
                "status": result["status"],
                "duration": result.get("duration", ""),
                "output_preview": result.get("output", result.get("error", ""))[:300],
            })
            continue

        # Agent still running — read tail of log file for live progress
        status_info: dict[str, Any] = {
            "index": idx,
            "label": label,
            "status": "running",
        }

        log_path = Path(log_file)
        if log_path.exists():
            try:
                text = log_path.read_text(encoding="utf-8", errors="replace")
                lines = text.rstrip().split("\n")
                total_lines = len(lines)
                recent = lines[-tail_lines:] if len(lines) > tail_lines else lines
                status_info["log_lines"] = total_lines
                status_info["recent_output"] = "\n".join(recent)
            except Exception as e:
                status_info["log_error"] = str(e)
        else:
            status_info["status"] = "starting"

        agent_statuses.append(status_info)

    completed = sum(1 for a in agent_statuses if a["status"] == "completed")
    errored = sum(1 for a in agent_statuses if a["status"] == "error")
    running = sum(1 for a in agent_statuses if a["status"] in ("running", "starting"))
    all_done = running == 0

    result: dict[str, Any] = {
        "job_id": job_id,
        "elapsed": elapsed,
        "all_done": all_done,
        "counts": {
            "total": len(job["agents"]),
            "completed": completed,
            "errored": errored,
            "running": running,
        },
        "agents": agent_statuses,
    }

    # If all done, include final outputs and write summary
    if all_done:
        summary_path = Path(job["log_dir"]) / "summary.txt"
        with open(summary_path, "w", encoding="utf-8") as sf:
            sf.write(f"Batch complete: {elapsed}\n")
            sf.write(f"Succeeded: {completed}/{len(job['agents'])}\n")
            sf.write(f"Failed: {errored}/{len(job['agents'])}\n\n")
            for a in agent_statuses:
                sf.write(f"  [{a['index']}] {a['label']} — {a['status']}")
                if a.get("duration"):
                    sf.write(f" ({a['duration']})")
                sf.write("\n")

        # Return full outputs instead of previews
        for a in result["agents"]:
            idx = a["index"]
            if idx in job["results"]:
                r = job["results"][idx]
                a["full_output"] = r.get("output", r.get("error", ""))

    return result


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
