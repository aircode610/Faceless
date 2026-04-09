"""
Agent operations: bootstrap and run tasks from the UI.
Long-running ops execute in background threads with polling.

Both bootstrap and run use LangGraph streaming (stream_mode="updates") to
get per-node progress events. Each event is appended to the job's `log`
array so the frontend can show a live feed of what's happening.
"""

from __future__ import annotations

import json
import os
import threading
import traceback
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from src.config import AGENT_CONFIG_PATH, DB_PATH
from src.dashboard.models import BootstrapRequest, RunTaskRequest
from src.tools.loader import get_mcp_catalog, get_mcps_with_credentials

router = APIRouter()

# ── In-memory job store ──────────────────────────────
# Jobs are short-lived (cleared on restart). That's fine — they're only
# used to track progress of the current bootstrap/run operation.

_jobs: dict[str, dict] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_log(job_id: str, level: str, message: str, detail: str | None = None):
    """Append an event to a job's log feed."""
    job = _jobs.get(job_id)
    if not job:
        return
    job.setdefault("log", []).append({
        "ts": _now_iso(),
        "level": level,  # "info" | "llm" | "done" | "error"
        "message": message,
        "detail": detail,
    })


def _set_step(job_id: str, step_idx: int, status: str):
    """Set a specific step's status by index."""
    job = _jobs.get(job_id)
    if not job:
        return
    steps = job.get("steps", [])
    if 0 <= step_idx < len(steps):
        steps[step_idx]["status"] = status


def _advance_steps_to(job_id: str, step_idx: int):
    """Mark all steps up to and including step_idx as done, the next one as running."""
    job = _jobs.get(job_id)
    if not job:
        return
    steps = job.get("steps", [])
    for i, step in enumerate(steps):
        if i <= step_idx:
            step["status"] = "done"
        elif i == step_idx + 1:
            step["status"] = "running"


# ── Agent status ─────────────────────────────────────

@router.get("/agent/status")
def get_agent_status():
    """Check if an agent has been bootstrapped."""
    exists = os.path.exists(AGENT_CONFIG_PATH)
    config = None
    if exists:
        with open(AGENT_CONFIG_PATH) as f:
            config = json.load(f)
    return {
        "bootstrapped": exists,
        "config": config,
    }


@router.get("/agent/mcps")
def get_default_mcps():
    """
    Return the MCP catalog the bootstrap form should show.
    Pulled from the tools loader — only MCPs with real implementations
    are listed, and each entry is flagged with whether the required
    credentials are currently available.
    """
    catalog = get_mcp_catalog()
    with_creds = set(get_mcps_with_credentials())
    return [
        {**entry, "credentials_available": entry["name"] in with_creds}
        for entry in catalog
    ]


# ── Bootstrap ────────────────────────────────────────

# Maps meta-agent node names to step indices
BOOTSTRAP_NODE_TO_STEP = {
    "select_mcps": 0,
    "generate_bootstrap": 1,
    "persist_artifacts": 2,
}


