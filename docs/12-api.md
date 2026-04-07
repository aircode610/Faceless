# API Server — FastAPI Backend

The dashboard backend exposes the SQLite data over a REST API consumed by the React frontend. It also serves the built frontend from `frontend/dist/`.

Reference implementation (Flask) to adapt from: `/Users/amirali.iranmanesh/JB/OpenSpace/openspace/dashboard_server.py`

---

## Setup

```python
# src/dashboard/server.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI(title="Agent Dashboard", version="1.0")

FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"

# Mount static assets
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

# SPA fallback — all non-API routes return index.html
@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(404)
    index = FRONTEND_DIST / "index.html"
    return FileResponse(str(index)) if index.exists() else {"error": "frontend not built"}
```

Run with: `uvicorn src.dashboard.server:app --host 0.0.0.0 --port 7788 --reload`

---

## All Endpoints

All API routes are prefixed with `/api/v1`.

### Overview

```
GET /api/v1/overview
```
Returns: skill summary stats, pipeline stage list, top-5 skills, recent-5 runs, system health.

---

### Skills

```
GET  /api/v1/skills
     ?active_only=true|false  (default true)
     &sort=score|updated|selections
     &limit=100
     &query=search_term
→ { items: Skill[], count: int }

GET  /api/v1/skills/{skill_id}
→ SkillDetail (includes lineage_graph, recent_analyses, source content)

GET  /api/v1/skills/{skill_id}/lineage
→ { skill_id, nodes: SkillLineageNode[], edges: SkillLineageEdge[] }

POST /api/v1/skills/{skill_id}/rollback
     body: { target_version_id: str }
→ SkillDetail (the new active record)
```

**`Skill` shape**:
```typescript
{
  skill_id: string          // "check-sql-injection__v2_e5f6"
  name: string
  description: string
  category: string          // "workflow" | "tool_guide" | "reference"
  is_active: boolean
  generation: number
  lineage_origin: string    // "BOOTSTRAP" | "FIXED" | "DERIVED" | "CAPTURED" | "ROLLBACK"
  total_selections: number
  total_applied: number
  total_completions: number
  total_fallbacks: number
  applied_rate: number
  completion_rate: number
  effective_rate: number
  fallback_rate: number
  score: number             // effective_rate * 100
  created_at: string
  last_updated: string
}
```

---

### Review Queue

```
GET  /api/v1/review/queue
→ ReviewItem[]    (all pending evolutions, sorted by priority)

GET  /api/v1/review/{skill_id}
→ ReviewItem      (includes content_diff and parent_content_snapshot)

POST /api/v1/review/{skill_id}/approve
     body: { reviewer_id: str, reason?: str, edited_content?: str }
→ { status: "approved", skill_id: str }

POST /api/v1/review/{skill_id}/reject
     body: { reviewer_id: str, reason: str }
→ { status: "rejected", skill_id: str }
```

**`ReviewItem` shape** (extends `Skill`):
```typescript
{
  ...Skill
  content_diff: string | null           // unified diff vs parent
  change_summary: string                // LLM one-liner
  parent_skill_ids: string[]
  parent_content_snapshot: string | null  // parent's SKILL.md content
  priority: "critical" | "high" | "medium" | "low"
  pattern_key: string | null
  recurrence_count: number
}
```

---

### Feature Requests

```
GET  /api/v1/review/features
→ FeatureRequest[]

POST /api/v1/review/features/{feat_id}/accept
→ { status: "accepted", resulting_evolution_id: str }

POST /api/v1/review/features/{feat_id}/defer
→ { status: "deferred" }

POST /api/v1/review/features/{feat_id}/dismiss
     body: { reason: str }
→ { status: "wont_fix" }
```

**`FeatureRequest` shape**:
```typescript
{
  id: string
  capability: string
  user_context: string
  complexity: "simple" | "medium" | "complex"
  priority: "critical" | "high" | "medium" | "low"
  recurrence_count: number
  status: "pending" | "accepted" | "deferred" | "wont_fix"
  created_at: string
  last_seen: string
}
```

---

### Execution Runs

```
GET /api/v1/runs
    ?limit=50 &status=success|incomplete|error &skill_id=...
→ { items: RunSummary[], count: int }

GET /api/v1/runs/{run_id}
→ RunDetail
```

**`RunSummary` shape**:
```typescript
{
  id: string
  task_description: string
  execution_status: string
  iterations: number
  selected_skill_ids: string[]
  llm_task_completed: boolean
  created_at: string
}
```

**`RunDetail`** adds:
```typescript
{
  ...RunSummary
  conversation: ConversationLine[]   // from conversations.jsonl
  trajectory: TrajectoryEntry[]      // from traj.jsonl
  skill_judgments: SkillJudgment[]   // from Trigger 1 output
  evolution_suggestions: EvolutionSuggestion[]
}
```

**`ConversationLine`**:
```typescript
{ role: "user"|"assistant"|"tool_call"|"tool_result", content: string, iter: number, name?: string, success?: boolean }
```

**`TrajectoryEntry`**:
```typescript
{ iter: number, tool: string, args: Record<string,unknown>, success: boolean, duration_ms: number }
```

---

### Constitution

```
GET /api/v1/constitution
→ { content: string, version: number }

PUT /api/v1/constitution
    body: { content: str, editor_id: str }
→ { version: number }

GET /api/v1/constitution/history
→ [{ version: number, editor_id: str, timestamp: str, content: str }]
```

---

### Audit Log

```
GET /api/v1/audit
    ?action=approved|rejected|rollback|...
    &skill_id=...
    &limit=100
→ AuditEntry[]
```

---

## Pydantic Models

Define in `src/dashboard/models.py`:

```python
from pydantic import BaseModel
from typing import Optional

class ApproveRequest(BaseModel):
    reviewer_id: str = "reviewer"
    reason: str = ""
    edited_content: Optional[str] = None

class RejectRequest(BaseModel):
    reviewer_id: str = "reviewer"
    reason: str

class RollbackRequest(BaseModel):
    target_version_id: str

class UpdateConstitutionRequest(BaseModel):
    content: str
    editor_id: str = "editor"
```

---

## File Layout

```
src/
  dashboard/
    server.py      ← FastAPI app, route registration, SPA fallback
    routes/
      overview.py
      skills.py
      review.py    ← queue, approve, reject, features
      runs.py
      constitution.py
      audit.py
    models.py      ← Pydantic request/response models
    serializers.py ← SkillRecord → dict helpers (adapt from OpenSpace dashboard_server.py)
```
