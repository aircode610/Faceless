"""Review queue endpoints: list, detail, approve, reject, features."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException

from src.dashboard.dependencies import get_store
from src.dashboard.models import ApproveRequest, DismissFeatureRequest, RejectRequest
from src.dashboard.serializers import serialize_skill
from src.skill_engine.store import SkillStore
from src.skill_engine.types import SkillRecord

router = APIRouter()

PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


@router.get("/review/queue")
def get_review_queue(store: SkillStore = Depends(get_store)):
    # Get all pending skills
    rows = store.conn.execute(
        "SELECT * FROM skills WHERE status = 'pending'"
    ).fetchall()

    items = []
    for r in rows:
        skill = SkillRecord(**dict(r))
        data = serialize_skill(skill)

        # Get evolution suggestion info for this skill
        evo = store.conn.execute(
            "SELECT * FROM evolution_suggestions WHERE resulting_skill_id = ? "
            "ORDER BY created_at DESC LIMIT 1",
            (skill.id,),
        ).fetchone()

        if evo:
            evo = dict(evo)
            data["priority"] = evo.get("priority", "medium")
            data["pattern_key"] = evo.get("pattern_key")
            data["recurrence_count"] = evo.get("recurrence_count", 1)
            data["direction"] = evo.get("direction", "")
            data["reason"] = evo.get("reason", "") or ""
            data["evolution_type"] = evo.get("type", "fix")
            data["source_run_id"] = evo.get("run_id")
        else:
            data["priority"] = "medium"
            data["pattern_key"] = None
            data["recurrence_count"] = 1
            data["direction"] = ""
            data["reason"] = ""
            data["evolution_type"] = "fix"
            data["source_run_id"] = None

        data["content_diff"] = skill.content_diff
        data["parent_content_snapshot"] = None
        if skill.parent_id:
            parent = store.get_skill(skill.parent_id)
            if parent:
                data["parent_content_snapshot"] = parent.content_snapshot or parent.content

        items.append(data)

    # Sort by priority
    items.sort(key=lambda x: PRIORITY_ORDER.get(x.get("priority", "medium"), 2))

    return items


# ── Feature Requests (must be before parameterized /review/{skill_id}) ───

@router.get("/review/features")
def get_feature_requests(store: SkillStore = Depends(get_store)):
    rows = store.conn.execute(
        "SELECT * FROM feature_requests ORDER BY created_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


@router.post("/review/features/{feat_id}/accept")
def accept_feature(feat_id: str, store: SkillStore = Depends(get_store)):
    row = store.conn.execute(
        "SELECT * FROM feature_requests WHERE id = ?", (feat_id,)
    ).fetchone()
    if not row:
        raise HTTPException(404, "Feature request not found")

    store.conn.execute(
        "UPDATE feature_requests SET status = 'accepted' WHERE id = ?", (feat_id,)
    )
    store.conn.commit()
    return {"status": "accepted", "feat_id": feat_id}


@router.post("/review/features/{feat_id}/defer")
def defer_feature(feat_id: str, store: SkillStore = Depends(get_store)):
    store.conn.execute(
        "UPDATE feature_requests SET status = 'deferred' WHERE id = ?", (feat_id,)
    )
    store.conn.commit()
    return {"status": "deferred"}


@router.post("/review/features/{feat_id}/dismiss")
def dismiss_feature(
    feat_id: str,
    req: DismissFeatureRequest,
    store: SkillStore = Depends(get_store),
):
    store.conn.execute(
        "UPDATE feature_requests SET status = 'wont_fix' WHERE id = ?", (feat_id,)
    )
    store.conn.commit()
    return {"status": "wont_fix"}


# ── Parameterized review detail (after fixed routes) ─

@router.get("/review/{skill_id}")
def get_review_detail(skill_id: str, store: SkillStore = Depends(get_store)):
    skill = store.get_skill(skill_id)
    if not skill:
        raise HTTPException(404, "Skill not found")
    if skill.status != "pending":
        raise HTTPException(400, "Skill is not pending review")

    data = serialize_skill(skill)
    data["content_diff"] = skill.content_diff
    data["parent_content_snapshot"] = None
    if skill.parent_id:
        parent = store.get_skill(skill.parent_id)
        if parent:
            data["parent_content_snapshot"] = parent.content_snapshot or parent.content

    evo = store.conn.execute(
        "SELECT * FROM evolution_suggestions WHERE resulting_skill_id = ? "
        "ORDER BY created_at DESC LIMIT 1",
        (skill_id,),
    ).fetchone()
    if evo:
        evo = dict(evo)
        data["priority"] = evo.get("priority", "medium")
        data["pattern_key"] = evo.get("pattern_key")
        data["recurrence_count"] = evo.get("recurrence_count", 1)
        data["direction"] = evo.get("direction", "")
        data["reason"] = evo.get("reason", "") or ""
        data["evolution_type"] = evo.get("type", "fix")
        data["source_run_id"] = evo.get("run_id")

    return data


@router.post("/review/{skill_id}/approve")
def approve_skill(
    skill_id: str,
    req: ApproveRequest,
    store: SkillStore = Depends(get_store),
):
    skill = store.get_skill(skill_id)
    if not skill:
        raise HTTPException(404, "Skill not found")
    if skill.status != "pending":
        raise HTTPException(400, "Skill is not pending")

    # If edited content provided, update it
    if req.edited_content:
        store.conn.execute(
            "UPDATE skills SET content = ? WHERE id = ?",
            (req.edited_content, skill_id),
        )

    # Supersede old active version
    store.conn.execute(
        "UPDATE skills SET status = 'superseded' WHERE name = ? AND status = 'active' AND id != ?",
        (skill.name, skill_id),
    )

    # Activate this one
    store.conn.execute(
        "UPDATE skills SET status = 'active' WHERE id = ?", (skill_id,)
    )
    store.conn.commit()

    action = "edited_and_approved" if req.edited_content else "approved"
    store.insert_audit(skill_id, action, reviewer=req.reviewer_id, note=req.reason)

    return {"status": "approved", "skill_id": skill_id}


@router.post("/review/{skill_id}/reject")
def reject_skill(
    skill_id: str,
    req: RejectRequest,
    store: SkillStore = Depends(get_store),
):
    skill = store.get_skill(skill_id)
    if not skill:
        raise HTTPException(404, "Skill not found")
    if skill.status != "pending":
        raise HTTPException(400, "Skill is not pending")

    store.conn.execute(
        "UPDATE skills SET status = 'rejected' WHERE id = ?", (skill_id,)
    )
    store.conn.commit()
    store.insert_audit(skill_id, "rejected", reviewer=req.reviewer_id, note=req.reason)

    return {"status": "rejected", "skill_id": skill_id}
