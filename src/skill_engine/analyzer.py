"""
"The Many-Faced God sees all that was done."
Trigger 1 — Post-execution analysis.
"""

from __future__ import annotations

import json
import os

from langchain_core.messages import HumanMessage

from src.config import (
    DB_PATH,
    MAX_CONVERSATION_CHARS,
    MAX_SKILL_CONTENT_CHARS,
    MAX_TOOL_ARGS_CHARS,
    MAX_TOOL_ERROR_CHARS,
    MAX_TOOL_RESULT_CHARS,
    MAX_TRAJ_SUMMARY_CHARS,
    RECURRENCE_MIN_DISTINCT_RUNS,
    RECURRENCE_PROMOTION_THRESHOLD,
)
from src.llm import get_llm
from src.prompts.skill_engine_prompts import EXECUTION_ANALYSIS_TEMPLATE
from src.skill_engine.store import SkillStore
from src.skill_engine.types import ExecutionAnalysis


# ── Truncation helpers ───────────────────────────────

def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... [truncated at {max_chars} chars]"


def _build_traj_summary(traj_data: list[dict]) -> str:
    """Summarize tool call trajectory."""
    lines = []
    for entry in traj_data:
        status = "OK" if entry.get("success") else "FAIL"
        tool = entry.get("tool", "unknown")
        dur = entry.get("duration_ms", "?")
        args_str = _truncate(json.dumps(entry.get("args", {})), MAX_TOOL_ARGS_CHARS)
        lines.append(f"[iter {entry.get('iter', '?')}] {tool}({args_str}) → {status} ({dur}ms)")
    return _truncate("\n".join(lines), MAX_TRAJ_SUMMARY_CHARS)


def _build_skill_section(skills: list[dict]) -> str:
    """Format selected skills for the analysis prompt."""
    parts = []
    for s in skills:
        content = _truncate(s.get("content", ""), MAX_SKILL_CONTENT_CHARS)
        parts.append(f"### Skill: {s['id']}\n{content}")
    return "\n\n---\n\n".join(parts)


def _priority_ladder(current: str) -> str:
    ladder = {"low": "medium", "medium": "high", "high": "critical"}
    return ladder.get(current, current)


# ── Main analyze function ────────────────────────────

def analyze_run(run_id: str, recording_dir: str, store: SkillStore) -> ExecutionAnalysis:
    """
    Run post-execution analysis (Trigger 1).
    Reads recording artifacts, calls LLM, updates DB.
    """
    # Load artifacts
    meta_path = os.path.join(recording_dir, "metadata.json")
    conv_path = os.path.join(recording_dir, "conversations.jsonl")
    traj_path = os.path.join(recording_dir, "traj.jsonl")

    with open(meta_path) as f:
        metadata = json.load(f)

    conversation_lines = []
    if os.path.exists(conv_path):
        with open(conv_path) as f:
            conversation_lines = [json.loads(line) for line in f if line.strip()]

    traj_data = []
    if os.path.exists(traj_path):
        with open(traj_path) as f:
            traj_data = [json.loads(line) for line in f if line.strip()]

    # Build prompt inputs
    task_description = metadata.get("task_description", "")
    execution_status = metadata.get("execution_status", "unknown")
    iterations = metadata.get("iterations", 0)
    tool_list = ", ".join(metadata.get("tool_list", []))
    selected_skill_ids = metadata.get("selected_skills", [])

    # Load skill content for selected skills
    skill_details = []
    for sid in selected_skill_ids:
        skill = store.get_skill(sid)
        if skill:
            skill_details.append({"id": sid, "content": skill.content})

    conversation_log = _truncate(
        "\n".join(json.dumps(c) for c in conversation_lines),
        MAX_CONVERSATION_CHARS,
    )
    traj_summary = _build_traj_summary(traj_data)
    skill_section = _build_skill_section(skill_details)

    prompt = EXECUTION_ANALYSIS_TEMPLATE.format(
        task_description=task_description,
        execution_status=execution_status,
        iterations=iterations,
        tool_list=tool_list,
        skill_section=skill_section,
        conversation_log=conversation_log,
        traj_summary=traj_summary,
        selected_skill_ids_json=json.dumps(selected_skill_ids),
    )

    # Call LLM with structured output
    llm = get_llm()
    structured_llm = llm.with_structured_output(ExecutionAnalysis)
    analysis: ExecutionAnalysis = structured_llm.invoke(
        [HumanMessage(content=prompt)]
    )

    # ── Update DB ────────────────────────────────────

    # Update run with task_completed
    store.update_run_analysis(run_id, analysis.task_completed)

    # Update skill counters + judgments
    judgment_map = {j.skill_id: j for j in analysis.skill_judgments}
    for sid in selected_skill_ids:
        j = judgment_map.get(sid)
        applied = j.skill_applied if j else False
        note = j.note if j else ""
        store.insert_judgment(run_id, sid, applied, note)
        store.update_skill_counters(sid, applied, analysis.task_completed)

    # Process evolution suggestions with recurrence tracking
    for sug in analysis.evolution_suggestions:
        sug_dict = sug.model_dump()
        pattern_key = sug.pattern_key

        if pattern_key:
            existing = store.get_suggestion_by_pattern_key(pattern_key)
            if existing:
                store.increment_recurrence(existing["id"], run_id)
                rec_count = existing["recurrence_count"] + 1
                if rec_count >= RECURRENCE_PROMOTION_THRESHOLD:
                    distinct = store.count_distinct_runs_for_pattern(pattern_key)
                    if distinct >= RECURRENCE_MIN_DISTINCT_RUNS:
                        new_priority = _priority_ladder(existing["priority"])
                        store.update_priority(existing["id"], new_priority)
                continue

        store.insert_evolution_suggestion(run_id, "trigger1", sug_dict)

    # Process feature requests
    for feat in analysis.feature_requests:
        store.insert_feature_request(run_id, feat.model_dump())

    # Record tool calls from traj
    tool_names_used = set()
    for entry in traj_data:
        tool_name = entry.get("tool", "unknown")
        tool_names_used.add(tool_name)
        store.insert_tool_call(
            run_id=run_id,
            tool_name=tool_name,
            success=entry.get("success", False),
            duration_ms=entry.get("duration_ms"),
            error_message=entry.get("error_message"),
        )

    # Populate skill_tool_deps from actual execution data — if a skill was
    # selected in a run that used a tool, record the dependency.
    for sid in selected_skill_ids:
        for tool_name in tool_names_used:
            store.upsert_skill_tool_dep(sid, tool_name)

    # Also store the tool names in agent_config for future extraction
    _update_known_tool_names(tool_names_used)

    return analysis


def _update_known_tool_names(new_names: set[str]):
    """Append newly seen tool names to agent_config.json for future use."""
    from src.config import AGENT_CONFIG_PATH

    if not os.path.exists(AGENT_CONFIG_PATH):
        return
    try:
        with open(AGENT_CONFIG_PATH) as f:
            config = json.load(f)
        existing = set(config.get("tool_names", []))
        updated = existing | new_names
        if updated != existing:
            config["tool_names"] = sorted(updated)
            with open(AGENT_CONFIG_PATH, "w") as f:
                json.dump(config, f, indent=2)
    except (json.JSONDecodeError, OSError):
        pass
