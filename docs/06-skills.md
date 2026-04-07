# Skills — Structure, Categories, Quality Metrics

Skills are the agent's learned knowledge. Each skill is a directory containing a `SKILL.md` file and optional supporting files. Skills are selected per-task, injected into the execution agent's system prompt, and improved over time through the evolution engine.

---

## Skill Directory Structure

```
skill-name/
├── SKILL.md              ← always loaded when skill is selected
├── .skill_id             ← sidecar file containing the skill's DB ID
├── scripts/              ← optional: executable helpers bundled with the skill
│   └── check_fstrings.py
├── references/           ← optional: large docs loaded only when needed
│   └── owasp-top10.md    ← include a table of contents if >300 lines
└── assets/               ← optional: templates, examples, static files
    └── review_template.md
```

The `.skill_id` sidecar contains the canonical skill ID (e.g., `check-sql-injection__v2_e5f6g7h8`). This ties the filesystem directory to the SQLite record.

---

## SKILL.md Format

```markdown
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
If a step requires a script, name it and describe what it does.
```

The `description` frontmatter is the only text the skill selector LLM sees during selection — the full `SKILL.md` is only loaded after the skill is selected. **Description quality is the most impactful single thing you can get right.**

---

## Skill Categories

| Category     | What it contains                                                          |
|--------------|---------------------------------------------------------------------------|
| `workflow`   | End-to-end multi-step procedure (e.g. "how to review a PR for SQL risks") |
| `tool_guide` | How to use a specific tool correctly (e.g. "how to call the GitHub API")  |
| `reference`  | Background knowledge / best practices (e.g. "OWASP injection cheat sheet")|

---

## The Undertrigger Problem

The most common skill quality failure: a description that says **what** the skill does but not **when** to trigger it. The LLM selector cannot reason about when to use a skill if the description doesn't tell it.

**Under-triggered description** (bad):
```
description: Checks for SQL injection vulnerabilities.
```

**Correctly triggered description** (good):
```
description: >
  Use whenever reviewing any PR that touches database queries, ORM models,
  raw SQL strings, or query builders — even when SQL injection is not
  mentioned in the PR description. This includes Django ORM .raw(),
  SQLAlchemy text(), psycopg2 cursor.execute(), and f-strings in SQL context.
```

The evolution engine re-checks descriptions after any FIX or DERIVED evolution (see `05-evolution-engine.md`, Principle 4).

---

## Quality Counters (Updated per Execution)

Each skill has four counters updated atomically after every Trigger 1 analysis:

```sql
UPDATE skills SET
  total_selections  = total_selections + 1,
  total_applied     = total_applied + ?,       -- 1 if skill_applied else 0
  total_completions = total_completions + ?,   -- 1 if applied AND task_completed else 0
  total_fallbacks   = total_fallbacks + ?,     -- 1 if NOT applied AND NOT completed else 0
  last_updated      = ?
WHERE id = ?
```

**`skill_applied`** is set by the analyzer LLM's judgment: did the agent actually follow this skill's instructions during the task?

**`total_completions`** increments only when the skill was applied AND the overall task was completed successfully.

**`total_fallbacks`** increments when the skill was NOT applied AND the task was NOT completed — the skill was selected but the agent fell back to improvising without it (a signal the instructions may be broken or irrelevant).

---

## Derived Metrics

| Metric            | Formula                                | Meaning                                            |
|-------------------|----------------------------------------|----------------------------------------------------|
| `applied_rate`    | `total_applied / total_selections`     | How often the agent actually follows this skill    |
| `completion_rate` | `total_completions / total_applied`    | Task success rate when the skill is followed       |
| `effective_rate`  | `total_completions / total_selections` | Overall value delivered per selection              |
| `fallback_rate`   | `total_fallbacks / total_selections`   | Selected but unable to apply (instructions broken) |

These metrics drive:
- **Quality pre-filter** (Stage 1 of skill selection): excludes demonstrably broken skills
- **Trigger 3 health check**: flags skills for FIX or DERIVED evolution
- **LLM selector display**: shows `completions/applied` ratio next to each skill

---

## Skill Lifecycle States

```
bootstrap    → active
evolution    → pending → approved → active
                      → rejected   (version preserved forever, never active)
rollback     → creates new active version from old content
```

Only `active` skills are selectable for task execution.
`pending` skills are visible in the approval queue only.
`superseded` skills are archived — they remain in SQLite for lineage queries but are not used.

---

## Skill ID Format

```
{skill-name}__v{generation}_{8-char-uuid}

check-sql-injection__v1_a1b2c3d4    ← generation 0 (bootstrap)
check-sql-injection__v2_e5f6g7h8    ← after first evolution (approved)
check-sql-injection__v3_ab12cd34    ← after second evolution
```

---

## Example Skill (PR Review Agent)

```markdown
---
name: check-sql-injection
description: >
  Use whenever reviewing any PR that touches database queries, ORM models,
  raw SQL strings, or query builder calls — even if the PR description does not
  mention SQL injection. Applies to Django ORM, SQLAlchemy, psycopg2, raw cursor
  usage, and f-string formatting in SQL contexts.
category: workflow
---

# SQL Injection Check

## Purpose
Catch SQL injection vulnerabilities before they reach production. This is the
most common critical vulnerability in backend PRs touching database layers.

## When to Apply
- Any diff containing: `.raw(`, `cursor.execute(`, `text(`, `query =`, `WHERE`
- Any file in: `models/`, `views/`, `repositories/`, `queries/`
- Any PR description mentioning: "database", "query", "migration", "SQL"

## Instructions

1. **Scan the diff for string interpolation in SQL context**
   Why: Python's f-string and %-formatting bypass parameterized query protection —
   the DB driver sees the final string, not the template.
   Look for: `f"SELECT ... {var}"`, `"SELECT ... " + var`, `"SELECT ... %s" % var`

2. **Check for ORM raw query usage**
   Why: ORM raw() and text() calls opt out of automatic escaping.
   Look for: `.raw(`, `text(`, `cursor.execute(`, `connection.execute(`

3. **Run the f-string scanner**
   Execute: `python scripts/check_fstrings.py {changed_files}`
   This script reports all f-strings where a variable is interpolated inside
   a string that contains SQL keywords (SELECT, INSERT, UPDATE, DELETE, WHERE).

4. **Flag any finding with the specific line number and a remediation suggestion**
   Good comment: "Line 47: `f"SELECT * FROM users WHERE id={user_id}"` — use
   parameterized query: `cursor.execute("SELECT * FROM users WHERE id=%s", [user_id])`"
```
