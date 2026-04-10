"""
"The Red God has his due, sweet girl, and only death may pay for life."
Triggers 2 & 3 — Tool degradation detection and periodic skill health check.

Both triggers run in the BACKGROUND after Trigger 1 completes.
Both use an LLM confirmation gate before dispatching to the evolution engine.
"""

from __future__ import annotations

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_core.messages import HumanMessage

from src.config import (
    DB_PATH,
    EVOLUTION_MAX_CONCURRENT,
    FALLBACK_THRESHOLD,
    HIGH_APPLIED_FOR_FIX,
    LOW_COMPLETION_THRESHOLD,
    MAX_SKILL_CONTENT_CHARS,
    METRIC_CHECK_EVERY_N_EXECUTIONS,
    METRIC_MIN_SELECTIONS_TO_EVALUATE,
    MIN_APPLIED_FOR_DERIVED,
    MODERATE_EFFECTIVE_THRESHOLD,
    TOOL_DEGRADED_RATE,
    TOOL_MIN_CALLS,
    TOOL_ROLLING_WINDOW,
)
from src.llm import get_llm
from src.prompts.skill_engine_prompts import EVOLUTION_CONFIRM_TEMPLATE
from src.skill_engine.evolver import evolve_skill
from src.skill_engine.store import SkillStore
from src.skill_engine.types import EvolutionConfirmation

logger = logging.getLogger(__name__)

# ── Anti-Loop Guard (Trigger 2) ──────────────────────
# Maps tool_name -> set of skill_ids that have already been addressed
# for that tool's degradation. Cleared when the tool recovers.
_addressed_degradations: dict[str, set[str]] = {}
_addressed_lock = threading.Lock()


# ── LLM Confirmation Gate ────────────────────────────

def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... [truncated at {max_chars} chars]"


def confirm_evolution(
    skill_id: str,
    skill_content: str,
    proposed_type: str,
    proposed_direction: str,
    trigger_context: str,
    recent_analyses: str,
) -> EvolutionConfirmation | None:
    """
    LLM confirmation gate for Triggers 2 & 3.
    Returns None on any error — fail-safe defaults to skipping evolution.
    """
    prompt = EVOLUTION_CONFIRM_TEMPLATE.format(
        skill_id=skill_id,
        skill_content=_truncate(skill_content, MAX_SKILL_CONTENT_CHARS),
        proposed_type=proposed_type,
        proposed_direction=proposed_direction,
        trigger_context=trigger_context,
        recent_analyses=recent_analyses,
    )

    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(EvolutionConfirmation)
        result: EvolutionConfirmation = structured_llm.invoke(
            [HumanMessage(content=prompt)]
        )
        return result
    except Exception as e:
        logger.warning(f"Confirmation gate failed for {skill_id}: {e}")
        return None


# ── Parallel Evolution Executor ──────────────────────

def _execute_evolutions_parallel(
    evolutions: list[tuple[str, str, str, str]],
) -> list[dict]:
    """
    Execute evolution suggestions in parallel, capped at EVOLUTION_MAX_CONCURRENT.
    Each tuple: (suggestion_id, skill_id, direction, evolution_type)
    """
    if not evolutions:
        return []

    results = []
    with ThreadPoolExecutor(max_workers=EVOLUTION_MAX_CONCURRENT) as pool:
        futures = {}
        for sug_id, skill_id, direction, evo_type in evolutions:
            future = pool.submit(
                evolve_skill,
                suggestion_id=sug_id,
                evolution_type=evo_type,
                target_skill_ids=[skill_id],
                direction=direction,
            )
            futures[future] = sug_id

        for future in as_completed(futures):
            sug_id = futures[future]
            try:
                result = future.result()
                results.append({
                    "suggestion_id": sug_id,
                    "succeeded": result.get("succeeded", False),
                    "resulting_skill_id": result.get("resulting_skill_id"),
                })
                logger.info(
                    f"Background evolution {sug_id}: "
                    f"succeeded={result.get('succeeded')}"
                )
            except Exception as e:
                logger.error(f"Background evolution {sug_id} failed: {e}")
                results.append({
                    "suggestion_id": sug_id,
                    "succeeded": False,
                    "error": str(e),
                })

    return results


# ── Trigger 2: Tool Degradation Detection ────────────

