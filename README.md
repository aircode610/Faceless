# Faceless

> *"A man has no name."* — Jaqen H'ghar

A self-improving skill-based agent framework. Faceless agents bootstrap themselves from a description, learn skills, execute tasks, analyze their own performance, and evolve their skill library over time — all with human-in-the-loop approval.

---

## Architecture

```
User Description + Available MCPs
        |
        v
 META-AGENT (runs once)
   1. Select MCPs
   2. Write constitution (immutable rules)
   3. Generate initial skills
   -> agent_config.json, constitution.md, skills/, SQLite DB

        |
        v  (repeat for every task)
 ORCHESTRATOR (per-task loop)
   1. Quality-filter skills -> LLM selects relevant ones
   2. Inject constitution + skills into system prompt
   3. Run execution agent (agentic loop, max 15 iterations)
   4. Record: conversations.jsonl, traj.jsonl, metadata.json
   5. Trigger 1 — post-execution analysis (blocking)
   -> evolution suggestions, feature requests, skill counter updates

        |
        v
 EVOLUTION ENGINE (not yet implemented)
   FIX / DERIVED / CAPTURED skill improvements
   -> all land as status=pending, require human approval

        |
        v
 APPROVAL GATE (dashboard UI)
   Approve / Reject / Edit & Approve
   Benchmark guard before any approval
```

## Tech Stack

| Layer | Choice |
|-------|--------|
| Agent Framework | LangGraph (StateGraph API) |
| LLM | Claude Sonnet via `langchain-anthropic` |
| Structured Output | `with_structured_output()` — no manual JSON parsing |
| Database | SQLite (single file at `agent/db/agent.db`) |
| Backend | FastAPI on port 7788 |
| Frontend | React + TypeScript + Vite + Tailwind CSS |
| Tracing | LangSmith (set `LANGSMITH_API_KEY` + `LANGSMITH_TRACING=true`) |

## Quick Start

```bash
# 1. Clone and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. Set your API key
export ANTHROPIC_API_KEY=your-key

# 3. Bootstrap an agent
python main.py bootstrap -d "Review GitHub PRs for security issues and test coverage gaps"

# 4. Run a task
python main.py run -t "Review this code for SQL injection: cursor.execute(f'SELECT * FROM users WHERE id={user_id}')"

# 5. Check status
python main.py status
```

## Dashboard

```bash
# Start the API server (serves both API and built frontend)
uvicorn src.dashboard.server:app --port 7788
# Visit http://localhost:7788

# Or for development with hot reload:
cd frontend && npm install && npm run dev
# Visit http://localhost:5173 (proxies API to :7788)
```

### Pages

| Page | Route | What it shows |
|------|-------|---------------|
| Dashboard | `/dashboard` | Metrics, pipeline diagram, top skills, recent runs |
| Skills Library | `/skills` | All skills with filter/sort/search, score bars |
| Skill Detail | `/skills/:id` | Quality metrics, SKILL.md content, version lineage, judgments |
| Runs | `/runs` | Execution list with status badges and skill tags |
| Run Detail | `/runs/:id` | Timeline, Skills Used, Analysis tabs |
| Review Queue | `/review` | Priority-sorted pending evolutions, diff viewer, approve/reject |
| Constitution | `/constitution` | Rendered markdown, inline editor, version history |

## API Endpoints