@router.post("/agent/bootstrap")
def start_bootstrap(req: BootstrapRequest):
    """Start agent bootstrap in background. Returns a job ID to poll."""
    for j in _jobs.values():
        if j["type"] == "bootstrap" and j["status"] == "running":
            raise HTTPException(409, "A bootstrap is already running")

    job_id = f"job_{uuid.uuid4().hex[:8]}"
    mcps = [m.model_dump() for m in req.mcps] if req.mcps else get_mcp_catalog()

    _jobs[job_id] = {
        "id": job_id,
        "type": "bootstrap",
        "status": "running",
        "description": req.description,
        "started_at": _now_iso(),
        "finished_at": None,
        "result": None,
        "error": None,
        "steps": [
            {"name": "Selecting MCPs", "status": "running"},
            {"name": "Generating constitution & skills", "status": "pending"},
            {"name": "Persisting artifacts", "status": "pending"},
        ],
        "log": [],
    }

    _append_log(job_id, "info", "Bootstrap started",
                f"Description: {req.description}")
    _append_log(job_id, "info", f"Available MCPs: {len(mcps)}",
                ", ".join(m["name"] for m in mcps))

    def _run():
        try:
            from src.meta_agent import create_meta_agent

            graph = create_meta_agent()
            initial_state = {
                "user_description": req.description,
                "available_mcps": mcps,
                "selected_mcps": [],
                "mcp_reasoning": "",
                "constitution": "",
                "skills": [],
                "agent_name": "",
                "error": None,
            }

            accumulated = dict(initial_state)

            # Log node-start events for each step as it comes up
            _append_log(job_id, "llm", "Calling LLM to select MCPs...",
                        "Prompt includes agent description and the full MCP catalog")

            for chunk in graph.stream(initial_state, stream_mode="updates"):
                for node_name, node_output in chunk.items():
                    step_idx = BOOTSTRAP_NODE_TO_STEP.get(node_name)
                    if step_idx is not None:
                        _advance_steps_to(job_id, step_idx)

                    if isinstance(node_output, dict):
                        accumulated.update(node_output)

                    # Per-node event logging with meaningful details
                    if node_name == "select_mcps":
                        selected = node_output.get("selected_mcps", []) if isinstance(node_output, dict) else []
                        reasoning = node_output.get("mcp_reasoning", "") if isinstance(node_output, dict) else ""
                        _append_log(
                            job_id, "done",
                            f"Selected {len(selected)} MCPs: {', '.join(selected)}",
                            reasoning[:400] if reasoning else None,
                        )
                        _append_log(
                            job_id, "llm",
                            "Calling LLM to generate constitution & skills...",
                            f"Will generate constitution + 5 initial skills using the selected MCPs"
                        )
                    elif node_name == "generate_bootstrap":
                        skills = node_output.get("skills", []) if isinstance(node_output, dict) else []
                        constitution = node_output.get("constitution", "") if isinstance(node_output, dict) else ""
                        _append_log(
                            job_id, "done",
                            f"Generated constitution ({len(constitution)} chars) + {len(skills)} skills",
                            "Skills: " + ", ".join(s.get("name", "?") for s in skills),
                        )
                        _append_log(
                            job_id, "info",
                            "Writing artifacts to disk and database...",
                            None,
                        )
                    elif node_name == "persist_artifacts":
                        _append_log(
                            job_id, "done",
                            "All artifacts persisted",
                            "agent_config.json, constitution.md, skills/*, agent.db all written"
                        )

            # Finalize
            for step in _jobs[job_id]["steps"]:
                step["status"] = "done"

            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["finished_at"] = _now_iso()
            _jobs[job_id]["result"] = {
                "agent_name": accumulated.get("agent_name", "unknown"),
                "selected_mcps": accumulated.get("selected_mcps", []),
                "skills_count": len(accumulated.get("skills", [])),
                "skills": [s.get("name", "?") for s in accumulated.get("skills", [])],
            }
            _append_log(job_id, "done",
                        f"Bootstrap complete: {_jobs[job_id]['result']['agent_name']}")

        except Exception as e:
            tb = traceback.format_exc()
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["finished_at"] = _now_iso()
            _jobs[job_id]["error"] = str(e)
            _append_log(job_id, "error", f"Bootstrap failed: {e}", tb[-500:])
            for step in _jobs[job_id]["steps"]:
                if step["status"] == "running":
                    step["status"] = "error"

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return {"job_id": job_id}


# ── Run Task ─────────────────────────────────────────

# Maps orchestrator node names to step indices
RUN_NODE_TO_STEP = {
    "init_run": 0,
    "select_skills": 0,
    "build_prompt": 1,
    "execute_task": 1,
    "record_artifacts": 2,
    "trigger1_analysis": 3,
    "evolution": 4,
}


