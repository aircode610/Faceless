"""
"A man must choose carefully which face to wear."
Skill selection: quality pre-filter + LLM selection.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from src.config import (
    MAX_SKILLS_PER_TASK,
    QUALITY_FILTER_MIN_SELECTIONS,
)
from src.llm import get_llm
from src.prompts.skill_engine_prompts import SKILL_SELECTION_TEMPLATE
from src.skill_engine.store import SkillStore
from src.skill_engine.types import SkillRecord, SkillSelectionResult


def _fallback_rate(skill: SkillRecord) -> float:
    if skill.total_selections == 0:
        return 0.0
    return skill.total_fallbacks / skill.total_selections


def quality_prefilter(skills: list[SkillRecord]) -> list[SkillRecord]:
    """Exclude demonstrably broken skills before LLM sees them."""
    result = []
    for skill in skills:
        # Never applied despite being selected multiple times
        if (
            skill.total_selections >= QUALITY_FILTER_MIN_SELECTIONS
            and skill.total_completions == 0
        ):
            continue
        # High fallback rate
        if (
            skill.total_applied >= QUALITY_FILTER_MIN_SELECTIONS
            and _fallback_rate(skill) > 0.5
        ):
            continue
        result.append(skill)
    return result


def _format_catalog(skills: list[SkillRecord]) -> str:
    """Format skills for the LLM selector."""
    lines = []
    for s in skills:
        completions = s.total_completions
        applied = max(s.total_applied, 1)
        rate = completions / applied
        desc = (s.description or "No description")[:200]
        lines.append(
            f"{s.id} — {s.name}: {desc} "
            f"(success {completions}/{s.total_applied} = {rate:.0%})"
        )
    return "\n".join(lines)


def select_skills(
    task_description: str,
    store: SkillStore,
    max_skills: int = MAX_SKILLS_PER_TASK,
) -> list[str]:
    """
    Two-stage skill selection:
      1. Quality pre-filter
      2. LLM picks the best skills for the task

    Returns list of skill IDs.
    """
    active_skills = store.get_active_skills()

    if not active_skills:
        return []

    filtered = quality_prefilter(active_skills)

    if not filtered:
        return []

    catalog_str = _format_catalog(filtered)

    llm = get_llm()
    structured_llm = llm.with_structured_output(SkillSelectionResult)

    prompt = SKILL_SELECTION_TEMPLATE.format(
        task=task_description,
        skills_catalog=catalog_str,
        max_skills=max_skills,
    )

    result: SkillSelectionResult = structured_llm.invoke(
        [HumanMessage(content=prompt)]
    )

    # Validate that returned IDs actually exist in our filtered set
    valid_ids = {s.id for s in filtered}
    selected = [sid for sid in result.skills if sid in valid_ids]

    return selected[:max_skills]
