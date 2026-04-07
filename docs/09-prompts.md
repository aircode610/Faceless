# All Prompts Reference

This document lists all LLM prompts used by the system, where each lives, and what extensions are needed beyond the base OpenSpace templates.

---

## Overview

| # | Prompt | Source | New? |
|---|--------|--------|------|
| 1 | Post-Execution Analysis | `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/prompts/skill_engine_prompts.py` | Extend with `priority`, `pattern_key`, `feature_requests` fields |
| 2 | FIX Evolution | `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/prompts/skill_engine_prompts.py` | Copy verbatim |
| 3 | DERIVED Evolution | `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/prompts/skill_engine_prompts.py` | Copy verbatim |
| 4 | CAPTURED Evolution | `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/prompts/skill_engine_prompts.py` | Copy verbatim |
| 5 | LLM Confirmation Gate | `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/prompts/skill_engine_prompts.py` | Copy verbatim |
| 6 | Skill Selection | `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/skill_engine/registry.py:676-704` | Copy verbatim |
| 7 | MCP Selection | New | New |
| 8 | Meta-Agent Bootstrap | New | New |

**Rule**: Copy OpenSpace prompts verbatim. Do not paraphrase or rewrite them. The constitution injection (`_format_constitution_block()`) is already built into the OpenSpace templates — pass `constitution` parameter and it will be injected automatically.

---

## Prompt 1 — Post-Execution Analysis

**Location**: `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/prompts/skill_engine_prompts.py`
**Class/method**: `SkillEnginePrompts.execution_analysis()`
**Template name**: `_EXECUTION_ANALYSIS_TEMPLATE` (lines 169-360)

**Inputs**:
```
task_description, execution_status, iterations, tool_list,
skill_section, conversation_log, traj_summary,
selected_skill_ids_json, resource_info
```

**Base output** (from OpenSpace):
```
task_completed, execution_note, tool_issues, skill_judgments, evolution_suggestions
```

**Extensions needed** (append these rules to the OpenSpace prompt's output section):

```
Extended fields for each evolution_suggestion:

- "priority": one of "critical" | "high" | "medium" | "low"
  critical = security gap or blocks core function
  high     = recurring pattern or significant user-facing miss
  medium   = improvement, workaround exists
  low      = minor, edge case

- "pattern_key": "{domain}.{specific-pattern}"
  A stable, reusable identifier for recurrence tracking across runs.
  Format: lowercase, hyphens, no spaces. Two-part: domain.pattern.
  Examples: "harden.sql-injection-fstring", "workflow.missing-test-check",
            "tool.pr-diff-empty-draft", "output.no-line-citation"
  Create a new key if no existing one fits. Keep it narrow — not "harden.security".

New top-level field:

- "feature_requests": list of capability gaps where no relevant skill exists.
  Each entry:
    "capability": one sentence on what the agent was asked to do but couldn't
    "user_context": why it was needed and how the failure manifested
    "complexity": "simple" | "medium" | "complex"

  Do NOT output a feature request if a skill exists but was applied incorrectly.
  That is an evolution_suggestion of type "fix".
  Feature requests are for genuine capability gaps — task types entirely outside scope.
```

**Full output schema**:
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
      "note": "Agent followed the injection check steps and flagged a bypass."
    }
  ],
  "evolution_suggestions": [
    {
      "type": "fix",
      "target_skills": ["check-sql-injection__v2_e5f6g7h8"],
      "category": "workflow",
      "direction": "Add a step for checking raw string interpolation in f-strings.",
      "priority": "high",
      "pattern_key": "harden.sql-injection-fstring"
    }
  ],
  "feature_requests": [
    {
      "capability": "Review Terraform plan diffs for security group misconfigurations",
      "user_context": "Agent was asked to review an infra PR but had no knowledge of Terraform syntax. Task failed.",
      "complexity": "medium"
    }
  ]
}
```

---

## Prompt 2 — FIX Evolution

**Location**: `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/prompts/skill_engine_prompts.py`
**Class/method**: `SkillEnginePrompts.evolution_fix()`
**Template name**: `_EVOLUTION_FIX_TEMPLATE` (lines 376-509)

**Inputs**: `current_content`, `direction`, `failure_context`, `tool_issue_summary`, `metric_summary`, `constitution`

**Output**: `CHANGE_SUMMARY: ...` followed by:
- Format A (preferred): a patch in unified diff format
- Format B: full SKILL.md rewrite

Ending with `<EVOLUTION_COMPLETE>` or `<EVOLUTION_FAILED>`.

The constitution block is automatically injected at the top of the prompt by `_format_constitution_block(constitution)`. Pass `constitution=None` if no constitution exists.

**Copy verbatim. Do not modify.**

---

## Prompt 3 — DERIVED Evolution

**Location**: `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/prompts/skill_engine_prompts.py`
**Class/method**: `SkillEnginePrompts.evolution_derived()`
**Template name**: `_EVOLUTION_DERIVED_TEMPLATE` (lines 512-656)

**Inputs**: `parent_content`, `direction`, `execution_insights`, `metric_summary`, `constitution`

**Output**: `CHANGE_SUMMARY: ...` followed by patch or full rewrite for a **new** skill directory, ending with `<EVOLUTION_COMPLETE>` or `<EVOLUTION_FAILED>`.

**Copy verbatim. Do not modify.**

---

## Prompt 4 — CAPTURED Evolution

**Location**: `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/prompts/skill_engine_prompts.py`
**Class/method**: `SkillEnginePrompts.evolution_captured()`
**Template name**: `_EVOLUTION_CAPTURED_TEMPLATE` (lines 659-765)

**Inputs**: `direction`, `category`, `execution_highlights`, `constitution`

**Output**: `CHANGE_SUMMARY: ...` followed by a complete new `SKILL.md`, ending with `<EVOLUTION_COMPLETE>` or `<EVOLUTION_FAILED>`.

No parent exists — this is always a full new file, never a patch.

**Copy verbatim. Do not modify.**

---

## Prompt 5 — LLM Confirmation Gate

**Location**: `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/prompts/skill_engine_prompts.py`
**Class/method**: `SkillEnginePrompts.evolution_confirm()`
**Template name**: `_EVOLUTION_CONFIRM_TEMPLATE` (lines 768-829)

**Inputs**: `skill_id`, `skill_content`, `proposed_type`, `proposed_direction`, `trigger_context`, `recent_analyses`

**Output**:
```json
{"proceed": true, "reasoning": "...", "adjusted_direction": "optional refined direction"}
```

On any parse error → default to `false`. Fail safe — never proceed on ambiguous output.

Used only by Trigger 2 (tool degradation) and Trigger 3 (metric health check). Trigger 1 suggestions skip this gate (they are already LLM-generated).

**Copy verbatim. Do not modify.**

---

## Prompt 6 — Skill Selection

**Location**: `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/skill_engine/registry.py:676-704`

```
You are a skill selector for an autonomous agent.

