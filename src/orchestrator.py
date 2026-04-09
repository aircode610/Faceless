"""
"A man is not Jaqen H'ghar. A man has no name."
The Orchestrator: the per-task runtime loop.

For every task:
  1. Select skills
  2. Build system prompt (constitution + skills)
  3. Run execution agent
  4. Record artifacts
  5. Trigger 1 — post-execution analysis (blocking)
  6. Evolution engine — process pending suggestions
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import END, START, StateGraph

from src.config import (
    AGENT_CONFIG_PATH,
    CONSTITUTION_PATH,
    DB_PATH,
    MAX_EXECUTION_ITERATIONS,
    RECORDINGS_DIR,
    SKILLS_DIR,
)
from src.execution_agent import run_execution_agent
from src.skill_engine.analyzer import analyze_run
from src.skill_engine.evolver import process_pending_evolutions
from src.skill_engine.registry import select_skills
from src.skill_engine.store import SkillStore
from src.skill_engine.triggers import dispatch_background_triggers
from src.tools.loader import load_tools_for_agent


# ── State ────────────────────────────────────────────

class OrchestratorState(TypedDict):
    task_description: str
    run_id: str
    selected_skill_ids: list[str]
    system_prompt: str
    execution_result: dict
    recording_dir: str
    analysis_result: dict | None
    evolution_results: list[dict]
    background_trigger_status: str
    tools: list  # LangChain tool objects to mount


# ── Prompt Builders ──────────────────────────────────

CONSTITUTION_BLOCK = """\
# Agent Constitution (Non-Negotiable Constraints)
# "The Faceless Men serve the Many-Faced God. These laws are absolute."

{constitution_content}

---
"""

SKILLS_BLOCK_HEADER = """\
# Active Skills
# "Each face grants knowledge. Use it wisely."

The following skills provide domain knowledge and tested procedures for this task.

How to use skills:
- If a skill contains step-by-step procedures or commands, follow them precisely.
- If a skill provides reference information or best practices, use it as context when making decisions.
- Skills supplement your available tools — you may use any tool alongside skill guidance.

---
"""

SKILL_ENTRY = """\
### Skill: {skill_id}
**Directory**: `{skill_dir}`

{skill_content}

