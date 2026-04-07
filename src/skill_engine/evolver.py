"""
"A girl must become no one to become someone new."
Evolution Engine — FIX / DERIVED / CAPTURED skill evolution.

Takes an EvolutionSuggestion and produces a new pending skill version.
"""

from __future__ import annotations

import difflib
import json
import logging
import os
import re
from typing import TypedDict

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

from src.config import (
    CONSTITUTION_PATH,
    DB_PATH,
    EVOLUTION_MAX_APPLY_ATTEMPTS,
    EVOLUTION_MAX_ITERATIONS,
    LLM_MODEL,
    LLM_TEMPERATURE,
    SKILLS_DIR,
)
from src.prompts.skill_engine_prompts import (
    CONSTITUTION_BLOCK,
    EVOLUTION_CAPTURED_TEMPLATE,
    EVOLUTION_DERIVED_TEMPLATE,
    EVOLUTION_FIX_TEMPLATE,
    EVOLUTION_PRINCIPLES,
)
from src.skill_engine.store import SkillStore
from src.skill_engine.types import SkillRecord

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────

def _load_constitution() -> str:
    if os.path.exists(CONSTITUTION_PATH):
        with open(CONSTITUTION_PATH) as f:
            return f.read()
    return ""


def _make_constitution_block(constitution: str) -> str:
    if not constitution:
        return ""
    return CONSTITUTION_BLOCK.format(constitution=constitution)


def _compute_diff(old_content: str, new_content: str) -> str:
    """Compute unified diff between old and new content."""
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    diff = difflib.unified_diff(old_lines, new_lines, fromfile="old", tofile="new")
    return "".join(diff)


def _extract_description(content: str) -> str:
    """Extract description from SKILL.md frontmatter."""
    lines = content.split("\n")
    in_fm = False
    desc_lines = []
    capturing = False
    for line in lines:
        if line.strip() == "---":
            if in_fm:
                break
            in_fm = True
            continue
        if in_fm:
            if line.startswith("description:"):
                text = line.split("description:", 1)[1].strip()
                if text and text != ">":
                    desc_lines.append(text)
                capturing = True
            elif capturing and (line.startswith("  ") or line.startswith("\t")):
                desc_lines.append(line.strip())
            elif capturing:
                break
    return " ".join(desc_lines) if desc_lines else ""


def _extract_name(content: str) -> str:
    """Extract name from SKILL.md frontmatter."""
    match = re.search(r"^name:\s*(.+)$", content, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _extract_category(content: str) -> str:
    """Extract category from SKILL.md frontmatter."""
    match = re.search(r"^category:\s*(.+)$", content, re.MULTILINE)
    return match.group(1).strip() if match else "workflow"


def _validate_skill_content(content: str) -> str | None:
    """Validate SKILL.md has proper frontmatter. Returns error message or None."""
    if "---" not in content:
        return "Missing YAML frontmatter (no --- markers found)"
    parts = content.split("---", 2)
    if len(parts) < 3:
        return "Incomplete frontmatter (need opening and closing ---)"
    fm = parts[1]
    if "name:" not in fm:
        return "Frontmatter missing 'name:' field"
    if "description:" not in fm:
        return "Frontmatter missing 'description:' field"
    return None


def _parse_evolution_output(raw: str) -> tuple[str | None, str | None, bool]:
    """
    Parse LLM evolution output.
    Returns: (change_summary, skill_content, succeeded)
    """
    if "<EVOLUTION_FAILED>" in raw:
        return None, None, False

    if "<EVOLUTION_COMPLETE>" not in raw:
        return None, None, False

    # Extract change summary
    change_summary = ""
    for line in raw.split("\n"):
        if line.startswith("CHANGE_SUMMARY:"):
            change_summary = line.split("CHANGE_SUMMARY:", 1)[1].strip()
            break

    # Extract content between CHANGE_SUMMARY and <EVOLUTION_COMPLETE>
    # The skill content is everything after the CHANGE_SUMMARY line
    # up to <EVOLUTION_COMPLETE>
    content = raw
    if "CHANGE_SUMMARY:" in content:
        content = content.split("\n", 1)
        content = content[1] if len(content) > 1 else ""
    content = content.split("<EVOLUTION_COMPLETE>")[0].strip()

    # Strip markdown code fences if present
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first and last lines if they are fences
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)

    return change_summary, content, True