# Task
{task}

# Available Skills
{skills_catalog}
    Format per skill: {id} — {name}: {description} (success {completions}/{applied} = {rate:.0%})

# Instructions
Step 1 — Plan: Think about how you would accomplish this task.
Step 2 — Match: Which skills directly teach workflows for the deliverables?
Step 3 — Quality check: Among matching skills, prefer higher success rates.
Step 4 — Decide: Select at most {max_skills} skills.

Return JSON:
{"brief_plan": "1-2 sentence plan", "skills": ["skill_id_1", "skill_id_2"]}
```

**Copy verbatim from registry.py. Do not modify.**

---

## Prompt 7 — MCP Selection (new)

**Location**: `/Users/amirali.iranmanesh/JB/OpenSpace/src/prompts/meta_agent_prompts.py` → `MCP_SELECTION_TEMPLATE`

Runs once at bootstrap, before constitution + skills are generated.

```
You are selecting tools for a specialized autonomous agent.

## Agent's Job
{user_description}

## Available MCPs
{mcp_list}

For each MCP, decide: does this agent need it to do its job?
Think about every step the agent will take on a typical task.

Be selective — only include MCPs the agent genuinely needs.
An agent that only reviews GitHub PRs does not need Trello or Slack.

Output JSON:
{
  "selected_mcps": ["github", "search"],
  "reasoning": "GitHub is needed to read diffs and post reviews. Search is needed to look up CVE databases. Trello and Slack are not needed for PR review."
}
```

**Output**: Written to `agent_config.json`. The selected MCPs are the only ones mounted when the execution agent runs.

---

## Prompt 8 — Meta-Agent Bootstrap (new)

**Location**: `/Users/amirali.iranmanesh/JB/OpenSpace/src/prompts/meta_agent_prompts.py` → `BOOTSTRAP_TEMPLATE`

Runs once at bootstrap, after MCP selection is confirmed.

```
You are bootstrapping a specialized autonomous agent.

## Agent's Job
{user_description}

## Tools Available to This Agent
{selected_mcps_with_descriptions}

## Your Job

1. Write a constitution.md — the agent's purpose in 2-3 sentences, plus 3-8 hard constraints
   it must never violate. These are immutable — the evolution system can never change them.

2. Write {N} initial skills. Each skill is a directory with a SKILL.md file.

SKILL.md format:
---
name: skill-name-lowercase-hyphens
description: >
  [CRITICAL] Write this as if convincing another agent to use this skill.
  State WHAT the skill does AND the SPECIFIC CONTEXTS in which to use it.
  Be explicit about triggers. Example: "Use this skill whenever reviewing any
  PR that touches database queries, ORM models, or raw SQL — even if the PR
  description does not mention SQL injection."
category: workflow | tool_guide | reference
---

# Skill Title

## Purpose
Why this skill exists and what problem it solves for the agent.

## When to Apply
Specific task contexts, file types, PR patterns, or signals that should trigger this skill.

## Instructions
Step-by-step procedures, tool usage patterns, or reference knowledge.
Explain WHY each step matters, not just what to do.
If a step requires a script, name it and describe what it does — put the script in scripts/.

3. For skills that require a reusable script or reference doc, list the additional files
   to create alongside the SKILL.md.

Output JSON:
{
  "constitution": "full constitution.md content",
  "skills": [
    {
      "name": "check-sql-injection",
      "category": "workflow",
      "content": "full SKILL.md content",
      "scripts": [
        {"filename": "scripts/check_interpolation.py", "content": "..."}
      ],
      "references": [
        {"filename": "references/owasp-injection.md", "content": "..."}
      ]
    }
  ]
}
```

**Key instructions baked into this prompt** (from Anthropic's skill-creator):
- Description must state **when** to trigger, not just what — be explicit and "pushy" about conditions
- Explain the **why** behind each instruction step
- Flag any step that requires a reusable script and put it in `scripts/`
- Keep each skill under 500 lines; use `references/` for large content

---

## Constitution Injection

All evolution prompts (2, 3, 4) inject the constitution automatically via `_format_constitution_block()` from `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/prompts/skill_engine_prompts.py`. This function prepends a block like:

```
# Constitution (Non-Negotiable Constraints)

{constitution_content}

The evolved skill must not violate any of the above constraints.
These rules override any other consideration.
```

Pass `constitution=None` if no constitution file exists — the function handles the None case gracefully.