def run_trigger2(run_id: str) -> list[dict]:
    """
    Detect degraded tools and propose evolutions for affected skills.
    Runs in background after every execution.
    """
    store = SkillStore(DB_PATH)
    try:
        # 1. Get currently problematic tools
        problematic = store.get_problematic_tools(
            TOOL_DEGRADED_RATE, TOOL_MIN_CALLS, TOOL_ROLLING_WINDOW
        )
        problematic_names = {t["tool_name"] for t in problematic}

        # 2. Clear recovered tools from addressed set
        with _addressed_lock:
            for tool_key in list(_addressed_degradations.keys()):
                if tool_key not in problematic_names:
                    del _addressed_degradations[tool_key]
                    logger.info(f"Tool '{tool_key}' recovered — cleared from addressed set")

        if not problematic:
            return []

        logger.info(
            f"Trigger 2: {len(problematic)} degraded tool(s): "
            f"{[t['tool_name'] for t in problematic]}"
        )

        # 3. For each problematic tool, find affected skills
        evolutions_to_run: list[tuple[str, str, str, str]] = []

        for tool in problematic:
            tool_name = tool["tool_name"]
            success_rate = tool["success_rate"]
            total_calls = tool["total_calls"]

            skill_ids = store.get_skills_for_tool(tool_name)
            if not skill_ids:
                continue

            for skill_id in skill_ids:
                # 4. Skip if already addressed
                with _addressed_lock:
                    if skill_id in _addressed_degradations.get(tool_name, set()):
                        continue

                skill = store.get_skill(skill_id)
                if not skill or skill.status != "active":
                    continue

                # 5. Build context for confirmation gate
                direction = (
                    f"Tool '{tool_name}' is degraded (success rate: "
                    f"{success_rate:.0%}, last {total_calls} calls). "
                    f"Update this skill to handle tool failures gracefully, "
                    f"add retry logic, or suggest alternative approaches when "
                    f"this tool fails."
                )

                trigger_context = (
                    f"Tool degradation detected: '{tool_name}' has a "
                    f"{success_rate:.0%} success rate over its last "
                    f"{total_calls} calls (threshold: {TOOL_DEGRADED_RATE:.0%})."
                )

                recent = store.get_recent_judgments_for_skill(skill_id, 5)
                recent_str = (
                    json.dumps(recent, indent=2) if recent else "No recent history."
                )

                # 6. LLM confirmation gate
                confirmation = confirm_evolution(
                    skill_id=skill_id,
                    skill_content=skill.content,
                    proposed_type="fix",
                    proposed_direction=direction,
                    trigger_context=trigger_context,
                    recent_analyses=recent_str,
                )

                # 7. Mark as addressed regardless of confirmation outcome
                with _addressed_lock:
                    _addressed_degradations.setdefault(tool_name, set()).add(skill_id)

                if confirmation and confirmation.proceed:
                    final_direction = confirmation.adjusted_direction or direction
                    sug_id = store.insert_evolution_suggestion(
                        run_id=run_id,
                        trigger="trigger2",
                        suggestion={
                            "type": "fix",
                            "target_skills": [skill_id],
                            "direction": final_direction,
                            "reason": confirmation.reasoning,
                            "priority": "high",
                            "pattern_key": f"tool.degraded-{tool_name}",
                        },
                    )
                    evolutions_to_run.append(
                        (sug_id, skill_id, final_direction, "fix")
                    )
                    logger.info(
                        f"Trigger 2: confirmed evolution for skill "
                        f"'{skill_id}' due to tool '{tool_name}'"
                    )
                else:
                    logger.info(
                        f"Trigger 2: skipped evolution for skill "
                        f"'{skill_id}' — confirmation gate rejected"
                    )

        # 8. Execute confirmed evolutions in parallel
        return _execute_evolutions_parallel(evolutions_to_run)

    except Exception as e:
        logger.error(f"Trigger 2 failed: {e}", exc_info=True)
        return []
    finally:
        store.close()


# ── Trigger 3: Periodic Skill Health Check ───────────

def _compute_skill_metrics(skill) -> dict:
    """Compute health metrics from skill counters."""
    sel = max(skill.total_selections, 1)
    app = max(skill.total_applied, 1)
    return {
        "fallback_rate": skill.total_fallbacks / sel,
        "applied_rate": skill.total_applied / sel,
        "completion_rate": skill.total_completions / app if skill.total_applied > 0 else 0.0,
        "effective_rate": skill.total_completions / sel,
    }