def _build_metric_summary(skill: SkillRecord) -> str:
    sel = max(skill.total_selections, 1)
    applied = max(skill.total_applied, 1)
    return (
        f"Selections: {skill.total_selections}, "
        f"Applied: {skill.total_applied} ({skill.total_applied/sel:.0%}), "
        f"Completions: {skill.total_completions} ({skill.total_completions/applied:.0%}), "
        f"Fallbacks: {skill.total_fallbacks} ({skill.total_fallbacks/sel:.0%})"
    )


# ── Evolution State ──────────────────────────────────

class EvolutionState(TypedDict):
    suggestion_id: str
    evolution_type: str  # "fix" | "derived" | "captured"
    target_skill_ids: list[str]
    direction: str
    category: str
    # Internal
    iteration: int
    max_iterations: int
    prompt: str
    raw_output: str
    change_summary: str
    new_content: str
    validation_error: str | None
    apply_attempts: int
    succeeded: bool
    resulting_skill_id: str | None
    error_reason: str


# ── Nodes ────────────────────────────────────────────

def build_prompt_node(state: EvolutionState) -> dict:
    """Build the evolution prompt based on type."""
    store = SkillStore(DB_PATH)
    constitution = _load_constitution()
    const_block = _make_constitution_block(constitution)
    evo_type = state["evolution_type"]

    try:
        if evo_type == "fix":
            target_id = state["target_skill_ids"][0] if state["target_skill_ids"] else ""
            skill = store.get_skill(target_id)
            if not skill:
                return {"error_reason": f"Target skill {target_id} not found", "succeeded": False}

            prompt = EVOLUTION_FIX_TEMPLATE.format(
                constitution_block=const_block,
                current_content=skill.content,
                direction=state["direction"],
                failure_context="From post-execution analysis.",
                tool_issue_summary="None reported.",
                metric_summary=_build_metric_summary(skill),
                principles=EVOLUTION_PRINCIPLES,
            )

        elif evo_type == "derived":
            target_id = state["target_skill_ids"][0] if state["target_skill_ids"] else ""
            skill = store.get_skill(target_id)
            if not skill:
                return {"error_reason": f"Parent skill {target_id} not found", "succeeded": False}

            prompt = EVOLUTION_DERIVED_TEMPLATE.format(
                constitution_block=const_block,
                parent_content=skill.content,
                direction=state["direction"],
                execution_insights="From post-execution analysis.",
                metric_summary=_build_metric_summary(skill),
                principles=EVOLUTION_PRINCIPLES,
            )

        elif evo_type == "captured":
            prompt = EVOLUTION_CAPTURED_TEMPLATE.format(
                constitution_block=const_block,
                direction=state["direction"],
                category=state.get("category", "workflow"),
                execution_highlights="Novel pattern detected during execution analysis.",
                principles=EVOLUTION_PRINCIPLES,
            )
        else:
            return {"error_reason": f"Unknown evolution type: {evo_type}", "succeeded": False}

        return {"prompt": prompt}
    finally:
        store.close()


def call_llm_node(state: EvolutionState) -> dict:
    """Call the LLM with the evolution prompt."""
    if state.get("error_reason"):
        return {}

    iteration = state.get("iteration", 0) + 1
    prompt = state["prompt"]

    # On retry after validation failure, append the error
    if state.get("validation_error"):
        prompt += (
            f"\n\n## VALIDATION ERROR (attempt {state['apply_attempts']})\n"
            f"Your previous output had this error: {state['validation_error']}\n"
            f"Please fix it and output the corrected SKILL.md content, "
            f"ending with <EVOLUTION_COMPLETE>."
        )

    llm = init_chat_model(LLM_MODEL, temperature=LLM_TEMPERATURE)
    response = llm.invoke([HumanMessage(content=prompt)])
    raw = response.content if isinstance(response.content, str) else str(response.content)

    return {"raw_output": raw, "iteration": iteration}


