"""GET /api/v1/overview — Dashboard summary."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.dashboard.dependencies import get_store
from src.dashboard.serializers import serialize_skill
from src.skill_engine.store import SkillStore

router = APIRouter()


@router.get("/overview")
def get_overview(store: SkillStore = Depends(get_store)):
    all_skills = store.get_active_skills()
    total_skills = len(all_skills)

    # Pending count
    pending_rows = store.conn.execute(
        "SELECT COUNT(*) FROM skills WHERE status = 'pending'"
    ).fetchone()
    pending_count = pending_rows[0]

    # Avg score
    avg_score = 0.0
    if all_skills:
        scores = []
        for s in all_skills:
            sel = max(s.total_selections, 1)
            scores.append(s.total_completions / sel * 100)
        avg_score = round(sum(scores) / len(scores), 1)

    # Run count
    total_runs = store.get_run_count()

    # Top 5 skills by score
    serialized = sorted(
        [serialize_skill(s) for s in all_skills],
        key=lambda x: x["score"],
        reverse=True,
    )
    top_skills = serialized[:5]

    # Recent 5 runs
    rows = store.conn.execute(
        "SELECT * FROM runs ORDER BY created_at DESC LIMIT 5"
    ).fetchall()
    recent_runs = [dict(r) for r in rows]

    # Pipeline stages
    pipeline = [
        {"name": "Bootstrap", "description": "MCP selection + constitution + skills"},
        {"name": "Select", "description": "Quality filter + LLM skill selection"},
        {"name": "Execute", "description": "Run execution agent with tools"},
        {"name": "Analyze", "description": "Post-execution analysis (Trigger 1)"},
        {"name": "Evolve", "description": "FIX / DERIVED / CAPTURED evolutions"},
        {"name": "Approve", "description": "Human review + benchmark guard"},
    ]

    return {
        "total_skills": total_skills,
        "avg_score": avg_score,
        "total_runs": total_runs,
        "pending_approvals": pending_count,
        "pipeline": pipeline,
        "top_skills": top_skills,
        "recent_runs": recent_runs,
    }
