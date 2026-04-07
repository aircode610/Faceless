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
You are bootstrapping a specialized autonomous agent.

## Agent's Job
{user_description}

## Tools Available to This Agent
{selected_mcps_with_descriptions}

## Your Job

1. Write a constitution.md — the agent's purpose in 2-3 sentences, plus 3-8 hard constraints
   it must never violate. These are immutable — the evolution system can never change them.

2. Write {num_skills} initial skills. Each skill is a directory with a SKILL.md file.

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
{{
  "constitution": "full constitution.md content",
  "skills": [
    {{
      "name": "check-sql-injection",
      "category": "workflow",
      "content": "full SKILL.md content",
      "scripts": [
        {{"filename": "scripts/check_interpolation.py", "content": "..."}}
      ],
      "references": [
        {{"filename": "references/owasp-injection.md", "content": "..."}}
      ]
    }}
  ]
}}
"""
