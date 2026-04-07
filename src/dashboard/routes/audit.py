"""Audit log endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.dashboard.dependencies import get_store
from src.skill_engine.store import SkillStore

router = APIRouter()


@router.get("/audit")
def get_audit_log(
    action: str = Query(""),
    skill_id: str = Query(""),
    limit: int = Query(100),
    store: SkillStore = Depends(get_store),
):
    query = "SELECT * FROM audit_log WHERE 1=1"
    params = []

    if action:
        query += " AND action = ?"
        params.append(action)

    if skill_id:
        query += " AND skill_id = ?"
        params.append(skill_id)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    rows = store.conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]