All routes prefixed with `/api/v1`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/overview` | Dashboard summary stats |
| GET | `/skills` | List skills (filterable, sortable) |
| GET | `/skills/:id` | Skill detail with lineage |
| GET | `/skills/:id/lineage` | Node-link lineage graph data |
| POST | `/skills/:id/rollback` | Rollback to a previous version |
| GET | `/review/queue` | Pending evolutions |
| GET | `/review/:id` | Evolution detail with diff |
| POST | `/review/:id/approve` | Approve (with optional edited content) |
| POST | `/review/:id/reject` | Reject with reason |
| GET | `/review/features` | Feature requests |
| POST | `/review/features/:id/accept` | Accept feature request |
| POST | `/review/features/:id/defer` | Defer feature request |
| POST | `/review/features/:id/dismiss` | Dismiss feature request |
| GET | `/runs` | List runs (filterable) |
| GET | `/runs/:id` | Run detail with conversation, trajectory, judgments |
| GET | `/constitution` | Current constitution |
| PUT | `/constitution` | Update constitution |
| GET | `/constitution/history` | Version history |
| GET | `/audit` | Audit log (filterable) |

## Project Structure

```
src/
  config.py                    # All thresholds and constants
  meta_agent.py                # LangGraph bootstrap: MCP selection -> constitution + skills
  orchestrator.py              # LangGraph per-task loop: select -> execute -> record -> analyze
  execution_agent.py           # LangGraph inner agent loop with tool calling
  skill_engine/
    types.py                   # Pydantic models for all data types
    store.py                   # SQLite schema + CRUD
    registry.py                # Two-stage skill selection (quality filter + LLM)
    analyzer.py                # Trigger 1: post-execution analysis
    evolver.py                 # Evolution engine: FIX/DERIVED/CAPTURED
  prompts/
    meta_agent_prompts.py      # MCP selection + bootstrap prompts
    skill_engine_prompts.py    # Skill selection + analysis + evolution prompts
  dashboard/
    server.py                  # FastAPI app with SPA fallback
    models.py                  # Pydantic request/response models
    serializers.py             # DB record -> API shape helpers
    dependencies.py            # FastAPI dependency injection
    routes/
      overview.py              # GET /overview
      skills.py                # Skills CRUD + lineage + rollback
      review.py                # Review queue + approve/reject + features
      runs.py                  # Runs list + detail
      constitution.py          # Constitution CRUD + history
      audit.py                 # Audit log

frontend/
  src/
    api/                       # Axios client + typed API functions
    components/                # MetricCard, DiffViewer, TraceTimeline, badges
    layouts/MainLayout.tsx     # Nav bar with live review count badge
    pages/                     # All 7 pages
    utils/                     # diffParser, format helpers

agent/                         # Generated at bootstrap (gitignored)
  agent_config.json
  constitution.md
  skills/
  db/agent.db

recordings/                    # Generated per task run (gitignored)
  run_{id}/
    conversations.jsonl
    traj.jsonl
    metadata.json
```

## What's Implemented

- [x] **Meta-Agent** — LangGraph graph: MCP selection -> constitution + initial skills generation -> persist to disk + SQLite
- [x] **Orchestrator** — LangGraph graph: skill selection -> prompt assembly -> execution agent -> artifact recording -> Trigger 1 analysis -> evolution
- [x] **Execution Agent** — LangGraph inner loop with tool calling, conversation/trajectory recording, `<COMPLETE>` termination
- [x] **Skill Selection** — Two-stage: quality pre-filter (exclude broken skills) + LLM selection with structured output
- [x] **Trigger 1 Analysis** — Post-execution LLM analysis with skill judgments, evolution suggestions, feature requests, recurrence tracking
- [x] **Evolution Engine** — FIX/DERIVED/CAPTURED LangGraph inner loop with validation, retry, diff computation, and pending skill creation
- [x] **MCP Tool Mounting** — `langchain-mcp-adapters` with `MultiServerMCPClient` connects real MCP servers (github, search) as LangChain tools based on agent config
- [x] **SQLite Store** — Full schema from spec (skills, runs, judgments, evolution_suggestions, feature_requests, tool_calls, audit_log)
- [x] **FastAPI Dashboard** — All endpoints from the API spec
- [x] **React Frontend** — All pages from the UI spec with design tokens
- [x] **LangSmith Tracing** — Configured via environment variables

**Full pipeline docs:** See [docs/RUNNING.md](docs/RUNNING.md) for step-by-step instructions.

## What's Not Yet Implemented

- [ ] **Trigger 2** — Tool degradation detection (background)
- [ ] **Trigger 3** — Periodic skill health check (background, every 5 runs)
- [ ] **LLM Confirmation Gate** — For Triggers 2 & 3
- [ ] **Benchmark Regression Guard** — Run benchmarks before approving evolutions
- [ ] **Approval CLI** — `manage.py` commands for terminal-based review
- [ ] **Lineage Graph Visualization** — Interactive node-link graph in frontend

---

*"Valar Morghulis"* — All men must die.
*"Valar Dohaeris"* — All men must serve.
