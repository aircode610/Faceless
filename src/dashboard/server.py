"""
"The House of Black and White welcomes all who seek its services."
FastAPI dashboard server — serves the API and the React frontend.

Run: uvicorn src.dashboard.server:app --host 0.0.0.0 --port 7788 --reload
"""

from __future__ import annotations

import os
from pathlib import Path

# ── Load .env BEFORE any other imports ──────────────
# Critical: this must run before anything that reads env vars (including
# LangSmith tracing init inside langchain-core).
from dotenv import load_dotenv
load_dotenv()

# LangChain's tracing still looks at the LANGCHAIN_* namespace in some
# code paths, so mirror the LANGSMITH_* variables across for compatibility.
for src_key, dst_key in [
    ("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2"),
    ("LANGSMITH_API_KEY", "LANGCHAIN_API_KEY"),
    ("LANGSMITH_ENDPOINT", "LANGCHAIN_ENDPOINT"),
    ("LANGSMITH_PROJECT", "LANGCHAIN_PROJECT"),
]:
    if os.environ.get(src_key) and not os.environ.get(dst_key):
        os.environ[dst_key] = os.environ[src_key]

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.dashboard.routes import agent, audit, constitution, overview, review, runs, skills

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
app.include_router(agent.router, prefix="/api/v1", tags=["agent"])
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
