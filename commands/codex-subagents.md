---
name: codex-subagents
description: "Orchestrate complex tasks by delegating to multiple parallel Codex agents with live monitoring"
category: orchestration
args: task description
---

# Codex Subagents - Orchestration with Live Monitoring

You are coordinating a complex task by delegating to multiple Codex sub-agents via MCP, with real-time progress visibility.

## Your Role

Act as an intelligent orchestrator that:
1. Analyzes the task and breaks it into **small, focused** agent jobs
2. Launches agents with `mcp__codex-subagent__spawn_agents_async` (non-blocking)
3. Monitors progress with `mcp__codex-subagent__check_agents_status` (polling)
4. Reports live progress to the user as agents work
5. Collects results and merges them when complete
6. Chains additional batches if needed

## Task: $ARGUMENTS

## Available MCP Tools

| Tool | Purpose |
|------|---------|
| `spawn_agents_async` | Launch agents, return immediately with `job_id` |
| `check_agents_status` | Poll agent progress — shows live log output per agent |
| `spawn_agents_parallel` | Launch agents and block until all complete (fallback) |

## Process Flow

### Step 1: Task Analysis & Decomposition

Break the task into **small, focused units** following these principles:

**Scope each agent narrowly:**
- BAD: "Scan all of vms/lib/ for null-contract bugs" (too broad, black box)
- GOOD: "Scan vms/lib/comments/ for null dereferences on data from DB lookups" (focused, observable)

**Target 1-3 specific directories or files per agent.** This keeps agents fast (~30-60s) and their logs readable.

**Use these decomposition strategies:**

**Directory-Based** (for codebase scans/audits):
```yaml
agent_0: Scan vms/lib/comments/ for [pattern]
agent_1: Scan vms/lib/payments/ for [pattern]
agent_2: Scan vms/lib/bears/ for [pattern]
```

**File-Based** (for implementation tasks):
```yaml
agent_0: [UserCard.tsx, UserCard.test.tsx]
agent_1: [ProductCard.tsx, ProductCard.test.tsx]
```

**Feature-Based** (for complete features):
```yaml
agent_0: Auth backend (models + API)
agent_1: Auth frontend (components + state)
agent_2: Auth tests (unit + integration)
```

### Step 2: Write Agent Prompts with Checkpoints

Every agent prompt MUST include checkpoint instructions so their logs show meaningful progress. Use this template:

```markdown
[Task description — 1-2 sentences, very specific scope]

Work through these steps IN ORDER. After each step, print a checkpoint line.

## Step 1: [First focused subtask]
[Specific instructions — what to look at, what patterns to match]
When done, print: "=== CHECKPOINT 1/N: [step name] — [count] findings ==="

## Step 2: [Second focused subtask]
[Specific instructions]
When done, print: "=== CHECKPOINT 2/N: [step name] — [count] findings ==="

## Step N: Compile Results
Compile all findings into a structured list. For each finding output:
- File path and line number
- The pattern/code
- Severity
- One-line description

Print: "=== COMPLETE: [total] findings ==="
```

**Why checkpoints matter:** The MCP server streams agent stdout to log files in real-time. When the orchestrator polls `check_agents_status`, it reads the tail of each log. Checkpoint lines make it immediately clear how far each agent has progressed.

### Step 3: Launch Agents (Non-Blocking)

```
mcp__codex-subagent__spawn_agents_async({
  agents: [
    { prompt: "...", label: "short-name-0" },
    { prompt: "...", label: "short-name-1" },
    { prompt: "...", label: "short-name-2" }
  ],
  log_dir: ".codex-temp/descriptive-name"  // optional
})
```

This returns immediately with:
- `job_id` — use for polling
- `log_dir` — where logs stream to
- `tail_command` — user can run this in another terminal

**Tell the user** the tail command so they can watch live if they want.

### Step 4: Monitor Progress (Polling Loop)

Poll every 20-30 seconds until all agents complete:

```
mcp__codex-subagent__check_agents_status({
  job_id: "<job_id>",
  tail_lines: 15
})
```

After each poll, **report to the user** what you see:
- Which agents are still running vs completed
- What step each running agent is on (from checkpoint lines in logs)
- Any findings or errors so far
- Elapsed time

Example update to user:
```
**Progress (45s elapsed, 1/3 done):**
- agent-0 (comments): Done — 3 findings (28s)
- agent-1 (payments): Step 2/3 — scanning processors/types/
- agent-2 (bears): Step 1/3 — scanning models/deviation/
```

**Stop polling when** `all_done: true` in the response.

### Step 5: Collect Results

When all agents are done, `check_agents_status` returns `full_output` for each agent. Compile the results:

1. Parse each agent's output
2. Deduplicate findings that overlap
3. Sort by severity/priority
4. Present a merged summary to the user

### Step 6: Chain Batches (if needed)

If the task requires >3 agents:
1. Launch batch 1 (up to 3 agents)
2. Monitor until complete
3. Report batch 1 results
4. Launch batch 2 with any context from batch 1
5. Repeat

## Agent Prompt Guidelines

**Keep prompts focused:**
- 1-3 directories max per agent
- Specific patterns to search for (not "find all bugs")
- Concrete output format (file, line, description)
- Limit on findings count (e.g., "limit to 10 strongest")

**Include checkpoint instructions in every prompt:**
- Explicit step-by-step structure
- "Print checkpoint after each step" instruction
- Final "=== COMPLETE ===" marker

**Include context the agent needs:**
- Full file paths (agents don't share your context)
- Specific function/class names to look for
- Examples of the pattern from other files if available

## Error Handling

**If an agent fails:**
1. Report the error from the log file
2. Decide whether to retry with a refined prompt or skip
3. Continue monitoring remaining agents

**If an agent is slow (>3 minutes):**
1. Report to user what the agent's log shows
2. Ask if they want to wait or kill it
3. Partial results from the log file are preserved either way

## Best Practices

- Keep agents small and focused — 30-90 seconds each is ideal
- Always include checkpoint instructions in prompts
- Poll every 20-30 seconds (not too fast, not too slow)
- Report progress to user after every poll
- Use descriptive labels for agents (shown in status output)
- Use descriptive log_dir names (not just timestamps)
- Max 3 agents per batch

---

**Always respond in English.**
