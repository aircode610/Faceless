# Faceless — 10-Minute Demo Script

**Audience**: Devs and product managers (not AI engineers).
**Goal**: Show an agent that builds itself, runs tasks, learns from mistakes, and improves — with humans in the loop.

---

## Before the demo

1. Make sure the server is running:
   ```bash
   source .venv/bin/activate
   export ANTHROPIC_API_KEY=your-key
   uvicorn src.dashboard.server:app --port 7788 --reload
   ```

2. If you want live MCP tools (optional but impressive):
   ```bash
   export GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxx
   export TAVILY_API_KEY=tvly-xxx
   ```

3. Open `http://localhost:7788` in your browser.

4. **Clean slate** (optional): Delete `agent/` and `recordings/` folders to start fresh.

---

## Part 1 — The Problem (1 min)

> "Today's AI agents are static. You build them, deploy them, and when they fail at something, a developer has to go in, figure out what went wrong, update the prompts or logic, and redeploy. That doesn't scale."
>
> "What if the agent could analyze its own failures, propose fixes, and improve itself — with a human approving every change?"
>
> "That's Faceless."

Open the **Dashboard** page. It should be empty (no agent yet).

---

## Part 2 — Bootstrap an Agent (2 min)

> "First, we describe what the agent should do. It figures out the rest."

1. Click **"Create Your Agent"**
2. Enter a description like: *"Review GitHub pull requests for security issues, code quality problems, and test coverage gaps"*
3. Click Create and wait (~30 seconds)

**While it's running, explain:**
> "Behind the scenes, a meta-agent is doing three things:
> 1. Picking which tools (MCP servers) this agent needs — it chose GitHub and search
> 2. Writing a constitution — hard rules the agent must always follow
> 3. Generating initial skills — reusable instructions for common tasks
>
> Think of skills like runbooks. Each one teaches the agent a specific procedure."

4. When done, show the **Dashboard** — you'll see 3 active skills, 0 runs.
5. Click into **Skills Library** — show the initial skills. Click one to show its SKILL.md content.
6. Quick look at **Constitution** — the rules the agent must follow.

---

## Part 3 — Run a Task (3 min)

> "Now let's give it real work."

1. Click **"Run a Task"**
2. Enter something like: *"Review this code for security issues: `cursor.execute(f'SELECT * FROM users WHERE id={user_id}')`"*
3. Wait for completion (~30-60 seconds)

**While it's running, explain:**
> "The orchestrator is doing this:
> 1. It looked at the task and picked the most relevant skills
> 2. It injected those skills plus the constitution into the agent's system prompt
> 3. The agent is now running — reasoning, calling tools, iterating — up to 20 cycles
> 4. Everything is being recorded: the full conversation, every tool call with timing"

4. When done, click into the run from **Runs** page
5. Show the **Result tab** — the agent's final answer, rendered in markdown
6. Switch to **Trace tab** — the full step-by-step conversation
7. Switch to **Skills Used** — which skills were selected and whether the agent followed them
8. Switch to **Analysis** — this is Trigger 1's output:

> "After every run, an LLM reviews the entire execution trace and asks: Did the agent follow its skills? What went wrong? What could be improved? It produces structured judgments and evolution suggestions."

---

## Part 4 — The Self-Improvement Loop (2 min)

> "This is where it gets interesting."

1. Go to **Review Queue**
2. If there are pending evolutions (there likely will be after the first run), click one

> "The system proposed a change. Let me walk you through what you see:"

3. Point out each element:
   - **Trigger badge** — where this came from (Post-Execution, Tool Degradation, or Health Check)
   - **Source explanation** — plain English description of why this was triggered
   - **Evolution type** — FIX (repair), DERIVED (enhancement), or CAPTURED (new skill)
   - **"Why this change?"** — the LLM's reasoning, grounded in evidence from the actual run
   - **Diff viewer** — exactly what changed in the skill

> "Every change needs human approval. You can approve, reject, or edit before approving. Nothing goes live without a human saying yes."

4. **Approve** one evolution
5. Go back to **Skills Library** — show the updated skill with its new version number

---

## Part 5 — Run Again and Watch It Improve (1.5 min)

> "Let's run another task and see if the improved skill makes a difference."

1. Run a second task (similar domain)
2. While waiting:

> "After 3 runs, a background health check (Trigger 3) will also evaluate skill metrics — applied rate, completion rate, fallback rate — and propose evolutions for underperforming skills. There's also Trigger 2 watching for tool failures."

3. Show the result and compare to the first run

> "The agent is getting better at its job without any manual prompt engineering."

---

## Part 6 — The Architecture (30 sec)

Go back to **Dashboard** and point at the **Pipeline** visualization:

> "To summarize the architecture:
> - **Meta-Agent**: creates the agent once
> - **Orchestrator**: runs every task through this pipeline
> - **Three triggers** watch for improvement opportunities
> - **Evolution engine** generates new skill versions
> - **Approval gate** keeps humans in control
>
> It's built on LangGraph for the state machines, Claude Sonnet for all LLM calls, and a standard React + FastAPI stack for the dashboard."

---

## Part 7 — Wrap Up (30 sec)

> "What we've built is a framework where agents improve themselves through experience. Each run generates data, that data drives analysis, and analysis produces targeted skill improvements — all with human oversight.
>
> The skills are just markdown files. The evolution types are composable. The approval gate is a hard requirement. And everything is traceable — every decision, every tool call, every change is recorded and visible in the dashboard.
>
> Questions?"

---

## Tips

- **If a run takes too long**: The agent has up to 20 iterations. Most tasks finish in 3-5. If it's stuck, that's actually a good demo moment — it shows why skills need improvement.
- **If no evolutions appear**: Run 2-3 tasks. Trigger 1 runs after every task and usually finds something to improve.
- **If you want to show Trigger 3**: Run 3 tasks. It fires every 3 runs.
- **If asked about cost**: Each run is a few Claude Sonnet calls. Analysis adds ~1 more. Evolution adds ~1 per suggestion. Total is typically 3-6 LLM calls per task.
- **If asked about LangSmith**: If configured, you can show the full LangGraph trace in LangSmith as a bonus.
- **Hover over info icons**: The UI has tooltip explanations on every technical term — use them if someone asks "what does Applied Rate mean?"
