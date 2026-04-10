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
   1. Select MCPs (tools the agent can use)
   2. Write constitution (immutable rules)
   3. Generate initial skills
   -> agent_config.json, constitution.md, skills/, SQLite DB

        |
        v  (repeat for every task)
 ORCHESTRATOR (per-task loop)
   1. Quality-filter skills -> LLM selects relevant ones
   2. Inject constitution + skills into system prompt
   3. Run execution agent (agentic loop, max 20 iterations)
   4. Record: conversations.jsonl, traj.jsonl, metadata.json
   5. Trigger 1 — post-execution analysis (blocking)
   -> evolution suggestions, feature requests, skill counter updates

        |
        v
 EVOLUTION ENGINE
   FIX / DERIVED / CAPTURED skill improvements
   -> all land as status=pending, require human approval

        |
        v  (background, non-blocking)
 TRIGGER 2 — Tool Degradation Detection (after every run)
   Rolling window success rate < 50% → LLM confirm → FIX evolution

 TRIGGER 3 — Periodic Skill Health Check (every 3 runs)
   Rule-based diagnosis → LLM confirm → FIX or DERIVED evolution

        |
        v
 APPROVAL GATE (dashboard UI)
   Approve / Reject / Edit & Approve
   Benchmark guard before any approval
```

## How It Works

### The Self-Improvement Loop

1. **Bootstrap**: Describe what your agent should do. The meta-agent picks the right tools (MCPs), writes a constitution (hard rules), and generates initial skills (reusable instructions).

2. **Execute**: Give the agent a task. It selects relevant skills, injects them into its prompt, and runs an agentic loop with tool calling until it completes or hits the iteration limit.

3. **Analyze**: After every run, Trigger 1 reviews the full execution trace — what the agent did, which skills it followed, what went wrong — and proposes improvements.

4. **Evolve**: The evolution engine turns proposals into new skill versions:
   - **FIX** — repair a broken or outdated skill in place
   - **DERIVED** — create an enhanced version from an existing skill
   - **CAPTURED** — extract a brand-new skill from a novel pattern

5. **Approve**: Every evolved skill lands as `pending`. A human reviews the diff, approves or rejects, and only then does it go live.

6. **Background Monitoring**: Trigger 2 watches for tools that start failing. Trigger 3 periodically checks skill health metrics. Both use an LLM confirmation gate to filter false positives before proposing evolutions.

### Key Concepts

| Term | What it means |
|------|---------------|
| **Skill** | A reusable instruction file (SKILL.md) injected into the agent's prompt when relevant to a task |
| **Constitution** | Immutable rules the agent must always follow, regardless of task or skills |
| **MCP** | Model Context Protocol — external tool servers (GitHub, search) the agent can call |
| **Evolution** | A proposed change to a skill: FIX (repair), DERIVED (enhance), CAPTURED (new) |
| **Trigger** | A mechanism that detects when skills need improvement and proposes evolutions |
| **Applied Rate** | How often the agent actually followed a skill's instructions when selected |
| **Completion Rate** | Of times a skill was applied, how often did the task succeed |
| **Effective Rate** | Overall: completions / selections |
| **Fallback Rate** | Skill selected but ignored AND task failed — signals a broken skill |
| **Score** | Weighted quality score (0-100%) combining the above metrics |

## Tech Stack

| Layer | Choice |
|-------|--------|
| Agent Framework | LangGraph (StateGraph API) |
| LLM | Claude Sonnet via `langchain-anthropic` |
| Structured Output | `with_structured_output()` — no manual JSON parsing |
| MCP Tools | `langchain-mcp-adapters` with `MultiServerMCPClient` |
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

# 2. Frontend
cd frontend && npm install && npm run build && cd ..

# 3. Set your API key
export ANTHROPIC_API_KEY=your-key

# 4. Start the dashboard (serves both API and frontend)
uvicorn src.dashboard.server:app --port 7788 --reload

# 5. Visit http://localhost:7788
#    Create agent -> Run tasks -> Review evolutions
```

### Optional: MCP Tools

```bash
# GitHub MCP (requires Docker)
export GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxx
docker pull ghcr.io/github/github-mcp-server

# Search MCP (Tavily)
export TAVILY_API_KEY=tvly-xxx
```

