# Orchestrator — Per-Task Execution Loop

The orchestrator is the main runtime loop. It runs for every task: selects skills, injects context, runs the execution agent, records artifacts, and fires the three evolution triggers.

---

## Source Files

| File | Role |
|------|------|
| `/Users/amirali.iranmanesh/JB/OpenSpace/src/orchestrator.py` | Main loop — new file |
| `/Users/amirali.iranmanesh/JB/OpenSpace/src/execution_agent.py` | Task performer — new file |
| `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/skill_engine/registry.py` | Skill selection — copy/adapt |
| `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/skill_engine/analyzer.py` | Trigger 1 (post-execution analysis) — copy/adapt |

---

## Per-Task Flow

```
Input: task_description (string)

1. Select skills
   └── quality pre-filter (exclude chronically failing skills)
   └── LLM selection from filtered catalog
   └── Output: list of selected skill IDs

2. Build system prompt
   └── Inject constitution (always first)
   └── Inject selected skill contents

3. Run execution agent
   └── Agentic loop, max 15 iterations
   └── MCPs mounted per agent_config.json
   └── Terminates when agent outputs <COMPLETE>

4. Record artifacts
   └── recordings/run_{id}/
       ├── conversations.jsonl   ← full LLM conversation
       ├── traj.jsonl            ← tool trace
       └── metadata.json         ← task, skills, status, iterations

5. Trigger 1 — post-execution analysis   [BLOCKING — wait for result]
   └── Reads recording artifacts
   └── LLM analyzes: task success? skills helped? what to evolve?
   └── Writes evolution suggestions + feature requests to DB
   └── Updates skill quality counters

6. Trigger 2 — tool degradation check    [BACKGROUND — fire and forget]
   └── Checks tool success rates from traj.jsonl history
   └── If any tool is degraded, evolves skills that depend on it

7. Trigger 3 — metric health check       [BACKGROUND — every 5 executions]
   └── Checks skill quality metrics in DB
   └── If any skill is underperforming, proposes FIX or DERIVED evolution
```

---

## System Prompt Construction

The system prompt has two injected sections: constitution first, then skills.

**Constitution block** (always injected, always first):

```markdown
# Agent Constitution (Non-Negotiable Constraints)

{constitution_content}

---
```

**Skills block** (follows constitution):

```markdown
# Active Skills

The following skills provide domain knowledge and tested procedures for this task.

How to use skills:
- If a skill contains step-by-step procedures or commands, follow them precisely.
- If a skill provides reference information or best practices, use it as context when making decisions.
- Skills supplement your available tools — you may use any tool alongside skill guidance.

---

### Skill: {skill_id}
**Directory**: `{skill_dir}`

{skill_content}

---
```

---

## Execution Agent

The execution agent (`/Users/amirali.iranmanesh/JB/OpenSpace/src/execution_agent.py`) runs with:
- The full system prompt (constitution + selected skills)
- All MCPs listed in `agent_config.json` mounted
- Max 15 iterations (configurable)
- Outputs `<COMPLETE>` when done

The execution agent **does not know about** the skill engine, evolution, or approval — it only sees the task and its tools.

---

## Recording Artifacts

Three files are written per run to `recordings/run_{id}/`:

**`conversations.jsonl`** — one JSON line per LLM turn:
```json
{"role": "user", "content": "Review PR #123 for security issues", "iter": 0}
{"role": "assistant", "content": "I'll start by examining the diff...", "iter": 1}
{"role": "tool_call", "name": "get_pr_diff", "args": {"pr": 123}, "iter": 1}
{"role": "tool_result", "name": "get_pr_diff", "content": "...", "success": true, "iter": 1}
```

**`traj.jsonl`** — one JSON line per tool invocation:
```json
{"iter": 1, "tool": "get_pr_diff", "args": {"pr": 123}, "success": true, "duration_ms": 340}
{"iter": 2, "tool": "post_review_comment", "args": {...}, "success": true, "duration_ms": 210}
```

**`metadata.json`**:
```json
{
  "task_id": "run_a1b2c3d4",
  "task_description": "Review PR #123 for security issues",
  "selected_skills": ["check-sql-injection__v2_e5f6g7h8", "review-output-format__v1_i9j0k1l2"],
  "tool_list": ["get_pr_diff", "post_review_comment", "search_code"],
  "execution_status": "success",
  "iterations": 4
}
```

---

## Truncation Limits

Apply before passing any artifact to an LLM:

| Field                     | Max Chars |
|---------------------------|-----------|
| Full conversation log     | 80,000    |
| Tool error message        | 1,000     |
| Tool success result       | 800       |
| Tool arguments            | 500       |
| Tool timeline summary     | 1,500     |
| Skill content (per skill) | 8,000     |

Truncation is implemented in `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/skill_engine/analyzer.py` — copy the truncation helpers from there.

---

## Trigger Dispatch

After recording is complete, the orchestrator dispatches all three triggers:

```python
# Trigger 1 — blocking: wait for result before returning
analysis = await analyzer.analyze(run_id)
await recurrence_tracker.process(analysis.evolution_suggestions)

# Trigger 2 — background: does not block the caller
asyncio.create_task(tool_degradation_trigger.run(run_id))

# Trigger 3 — background: only fires every 5 executions
if execution_count % METRIC_CHECK_EVERY_N_EXECUTIONS == 0:
    asyncio.create_task(metric_health_trigger.run())
```

For detailed trigger behavior, see `04-evolution-triggers.md`.
