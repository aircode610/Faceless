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
cd frontend && npm install && cd ..

# Required
export ANTHROPIC_API_KEY=your-key

# Optional — LangSmith tracing
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=your-langsmith-key
export LANGSMITH_PROJECT=faceless
```

---

## The Pipeline — Step by Step

### Step 1: Bootstrap — Create Your Agent

The meta-agent runs **once** to create the agent's identity: which tools it uses,
what rules it follows, and what skills it starts with.

```bash
python main.py bootstrap \
  -d "Review GitHub pull requests for security issues and test coverage gaps"
```

**What happens:**
1. LLM selects MCPs from the catalog (e.g., picks `github`, `filesystem`, `terminal`)
2. LLM generates a constitution (immutable rules) and 5 initial skills
3. Everything is written to `agent/` directory and `agent/db/agent.db`

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

**Custom MCPs:** Create a JSON file with your MCPs and pass it:
```bash
python main.py bootstrap \
  -d "your agent description" \
  -m path/to/my-mcps.json
```

MCP JSON format:
```json
[
  {"name": "github", "description": "Read/write GitHub repos, PRs, issues"},
  {"name": "jira", "description": "Read/write Jira tickets"}
]
```

---

### Step 2: Run a Task

The orchestrator runs the full per-task loop: skill selection, execution,
recording, analysis, and evolution.

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

**Output example:**
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

### Step 3: Review & Approve (Dashboard)

Start the dashboard server:

```bash
# Production (serves built frontend)
cd frontend && npm run build && cd ..
uvicorn src.dashboard.server:app --port 7788
# Visit http://localhost:7788

# Development (hot reload)
uvicorn src.dashboard.server:app --port 7788 &
cd frontend && npm run dev
# Visit http://localhost:5173
```

**Dashboard pages:**

| Page | URL | What to do |
|------|-----|------------|
| Dashboard | `/dashboard` | Overview: metrics, pipeline, top skills, recent runs |
| Skills | `/skills` | Browse all skills, filter by status, search |
| Skill Detail | `/skills/:id` | View skill content, quality metrics, version history |
| Runs | `/runs` | See all task executions |
| Run Detail | `/runs/:id` | Timeline of what the agent did, skill judgments, analysis |
| **Review Queue** | `/review` | **Approve or reject pending evolutions** |
| Constitution | `/constitution` | View/edit the immutable rules |

**Review workflow:**
1. Go to `/review`
2. Click a pending evolution in the left panel
3. Review the diff (what changed vs. the parent skill)
4. Read the direction (why it was suggested)
5. Click **Approve** (green) or **Reject** (red, with reason)
6. On approval: old skill → superseded, new skill → active
7. On rejection: old skill stays active, new skill marked rejected

---

### Step 4: Run More Tasks — Watch It Improve

Each task run:
- Uses the **latest active skills** (including newly approved ones)
- Produces new analysis and evolution suggestions
- Skills that get applied successfully build up quality scores
- Recurring patterns get auto-escalated in priority

```bash
# Run several tasks to build up skill quality data
python main.py run -t "Check this Flask endpoint for XSS: return render_template_string(request.args['name'])"
python main.py run -t "Review this code for hardcoded credentials: db_password = 'admin123'"
python main.py run -t "Analyze test coverage for this PR that adds a new API endpoint"
```

Check agent status any time:
```bash
python main.py status
```

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
python main.py bootstrap -d "..."
        │
        ▼
┌─ META-AGENT (LangGraph) ────────────┐
│  select_mcps → generate_bootstrap    │
│  → persist_artifacts                 │
└──────────────────────────────────────┘
        │
        ▼  (repeat per task)
python main.py run -t "..."
        │
        ▼
┌─ ORCHESTRATOR (LangGraph) ──────────┐
│  init_run → select_skills            │
│  → build_prompt → execute_task       │
│  → record_artifacts                  │
│  → trigger1_analysis                 │
│  → evolution  ◄── NEW               │
└──────────────────────────────────────┘
        │
        ▼
┌─ EVOLUTION ENGINE (LangGraph) ──────┐
│  build_prompt → call_llm             │
│  → parse_output → validate           │
│  → [retry | persist | fail]          │
│  All results: status=pending         │
└──────────────────────────────────────┘
        │
        ▼
┌─ DASHBOARD (FastAPI + React) ───────┐
│  /review — approve/reject evolutions │
│  /skills — browse skill library      │
│  /runs   — execution traces          │
└──────────────────────────────────────┘
```

---

## Troubleshooting

**"No agent found"** — Run `python main.py bootstrap` first.

**Evolution fails** — Check the error reason in the output. Common causes:
- LLM returned `<EVOLUTION_FAILED>` (determined the change wasn't worthwhile)
- SKILL.md validation failed (missing frontmatter) after 3 retries

**Empty tool list** — Currently the execution agent runs without MCP tools.
To add tools, pass them via the `tools` parameter in `run_task()`.

**LangSmith not working** — Ensure `LANGSMITH_API_KEY` is valid and
`LANGSMITH_TRACING=true` is set before starting.

**Port in use** — `lsof -ti :7788 | xargs kill -9` to free the port.

---

*"A girl has many faces. And now she has the skills to match."*
