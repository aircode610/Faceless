# Meta-Agent Bootstrapping

This layer runs **once**, before the agent is ever deployed.
It produces everything the agent needs to start running: which MCPs to mount, the immutable constitution, and the initial skill library.

---

## When It Runs

Triggered by the user providing a one-paragraph agent description. Never runs again after bootstrap (unless you want to re-bootstrap a new agent from scratch).

---

## Inputs

1. **Agent description** — natural language, e.g. `"Review GitHub pull requests for security issues and test coverage gaps"`
2. **Available MCP list** — the full catalog of MCPs the user has configured:

```json
[
  {"name": "github",  "description": "Read/write GitHub repos, PRs, issues, reviews"},
  {"name": "trello",  "description": "Read/write Trello boards and cards"},
  {"name": "search",  "description": "Web search via Tavily"},
  {"name": "sqlite",  "description": "Query local SQLite databases"},
  {"name": "slack",   "description": "Post messages to Slack channels"}
]
```

---

## What It Produces

```
agent/
  agent_config.json        ← selected MCPs for this agent
  constitution.md          ← immutable, never touched by evolution
  skills/
    check-sql-injection/
      SKILL.md             ← generation 0, status=active
      scripts/             ← optional: executable helpers bundled with the skill
      references/          ← optional: large reference docs
    check-auth-bypass/
      SKILL.md
    review-output-format/
      SKILL.md
```

All generation-0 skills are inserted into SQLite with `status=active`, `generation=0`, `parent_id=NULL`, `lineage_origin="BOOTSTRAP"`.

---

## Step 1 — MCP Selection

The meta-agent reads the agent description and the full MCP catalog, then selects only the MCPs this agent genuinely needs. Only selected MCPs are mounted when the execution agent runs.

**Prompt** (`/Users/amirali.iranmanesh/JB/OpenSpace/src/prompts/meta_agent_prompts.py` → `MCP_SELECTION_TEMPLATE`):

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

**Output written to `agent_config.json`**:

```json
{
  "agent_name": "pr-review-agent",
  "selected_mcps": ["github", "search"],
  "created_at": "2026-04-07T14:00:00Z"
}
```

---

## Step 2 — Constitution + Initial Skills

After MCP selection is confirmed, a second LLM call produces the constitution and all initial skills.

**Prompt** (`/Users/amirali.iranmanesh/JB/OpenSpace/src/prompts/meta_agent_prompts.py` → `BOOTSTRAP_TEMPLATE`):

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

---

## Skill Categories

| Category     | What it contains                                                          |
|--------------|---------------------------------------------------------------------------|
| `workflow`   | End-to-end multi-step procedure (e.g. "how to review a PR")              |
| `tool_guide` | How to use a specific tool correctly (e.g. "how to call the GitHub API")  |
| `reference`  | Background knowledge / best practices (e.g. "OWASP Top 10 cheat sheet")  |

---

## Skill Directory Structure (Progressive Disclosure)

Each skill is a directory. The `SKILL.md` file is always loaded when the skill is selected. Everything else is loaded on demand or bundled for the agent to invoke.

```
skill-name/
├── SKILL.md              ← always loaded when skill is selected (<500 lines ideal)
├── scripts/              ← executable helpers; agent runs them, does not rewrite them
│   └── check_fstrings.py
├── references/           ← large docs loaded only when needed
│   └── owasp-top10.md    ← include a table of contents if >300 lines
└── assets/               ← templates, examples, static files
    └── review_template.md
```

**Key rules**:
- If the agent repeatedly writes the same helper script across different task runs, the evolution engine (CAPTURED type) should detect this and bundle the script into `scripts/`.
- If a skill grows beyond 500 lines, move the heavy content to `references/` and add a table of contents.

---

## Description Quality — The Undertrigger Problem

The `description` field in `SKILL.md` frontmatter is the **primary signal** the skill selector uses. If descriptions are too vague, the skill gets under-triggered and never applied.

**Bad (what-only)**:
```
description: Checks for SQL injection vulnerabilities.
```

**Good (when + what)**:
```
description: >
  Use whenever reviewing any PR that touches database queries, ORM models,
  raw SQL strings, or query builders — even when SQL injection is not
  mentioned in the PR description. This includes Django ORM .raw(), SQLAlchemy
  text(), psycopg2 cursor.execute(), and Python f-strings in SQL context.
```

The description must read as if it is convincing another agent to pick this skill. State the specific trigger conditions explicitly — file types, method names, PR patterns, keywords in the task description.

---

## Source Files

| File | Role |
|------|------|
| `/Users/amirali.iranmanesh/JB/OpenSpace/src/prompts/meta_agent_prompts.py` | MCP selection prompt + bootstrap prompt (create new) |
| `/Users/amirali.iranmanesh/JB/OpenSpace/src/meta_agent.py` | Orchestrates the two-step bootstrap, writes agent_config.json + constitution.md, inserts skills into SQLite |

The prompts for evolution and execution are in `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/prompts/skill_engine_prompts.py` — copy verbatim, do not write new versions.
