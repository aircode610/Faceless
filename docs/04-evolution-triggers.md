# Evolution Triggers

Three triggers analyze task executions and propose skill improvements. All three produce `EvolutionSuggestion` records that go into the evolution engine. All evolved skills land in `status=pending` and require human approval before going live.

---

## Source Files

| File | Role |
|------|------|
| `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/skill_engine/analyzer.py` | Trigger 1 (post-execution analysis loop) — copy/adapt |
| `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/skill_engine/evolver.py` | Evolution engine called by all triggers — copy/adapt |
| `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/prompts/skill_engine_prompts.py` | All 5 prompts — copy verbatim |
| `/Users/amirali.iranmanesh/JB/OpenSpace/src/recurrence/tracker.py` | Pattern recurrence tracking — new file |

---

## Trigger 1 — Post-Execution Analysis

**When**: After every single task execution, synchronously (blocks the orchestrator until complete).

**Why blocking**: The skill counter updates (total_selections, total_applied, etc.) are needed before Trigger 3 can run. Trigger 1 also writes the recurrence records that drive priority escalation.

### Flow

```
Load recording artifacts:
  conversations.jsonl, traj.jsonl, metadata.json

Build analysis prompt (Prompt 1 — see 09-prompts.md)
  Inputs: task_description, execution_status, iterations, tool_list,
          skill_section (selected skill contents), conversation_log,
          traj_summary, selected_skill_ids_json

Run analyzer LLM loop (max 5 iterations, tools enabled for verification)

Parse JSON output:
  task_completed, execution_note, tool_issues, skill_judgments,
  evolution_suggestions, feature_requests

Update per-skill counters in DB:
  total_selections += 1
  total_applied += (1 if skill_applied else 0)
  total_completions += (1 if applied AND task_completed else 0)
  total_fallbacks += (1 if NOT applied AND NOT completed else 0)

For each evolution_suggestion:
  look up matching pattern_key in evolution_suggestions table
  if match → increment recurrence_count on existing suggestion
  if recurrence_count >= RECURRENCE_PROMOTION_THRESHOLD (3) across 2+ distinct runs
      → auto-escalate priority (medium→high, high→critical)
  dispatch suggestion to evolution engine

For each feature_request:
  insert into feature_requests table (status=pending)
```

### Analyzer Output Schema

```json
{
  "task_completed": true,
  "execution_note": "2-3 sentence overview of execution quality and outcome.",
  "tool_issues": [
    "mcp:github:get_pr_diff — returned empty diff for a draft PR; likely a filter issue"
  ],
  "skill_judgments": [
    {
      "skill_id": "check-sql-injection__v2_e5f6g7h8",
      "skill_applied": true,
      "note": "Agent followed the injection check steps and correctly flagged a parameterized query bypass."
    }
  ],
  "evolution_suggestions": [
    {
      "type": "fix",
      "target_skills": ["check-sql-injection__v2_e5f6g7h8"],
      "category": "workflow",
      "direction": "Add a step for checking raw string interpolation in f-strings — agent missed it.",
      "priority": "high",
      "pattern_key": "harden.sql-injection-fstring"
    }
  ],
  "feature_requests": [
    {
      "capability": "Review Terraform plan diffs for security group misconfigurations",
      "user_context": "User asked agent to review an infra PR but agent had no knowledge of Terraform syntax",
      "complexity": "medium"
    }
  ]
}
```

### Priority Values

| Priority   | When to assign                                              |
|------------|-------------------------------------------------------------|
| `critical` | Security gap or blocks the agent's core function           |
| `high`     | Significant impact, recurring pattern, or user-facing miss |
| `medium`   | Improvement with workaround exists                         |
| `low`      | Minor, edge case, cosmetic                                 |

### Pattern Key Format

`"{domain}.{specific-pattern}"` — lowercase, hyphens, no spaces.

- Domain examples: `harden`, `workflow`, `tool`, `output`, `coverage`
- Pattern examples: `harden.sql-injection-fstring`, `workflow.missing-test-check`, `tool.pr-diff-empty-draft`
- Keep keys narrow enough that unrelated issues don't share a key
- The analyzer LLM assigns the key; the orchestrator looks it up to detect recurrence

### Feature Requests vs Evolution Suggestions

- **Evolution suggestion**: a skill exists but was applied incorrectly or incompletely → propose `fix`
- **Feature request**: no relevant skill exists at all, task type is entirely outside current scope → FEAT entry

Do not output a feature request if a skill could have helped but wasn't selected or wasn't applied. That is a skill quality problem, not a capability gap.

---

## Trigger 2 — Tool Degradation Detection

**When**: After every execution, in background (does not block caller).

### Threshold

A tool is "problematic" when:
- `recent_success_rate < 0.5` (rolling window of last 100 calls)
- `total_calls >= 5` (minimum data requirement)

### Flow