def parse_output_node(state: EvolutionState) -> dict:
    """Parse the LLM output into change_summary + content."""
    if state.get("error_reason"):
        return {}

    raw = state.get("raw_output", "")
    change_summary, content, succeeded = _parse_evolution_output(raw)

    if not succeeded:
        return {
            "succeeded": False,
            "error_reason": "LLM returned EVOLUTION_FAILED or unparseable output",
        }

    return {
        "change_summary": change_summary or "",
        "new_content": content or "",
        "succeeded": True,
    }


def validate_node(state: EvolutionState) -> dict:
    """Validate the parsed SKILL.md content."""
    if not state.get("succeeded"):
        return {}

    content = state.get("new_content", "")
    error = _validate_skill_content(content)
    attempts = state.get("apply_attempts", 0) + 1

    if error:
        if attempts >= EVOLUTION_MAX_APPLY_ATTEMPTS:
            return {
                "succeeded": False,
                "error_reason": f"Validation failed after {attempts} attempts: {error}",
                "apply_attempts": attempts,
                "validation_error": error,
            }
        return {
            "validation_error": error,
            "apply_attempts": attempts,
        }

    return {"validation_error": None, "apply_attempts": attempts}


def persist_node(state: EvolutionState) -> dict:
    """Write the evolved skill to DB and filesystem."""
    if not state.get("succeeded") or state.get("validation_error"):
        return {}

    store = SkillStore(DB_PATH)
    evo_type = state["evolution_type"]
    content = state["new_content"]

    try:
        name = _extract_name(content)
        description = _extract_description(content)
        category = _extract_category(content)

        if evo_type == "fix":
            target_id = state["target_skill_ids"][0]
            parent = store.get_skill(target_id)
            if not parent:
                return {"error_reason": "Parent skill disappeared", "succeeded": False}

            new_id = store.make_skill_id(parent.name, parent.generation + 1)
            name = name or parent.name
            diff = _compute_diff(parent.content, content)

            record = SkillRecord(
                id=new_id,
                name=name,
                description=description or parent.description,
                category=category or parent.category,
                content=content,
                status="pending",
                generation=parent.generation + 1,
                parent_id=target_id,
                lineage_origin="FIXED",
                content_diff=diff,
            )

        elif evo_type == "derived":
            target_id = state["target_skill_ids"][0]
            parent = store.get_skill(target_id)
            if not parent:
                return {"error_reason": "Parent skill disappeared", "succeeded": False}

            # Use extracted name or derive from parent
            derived_name = name or f"{parent.name}-enhanced"
            new_id = store.make_skill_id(derived_name, parent.generation + 1)
            diff = _compute_diff(parent.content, content)

            record = SkillRecord(
                id=new_id,
                name=derived_name,
                description=description,
                category=category or parent.category,
                content=content,
                status="pending",
                generation=parent.generation + 1,
                parent_id=target_id,
                lineage_origin="DERIVED",
                content_diff=diff,
            )

            # Multi-parent support
            store.conn.execute(
                "INSERT OR IGNORE INTO skill_parents (skill_id, parent_id) VALUES (?, ?)",
                (new_id, target_id),
            )
            store.conn.commit()

        elif evo_type == "captured":
            captured_name = name or "captured-skill"
            new_id = store.make_skill_id(captured_name, 1)

            record = SkillRecord(
                id=new_id,
                name=captured_name,
                description=description,
                category=category,
                content=content,
                status="pending",
                generation=1,
                parent_id=None,
                lineage_origin="CAPTURED",
                content_diff=None,
            )
        else:
            return {"error_reason": f"Unknown type: {evo_type}", "succeeded": False}

        # Insert into DB
        store.insert_skill(record)
        store.insert_audit(
            new_id, "evolution_created",
            reviewer="evolution-engine",
            note=f"{evo_type.upper()}: {state.get('change_summary', '')[:200]}",
        )

        # Update the evolution suggestion status
        if state.get("suggestion_id"):
            store.update_suggestion_status(
                state["suggestion_id"], "executed", resulting_skill_id=new_id
            )

        # Write skill directory (pending — will be activated on approval)
        skill_dir = os.path.join(SKILLS_DIR, record.name)
        os.makedirs(skill_dir, exist_ok=True)
        # Write to a pending subdirectory so we don't overwrite active skill
        pending_dir = os.path.join(skill_dir, f".pending_{new_id}")
        os.makedirs(pending_dir, exist_ok=True)
        with open(os.path.join(pending_dir, "SKILL.md"), "w") as f:
            f.write(content)
        with open(os.path.join(pending_dir, ".skill_id"), "w") as f:
            f.write(new_id)

        logger.info(f"Evolution {evo_type} succeeded: {new_id}")
        return {"resulting_skill_id": new_id, "succeeded": True}

    finally:
        store.close()