def _diagnose_skill(metrics: dict) -> tuple[str, str] | None:
    """
    Rule-based diagnosis from the spec.
    Returns (evolution_type, direction) or None.
    """
    if metrics["fallback_rate"] > FALLBACK_THRESHOLD:
        return (
            "fix",
            "High fallback rate: skill is being selected but cannot be applied. "
            "Instructions may be outdated or reference unavailable tools.",
        )

    if (
        metrics["applied_rate"] > HIGH_APPLIED_FOR_FIX
        and metrics["completion_rate"] < LOW_COMPLETION_THRESHOLD
    ):
        return (
            "fix",
            "Low completion despite reasonable application rate: skill "
            "instructions may be incorrect or incomplete.",
        )

    if (
        metrics["effective_rate"] < MODERATE_EFFECTIVE_THRESHOLD
        and metrics["applied_rate"] > MIN_APPLIED_FOR_DERIVED
    ):
        return (
            "derived",
            "Moderate effective rate: skill could benefit from improvement "
            "— better steps, error handling, or broader scope.",
        )

    return None


def run_trigger3() -> list[dict]:
    """
    Periodic health check — diagnose underperforming skills and propose evolutions.
    Runs in background every METRIC_CHECK_EVERY_N_EXECUTIONS runs.
    """
    store = SkillStore(DB_PATH)
    try:
        active_skills = store.get_active_skills()
        evolutions_to_run: list[tuple[str, str, str, str]] = []

        logger.info(
            f"Trigger 3: checking {len(active_skills)} active skill(s)"
        )

        for skill in active_skills:
            # Skip skills without enough data
            if skill.total_selections < METRIC_MIN_SELECTIONS_TO_EVALUATE:
                continue

            # Compute metrics and diagnose
            metrics = _compute_skill_metrics(skill)
            diagnosis = _diagnose_skill(metrics)

            if not diagnosis:
                continue

            evo_type, direction = diagnosis

            trigger_context = (
                f"Health check metrics — Selections: {skill.total_selections}, "
                f"Applied rate: {metrics['applied_rate']:.0%}, "
                f"Fallback rate: {metrics['fallback_rate']:.0%}, "
                f"Completion rate: {metrics['completion_rate']:.0%}, "
                f"Effective rate: {metrics['effective_rate']:.0%}"
            )

            recent = store.get_recent_judgments_for_skill(skill.id, 5)
            recent_str = (
                json.dumps(recent, indent=2) if recent else "No recent history."
            )

            # LLM confirmation gate
            confirmation = confirm_evolution(
                skill_id=skill.id,
                skill_content=skill.content,
                proposed_type=evo_type,
                proposed_direction=direction,
                trigger_context=trigger_context,
                recent_analyses=recent_str,
            )

            if confirmation and confirmation.proceed:
                final_direction = confirmation.adjusted_direction or direction
                sug_id = store.insert_evolution_suggestion(
                    run_id=None,
                    trigger="trigger3",
                    suggestion={
                        "type": evo_type,
                        "target_skills": [skill.id],
                        "direction": final_direction,
                        "reason": confirmation.reasoning,
                        "priority": "medium",
                        "pattern_key": f"health.{evo_type}-{skill.name}",
                    },
                )
                evolutions_to_run.append(
                    (sug_id, skill.id, final_direction, evo_type)
                )
                logger.info(
                    f"Trigger 3: confirmed {evo_type} evolution for "
                    f"'{skill.id}' — {trigger_context}"
                )
            else:
                logger.info(
                    f"Trigger 3: skipped evolution for '{skill.id}' "
                    f"— confirmation gate rejected"
                )

        # Execute confirmed evolutions in parallel
        return _execute_evolutions_parallel(evolutions_to_run)

    except Exception as e:
        logger.error(f"Trigger 3 failed: {e}", exc_info=True)
        return []
    finally:
        store.close()


# ── Background Dispatcher ────────────────────────────

def dispatch_background_triggers(run_id: str):
    """
    Spawn background threads for Trigger 2 (always) and Trigger 3
    (every N executions). Non-blocking — returns immediately.
    """
    # Trigger 2: always fires in background
    t2 = threading.Thread(
        target=run_trigger2,
        args=(run_id,),
        daemon=True,
        name=f"trigger2-{run_id}",
    )
    t2.start()
    logger.info(f"Trigger 2 dispatched in background for run {run_id}")

    # Trigger 3: check run count, fire if divisible by N
    store = SkillStore(DB_PATH)
    try:
        run_count = store.get_run_count()
        if run_count > 0 and run_count % METRIC_CHECK_EVERY_N_EXECUTIONS == 0:
            t3 = threading.Thread(
                target=run_trigger3,
                daemon=True,
                name=f"trigger3-{run_id}",
            )
            t3.start()
            logger.info(
                f"Trigger 3 dispatched in background "
                f"(run count: {run_count})"
            )
        else:
            logger.debug(
                f"Trigger 3 skipped (run count: {run_count}, "
                f"fires every {METRIC_CHECK_EVERY_N_EXECUTIONS})"
            )
    finally:
        store.close()