```
get_problematic_tools()  ← reads from traj.jsonl history in DB

For each problematic tool:
  find active skills that use this tool (via skill_tool_deps table)

  skip if already addressed for this tool+skill combo:
    _addressed_degradations: dict[tool_key, set[skill_id]]
    if skill_id in _addressed_degradations[tool_key]: skip

  build issue summary:
    "Tool X degraded — success rate: Y%, calls: Z"
  build direction:
    "Update skill to handle tool failures gracefully or suggest alternatives"

  call LLM confirmation gate (see below)

  if confirmed → dispatch to evolution engine
  mark tool+skill combo as addressed

  when a tool recovers (drops off the problematic list):
    del _addressed_degradations[tool_key]   # allow re-evaluation later

Execute all confirmed evolutions in parallel (throttled, max 3 concurrent)
```

The `skill_tool_deps` table maps skill IDs to the tool names they reference. Populate this at skill creation/evolution time by parsing the skill content for tool names.

---

## Trigger 3 — Periodic Skill Health Check

**When**: Every 5 executions, in background.

**Minimum data requirement**: `total_selections >= 5` (skip skills with too little history).

### Rule-Based Diagnosis

| Condition                                          | Evolution Type | Direction |
|----------------------------------------------------|----------------|-----------|
| `fallback_rate > 0.40`                             | FIX            | "High fallback rate: skill is being selected but cannot be applied. Instructions may be outdated or reference unavailable tools." |
| `applied_rate > 0.40` AND `completion_rate < 0.35` | FIX            | "Low completion despite reasonable application rate: skill instructions may be incorrect or incomplete." |
| `effective_rate < 0.55` AND `applied_rate > 0.25`  | DERIVED        | "Moderate effective rate: skill could benefit from improvement — better steps, error handling, or broader scope." |
| Otherwise                                          | None           | — |

### Flow

```
For each active skill with total_selections >= 5:
  compute metrics: fallback_rate, applied_rate, completion_rate, effective_rate
  run rule-based diagnosis → (EvolutionType, direction) or None
  if diagnosed: call LLM confirmation gate
  if confirmed: dispatch to evolution engine

Execute all confirmed evolutions in parallel
```

---

## LLM Confirmation Gate (Triggers 2 and 3 Only)

Trigger 1 suggestions go directly to the evolution engine — they are already LLM-generated.

Triggers 2 and 3 use rigid thresholds that can produce false positives. The confirmation gate filters them before dispatching evolution.

**Prompt** (verbatim from `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/prompts/skill_engine_prompts.py` → `_EVOLUTION_CONFIRM_TEMPLATE`, lines 768-829):

```
You are an expert evaluating whether a skill needs evolution.

A rule-based monitoring system has flagged a skill as a candidate for evolution
based on health metrics or tool degradation signals.

## Skill Under Review
ID: {skill_id}
Content (may be truncated): {skill_content}

## Proposed Evolution
Type: {proposed_type}
Direction: {proposed_direction}

## Trigger Context
{trigger_context}

## Recent Execution History
{recent_analyses}

## Decision Criteria
1. Is the signal real? Could poor metrics come from external factors (task shift, tool outage)?
2. Is the skill actually problematic? Are the instructions actually wrong?
3. Is evolution worth the cost? Is this skill used enough to matter?
4. Is the proposed direction correct? Does it address the root cause?

Output JSON:
{"proceed": true, "reasoning": "...", "adjusted_direction": "optional refined direction"}
```

On any parse error → defaults to `false` (skip evolution). Fail safe.

---

## Recurrence Tracking

After Trigger 1 runs, the orchestrator calls `recurrence/tracker.py` to process each suggestion:

```python
existing = db.get_suggestion_by_pattern_key(pattern_key)

if existing:
    db.increment_recurrence(existing.id, new_run_id=run_id)
    recurrence_count = existing.recurrence_count + 1

    if recurrence_count >= RECURRENCE_PROMOTION_THRESHOLD:   # default: 3
        distinct_runs = db.count_distinct_runs_for_pattern(pattern_key)
        if distinct_runs >= 2:
            new_priority = escalate(existing.priority)  # medium→high, high→critical
            db.update_priority(existing.id, new_priority)
else:
    db.insert_suggestion(suggestion)
```

The recurrence badge (`Recurrence: 3×`) appears in the approval UI when `recurrence_count >= 2`, surfacing systemic patterns to reviewers.

---

## Anti-Loop Mechanisms

| Mechanism | Trigger | How it works |
|-----------|---------|--------------|
| Bounded by execution | T1 | Fires once per task, produces at most N suggestions — no loop possible |
| Addressed-set guard | T2 | `_addressed_degradations` dict prevents re-processing same tool+skill combo |
| Data-driven cooldown | T3 | Newly evolved skills start at `total_selections=0`, need 5 runs before T3 evaluates them |
| Approval gate | All | No evolution goes live without human sign-off — even if all guards fail |
| Max concurrent semaphore | All | `asyncio.Semaphore(3)` limits parallel evolution LLM calls |
