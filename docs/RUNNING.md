# Running the Faceless Pipeline End-to-End

> *"Valar Dohaeris"* — All men must serve. Here's how.

---

## Prerequisites

```bash
# Python 3.11+ with venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Node.js 18+ (for frontend)
cd frontend && npm install && npm run build && cd ..

# Required
export ANTHROPIC_API_KEY=your-key

# Optional — LangSmith tracing
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=your-langsmith-key
export LANGSMITH_PROJECT=faceless

# Optional — MCP tools (only needed for the MCPs you select)
# Node.js + npx must be installed (brew install node)
export GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxx  # for github MCP
export TAVILY_API_KEY=tvly_xxx               # for search MCP
```

## MCP Tools

Faceless uses [`langchain-mcp-adapters`](https://github.com/langchain-ai/langchain-mcp-adapters)
to mount real MCP servers as LangChain tools for the execution agent.

Currently wired up:

| MCP name | Backing server | Required env var |
|----------|---------------|------------------|
| `github` | `@modelcontextprotocol/server-github` (npx stdio) | `GITHUB_PERSONAL_ACCESS_TOKEN` |
| `search` | `tavily-mcp` (npx stdio) | `TAVILY_API_KEY` |

If the agent was bootstrapped with an MCP selected but the corresponding env
var is missing at run time, that MCP is silently skipped — the task still runs,
just without those tools.

Other MCPs in the catalog (trello, slack, sqlite, filesystem, terminal) are
accepted during bootstrap but don't have a real server bound yet — they'll
also be skipped at run time.

To add a new MCP, edit `src/tools/loader.py` and add an entry to
`MCP_SERVER_SPECS` with the command, args, and required env vars.

---

## Two Ways to Use Faceless

### Option A: Web Dashboard (Recommended)

Start the server and do everything from the browser:

```bash
uvicorn src.dashboard.server:app --port 7788
# Visit http://localhost:7788
```

For frontend development with hot reload:
```bash
uvicorn src.dashboard.server:app --port 7788 &
cd frontend && npm run dev
# Visit http://localhost:5173
```

### Option B: CLI

```bash
python main.py bootstrap -d "your agent description"
python main.py run -t "your task"
python main.py status
```

Both methods use the same backend — the dashboard and CLI share the same agent, DB, and artifacts.

---

## The Pipeline — Step by Step

### Step 1: Create Your Agent

The meta-agent runs **once** to create the agent's identity: which tools it uses,
what rules it follows, and what skills it starts with.

#### Via Dashboard

1. Open `http://localhost:7788` — if no agent exists, the dashboard shows a welcome
   screen with a **Create Your Agent** button
2. Click **Create Agent** (or visit `/create` directly)
3. Write your agent description (e.g., "Review GitHub PRs for security issues")
4. Toggle which MCPs (tools) should be available — the LLM will pick only the ones it needs
5. Click **Begin the Ritual**
6. Watch the step-by-step progress as the LLM selects MCPs, generates a constitution,
   and creates initial skills
7. When done, click **Go to Dashboard** or **Run a Task**

#### Via CLI

```bash
python main.py bootstrap \
  -d "Review GitHub pull requests for security issues and test coverage gaps"
```

**What happens:**
1. LLM selects MCPs from the catalog (e.g., picks `github`, `filesystem`, `terminal`)
2. LLM generates a constitution (immutable rules) and 5 initial skills
3. Everything is written to `agent/` directory and `agent/db/agent.db`

**Custom MCPs (CLI only):** Create a JSON file and pass it:
```bash
python main.py bootstrap -d "your agent description" -m path/to/my-mcps.json
```

MCP JSON format:
```json
[
  {"name": "github", "description": "Read/write GitHub repos, PRs, issues"},
  {"name": "jira", "description": "Read/write Jira tickets"}
]
```

**Outputs:**
```
agent/
  agent_config.json          # Selected MCPs + agent name
  constitution.md            # Immutable rules (never touched by evolution)
  skills/
    sql-injection-detection/
      SKILL.md               # Skill content
      .skill_id              # DB identifier
    test-coverage-analysis/
      SKILL.md
    ...
  db/
    agent.db                 # SQLite — all state
```

---

### Step 2: Run a Task

The orchestrator runs the full per-task loop: skill selection, execution,
recording, analysis, and evolution.

#### Via Dashboard

1. Click **Run Task** in the nav bar (or the button on the dashboard)
2. Type your task in the textarea — or click one of the example buttons to try a preset
3. Click **Execute Task**
4. Watch real-time step progress:
   - **Selecting skills** — quality filter + LLM picks relevant skills
   - **Executing task** — agent runs with constitution + skills injected
   - **Recording artifacts** — conversation, tool trace, metadata saved
   - **Analyzing execution** — LLM reviews what happened (Trigger 1)
   - **Running evolutions** — FIX/DERIVED/CAPTURED suggestions processed
5. When done, see the results:
   - Task completion status
   - Stats: skills used, suggestions, evolutions, feature requests
   - Evolution details with success/failure for each
6. Click **View Run Details** to see the full execution trace, or
   **Review Evolutions** to approve/reject pending skill changes

#### Via CLI

```bash
python main.py run \
  -t "Review this Python code for SQL injection: cursor.execute(f'SELECT * FROM users WHERE id={user_id}')"
```

**What happens (6 steps):**

1. **Skill Selection** — Quality pre-filter removes broken skills, then LLM picks
   the most relevant skills for this task (max 3)

2. **Prompt Assembly** — Constitution + selected skill contents are injected into
   the execution agent's system prompt

3. **Execution** — The agent runs in a tool-calling loop (max 15 iterations),
   recording every conversation turn and tool call

4. **Recording** — Three artifacts are written to `recordings/run_{id}/`:
   - `conversations.jsonl` — full LLM conversation
   - `traj.jsonl` — tool call trace with timing
   - `metadata.json` — task, skills, status, iterations

5. **Trigger 1 Analysis** — An LLM analyzes the execution:
   - Did the task succeed?
   - Were the selected skills actually followed?
   - What should be improved? (evolution suggestions)
   - Are there capability gaps? (feature requests)
   - Updates skill quality counters in the DB

6. **Evolution Engine** — Processes all pending evolution suggestions:
   - **FIX**: Repairs a broken/outdated skill in place
   - **DERIVED**: Creates an enhanced version as a new skill
   - **CAPTURED**: Extracts a novel pattern as a brand-new skill
   - All evolved skills land as `status=pending` — they need human approval

**CLI output example:**
```
✅ Task complete. Run ID: run_5370798b
  📁 Recording: recordings/run_5370798b/
  ✅ Task completed: True
  📝 Agent identified the SQL injection vulnerability...

  🔄 Evolution suggestions (2):
    → [medium] fix: Remove unavailable script reference...
    → [high] derived: Add Python f-string specific patterns...

  🧬 Evolution engine ran (2 suggestions):
    ✅ FIX: Replaced unavailable script reference...
       → pending approval: sql-injection-detection__v2_f922ccad
    ✅ DERIVED: Enhanced SQL injection detection...
       → pending approval: sql-injection-detection-enhanced__v2_4443a4f0

  🏛️  2 evolution(s) await review at /review
```

---

### Step 3: Review & Approve

After tasks run and produce evolution suggestions, a human reviews them.

1. Go to `/review` in the dashboard
2. The left panel shows pending evolutions, sorted by priority (critical → low)
3. Click an item to see:
   - The direction (why this evolution was suggested)
   - The diff viewer (what changed vs. the parent skill)
   - Recurrence count (how many times this pattern was seen)
4. Click **Approve** (green) or **Reject** (red, with reason)
5. On approval: old skill → superseded, new skill → active
6. On rejection: old skill stays active, new skill marked rejected
7. Below evolutions: **Feature Requests** — capability gaps the agent can't fill.
   Accept, defer, or dismiss them.

---

### Step 4: Run More Tasks — Watch It Improve

Each task run:
- Uses the **latest active skills** (including newly approved ones)
- Produces new analysis and evolution suggestions
- Skills that get applied successfully build up quality scores
- Recurring patterns get auto-escalated in priority

Run several tasks from the dashboard to see the improvement loop:

```
"Check this Flask endpoint for XSS: return render_template_string(request.args['name'])"
"Review this code for hardcoded credentials: db_password = 'admin123'"
"Analyze test coverage for this PR that adds a new API endpoint"
"Review this Node.js code for path traversal: fs.readFile(req.query.path)"
```

Check agent status any time: `python main.py status` or visit `/dashboard`.

---

## Dashboard Pages

| Page | URL | What it shows |
|------|-----|---------------|
| Dashboard | `/dashboard` | Metrics, pipeline diagram, top skills, recent runs. Welcome screen + create CTA when no agent exists. |
| **Create Agent** | `/create` | Agent description form, MCP toggle list, live bootstrap progress with step tracking |
| **Run Task** | `/run` | Task input with examples, live execution progress, results with evolution details |
| Skills Library | `/skills` | All skills with filter/sort/search, score bars |
| Skill Detail | `/skills/:id` | Quality metrics, SKILL.md content, version lineage, judgments |
| Runs | `/runs` | Execution list with status badges and skill tags |
| Run Detail | `/runs/:id` | Timeline, Skills Used, Analysis tabs |
| Review Queue | `/review` | Priority-sorted pending evolutions, diff viewer, approve/reject, feature requests |
| Constitution | `/constitution` | Rendered markdown, inline editor, version history |

---

## API Endpoints for Agent Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/agent/status` | Check if agent is bootstrapped, get config |
| GET | `/api/v1/agent/mcps` | Get default MCP catalog |
| POST | `/api/v1/agent/bootstrap` | Start bootstrap (returns job ID) |
| POST | `/api/v1/agent/run` | Start task run (returns job ID) |
| GET | `/api/v1/agent/jobs/{id}` | Poll job status with step-level progress |
| GET | `/api/v1/agent/jobs` | List recent jobs |

Bootstrap and run operations execute in background threads. The frontend polls
`/agent/jobs/{id}` every 2 seconds to update the step progress UI. Steps track
real LangGraph node execution via `stream_mode="updates"`.

---

## How Evolution Works

When Trigger 1 (post-execution analysis) finds something to improve,
it creates an evolution suggestion. The evolution engine then:

### FIX — Repair a Skill In Place
- Takes the current SKILL.md + a direction ("what's wrong")
- LLM produces an updated version
- Validates the output has proper YAML frontmatter
- Retries up to 3 times if validation fails
- Writes the new version as `status=pending` in the DB
- On approval: replaces the old skill

### DERIVED — Create an Enhanced Version
- Takes a parent skill + enhancement direction
- LLM produces a new skill (may have a different name)
- Same validation and retry logic
- On approval: parent is superseded, new skill becomes active

### CAPTURED — Extract a Novel Pattern
- No parent — brand-new skill from a discovered pattern
- LLM creates a complete new SKILL.md
- On approval: added to the active skill library

**Evolution principles enforced:**
1. Explain the *why*, not just the *what*
2. Keep skills lean — remove steps that don't pull their weight
3. Bundle repeated scripts into `scripts/`
4. Re-check the description after content changes
5. Generalize — fix the root pattern, not the specific instance

---

## Skill Quality Metrics

Each skill tracks four counters, updated after every task:

| Metric | Formula | Meaning |
|--------|---------|---------|
| Applied Rate | `applied / selections` | How often the agent follows it |
| Completion Rate | `completions / applied` | Task success when followed |
| Effective Rate | `completions / selections` | Overall value per selection |
| Fallback Rate | `fallbacks / selections` | Selected but not usable |

Skills with poor metrics are:
- **Filtered out** of the selection pool (quality pre-filter)
- **Flagged** for evolution by Trigger 3 (health check, every 5 runs)

---

## Architecture Diagram

```
   Browser / CLI
        │
        ▼
┌─ DASHBOARD (FastAPI + React) ──────────────────────┐
│  /create   — bootstrap agent from browser           │
│  /run      — run tasks from browser                 │
│  /review   — approve/reject evolutions              │
│  /skills   — browse skill library                   │
│  /runs     — execution traces                       │
│  Background jobs with step-level polling             │
└────────────────────────────────────────────────────-┘
        │
        ▼
┌─ META-AGENT (LangGraph) ──────────────────────────-┐
│  select_mcps → generate_bootstrap → persist          │
│  Runs once at agent creation                         │
└─────────────────────────────────────────────────────┘
        │
        ▼  (repeat per task)
┌─ ORCHESTRATOR (LangGraph) ─────────────────────────┐
│  init_run → select_skills → build_prompt             │
│  → execute_task → record_artifacts                   │
│  → trigger1_analysis → evolution                     │
│  Step progress streamed via LangGraph updates        │
└─────────────────────────────────────────────────────┘
        │
        ▼
┌─ EVOLUTION ENGINE (LangGraph) ─────────────────────┐
│  build_prompt → call_llm → parse_output → validate   │
│  → [retry | persist | fail]                          │
│  All results: status=pending                         │
└─────────────────────────────────────────────────────┘
```

---

## Troubleshooting

**"No agent found"** — Visit `/create` in the dashboard or run `python main.py bootstrap`.

**"A bootstrap is already running" / "A task is already running"** — Only one
bootstrap or task can run at a time. Wait for it to finish or restart the server.

**Evolution fails** — Check the error reason in the output. Common causes:
- LLM returned `<EVOLUTION_FAILED>` (determined the change wasn't worthwhile)
- SKILL.md validation failed (missing frontmatter) after 3 retries

**Empty tool list / "[mcp] Skipping 'X' MCP"** — Means the env var for that
MCP server isn't set. Add it to `.env` or export it in your shell. See the
**MCP Tools** section for the required variables. The task still runs; it
just won't have those tools available.

**`npx: command not found`** — Install Node.js: `brew install node`.
The github and search MCP servers are launched via `npx` stdio.

**LangSmith not working** — Ensure `LANGSMITH_API_KEY` is valid and
`LANGSMITH_TRACING=true` is set before starting.

**Port in use** — `lsof -ti :7788 | xargs kill -9` to free the port.

**Frontend not loading** — Make sure you built it: `cd frontend && npm run build`.
Or use dev mode: `cd frontend && npm run dev` (requires API server on :7788).

---

*"A girl has many faces. And now she has the skills to match."*
