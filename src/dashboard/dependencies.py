"""
FastAPI dependency for database access.

Each request gets its own SkillStore connection — simple, safe, and
avoids cursor races from sharing a single sqlite3 connection across
FastAPI's threadpool workers.
"""

from __future__ import annotations

from typing import Generator

from src.config import DB_PATH
from src.skill_engine.store import SkillStore


def get_store() -> Generator[SkillStore, None, None]:
    store = SkillStore(DB_PATH)
    try:
        yield store
    finally:
        store.close()
