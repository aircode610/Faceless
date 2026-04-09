"""
"The Many-Faced God demands precision."
Prompts for skill selection, post-execution analysis, and evolution.
"""

SKILL_SELECTION_TEMPLATE = """\
You are a skill selector for an autonomous agent.

# Task
{task}

# Available Skills
{skills_catalog}

# Instructions
Step 1 — Plan: Think about how you would accomplish this task.
Step 2 — Match: Which skills directly teach workflows for the deliverables?
Step 3 — Quality check: Among matching skills, prefer higher success rates.
Step 4 — Decide: Select at most {max_skills} skills.

Return JSON:
{{"brief_plan": "1-2 sentence plan", "skills": ["skill_id_1", "skill_id_2"]}}
"""


EXECUTION_ANALYSIS_TEMPLATE = """\
You are analyzing the execution of an autonomous agent that just completed a task.

## Task
{task_description}

## Execution Status: {execution_status}
## Iterations: {iterations}
## Tools Available: {tool_list}

## Skills That Were Selected
{skill_section}

## Conversation Log (may be truncated)
{conversation_log}

## Tool Call Timeline
{traj_summary}

## Selected Skill IDs
{selected_skill_ids_json}

## Your Analysis

Analyze the execution and produce a JSON report:

1. **task_completed**: Did the agent accomplish the stated task?
2. **execution_note**: 2-3 sentence overview of execution quality and outcome.
3. **tool_issues**: List any tool errors, timeouts, or unexpected behavior.
4. **skill_judgments**: For EACH selected skill, did the agent actually follow its instructions?
5. **evolution_suggestions**: Propose improvements to skills. Types:
   - "fix": repair a broken/outdated skill in place
   - "derived": create enhanced version as new skill
   - "captured": extract a novel pattern as brand-new skill
6. **feature_requests**: Genuine capability gaps (NOT skill quality problems).

For each evolution_suggestion include:
- "direction": the instruction to the evolution engine — WHAT to change (imperative).
  Example: "Add a step for checking raw string interpolation in f-strings."

- "reason": the justification for the change — WHY it's needed, grounded in
  concrete evidence from THIS task's conversation log and tool trace.
  State what the agent actually did (or failed to do), cite specific
  observations from the execution. This is what a human reviewer will read
  when deciding whether to approve.
  Example: "During this run the agent reviewed an f-string SQL query but
  flagged only the parameterized queries, missing the f-string interpolation
  at line 23 of the diff. Without this step, future reviews will continue
  to miss f-string injection — a common Python-specific bypass."

- "priority": "critical" | "high" | "medium" | "low"
  critical = security gap or blocks core function
  high     = recurring pattern or significant user-facing miss
  medium   = improvement, workaround exists
  low      = minor, edge case

- "pattern_key": "{{domain}}.{{specific-pattern}}"
  A stable, reusable identifier for recurrence tracking.
  Format: lowercase, hyphens, no spaces. Two-part: domain.pattern.

Output JSON:
{{
  "task_completed": true,
  "execution_note": "...",
  "tool_issues": ["..."],
  "skill_judgments": [
    {{"skill_id": "...", "skill_applied": true, "note": "..."}}
  ],
  "evolution_suggestions": [
    {{
      "type": "fix",
      "target_skills": ["..."],
      "category": "workflow",
      "direction": "WHAT to change (imperative)",
      "reason": "WHY — concrete evidence from THIS run's trace",
      "priority": "high",
      "pattern_key": "harden.sql-injection-fstring"
    }}
  ],
  "feature_requests": [
    {{
      "capability": "...",
      "user_context": "...",
      "complexity": "medium"
    }}
  ]
}}
"""


# ── Evolution Prompts ────────────────────────────────

CONSTITUTION_BLOCK = """\
# Constitution (Non-Negotiable Constraints)

{constitution}

The evolved skill must not violate any of the above constraints.
These rules override any other consideration.

---

"""

EVOLUTION_PRINCIPLES = """\
## Evolution Principles

1. **Explain the why, not just the what.** Don't write "ALWAYS check f-strings".
   Write why: because Python's f-string interpolation bypasses parameterized query protection.
   LLMs follow reasoning better than rules, and reasoning generalizes to edge cases.

2. **Keep skills lean.** Remove steps that aren't pulling their weight.
   Lean skills are faster to inject and easier to follow.

3. **Bundle repeated scripts.** If execution logs show the agent writing the same helper
   across 2+ runs, it should be in scripts/ in the skill directory.

4. **Re-check the description after any evolution.** When content changes significantly,
   the description frontmatter may become stale. Update it to accurately reflect
   the new trigger conditions.

5. **Generalize, don't overfit.** Suggestions come from a single task run.
   The fix should address the root pattern, not the specific instance.
"""


EVOLUTION_FIX_TEMPLATE = """\
{constitution_block}You are evolving a skill by fixing it in place.

## Current Skill Content
```
{current_content}
```

## What Needs Fixing
{direction}

## Failure Context
{failure_context}

## Tool Issues (if any)
{tool_issue_summary}

## Skill Quality Metrics
{metric_summary}

{principles}

## Output Instructions

1. First line: `CHANGE_SUMMARY: <one-line description of what you changed>`
2. Then output the COMPLETE updated SKILL.md content.
   - It MUST start with valid YAML frontmatter between `---` markers
   - It MUST include: name, description, category fields
   - The description MUST state WHEN to trigger, not just WHAT it does
3. End with `<EVOLUTION_COMPLETE>` on its own line.

If you determine the skill cannot be meaningfully fixed, output:
`<EVOLUTION_FAILED>` with a brief explanation.
"""


EVOLUTION_DERIVED_TEMPLATE = """\
{constitution_block}You are creating an enhanced version of a skill as a new skill.

## Parent Skill Content
```
{parent_content}
```

## Enhancement Direction
{direction}

## Execution Insights
{execution_insights}

## Skill Quality Metrics
{metric_summary}

{principles}

## Output Instructions

1. First line: `CHANGE_SUMMARY: <one-line description of what the new skill adds>`
2. Then output the COMPLETE new SKILL.md content.
   - It MUST start with valid YAML frontmatter between `---` markers
   - It MUST include: name, description, category fields
   - The name should reflect the enhancement (e.g., original-enhanced, original-v2)
   - The description MUST state WHEN to trigger, not just WHAT it does
3. End with `<EVOLUTION_COMPLETE>` on its own line.

If you determine the enhancement is not worthwhile, output:
`<EVOLUTION_FAILED>` with a brief explanation.
"""


EVOLUTION_CAPTURED_TEMPLATE = """\
{constitution_block}You are creating a brand-new skill from a pattern discovered during execution.

## What Was Discovered
{direction}

## Skill Category
{category}

## Execution Highlights
{execution_highlights}

{principles}

## Output Instructions

1. First line: `CHANGE_SUMMARY: <one-line description of the new skill>`
2. Then output the COMPLETE SKILL.md content for this new skill.
   - It MUST start with valid YAML frontmatter between `---` markers
   - It MUST include: name, description, category fields
   - The name should be descriptive and lowercase-hyphenated
   - The description MUST state WHEN to trigger, not just WHAT it does
   - Include ## Purpose, ## When to Apply, ## Instructions sections
3. End with `<EVOLUTION_COMPLETE>` on its own line.

If you determine this pattern is not worth capturing as a skill, output:
`<EVOLUTION_FAILED>` with a brief explanation.
"""


EVOLUTION_CONFIRM_TEMPLATE = """\
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
{{"proceed": true, "reasoning": "...", "adjusted_direction": "optional refined direction"}}
"""
