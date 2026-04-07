"""
FastAPI dependency for database access.
"""

from __future__ import annotations

from src.config import DB_PATH
from src.skill_engine.store import SkillStore

# Single connection reused across requests (SQLite is single-writer anyway)
_store: SkillStore | None = None


def get_store() -> SkillStore:
    global _store
    if _store is None:
        _store = SkillStore(DB_PATH)
    return _store