---
"""


def _build_system_prompt(
    constitution_content: str,
    skills: list[dict],
) -> str:
    """Assemble the full system prompt from constitution + skills."""
    parts = [CONSTITUTION_BLOCK.format(constitution_content=constitution_content)]

    if skills:
        parts.append(SKILLS_BLOCK_HEADER)
        for s in skills:
            parts.append(SKILL_ENTRY.format(
                skill_id=s["id"],
                skill_dir=s.get("dir", ""),
                skill_content=s["content"],
            ))

    parts.append(
        "\nWhen you have completed the task, include <COMPLETE> in your final response."
    )

    return "\n".join(parts)


# ── Nodes ────────────────────────────────────────────

def init_run(state: OrchestratorState) -> dict:
    """Generate run ID and prepare recording directory."""
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    recording_dir = os.path.join(RECORDINGS_DIR, run_id)
    os.makedirs(recording_dir, exist_ok=True)
    return {"run_id": run_id, "recording_dir": recording_dir}


def select_skills_node(state: OrchestratorState) -> dict:
    """Stage 1+2: Quality filter → LLM skill selection."""
    store = SkillStore(DB_PATH)
    try:
        selected = select_skills(state["task_description"], store)
        return {"selected_skill_ids": selected}
    finally:
        store.close()


def build_prompt_node(state: OrchestratorState) -> dict:
    """Build the full system prompt with constitution + selected skills."""
    # Load constitution
    constitution = ""
    if os.path.exists(CONSTITUTION_PATH):
        with open(CONSTITUTION_PATH) as f:
            constitution = f.read()

    # Load skill contents
    store = SkillStore(DB_PATH)
    skill_details = []
    try:
        for sid in state["selected_skill_ids"]:
            skill = store.get_skill(sid)
            if skill:
                skill_dir = os.path.join(SKILLS_DIR, skill.name)
                skill_details.append({
                    "id": sid,
                    "dir": skill_dir,
                    "content": skill.content,
                })
    finally:
        store.close()

    system_prompt = _build_system_prompt(constitution, skill_details)
    return {"system_prompt": system_prompt}


def execute_task_node(state: OrchestratorState) -> dict:
    """Run the execution agent."""
    result = run_execution_agent(
        task_description=state["task_description"],
        system_prompt=state["system_prompt"],
        tools=state.get("tools", []),
        max_iterations=MAX_EXECUTION_ITERATIONS,
    )
    return {"execution_result": result}


def record_artifacts_node(state: OrchestratorState) -> dict:
    """Write recording artifacts to disk and DB."""
    result = state["execution_result"]
    recording_dir = state["recording_dir"]
    run_id = state["run_id"]

    # Determine status
    task_complete = result.get("task_complete", False)
    iteration = result.get("iteration", 0)
    exec_status = "success" if task_complete else (
        "incomplete" if iteration >= MAX_EXECUTION_ITERATIONS else "error"
    )

    # Collect tool names
    tools_used = list(result.get("tools_used", set()))

    # Write conversations.jsonl
    conv_log = result.get("conversation_log", [])
    with open(os.path.join(recording_dir, "conversations.jsonl"), "w") as f:
        for entry in conv_log:
            f.write(json.dumps(entry) + "\n")

    # Write traj.jsonl
    tool_trace = result.get("tool_trace", [])
    with open(os.path.join(recording_dir, "traj.jsonl"), "w") as f:
        for entry in tool_trace:
            f.write(json.dumps(entry) + "\n")

    # Write metadata.json
    metadata = {
        "task_id": run_id,
        "task_description": state["task_description"],
        "selected_skills": state["selected_skill_ids"],
        "tool_list": tools_used,
        "execution_status": exec_status,
        "iterations": iteration,
    }
    with open(os.path.join(recording_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    # Insert run record
    store = SkillStore(DB_PATH)
    try:
        store.insert_run(
            run_id=run_id,
            task_description=state["task_description"],
            selected_skill_ids=state["selected_skill_ids"],
            execution_status=exec_status,
            iterations=iteration,
            recording_dir=recording_dir,
        )
    finally:
        store.close()

    return {}


def trigger1_analysis_node(state: OrchestratorState) -> dict:
    """Trigger 1: Post-execution analysis (blocking)."""
    store = SkillStore(DB_PATH)
    try:
        analysis = analyze_run(
            run_id=state["run_id"],
            recording_dir=state["recording_dir"],
            store=store,
        )
        return {"analysis_result": analysis.model_dump()}
    finally:
        store.close()


def evolution_node(state: OrchestratorState) -> dict:
    """Process pending evolution suggestions through the evolution engine."""
    store = SkillStore(DB_PATH)
    try:
        results = process_pending_evolutions(store)
        return {"evolution_results": results}
    finally:
        store.close()


def dispatch_triggers_node(state: OrchestratorState) -> dict:
    """Fire Trigger 2 & 3 in background threads. Non-blocking."""
    dispatch_background_triggers(state["run_id"])
    return {"background_trigger_status": "dispatched"}


# ── Graph ────────────────────────────────────────────

def build_orchestrator_graph() -> StateGraph:
    """
    The Faceless ritual for each task:
      init → select_skills → build_prompt → execute → record → analyze
    """
    graph = StateGraph(OrchestratorState)

    graph.add_node("init_run", init_run)
    graph.add_node("select_skills", select_skills_node)
    graph.add_node("build_prompt", build_prompt_node)
    graph.add_node("execute_task", execute_task_node)
    graph.add_node("record_artifacts", record_artifacts_node)
    graph.add_node("trigger1_analysis", trigger1_analysis_node)
    graph.add_node("evolution", evolution_node)
    graph.add_node("dispatch_triggers", dispatch_triggers_node)

    graph.add_edge(START, "init_run")
    graph.add_edge("init_run", "select_skills")
    graph.add_edge("select_skills", "build_prompt")
    graph.add_edge("build_prompt", "execute_task")
    graph.add_edge("execute_task", "record_artifacts")
    graph.add_edge("record_artifacts", "trigger1_analysis")
    graph.add_edge("trigger1_analysis", "evolution")
    graph.add_edge("evolution", "dispatch_triggers")
    graph.add_edge("dispatch_triggers", END)

    return graph


def create_orchestrator():
    """Compile and return the orchestrator graph."""
    graph = build_orchestrator_graph()
    return graph.compile()


# ── Public API ───────────────────────────────────────

def run_task(
    task_description: str,
    tools: list | None = None,
) -> dict:
    """
    Run a single task through the full orchestrator pipeline.

    Args:
        task_description: What the agent should do.
        tools: Optional list of LangChain tool objects to mount. If None,
               tools are auto-loaded from the agent's selected MCPs via
               langchain-mcp-adapters.

    Returns:
        Final orchestrator state with execution results and analysis.
    """
    orchestrator = create_orchestrator()

    # Auto-load MCP tools if the caller didn't pass any
    if tools is None:
        tools = load_tools_for_agent()
        if tools:
            print(f"[orchestrator] Loaded {len(tools)} MCP tools: "
                  f"{[t.name for t in tools]}")

    result = orchestrator.invoke({
        "task_description": task_description,
        "run_id": "",
        "selected_skill_ids": [],
        "system_prompt": "",
        "execution_result": {},
        "recording_dir": "",
        "analysis_result": None,
        "evolution_results": [],
        "background_trigger_status": "",
        "tools": tools or [],
    })

    return result
