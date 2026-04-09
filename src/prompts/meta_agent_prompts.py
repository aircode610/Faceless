"""
"The price is paid. The name is given."
Prompts for the meta-agent bootstrap sequence.
"""

MCP_SELECTION_TEMPLATE = """\
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
{{
  "selected_mcps": ["github", "search"],
  "reasoning": "GitHub is needed to read diffs and post reviews. Search is needed to look up CVE databases. Trello and Slack are not needed for PR review."
}}
"""


BOOTSTRAP_TEMPLATE = """\
You are bootstrapping a specialized autonomous agent. Be concise — shorter skills are better.

## Agent's Job
{user_description}

## Tools Available to This Agent
{selected_mcps_with_descriptions}

## Your Job

1. **constitution**: a short markdown document (≤ 800 chars) with:
   - 2-3 sentences describing the agent's purpose
   - 3-5 hard constraints it must never violate

2. **skills**: exactly {num_skills} focused skills. Keep each SKILL.md ≤ 1500 chars.

Each skill must be a single SKILL.md string formatted like this:

---
name: skill-name-lowercase-hyphens
description: >
  [CRITICAL] Convince another agent to pick this skill. State WHAT it does
  AND the SPECIFIC CONTEXTS that should trigger it. Be explicit about triggers
  (file types, patterns, keywords).
category: workflow
---

# Skill Title

## Purpose
Why this skill exists (1-2 sentences).

## When to Apply
Specific triggers — file types, patterns, keywords.

## Instructions
3-6 numbered steps. Explain the WHY briefly where non-obvious.

Category must be one of: workflow | tool_guide | reference.

Important: output ONLY the three fields (name, category, content) per skill.
Do NOT include any scripts or references arrays — those are added later
through the evolution system. Keep it lean.
"""
