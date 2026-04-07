"""Constitution endpoints: get, update, history."""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from glob import glob

from fastapi import APIRouter, Depends, HTTPException

from src.config import CONSTITUTION_PATH
from src.dashboard.dependencies import get_store
from src.dashboard.models import UpdateConstitutionRequest
from src.skill_engine.store import SkillStore

router = APIRouter()


def _get_version_count() -> int:
    """Count constitution versions (main file + backups)."""
    base_dir = os.path.dirname(CONSTITUTION_PATH)
    backups = glob(os.path.join(base_dir, "constitution_v*.md"))
    return len(backups) + 1


@router.get("/constitution")
def get_constitution():
    if not os.path.exists(CONSTITUTION_PATH):
        return {"content": "", "version": 0}

    with open(CONSTITUTION_PATH) as f:
        content = f.read()

    return {"content": content, "version": _get_version_count()}


@router.put("/constitution")
def update_constitution(
    req: UpdateConstitutionRequest,
    store: SkillStore = Depends(get_store),
):
    version = _get_version_count()

    # Backup current version
    if os.path.exists(CONSTITUTION_PATH):
        backup_path = os.path.join(
            os.path.dirname(CONSTITUTION_PATH),
            f"constitution_v{version}.md",
        )
        shutil.copy2(CONSTITUTION_PATH, backup_path)

    # Write new version
    with open(CONSTITUTION_PATH, "w") as f:
        f.write(req.content)

    new_version = version + 1

    store.insert_audit(
        "constitution", "constitution_edited",
        reviewer=req.editor_id,
        note=f"Updated to version {new_version}",
    )

    return {"version": new_version}


@router.get("/constitution/history")
def get_constitution_history():
    base_dir = os.path.dirname(CONSTITUTION_PATH)
    history = []

    # Current version
    if os.path.exists(CONSTITUTION_PATH):
        stat = os.stat(CONSTITUTION_PATH)
        with open(CONSTITUTION_PATH) as f:
            content = f.read()
        history.append({
            "version": _get_version_count(),
            "editor_id": "current",
            "timestamp": datetime.fromtimestamp(
                stat.st_mtime, tz=timezone.utc
            ).isoformat(),
            "content": content,
        })

    # Backup versions
    backups = sorted(glob(os.path.join(base_dir, "constitution_v*.md")))
    for bp in backups:
        fname = os.path.basename(bp)
        # Extract version number
        v = fname.replace("constitution_v", "").replace(".md", "")
        stat = os.stat(bp)
        with open(bp) as f:
            content = f.read()
        history.append({
            "version": int(v) if v.isdigit() else 0,
            "editor_id": "archived",
            "timestamp": datetime.fromtimestamp(
                stat.st_mtime, tz=timezone.utc
            ).isoformat(),
            "content": content,
        })

    history.sort(key=lambda x: x["version"], reverse=True)
    return history
