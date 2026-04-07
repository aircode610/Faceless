# Database — SQLite Schema

All persistent state is stored in a single SQLite database at `agent/db/agent.db`.

---

## Source Files

| File | Role |
|------|------|
| `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/skill_engine/store.py` | SQLite read/write patterns — copy/adapt |
| `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/skill_engine/types.py` | SkillRecord, ExecutionAnalysis, EvolutionSuggestion types — copy/adapt |

---

## Full Schema

```sql
-- ============================================================
-- Core skill versions
-- Every version is preserved forever. Never delete rows here.
-- ============================================================
CREATE TABLE skills (
    id TEXT PRIMARY KEY,              -- "check-sql-injection__v2_e5f6g7h8"
    name TEXT NOT NULL,               -- "check-sql-injection"
    description TEXT,                 -- from SKILL.md frontmatter
    category TEXT,                    -- "workflow" | "tool_guide" | "reference"
    content TEXT NOT NULL,            -- full SKILL.md content
    status TEXT DEFAULT 'active',     -- "active" | "pending" | "superseded" | "rejected"
    generation INTEGER DEFAULT 0,
    parent_id TEXT,                   -- NULL for generation 0 (BOOTSTRAP) and CAPTURED
    lineage_origin TEXT,              -- "BOOTSTRAP" | "FIXED" | "DERIVED" | "CAPTURED" | "ROLLBACK"
    content_diff TEXT,                -- unified diff vs parent (NULL for gen 0 and CAPTURED)
    content_snapshot TEXT,            -- redundant with content, kept for archival integrity
    total_selections INTEGER DEFAULT 0,
    total_applied INTEGER DEFAULT 0,
    total_completions INTEGER DEFAULT 0,
    total_fallbacks INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,         -- ISO 8601
    last_updated TEXT NOT NULL
);

-- Index for fast lookup of active skills by name
CREATE INDEX idx_skills_name_status ON skills(name, status);

-- ============================================================
-- Multi-parent support for DERIVED merges
-- (FIX and ROLLBACK only ever have one parent, stored in skills.parent_id)
-- ============================================================
CREATE TABLE skill_parents (
    skill_id TEXT NOT NULL,
    parent_id TEXT NOT NULL,
    PRIMARY KEY (skill_id, parent_id),
    FOREIGN KEY (skill_id) REFERENCES skills(id),
    FOREIGN KEY (parent_id) REFERENCES skills(id)
);

-- ============================================================
-- Execution runs — one row per task execution
-- ============================================================
CREATE TABLE runs (
    id TEXT PRIMARY KEY,              -- "run_a1b2c3d4"
    task_description TEXT NOT NULL,
    selected_skill_ids TEXT,          -- JSON array of skill IDs
    execution_status TEXT,            -- "success" | "incomplete" | "error"
    iterations INTEGER,
    recording_dir TEXT,               -- path to recordings/run_{id}/
    llm_task_completed INTEGER,       -- 0/1 — from Trigger 1 analyzer
    created_at TEXT NOT NULL
);

-- ============================================================
-- Per-run per-skill judgments — written by Trigger 1
-- ============================================================
CREATE TABLE skill_judgments (
    run_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    skill_applied INTEGER NOT NULL,   -- 0/1: did the agent actually use this skill?
    note TEXT,                        -- analyzer's explanation
    PRIMARY KEY (run_id, skill_id),
    FOREIGN KEY (run_id) REFERENCES runs(id),
    FOREIGN KEY (skill_id) REFERENCES skills(id)
);

-- ============================================================
-- Evolution suggestions — from all three triggers
-- Recurrence is tracked per pattern_key, not per skill
-- ============================================================
CREATE TABLE evolution_suggestions (
    id TEXT PRIMARY KEY,
    run_id TEXT,                      -- NULL for Trigger 2/3 suggestions
    trigger TEXT NOT NULL,            -- "trigger1" | "trigger2" | "trigger3"
    type TEXT NOT NULL,               -- "fix" | "derived" | "captured"
    target_skill_ids TEXT,            -- JSON array; NULL for CAPTURED
    category TEXT,                    -- "workflow" | "tool_guide" | "reference"
    direction TEXT NOT NULL,          -- the evolution instruction for the LLM
    priority TEXT DEFAULT 'medium',   -- "critical" | "high" | "medium" | "low"
    pattern_key TEXT,                 -- e.g. "harden.sql-injection-fstring"
    recurrence_count INTEGER DEFAULT 1,
    run_ids TEXT,                     -- JSON array of all run_ids that triggered this pattern
    status TEXT DEFAULT 'pending_execution',
    --   "pending_execution" → waiting to be run through evolution engine
    --   "executed"          → evolution ran, resulting_skill_id populated
    --   "failed"            → evolution engine returned EVOLUTION_FAILED
    --   "skipped"           → confirmation gate rejected
    --   "wont_fix"          → manually dismissed
    resulting_skill_id TEXT,          -- populated after evolution engine succeeds
    created_at TEXT NOT NULL,
    last_seen TEXT NOT NULL           -- updated each time recurrence_count increments
);

CREATE INDEX idx_evolution_pattern_key ON evolution_suggestions(pattern_key);

-- ============================================================
-- Feature requests — capability gaps the agent cannot fill
-- ============================================================
CREATE TABLE feature_requests (
    id TEXT PRIMARY KEY,              -- "feat_20260407_b3c4"
    run_id TEXT NOT NULL,
    capability TEXT NOT NULL,         -- what the agent was asked to do but couldn't
    user_context TEXT,                -- why it was needed, how the failure manifested
    complexity TEXT,                  -- "simple" | "medium" | "complex"
    priority TEXT DEFAULT 'medium',   -- "critical" | "high" | "medium" | "low"
    recurrence_count INTEGER DEFAULT 1,
    run_ids TEXT,                     -- JSON array
    status TEXT DEFAULT 'pending',    -- "pending" | "accepted" | "deferred" | "wont_fix"
    resulting_skill_id TEXT,          -- populated when accepted → CAPTURED evolution runs
    created_at TEXT NOT NULL,
    last_seen TEXT NOT NULL
);

-- ============================================================
-- Tool quality tracking — used by Trigger 2
-- ============================================================
CREATE TABLE tool_calls (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,          -- e.g. "mcp:github:get_pr_diff"
    success INTEGER NOT NULL,         -- 0/1
    duration_ms INTEGER,
    error_message TEXT,               -- truncated to 1000 chars
    created_at TEXT NOT NULL
);

CREATE INDEX idx_tool_calls_name ON tool_calls(tool_name, created_at);

-- ============================================================
-- Skill-tool dependency map — used by Trigger 2
-- Populated at skill creation/evolution by parsing SKILL.md for tool names
-- ============================================================
CREATE TABLE skill_tool_deps (
    skill_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    PRIMARY KEY (skill_id, tool_name),
    FOREIGN KEY (skill_id) REFERENCES skills(id)
);

-- ============================================================
-- Approval audit log — every state-changing human action
-- ============================================================
CREATE TABLE audit_log (
    id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL,
    action TEXT NOT NULL,             -- "bootstrap" | "approved" | "rejected" |
                                      -- "edited_and_approved" | "rollback" | "constitution_edited"
    reviewer TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    parent_id TEXT,
    content_diff TEXT,
    benchmark_passed INTEGER,         -- 0/1
    benchmark_details TEXT,           -- JSON: {"passed": 12, "total": 12}
    note TEXT                         -- rejection reason, rollback note, etc.
);
```

