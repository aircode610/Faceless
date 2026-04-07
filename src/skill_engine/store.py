"""
The ledger of the House of Black and White.
SQLite storage for skills, runs, and evolution state.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone

from src.skill_engine.types import SkillRecord


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_id() -> str:
    return uuid.uuid4().hex[:8]


class SkillStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    # ── Schema ───────────────────────────────────────

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS skills (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT,
                content TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                generation INTEGER DEFAULT 0,
                parent_id TEXT,
                lineage_origin TEXT,
                content_diff TEXT,
                content_snapshot TEXT,
                total_selections INTEGER DEFAULT 0,
                total_applied INTEGER DEFAULT 0,
                total_completions INTEGER DEFAULT 0,
                total_fallbacks INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                last_updated TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_skills_name_status ON skills(name, status);

            CREATE TABLE IF NOT EXISTS skill_parents (
                skill_id TEXT NOT NULL,
                parent_id TEXT NOT NULL,
                PRIMARY KEY (skill_id, parent_id),
                FOREIGN KEY (skill_id) REFERENCES skills(id),
                FOREIGN KEY (parent_id) REFERENCES skills(id)
            );

            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                task_description TEXT NOT NULL,
                selected_skill_ids TEXT,
                execution_status TEXT,
                iterations INTEGER,
                recording_dir TEXT,
                llm_task_completed INTEGER,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS skill_judgments (
                run_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                skill_applied INTEGER NOT NULL,
                note TEXT,
                PRIMARY KEY (run_id, skill_id),
                FOREIGN KEY (run_id) REFERENCES runs(id),
                FOREIGN KEY (skill_id) REFERENCES skills(id)
            );

            CREATE TABLE IF NOT EXISTS evolution_suggestions (
                id TEXT PRIMARY KEY,
                run_id TEXT,
                trigger TEXT NOT NULL,
                type TEXT NOT NULL,
                target_skill_ids TEXT,
                category TEXT,
                direction TEXT NOT NULL,
                priority TEXT DEFAULT 'medium',
                pattern_key TEXT,
                recurrence_count INTEGER DEFAULT 1,
                run_ids TEXT,
                status TEXT DEFAULT 'pending_execution',
                resulting_skill_id TEXT,
                created_at TEXT NOT NULL,
                last_seen TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_evolution_pattern_key
                ON evolution_suggestions(pattern_key);

            CREATE TABLE IF NOT EXISTS feature_requests (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                capability TEXT NOT NULL,
                user_context TEXT,
                complexity TEXT,
                priority TEXT DEFAULT 'medium',
                recurrence_count INTEGER DEFAULT 1,
                run_ids TEXT,
                status TEXT DEFAULT 'pending',
                resulting_skill_id TEXT,
                created_at TEXT NOT NULL,
                last_seen TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tool_calls (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                success INTEGER NOT NULL,
                duration_ms INTEGER,
                error_message TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tool_calls_name
                ON tool_calls(tool_name, created_at);

            CREATE TABLE IF NOT EXISTS skill_tool_deps (
                skill_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                PRIMARY KEY (skill_id, tool_name),
                FOREIGN KEY (skill_id) REFERENCES skills(id)
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                action TEXT NOT NULL,
                reviewer TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                parent_id TEXT,
                content_diff TEXT,
                benchmark_passed INTEGER,
                benchmark_details TEXT,
                note TEXT
            );
        """)
        self.conn.commit()

    # ── Skills CRUD ──────────────────────────────────

    def make_skill_id(self, name: str, generation: int = 0) -> str:
        return f"{name}__v{generation + 1}_{_short_id()}"

    def insert_skill(self, skill: SkillRecord) -> str:
        now = _now()
        skill.created_at = skill.created_at or now
        skill.last_updated = skill.last_updated or now
        skill.content_snapshot = skill.content

        self.conn.execute(
            """INSERT INTO skills
               (id, name, description, category, content, status, generation,
                parent_id, lineage_origin, content_diff, content_snapshot,
                total_selections, total_applied, total_completions, total_fallbacks,
                created_at, last_updated)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                skill.id, skill.name, skill.description, skill.category,
                skill.content, skill.status, skill.generation,
                skill.parent_id, skill.lineage_origin,
                skill.content_diff, skill.content_snapshot,
                skill.total_selections, skill.total_applied,
                skill.total_completions, skill.total_fallbacks,
                skill.created_at, skill.last_updated,
            ),
        )
        self.conn.commit()
        return skill.id

    def get_active_skills(self) -> list[SkillRecord]:
        rows = self.conn.execute(
            "SELECT * FROM skills WHERE status = 'active'"
        ).fetchall()
        return [SkillRecord(**dict(r)) for r in rows]

    def get_skill(self, skill_id: str) -> SkillRecord | None:
        row = self.conn.execute(
            "SELECT * FROM skills WHERE id = ?", (skill_id,)
        ).fetchone()
        return SkillRecord(**dict(row)) if row else None

    # ── Runs ─────────────────────────────────────────

    def insert_run(
        self,
        run_id: str,
        task_description: str,
        selected_skill_ids: list[str],
        execution_status: str,
        iterations: int,
        recording_dir: str,
    ) -> str:
        self.conn.execute(
            """INSERT INTO runs
               (id, task_description, selected_skill_ids, execution_status,
                iterations, recording_dir, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (
                run_id, task_description, json.dumps(selected_skill_ids),
                execution_status, iterations, recording_dir, _now(),
            ),
        )
        self.conn.commit()
        return run_id

    def update_run_analysis(self, run_id: str, task_completed: bool):
        self.conn.execute(
            "UPDATE runs SET llm_task_completed = ? WHERE id = ?",
            (1 if task_completed else 0, run_id),
        )
        self.conn.commit()

    def get_run_count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) FROM runs").fetchone()
        return row[0]

    # ── Skill Judgments ──────────────────────────────

    def insert_judgment(self, run_id: str, skill_id: str, applied: bool, note: str):
        self.conn.execute(
            """INSERT OR REPLACE INTO skill_judgments
               (run_id, skill_id, skill_applied, note) VALUES (?,?,?,?)""",
            (run_id, skill_id, 1 if applied else 0, note),
        )
        self.conn.commit()

    def update_skill_counters(
        self, skill_id: str, applied: bool, task_completed: bool
    ):
        self.conn.execute(
            """UPDATE skills SET
                total_selections = total_selections + 1,
                total_applied = total_applied + ?,
                total_completions = total_completions + ?,
                total_fallbacks = total_fallbacks + ?,
                last_updated = ?
               WHERE id = ?""",
            (
                1 if applied else 0,
                1 if (applied and task_completed) else 0,
                1 if (not applied and not task_completed) else 0,
                _now(),
                skill_id,
            ),
        )
        self.conn.commit()

    # ── Evolution Suggestions ────────────────────────

    def insert_evolution_suggestion(
        self, run_id: str | None, trigger: str, suggestion: dict
    ) -> str:
        evo_id = f"evo_{_short_id()}"
        now = _now()
        self.conn.execute(
            """INSERT INTO evolution_suggestions
               (id, run_id, trigger, type, target_skill_ids, category,
                direction, priority, pattern_key, run_ids, created_at, last_seen)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                evo_id, run_id, trigger,
                suggestion.get("type", "fix"),
                json.dumps(suggestion.get("target_skills", [])),
                suggestion.get("category", "workflow"),
                suggestion.get("direction", ""),
                suggestion.get("priority", "medium"),
                suggestion.get("pattern_key", ""),
                json.dumps([run_id] if run_id else []),
                now, now,
            ),
        )
        self.conn.commit()
        return evo_id

    def get_suggestion_by_pattern_key(self, pattern_key: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM evolution_suggestions WHERE pattern_key = ? ORDER BY created_at DESC LIMIT 1",
            (pattern_key,),
        ).fetchone()
        return dict(row) if row else None

    def increment_recurrence(self, evo_id: str, new_run_id: str):
        row = self.conn.execute(
            "SELECT run_ids, recurrence_count FROM evolution_suggestions WHERE id = ?",
            (evo_id,),
        ).fetchone()
        if row:
            run_ids = json.loads(row["run_ids"] or "[]")
            if new_run_id not in run_ids:
                run_ids.append(new_run_id)
            self.conn.execute(
                """UPDATE evolution_suggestions SET
                    recurrence_count = recurrence_count + 1,
                    run_ids = ?, last_seen = ?
                   WHERE id = ?""",
                (json.dumps(run_ids), _now(), evo_id),
            )
            self.conn.commit()

    def count_distinct_runs_for_pattern(self, pattern_key: str) -> int:
        row = self.conn.execute(
            "SELECT run_ids FROM evolution_suggestions WHERE pattern_key = ?",
            (pattern_key,),
        ).fetchone()
        if row and row["run_ids"]:
            return len(set(json.loads(row["run_ids"])))
        return 0

    def update_priority(self, evo_id: str, new_priority: str):
        self.conn.execute(
            "UPDATE evolution_suggestions SET priority = ? WHERE id = ?",
            (new_priority, evo_id),
        )
        self.conn.commit()

    def update_suggestion_status(
        self, evo_id: str, status: str, resulting_skill_id: str | None = None
    ):
        if resulting_skill_id:
            self.conn.execute(
                "UPDATE evolution_suggestions SET status = ?, resulting_skill_id = ? WHERE id = ?",
                (status, resulting_skill_id, evo_id),
            )
        else:
            self.conn.execute(
                "UPDATE evolution_suggestions SET status = ? WHERE id = ?",
                (status, evo_id),
            )
        self.conn.commit()

    def get_pending_suggestions(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM evolution_suggestions WHERE status = 'pending_execution' ORDER BY created_at"
        ).fetchall()
        return [dict(r) for r in rows]

    def supersede_skill(self, skill_id: str):
        self.conn.execute(
            "UPDATE skills SET status = 'superseded', last_updated = ? WHERE id = ?",
            (_now(), skill_id),
        )
        self.conn.commit()

    # ── Feature Requests ─────────────────────────────

    def insert_feature_request(self, run_id: str, feat: dict) -> str:
        feat_id = f"feat_{_short_id()}"
        now = _now()
        self.conn.execute(
            """INSERT INTO feature_requests
               (id, run_id, capability, user_context, complexity,
                run_ids, created_at, last_seen)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                feat_id, run_id,
                feat.get("capability", ""),
                feat.get("user_context", ""),
                feat.get("complexity", "medium"),
                json.dumps([run_id]),
                now, now,
            ),
        )
        self.conn.commit()
        return feat_id

    # ── Tool Calls ───────────────────────────────────

    def insert_tool_call(
        self, run_id: str, tool_name: str, success: bool,
        duration_ms: int | None = None, error_message: str | None = None
    ):
        self.conn.execute(
            """INSERT INTO tool_calls
               (id, run_id, tool_name, success, duration_ms, error_message, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (
                f"tc_{_short_id()}", run_id, tool_name,
                1 if success else 0, duration_ms,
                (error_message or "")[:1000], _now(),
            ),
        )
        self.conn.commit()

    # ── Audit Log ────────────────────────────────────

    def insert_audit(
        self, skill_id: str, action: str, reviewer: str = "system", note: str = ""
    ):
        self.conn.execute(
            """INSERT INTO audit_log
               (id, skill_id, action, reviewer, timestamp, note)
               VALUES (?,?,?,?,?,?)""",
            (f"audit_{_short_id()}", skill_id, action, reviewer, _now(), note),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()
