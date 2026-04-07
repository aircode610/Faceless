"""Execution runs endpoints: list, detail."""

from __future__ import annotations

import json
import os

from fastapi import APIRouter, Depends, HTTPException, Query

from src.dashboard.dependencies import get_store
from src.skill_engine.store import SkillStore

router = APIRouter()


@router.get("/runs")
def list_runs(
    limit: int = Query(50),
    status: str = Query(""),
    skill_id: str = Query(""),
    store: SkillStore = Depends(get_store),
):
    query = "SELECT * FROM runs WHERE 1=1"
    params = []

    if status:
        query += " AND execution_status = ?"
        params.append(status)

    if skill_id:
        query += " AND selected_skill_ids LIKE ?"
        params.append(f"%{skill_id}%")

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = store.conn.execute(query, params).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        d["selected_skill_ids"] = json.loads(d.get("selected_skill_ids") or "[]")
        d["llm_task_completed"] = bool(d.get("llm_task_completed"))
        items.append(d)

    count_row = store.conn.execute("SELECT COUNT(*) FROM runs").fetchone()
    return {"items": items, "count": count_row[0]}


@router.get("/runs/{run_id}")
def get_run_detail(run_id: str, store: SkillStore = Depends(get_store)):
    row = store.conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Run not found")

    data = dict(row)
    data["selected_skill_ids"] = json.loads(data.get("selected_skill_ids") or "[]")
    data["llm_task_completed"] = bool(data.get("llm_task_completed"))

    recording_dir = data.get("recording_dir", "")

    # Load conversations.jsonl
    conv_path = os.path.join(recording_dir, "conversations.jsonl") if recording_dir else ""
    conversation = []
    if conv_path and os.path.exists(conv_path):
        with open(conv_path) as f:
            conversation = [json.loads(line) for line in f if line.strip()]
    data["conversation"] = conversation

    # Load traj.jsonl
    traj_path = os.path.join(recording_dir, "traj.jsonl") if recording_dir else ""
    trajectory = []
    if traj_path and os.path.exists(traj_path):
        with open(traj_path) as f:
            trajectory = [json.loads(line) for line in f if line.strip()]
    data["trajectory"] = trajectory

    # Skill judgments
    judgments = store.conn.execute(
        "SELECT * FROM skill_judgments WHERE run_id = ?", (run_id,)
    ).fetchall()
    data["skill_judgments"] = [dict(j) for j in judgments]

    # Evolution suggestions from this run
    evos = store.conn.execute(
        "SELECT * FROM evolution_suggestions WHERE run_id = ?", (run_id,)
    ).fetchall()
    data["evolution_suggestions"] = [dict(e) for e in evos]

    return data