---

## Table Guide

| Table | Written by | Read by |
|-------|------------|---------|
| `skills` | Meta-agent, evolution engine, rollback | Skill selector, orchestrator, approval queue |
| `skill_parents` | Evolution engine (DERIVED merges) | Rollback, lineage queries |
| `runs` | Orchestrator (after each execution) | Trigger 1, Trigger 3 |
| `skill_judgments` | Trigger 1 analyzer | Skill quality metrics, evolution prompts |
| `evolution_suggestions` | Triggers 1/2/3 | Evolution engine, approval queue, recurrence tracker |
| `feature_requests` | Trigger 1 analyzer | Approval queue (feat commands) |
| `tool_calls` | Orchestrator (from traj.jsonl) | Trigger 2 tool degradation check |
| `skill_tool_deps` | Meta-agent, evolution engine | Trigger 2 (which skills use which tools) |
| `audit_log` | Approval gate (all actions) | `manage.py audit` command |

---

## Lineage Query — Walk Skill History

```sql
-- Walk the full lineage of a skill back to generation 0
WITH RECURSIVE lineage(id, name, generation, parent_id, status, created_at) AS (
  SELECT id, name, generation, parent_id, status, created_at
  FROM skills WHERE id = :skill_id
  UNION ALL
  SELECT s.id, s.name, s.generation, s.parent_id, s.status, s.created_at
  FROM skills s JOIN lineage l ON s.id = l.parent_id
)
SELECT * FROM lineage ORDER BY generation;
```

---

## Skill Quality Metrics Query

```sql
-- Compute derived metrics for all active skills
SELECT
  id,
  name,
  total_selections,
  total_applied,
  total_completions,
  total_fallbacks,
  CAST(total_applied AS REAL) / MAX(total_selections, 1)     AS applied_rate,
  CAST(total_completions AS REAL) / MAX(total_applied, 1)    AS completion_rate,
  CAST(total_completions AS REAL) / MAX(total_selections, 1) AS effective_rate,
  CAST(total_fallbacks AS REAL) / MAX(total_selections, 1)   AS fallback_rate
FROM skills
WHERE status = 'active'
ORDER BY effective_rate DESC;
```

---

## Key Invariants

1. **Never delete rows from `skills`** — every version must be preserved for lineage, diffing, and rollback.
2. **Never mutate `content_snapshot`** — it is the immutable record of what the skill said at a given version.
3. **A skill is `active` only if it is selected-able** — `pending`, `superseded`, and `rejected` skills must never appear in the skill selector catalog.
4. **At most one `active` skill per `name`** — enforce this at write time in `store.py`.
5. **`content_diff` is always computed against `parent_id`** — if there is no parent (CAPTURED, gen-0), `content_diff` is NULL.
