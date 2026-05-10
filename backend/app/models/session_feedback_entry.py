"""Database model for session feedback entries (per-turn inline feedback persistence)."""

from __future__ import annotations

from typing import List, Optional

from sqlmodel import Column, Field, String
from sqlalchemy.dialects.postgresql import ARRAY

from app.models.base import BaseModel


class SessionFeedbackEntry(BaseModel, table=True):
    """Persists each turn's inline feedback for a session."""

    __tablename__ = "session_feedback_entry"

    id: Optional[str] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="session.id", index=True)
    turn_id: str = Field(index=True)
    feedback_request_id: str = Field(default="")
    status: str = Field(default="pending")  # pending | ready | failed
    feedback: List[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)))
