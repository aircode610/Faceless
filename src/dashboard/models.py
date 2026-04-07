"""
Pydantic request/response models for the dashboard API.
"""

from __future__ import annotations

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


class DismissFeatureRequest(BaseModel):
    reason: str = ""
