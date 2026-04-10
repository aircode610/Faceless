# Faceless — Project Guide

## What is this?

Faceless is a self-improving skill-based agent framework built on LangGraph + Claude Sonnet. The agent bootstraps from a description, executes tasks with MCP tools, analyzes its own performance, and evolves its skill library — with human-in-the-loop approval for all changes.

Game of Thrones (Faceless Men) themed. Docstrings and UI use GoT quotes.

## How to run

```bash
# Backend + frontend (production)
source .venv/bin/activate
cd frontend && npm run build && cd ..
uvicorn src.dashboard.server:app --port 7788 --reload

# Frontend dev (hot reload)
cd frontend && npm run dev   # localhost:5173, proxies API to :7788
```

Required env vars: `ANTHROPIC_API_KEY`. Optional: `GITHUB_PERSONAL_ACCESS_TOKEN`, `TAVILY_API_KEY`, `LANGSMITH_API_KEY`.

## Architecture Overview

### Pipeline (per task)

```
init_run → select_skills → build_prompt → execute_task → record_artifacts
  → trigger1_analysis → evolution → dispatch_triggers → END
```

All orchestrated via a LangGraph `StateGraph` in `src/orchestrator.py`.

### Key modules

| File | What it does |
|------|-------------|
| `src/meta_agent.py` | One-time bootstrap: pick MCPs, write constitution, generate initial skills |
| `src/orchestrator.py` | Per-task LangGraph pipeline (the main loop) |
| `src/execution_agent.py` | Inner agentic loop: LLM + tool calling until `<COMPLETE>` or max iterations |
| `src/skill_engine/analyzer.py` | Trigger 1: post-execution LLM analysis (blocking) |
| `src/skill_engine/triggers.py` | Triggers 2 & 3: tool degradation + health check (background threads) |
| `src/skill_engine/evolver.py` | Evolution engine: FIX/DERIVED/CAPTURED via LangGraph inner loop |
| `src/skill_engine/store.py` | SQLite CRUD for everything |
| `src/skill_engine/registry.py` | Two-stage skill selection (quality filter + LLM) |
| `src/skill_engine/types.py` | All Pydantic models |
| `src/prompts/skill_engine_prompts.py` | All LLM prompt templates |
| `src/tools/loader.py` | MCP server specs + `MultiServerMCPClient` loader |
| `src/config.py` | All thresholds and magic numbers |
| `src/llm.py` | Central LLM factory (`get_llm()`) |

### Three Evolution Triggers

| Trigger | When | How |
|---------|------|-----|
| **T1** (Post-Execution) | After every run, blocking | LLM analyzes full trace → suggests FIX/DERIVED/CAPTURED |
| **T2** (Tool Degradation) | After every run, background | Rolling window success rate < 50% → LLM confirms → FIX |
| **T3** (Health Check) | Every 3 runs, background | Rule-based metric diagnosis → LLM confirms → FIX or DERIVED |

T2 and T3 use an LLM confirmation gate (`EVOLUTION_CONFIRM_TEMPLATE`) to filter false positives. They run as daemon threads via `dispatch_background_triggers()`.

### Anti-loop mechanisms

- T1: bounded by execution (fires once per task)
- T2: `_addressed_degradations` dict prevents re-processing same tool+skill combo; clears when tool recovers
- T3: new skills start at `total_selections=0`, need 3 runs before evaluation
- All: evolved skills land as `status=pending`, need human approval

## Patterns to follow

- **LLM calls**: Always use `get_llm()` from `src/llm.py`. Use `llm.with_structured_output(PydanticModel)` for structured responses.
- **Store lifecycle**: `store = SkillStore(DB_PATH)` in a try/finally with `store.close()`.
- **State machines**: Use LangGraph `StateGraph` with `TypedDict` state, named nodes, and conditional edges.
- **Skill IDs**: `{name}__v{generation+1}_{8-char-uuid}` via `store.make_skill_id()`.
- **Truncation**: Use `_truncate(text, max_chars)` before passing content to LLM prompts.
- **Background work**: `threading.Thread(daemon=True)` for non-blocking triggers.
- **Config**: All thresholds live in `src/config.py`. Import from there, never hardcode.

## Frontend

- React + TypeScript + Vite + Tailwind CSS v4
- Tailwind typography plugin (`@tailwindcss/typography`) for markdown rendering
- Components: `InfoTip` (hover tooltips), `TriggerBadge`, `EvolutionTypeBadge`, `PriorityBadge`
- API client in `frontend/src/api/client.ts` (Axios, base URL `/api/v1`)
- Build: `cd frontend && npm run build` → outputs to `frontend/dist/` → served by FastAPI

## Database

SQLite at `agent/db/agent.db`. Tables: `skills`, `skill_parents`, `runs`, `skill_judgments`, `evolution_suggestions`, `feature_requests`, `tool_calls`, `skill_tool_deps`, `audit_log`. Schema auto-created by `SkillStore._init_schema()`.

## MCP Servers

Defined in `src/tools/loader.py` → `MCP_SERVER_SPECS`:
- **github**: `docker run ghcr.io/github/github-mcp-server` (needs `GITHUB_PERSONAL_ACCESS_TOKEN`)
- **search**: `npx tavily-mcp@latest` (needs `TAVILY_API_KEY`)

Tool deps tracked in `skill_tool_deps` table, populated from execution traces and skill content analysis.
