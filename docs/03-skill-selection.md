# Skill Selection

Skill selection runs at the start of every task execution. It determines which skills from the library are injected into the execution agent's system prompt for this specific task.

---

## Source Files

| File | Role |
|------|------|
| `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/skill_engine/registry.py` | LLM selection call + quality pre-filter — copy/adapt |
| `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/skill_engine/store.py` | SQLite reads for skill catalog — copy/adapt |

Key function: `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/skill_engine/registry.py:676-704` (LLM selection prompt).

---

## Two-Stage Process

### Stage 1 — Quality-Based Pre-Filter

Before calling the LLM, filter out skills that are demonstrably broken:

```python
def quality_prefilter(skills: list[SkillRecord]) -> list[SkillRecord]:
    result = []
    for skill in skills:
        # Exclude: selected 2+ times but never actually applied
        if skill.total_selections >= QUALITY_FILTER_MIN_SELECTIONS and skill.total_completions == 0:
            continue
        # Exclude: high fallback rate (selected but instructions can't be followed)
        if skill.total_applied >= QUALITY_FILTER_MIN_SELECTIONS and fallback_rate(skill) > 0.5:
            continue
        result.append(skill)
    return result
```

**Why this matters**: When a skill has a FIX evolution in `pending` state awaiting approval, the current broken version is still `active` in the DB. The quality filter prevents it from being selected while its fix is waiting for review.

Thresholds:
- `QUALITY_FILTER_MIN_SELECTIONS = 2` (minimum data before filter activates)

### Stage 2 — LLM Selection

The LLM sees the filtered catalog with quality stats and picks the final set.

**Prompt** (from `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/skill_engine/registry.py:676-704`):

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

**Default `max_skills`**: 3 (configurable).

---

## How Skills Are Formatted for the Catalog

Each entry in `{skills_catalog}` follows this format:

```
check-sql-injection__v2_e5f6g7h8 — check-sql-injection: Use whenever reviewing any PR
that touches database queries, ORM models, or raw SQL — even if the PR description does
not mention SQL injection. (success 14/18 = 78%)
```

The description field in the catalog is the `description` frontmatter from `SKILL.md`. This is why description quality matters so much — the LLM selector reads exactly this text to decide whether to pick the skill.

---

## After Selection

Selected skill IDs are passed to the orchestrator, which:
1. Loads the full `SKILL.md` content for each selected skill from the filesystem (`agent/skills/{name}/SKILL.md`)
2. Injects them into the system prompt (see `02-orchestrator.md` for prompt format)
3. Records selected skill IDs in `metadata.json` and the `runs` table

---

## Quality Metrics (Read During Selection)

The skill catalog includes live quality stats computed from the `skills` table:

| Metric            | Formula                                | What it means                            |
|-------------------|----------------------------------------|------------------------------------------|
| `applied_rate`    | `total_applied / total_selections`     | How often the agent actually uses it     |
| `completion_rate` | `total_completions / total_applied`    | Task success rate when it is followed    |
| `effective_rate`  | `total_completions / total_selections` | Overall value per selection              |
| `fallback_rate`   | `total_fallbacks / total_selections`   | Selected but not usable (instructions broken) |

Only `completions/applied` is shown to the LLM selector (the most actionable ratio). The full metrics are used by Trigger 3 for health checks.
