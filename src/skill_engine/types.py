"""
Every face in the Hall of Faces has a record.
Data types for the Faceless skill engine.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── MCP Types ────────────────────────────────────────

class MCPDefinition(BaseModel):
    name: str
    description: str


class MCPSelectionResult(BaseModel):
    """LLM output for MCP selection step."""
    selected_mcps: list[str]
    reasoning: str


# ── Bootstrap Types ──────────────────────────────────

class SkillScript(BaseModel):
    filename: str
    content: str


class BootstrapSkill(BaseModel):
    """
    Minimal skill schema for bootstrap — intentionally flat.
    Nested scripts/references blow up the structured output generation
    and are rarely needed at bootstrap time anyway. They can be added
    later via CAPTURED evolution.
    """
    name: str
    category: str
    content: str


class BootstrapResult(BaseModel):
    """LLM output for the bootstrap step."""
    constitution: str
    skills: list[BootstrapSkill]


# ── Skill Record (DB) ───────────────────────────────

class SkillRecord(BaseModel):
    id: str
    name: str
    description: str | None = None
    category: str | None = None
    content: str
    status: str = "active"
    generation: int = 0
    parent_id: str | None = None
    lineage_origin: str = "BOOTSTRAP"
    content_diff: str | None = None
    content_snapshot: str | None = None
    total_selections: int = 0
    total_applied: int = 0
    total_completions: int = 0
    total_fallbacks: int = 0
    created_at: str = ""
    last_updated: str = ""


# ── Skill Selection ──────────────────────────────────

class SkillSelectionResult(BaseModel):
    """LLM output for skill selection."""
    brief_plan: str
    skills: list[str]


# ── Execution Analysis (Trigger 1) ──────────────────

class SkillJudgment(BaseModel):
    skill_id: str
    skill_applied: bool
    note: str


class EvolutionSuggestion(BaseModel):
    type: str  # "fix" | "derived" | "captured"
    target_skills: list[str] = Field(default_factory=list)
    category: str = "workflow"
    direction: str
    reason: str = ""  # WHY this evolution is needed, grounded in trace evidence
    priority: str = "medium"
    pattern_key: str = ""


class FeatureRequest(BaseModel):
    capability: str
    user_context: str
    complexity: str = "medium"


class ExecutionAnalysis(BaseModel):
    """LLM output from post-execution analysis (Trigger 1)."""
    task_completed: bool
    execution_note: str
    tool_issues: list[str] = Field(default_factory=list)
    skill_judgments: list[SkillJudgment] = Field(default_factory=list)
    evolution_suggestions: list[EvolutionSuggestion] = Field(default_factory=list)
    feature_requests: list[FeatureRequest] = Field(default_factory=list)
