"""Skills endpoints: list, detail, lineage, rollback."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query

from src.dashboard.dependencies import get_store
from src.dashboard.models import RollbackRequest
from src.dashboard.serializers import serialize_skill
from src.skill_engine.store import SkillStore
from src.skill_engine.types import SkillRecord

router = APIRouter()


@router.get("/skills")
def list_skills(
    active_only: bool = Query(True),
    sort: str = Query("score"),
    limit: int = Query(100),
    query: str = Query(""),
    store: SkillStore = Depends(get_store),
):
    if active_only:
        skills = store.get_active_skills()
    else:
        rows = store.conn.execute("SELECT * FROM skills").fetchall()
        skills = [SkillRecord(**dict(r)) for r in rows]

    # Search filter
    if query:
        q = query.lower()
        skills = [
            s for s in skills
            if q in (s.name or "").lower()
            or q in (s.description or "").lower()
        ]

    serialized = [serialize_skill(s) for s in skills]

    # Sort
    sort_key = {
        "score": lambda x: x["score"],
        "updated": lambda x: x["last_updated"],
        "selections": lambda x: x["total_selections"],
    }.get(sort, lambda x: x["score"])
    serialized.sort(key=sort_key, reverse=True)

    return {"items": serialized[:limit], "count": len(serialized)}


@router.get("/skills/{skill_id}")
def get_skill_detail(skill_id: str, store: SkillStore = Depends(get_store)):
    skill = store.get_skill(skill_id)
    if not skill:
        raise HTTPException(404, "Skill not found")

    data = serialize_skill(skill)

    # Lineage — all versions of the same name
    rows = store.conn.execute(
        "SELECT * FROM skills WHERE name = ? ORDER BY generation",
        (skill.name,),
    ).fetchall()
    lineage = [serialize_skill(SkillRecord(**dict(r))) for r in rows]
    data["lineage"] = lineage

    # Recent judgments
    judgments = store.conn.execute(
        "SELECT * FROM skill_judgments WHERE skill_id = ? ORDER BY run_id DESC LIMIT 10",
        (skill_id,),
    ).fetchall()
    data["recent_judgments"] = [dict(j) for j in judgments]

    return data


@router.get("/skills/{skill_id}/lineage")
def get_skill_lineage(skill_id: str, store: SkillStore = Depends(get_store)):
    skill = store.get_skill(skill_id)
    if not skill:
        raise HTTPException(404, "Skill not found")

    rows = store.conn.execute(
        "SELECT * FROM skills WHERE name = ? ORDER BY generation",
        (skill.name,),
    ).fetchall()

    nodes = []
    edges = []
    for r in rows:
        rec = SkillRecord(**dict(r))
        nodes.append({
            "id": rec.id,
            "name": rec.name,
            "generation": rec.generation,
            "status": rec.status,
            "lineage_origin": rec.lineage_origin,
            "effective_rate": rec.total_completions / max(rec.total_selections, 1),
        })
        if rec.parent_id:
            edges.append({"source": rec.parent_id, "target": rec.id})

    # Also check skill_parents for multi-parent
    for r in rows:
        parents = store.conn.execute(
            "SELECT parent_id FROM skill_parents WHERE skill_id = ?",
            (dict(r)["id"],),
        ).fetchall()
        for p in parents:
            edge = {"source": p["parent_id"], "target": dict(r)["id"]}
            if edge not in edges:
                edges.append(edge)

    return {"skill_id": skill_id, "nodes": nodes, "edges": edges}


@router.post("/skills/{skill_id}/rollback")
def rollback_skill(
    skill_id: str,
    req: RollbackRequest,
    store: SkillStore = Depends(get_store),
):
    target = store.get_skill(req.target_version_id)
    if not target:
        raise HTTPException(404, "Target version not found")

    current = store.get_skill(skill_id)
    if not current:
        raise HTTPException(404, "Current skill not found")

    # Create new version with old content
    new_id = store.make_skill_id(target.name, current.generation + 1)
    new_record = SkillRecord(
        id=new_id,
        name=target.name,
        description=target.description,
        category=target.category,
        content=target.content,
        status="active",
        generation=current.generation + 1,
        parent_id=skill_id,
        lineage_origin="ROLLBACK",
    )

    # Supersede current
    store.conn.execute(
        "UPDATE skills SET status = 'superseded' WHERE id = ?", (skill_id,)
    )
    store.insert_skill(new_record)
    store.insert_audit(new_id, "rollback", note=f"Rolled back to {req.target_version_id}")
    store.conn.commit()

    return serialize_skill(new_record)
