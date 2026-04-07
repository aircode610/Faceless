"""
"The House of Black and White welcomes all who seek its services."
FastAPI dashboard server — serves the API and the React frontend.

Run: uvicorn src.dashboard.server:app --host 0.0.0.0 --port 7788 --reload
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.dashboard.routes import audit, constitution, overview, review, runs, skills

app = FastAPI(
    title="Faceless — Agent Dashboard",
    description="A Man Has No Name. But he has an API.",
    version="1.0.0",
)

# CORS for dev (Vite runs on :5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:7788"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routes ───────────────────────────────────────
app.include_router(overview.router, prefix="/api/v1", tags=["overview"])
app.include_router(skills.router, prefix="/api/v1", tags=["skills"])
app.include_router(review.router, prefix="/api/v1", tags=["review"])
app.include_router(runs.router, prefix="/api/v1", tags=["runs"])
app.include_router(constitution.router, prefix="/api/v1", tags=["constitution"])
app.include_router(audit.router, prefix="/api/v1", tags=["audit"])

# ── Static Frontend ──────────────────────────────────
FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(FRONTEND_DIST / "assets")),
        name="assets",
    )


# SPA fallback — all non-API routes return index.html
@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(404, "API route not found")
    index = FRONTEND_DIST / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {
        "message": "Valar Morghulis. Frontend not built yet.",
        "hint": "cd frontend && npm install && npm run build",
    }
