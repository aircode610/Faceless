"""
"Every face tells a story." — Serializers for DB records → API responses.
"""

from __future__ import annotations

from src.skill_engine.types import SkillRecord


def serialize_skill(skill: SkillRecord) -> dict:
    """Convert a SkillRecord to the API Skill shape."""
    selections = max(skill.total_selections, 1)
    applied = max(skill.total_applied, 1)

    applied_rate = skill.total_applied / selections
    completion_rate = skill.total_completions / applied
    effective_rate = skill.total_completions / selections
    fallback_rate = skill.total_fallbacks / selections

    return {
        "skill_id": skill.id,
        "name": skill.name,
        "description": skill.description or "",
        "category": skill.category or "workflow",
        "is_active": skill.status == "active",
        "status": skill.status,
        "generation": skill.generation,
        "lineage_origin": skill.lineage_origin or "BOOTSTRAP",
        "parent_id": skill.parent_id,
        "content": skill.content,
        "total_selections": skill.total_selections,
        "total_applied": skill.total_applied,
        "total_completions": skill.total_completions,
        "total_fallbacks": skill.total_fallbacks,
        "applied_rate": round(applied_rate, 3),
        "completion_rate": round(completion_rate, 3),
        "effective_rate": round(effective_rate, 3),
        "fallback_rate": round(fallback_rate, 3),
        "score": round(effective_rate * 100, 1),
        "created_at": skill.created_at,
        "last_updated": skill.last_updated,
    }