@router.post("/agent/run")
def start_run(req: RunTaskRequest):
    """Start a task run in background. Returns a job ID to poll."""
    if not os.path.exists(AGENT_CONFIG_PATH):
        raise HTTPException(400, "No agent bootstrapped yet. Create one first.")

    for j in _jobs.values():
        if j["type"] == "run" and j["status"] == "running":
            raise HTTPException(409, "A task is already running")

    job_id = f"job_{uuid.uuid4().hex[:8]}"
    _jobs[job_id] = {
        "id": job_id,
        "type": "run",
        "status": "running",
        "task": req.task,
        "started_at": _now_iso(),
        "finished_at": None,
        "result": None,
        "error": None,
        "steps": [
            {"name": "Selecting skills", "status": "running"},
            {"name": "Executing task", "status": "pending"},
            {"name": "Recording artifacts", "status": "pending"},
            {"name": "Analyzing execution", "status": "pending"},
            {"name": "Running evolutions", "status": "pending"},
        ],
        "log": [],
    }

    _append_log(job_id, "info", "Task started", f"Task: {req.task[:200]}")

    def _run():
        try:
            from src.orchestrator import create_orchestrator
            from src.tools.loader import load_tools_for_agent

            orchestrator = create_orchestrator()

            # Load real MCP tools for the selected MCPs
            _append_log(job_id, "info", "Loading MCP tools...")
            tools = load_tools_for_agent()
            if tools:
                _append_log(
                    job_id, "done",
                    f"Loaded {len(tools)} MCP tools",
                    ", ".join(t.name for t in tools),
                )
            else:
                _append_log(job_id, "info", "No MCP tools loaded (none selected or missing credentials)")

            initial_state = {
                "task_description": req.task,
                "run_id": "",
                "selected_skill_ids": [],
                "system_prompt": "",
                "execution_result": {},
                "recording_dir": "",
                "analysis_result": None,
                "evolution_results": [],
                "tools": tools,
            }

            accumulated = dict(initial_state)

            for chunk in orchestrator.stream(initial_state, stream_mode="updates"):
                for node_name, node_output in chunk.items():
                    step_idx = RUN_NODE_TO_STEP.get(node_name)
                    if step_idx is not None:
                        _advance_steps_to(job_id, step_idx)

                    if isinstance(node_output, dict):
                        accumulated.update(node_output)

                    # Per-node event logging
                    if node_name == "init_run":
                        _append_log(
                            job_id, "info",
                            f"Run ID: {node_output.get('run_id', '?')}",
                            f"Recording dir: {node_output.get('recording_dir', '?')}"
                        )
                    elif node_name == "select_skills":
                        selected = node_output.get("selected_skill_ids", []) if isinstance(node_output, dict) else []
                        _append_log(
                            job_id, "done",
                            f"Selected {len(selected)} skills for this task",
                            "\n".join(selected) if selected else "No skills matched",
                        )
                    elif node_name == "build_prompt":
                        prompt = node_output.get("system_prompt", "") if isinstance(node_output, dict) else ""
                        _append_log(
                            job_id, "info",
                            f"System prompt assembled ({len(prompt)} chars)",
                            "Constitution + selected skills injected",
                        )
                        _append_log(
                            job_id, "llm",
                            "Execution agent is now running...",
                            f"Max iterations: 15 | Tools available: {len(tools)}"
                        )
                    elif node_name == "execute_task":
                        exec_result = node_output.get("execution_result", {}) if isinstance(node_output, dict) else {}
                        iters = exec_result.get("iteration", 0)
                        complete = exec_result.get("task_complete", False)
                        tools_used = list(exec_result.get("tools_used", set()))
                        _append_log(
                            job_id, "done",
                            f"Execution finished after {iters} iterations "
                            f"({'complete' if complete else 'incomplete'})",
                            f"Tools called: {', '.join(tools_used) if tools_used else 'none'}",
                        )
                    elif node_name == "record_artifacts":
                        _append_log(
                            job_id, "done",
                            "Artifacts recorded",
                            "conversations.jsonl, traj.jsonl, metadata.json",
                        )
                    elif node_name == "trigger1_analysis":
                        analysis = node_output.get("analysis_result", {}) if isinstance(node_output, dict) else {}
                        if isinstance(analysis, dict):
                            completed = analysis.get("task_completed", False)
                            evo_count = len(analysis.get("evolution_suggestions", []))
                            feat_count = len(analysis.get("feature_requests", []))
                            _append_log(
                                job_id, "done",
                                f"Analysis: task {'completed' if completed else 'incomplete'}",
                                f"{evo_count} evolution suggestions, {feat_count} feature requests\n"
                                f"Note: {analysis.get('execution_note', '')[:300]}",
                            )
                    elif node_name == "evolution":
                        evo_results = node_output.get("evolution_results", []) if isinstance(node_output, dict) else []
                        succeeded = [e for e in evo_results if e.get("succeeded")]
                        failed = [e for e in evo_results if not e.get("succeeded")]
                        if evo_results:
                            detail = "\n".join(
                                f"✅ {e['type'].upper()}: {e.get('change_summary','')[:80]}"
                                for e in succeeded
                            ) + "\n" + "\n".join(
                                f"❌ {e['type'].upper()}: {e.get('error_reason','')[:80]}"
                                for e in failed
                            )
                            _append_log(
                                job_id, "done",
                                f"Evolution engine: {len(succeeded)} succeeded, {len(failed)} failed",
                                detail.strip(),
                            )
                        else:
                            _append_log(
                                job_id, "info",
                                "No evolution suggestions to process",
                            )

            # Finalize
            for step in _jobs[job_id]["steps"]:
                step["status"] = "done"

            analysis = accumulated.get("analysis_result") or {}
            evo_results = accumulated.get("evolution_results", [])

            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["finished_at"] = _now_iso()
            _jobs[job_id]["result"] = {
                "run_id": accumulated.get("run_id", ""),
                "task_completed": analysis.get("task_completed", False),
                "execution_note": analysis.get("execution_note", ""),
                "selected_skills": accumulated.get("selected_skill_ids", []),
                "evolution_suggestions": len(analysis.get("evolution_suggestions", [])),
                "feature_requests": len(analysis.get("feature_requests", [])),
                "evolutions_succeeded": len([e for e in evo_results if e.get("succeeded")]),
                "evolutions_failed": len([e for e in evo_results if not e.get("succeeded")]),
                "evolution_details": evo_results,
            }
            _append_log(job_id, "done", "Task complete")

        except Exception as e:
            tb = traceback.format_exc()
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["finished_at"] = _now_iso()
            _jobs[job_id]["error"] = str(e)
            _append_log(job_id, "error", f"Task failed: {e}", tb[-500:])
            for step in _jobs[job_id]["steps"]:
                if step["status"] in ("running", "pending"):
                    step["status"] = "error" if step["status"] == "running" else "skipped"

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return {"job_id": job_id}


# ── Job polling ──────────────────────────────────────

@router.get("/agent/jobs/{job_id}")
def get_job_status(job_id: str):
    """Poll the status of a background job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.get("/agent/jobs")
def list_jobs():
    """List all recent jobs."""
    jobs = sorted(_jobs.values(), key=lambda j: j["started_at"], reverse=True)
    return jobs[:20]