def should_retry(state: EvolutionState) -> str:
    """Decide whether to retry, persist, or give up."""
    if state.get("error_reason") and not state.get("validation_error"):
        return END

    if not state.get("succeeded", False):
        return END

    if state.get("validation_error"):
        if state.get("apply_attempts", 0) >= EVOLUTION_MAX_APPLY_ATTEMPTS:
            return END
        return "call_llm"  # Retry with validation error feedback

    # Succeeded and valid — persist
    return "persist"


# ── Graph ────────────────────────────────────────────

def build_evolver_graph() -> StateGraph:
    """
    The ritual of transformation:
      build_prompt → call_llm → parse → validate → [retry|persist|end]
    """
    graph = StateGraph(EvolutionState)

    graph.add_node("build_prompt", build_prompt_node)
    graph.add_node("call_llm", call_llm_node)
    graph.add_node("parse_output", parse_output_node)
    graph.add_node("validate", validate_node)
    graph.add_node("persist", persist_node)

    graph.add_edge(START, "build_prompt")
    graph.add_edge("build_prompt", "call_llm")
    graph.add_edge("call_llm", "parse_output")
    graph.add_edge("parse_output", "validate")
    graph.add_conditional_edges("validate", should_retry, ["call_llm", "persist", END])
    graph.add_edge("persist", END)

    return graph


def create_evolver():
    """Compile and return the evolution engine graph."""
    return build_evolver_graph().compile()


# ── Public API ───────────────────────────────────────

def evolve_skill(
    suggestion_id: str,
    evolution_type: str,
    target_skill_ids: list[str],
    direction: str,
    category: str = "workflow",
) -> dict:
    """
    Run a single evolution. Returns the final state dict.

    Args:
        suggestion_id: DB ID of the evolution suggestion
        evolution_type: "fix" | "derived" | "captured"
        target_skill_ids: List of skill IDs to evolve (empty for captured)
        direction: What to change/create
        category: Skill category (for captured)
    """
    evolver = create_evolver()

    result = evolver.invoke({
        "suggestion_id": suggestion_id,
        "evolution_type": evolution_type,
        "target_skill_ids": target_skill_ids,
        "direction": direction,
        "category": category,
        "iteration": 0,
        "max_iterations": EVOLUTION_MAX_ITERATIONS,
        "prompt": "",
        "raw_output": "",
        "change_summary": "",
        "new_content": "",
        "validation_error": None,
        "apply_attempts": 0,
        "succeeded": False,
        "resulting_skill_id": None,
        "error_reason": "",
    })

    # Mark failed suggestions
    if not result.get("succeeded") and suggestion_id:
        store = SkillStore(DB_PATH)
        try:
            store.update_suggestion_status(suggestion_id, "failed")
        finally:
            store.close()

    return result


def process_pending_evolutions(store: SkillStore) -> list[dict]:
    """
    Process all pending evolution suggestions.
    Called by the orchestrator after Trigger 1.
    Returns list of evolution results.
    """
    pending = store.get_pending_suggestions()
    results = []

    for sug in pending:
        target_ids = json.loads(sug.get("target_skill_ids") or "[]")
        evo_type = sug.get("type", "fix")
        direction = sug.get("direction", "")
        category = sug.get("category", "workflow")

        logger.info(
            f"Processing evolution: {evo_type} on {target_ids} — {direction[:60]}"
        )

        result = evolve_skill(
            suggestion_id=sug["id"],
            evolution_type=evo_type,
            target_skill_ids=target_ids,
            direction=direction,
            category=category,
        )

        results.append({
            "suggestion_id": sug["id"],
            "type": evo_type,
            "succeeded": result.get("succeeded", False),
            "resulting_skill_id": result.get("resulting_skill_id"),
            "change_summary": result.get("change_summary", ""),
            "error_reason": result.get("error_reason", ""),
        })

    return results
