# Self-Improving Skill-Based Agent — Project Index

This directory is the complete specification for building the prototype.
Every document is self-contained and scoped to one layer of the system.
Give individual files to your coding agent per task.

---

## System in One Paragraph

The user gives the meta-agent a description of what they want an agent to do plus a list of available MCPs.
The meta-agent selects the right MCPs, writes a constitution (immutable rules), and generates initial skills (markdown knowledge files).
Every time the execution agent runs a task, three triggers analyze the run and propose skill improvements.
Those improvements land in a `pending` state and require human approval before going live.
Over time, the agent's skill library grows and improves from real usage.

---

## End-to-End Flow

```
User Description + Available MCP List
        │
        ▼
┌──────────────────────────────────────────────────────┐
│  META-AGENT  (runs once at bootstrap)                │
│  1. Select MCPs needed for this agent                │
│  2. Write constitution.md (immutable)                │
│  3. Generate N initial skills (generation 0)         │
│  → outputs: agent_config.json, constitution.md,      │
│             skills/ in SQLite                        │
└──────────────────────────────────────────────────────┘
        │
        ▼  (repeat for every task)
┌──────────────────────────────────────────────────────┐
│  ORCHESTRATOR  (per-task loop)                       │
│  1. Quality-filter skills → LLM selects relevant     │
│  2. Inject constitution + skills into system prompt  │
│  3. Run execution agent (agentic loop, max 15 iters) │
│  4. Record: conversations.jsonl, traj.jsonl,         │
│             metadata.json                            │
│  5. Trigger 1 — post-execution analysis  [blocking]  │
│  6. Trigger 2 — tool degradation         [background]│
│  7. Trigger 3 — metric health check      [background]│
└──────────────────────────────────────────────────────┘
        │
        ▼  (triggers produce evolution suggestions)
┌──────────────────────────────────────────────────────┐
│  EVOLUTION ENGINE                                    │
│  FIX     → repair broken/outdated skill in place     │
│  DERIVED → create enhanced version in new directory  │
│  CAPTURED→ extract novel pattern as brand-new skill  │
│  → all land in DB with status=pending                │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────┐
│  APPROVAL GATE  (CLI: manage.py pending/approve/...) │
│  Skill evolutions: Approve / Reject / Edit & Approve │
│  Feature requests: Accept → CAPTURED / Defer / Wont  │
│  Benchmark guard runs before any approval            │
│  Every action written to audit_log                   │
└──────────────────────────────────────────────────────┘
```

---

## Document Index

| File | Layer | What it covers |
|---|---|---|
| [01-meta-agent.md](01-meta-agent.md) | Bootstrap | MCP selection, constitution, initial skill generation |
| [02-orchestrator.md](02-orchestrator.md) | Runtime | Execution loop, context injection, recording artifacts |
| [03-skill-selection.md](03-skill-selection.md) | Runtime | Quality filter, LLM selection prompt |
| [04-evolution-triggers.md](04-evolution-triggers.md) | Evolution | 3 triggers, confirmation gate, flows |
| [05-evolution-engine.md](05-evolution-engine.md) | Evolution | Inner loop, FIX/DERIVED/CAPTURED, principles |
| [06-skills.md](06-skills.md) | Skills | Structure, categories, quality metrics, recurrence detection |
| [07-approval-cli.md](07-approval-cli.md) | Approval | Lifecycle, reviewer UI, feature requests, benchmark, audit, rollback |
| [08-database.md](08-database.md) | Database | Full SQLite schema + table guide |
| [09-prompts.md](09-prompts.md) | Prompts | All LLM prompts with exact OpenSpace file references |
| [10-config.md](10-config.md) | Config | All thresholds and constants |
| [11-ui.md](11-ui.md) | Frontend | Showcase dashboard: pages, components, design tokens, demo script |
| [12-api.md](12-api.md) | Backend | FastAPI server: all endpoints, request/response shapes, file layout |

---

## Source References

This design draws from two external sources. Coding agents should read these when implementing the referenced components.

| Source | What to reuse |
|---|---|
| `openspace/prompts/skill_engine_prompts.py` | All 5 evolution/analysis prompts — copy verbatim |
| `openspace/skill_engine/evolver.py` | FIX/DERIVED/CAPTURED logic, inner loop, apply-with-retry |
| `openspace/skill_engine/analyzer.py` | Post-execution analysis loop, artifact loading, truncation |
| `openspace/skill_engine/registry.py` | Skill selection LLM call, quality pre-filter |
| `openspace/skill_engine/store.py` | SQLite read/write patterns |
| `openspace/skill_engine/types.py` | SkillRecord, ExecutionAnalysis, EvolutionSuggestion types |
| Anthropic skill-creator SKILL.md | Skill structure, description quality, evolution principles |

---

## File / Directory Layout (Runtime)

```
agent/
  agent_config.json          ← selected MCPs (written at bootstrap)
  constitution.md            ← immutable; versioned backups as constitution_vN.md
  skills/
    check-sql-injection/
      SKILL.md               ← always loaded when skill is selected
      .skill_id              ← sidecar: "check-sql-injection__v2_e5f6g7h8"
      scripts/               ← optional bundled executable helpers
      references/            ← optional large reference docs (TOC if >300 lines)
      assets/                ← optional templates / static files
  db/
    agent.db                 ← SQLite: all tables (see 08-database.md)
  recordings/
    run_a1b2c3d4/
      metadata.json
      conversations.jsonl
      traj.jsonl

src/
  meta_agent.py              ← bootstrap: MCP selection → constitution + skills
  orchestrator.py            ← main loop + triggers
  execution_agent.py         ← task performer
  skill_engine/
    registry.py              ← skill selection
    analyzer.py              ← Trigger 1
    evolver.py               ← FIX / DERIVED / CAPTURED
    store.py                 ← SQLite I/O
    types.py                 ← data types
  prompts/
    skill_engine_prompts.py  ← copy from OpenSpace (verbatim)
    meta_agent_prompts.py    ← MCP selection + bootstrap prompts
  approval/
    queue.py                 ← pending evolutions + feature requests
    benchmark.py             ← regression guard
    cli.py                   ← manage.py commands
  audit/
    log.py                   ← audit_log writer
  recurrence/
    tracker.py               ← pattern_key dedup + priority escalation
```
