"""Database operations for session feedback entries."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.core.logging import logger
from app.models.session_feedback_entry import SessionFeedbackEntry


class SessionFeedbackRepository:
    """Handles CRUD operations for session feedback entries."""

    def __init__(self, engine: Engine):
        self._engine = engine

    @property
    def engine(self) -> Engine:
        return self._engine

    async def upsert_entry(
        self,
        id: str,
        session_id: str,
        turn_id: str,
        feedback_request_id: str,
        status: str = "pending",
        feedback: Optional[List[str]] = None,
    ) -> SessionFeedbackEntry:
        """Create or update a session feedback entry."""
        with Session(self.engine) as session:
            entry = session.get(SessionFeedbackEntry, id)
            if entry:
                entry.status = status
                if feedback is not None:
                    entry.feedback = feedback
                entry.feedback_request_id = feedback_request_id
            else:
                entry = SessionFeedbackEntry(
                    id=id,
                    session_id=session_id,
                    turn_id=turn_id,
                    feedback_request_id=feedback_request_id,
                    status=status,
                    feedback=feedback or [],
                )
                session.add(entry)
            session.commit()
            session.refresh(entry)
            return entry

    async def update_status(
        self,
        id: str,
        status: str,
        feedback: Optional[List[str]] = None,
    ) -> None:
        """Update the status (and optionally feedback) of an entry."""
        with Session(self.engine) as session:
            entry = session.get(SessionFeedbackEntry, id)
            if entry:
                entry.status = status
                if feedback is not None:
                    entry.feedback = feedback
                session.commit()

    async def get_by_session(self, session_id: str) -> List[SessionFeedbackEntry]:
        """Get all feedback entries for a session, ordered by created_at."""
        with Session(self.engine) as session:
            statement = (
                select(SessionFeedbackEntry)
                .where(SessionFeedbackEntry.session_id == session_id)
                .order_by(SessionFeedbackEntry.created_at)
            )
            results = session.exec(statement).all()
            return list(results)