### Optional: LangSmith Tracing

```bash
export LANGSMITH_API_KEY=lsv2_xxx
export LANGSMITH_TRACING=true
export LANGSMITH_PROJECT=faceless
```

## Dashboard

### Pages

| Page | Route | What it shows |
|------|-------|---------------|
| Dashboard | `/dashboard` | Metrics, pipeline diagram, top skills, recent runs |
| Skills Library | `/skills` | All skills with filter/sort/search, score bars |
| Skill Detail | `/skills/:id` | Quality metrics with explanations, SKILL.md content, version lineage, judgments |
| Runs | `/runs` | Execution list with status badges and skill tags |
| Run Detail | `/runs/:id` | Result (agent's final answer), Trace, Skills Used, Analysis tabs |
| Review Queue | `/review` | Priority-sorted pending evolutions with trigger source, diff viewer, approve/reject |
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
| GET | `/review/queue` | Pending evolutions (includes trigger source) |
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
  llm.py                       # Central LLM factory (model, temperature, tokens)
  meta_agent.py                # LangGraph bootstrap: MCP selection -> constitution + skills
  orchestrator.py              # LangGraph per-task loop: select -> execute -> record -> analyze -> triggers
  execution_agent.py           # LangGraph inner agent loop with tool calling
  skill_engine/
    types.py                   # Pydantic models for all data types
    store.py                   # SQLite schema + CRUD
    registry.py                # Two-stage skill selection (quality filter + LLM)
    analyzer.py                # Trigger 1: post-execution analysis
    triggers.py                # Triggers 2 & 3: tool degradation + skill health check + LLM confirmation gate
    evolver.py                 # Evolution engine: FIX/DERIVED/CAPTURED
  prompts/
    meta_agent_prompts.py      # MCP selection + bootstrap prompts
    skill_engine_prompts.py    # Skill selection + analysis + evolution + confirmation prompts
  tools/
    loader.py                  # MCP server specs + langchain-mcp-adapters loader
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
    components/                # MetricCard, DiffViewer, TraceTimeline, InfoTip, badges
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
- [x] **Orchestrator** — LangGraph graph: skill selection -> prompt assembly -> execution agent -> artifact recording -> Trigger 1 analysis -> evolution -> background triggers
- [x] **Execution Agent** — LangGraph inner loop with tool calling, conversation/trajectory recording, `<COMPLETE>` termination
- [x] **Skill Selection** — Two-stage: quality pre-filter (exclude broken skills) + LLM selection with structured output
- [x] **Trigger 1 Analysis** — Post-execution LLM analysis with skill judgments, evolution suggestions, feature requests, recurrence tracking
- [x] **Trigger 2** — Tool degradation detection (background, after every run) with LLM confirmation gate
- [x] **Trigger 3** — Periodic skill health check (background, every 3 runs) with rule-based diagnosis + LLM confirmation gate
- [x] **Evolution Engine** — FIX/DERIVED/CAPTURED LangGraph inner loop with validation, retry, diff computation, and pending skill creation
- [x] **MCP Tool Mounting** — `langchain-mcp-adapters` with `MultiServerMCPClient` connects real MCP servers (GitHub via Docker, Tavily search) as LangChain tools
- [x] **SQLite Store** — Full schema (skills, runs, judgments, evolution_suggestions, feature_requests, tool_calls, skill_tool_deps, audit_log)
- [x] **FastAPI Dashboard** — All endpoints with trigger source attribution
- [x] **React Frontend** — All pages with info tooltips, trigger badges, markdown rendering, and design tokens
- [x] **LangSmith Tracing** — Configured via environment variables

## What's Not Yet Implemented

- [ ] **Benchmark Regression Guard** — Run benchmarks before approving evolutions
- [ ] **Approval CLI** — `manage.py` commands for terminal-based review
- [ ] **Lineage Graph Visualization** — Interactive node-link graph in frontend

**Full pipeline docs:** See [docs/RUNNING.md](docs/RUNNING.md) for step-by-step instructions.

---

*"Valar Morghulis"* — All men must die.
*"Valar Dohaeris"* — All men must serve.
