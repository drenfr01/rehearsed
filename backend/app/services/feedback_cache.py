"""In-memory cache for async inline feedback generation.

This enables background generation of inline feedback without blocking chat latency.
The student response is returned immediately while feedback is computed asynchronously.

NOTE: This cache is process-local (single-worker assumption). If you scale to multiple
workers/instances, replace this with a shared store (Redis/GCS/Postgres).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

from langchain_core.messages import BaseMessage
from langfuse import propagate_attributes, observe

from app.core.logging import logger

FeedbackStatus = Literal["pending", "ready", "failed"]


@dataclass
class FeedbackEntry:
    """A single entry in the feedback cache."""
    feedback_id: str
    session_id: str
    status: FeedbackStatus
    created_at: float
    feedback: List[str] = field(default_factory=list)
    error: str = ""
    # Store context for pending entries (used by background task)
    scenario_id: Optional[int] = None
    messages: Optional[List[BaseMessage]] = None

    def to_api_payload(self) -> dict:
        """Convert the feedback entry to an API payload."""
        if self.status == "ready":
            return {
                "status": "ready",
                "feedback": self.feedback,
            }
        if self.status == "failed":
            return {"status": "failed", "feedback": []}
        return {"status": "pending", "feedback": []}


class FeedbackCache:
    """A simple TTL in-memory cache for feedback entries."""

    def __init__(self, ttl_seconds: int = 15 * 60, max_entries: int = 2000):
        """Initialize the feedback cache.
        
        Args:
            ttl_seconds: Time-to-live for cache entries (default: 15 minutes)
            max_entries: Maximum number of entries before eviction (default: 2000)
        """
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._entries: Dict[str, FeedbackEntry] = {}

    def _cleanup(self) -> None:
        """Cleanup the feedback cache based on both TTL and max size."""
        now = time.time()
        # TTL cleanup
        expired = [k for k, v in self._entries.items() if now - v.created_at > self._ttl_seconds]
        for k in expired:
            self._entries.pop(k, None)

        # Simple max-size enforcement: evict oldest
        if len(self._entries) <= self._max_entries:
            return
        overflow = len(self._entries) - self._max_entries
        oldest_keys = sorted(self._entries, key=lambda k: self._entries[k].created_at)[:overflow]
        for k in oldest_keys:
            self._entries.pop(k, None)

    def get(self, feedback_id: str) -> Optional[FeedbackEntry]:
        """Get an entry from the feedback cache."""
        self._cleanup()
        return self._entries.get(feedback_id)

    def put_pending(
        self, 
        feedback_id: str, 
        session_id: str,
        scenario_id: int,
        messages: List[BaseMessage],
    ) -> FeedbackEntry:
        """Put a pending entry into the feedback cache with context for background processing."""
        self._cleanup()
        entry = FeedbackEntry(
            feedback_id=feedback_id,
            session_id=session_id,
            status="pending",
            created_at=time.time(),
            scenario_id=scenario_id,
            messages=messages,
        )
        self._entries[feedback_id] = entry
        return entry

    def put_ready(self, feedback_id: str, session_id: str, feedback: List[str]) -> None:
        """Put a ready entry into the feedback cache."""
        self._cleanup()
        self._entries[feedback_id] = FeedbackEntry(
            feedback_id=feedback_id,
            session_id=session_id,
            status="ready",
            created_at=time.time(),
            feedback=feedback,
        )

    def put_failed(self, feedback_id: str, session_id: str, error: str) -> None:
        """Put a failed entry into the feedback cache."""
        self._cleanup()
        self._entries[feedback_id] = FeedbackEntry(
            feedback_id=feedback_id,
            session_id=session_id,
            status="failed",
            created_at=time.time(),
            error=error,
        )


# Global singleton instance
feedback_cache = FeedbackCache()


@observe(name="generate_async_feedback")
async def generate_feedback_and_store(
    feedback_id: str,
    llm,
    session_id: str = None,
) -> None:
    """Background task: generate inline feedback and store in cache.
    
    Retrieves the scenario_id and messages from the pending cache entry.
    
    Args:
        feedback_id: Unique ID for this feedback request (must exist in cache as pending)
        llm: The LLM instance to use for generation
        session_id: The session ID for Langfuse tracking (optional, falls back to entry.session_id)
    """
    from app.core.prompts.feedback import format_feedback_instructions
    from app.schemas.graph import GeneralResponse
    from app.services.database import database_service
    from langchain_core.messages import SystemMessage
    
    # Get the pending entry with context
    entry = feedback_cache.get(feedback_id)
    if entry is None:
        logger.error("async_feedback_entry_not_found", feedback_id=feedback_id)
        return
    
    entry_session_id = entry.session_id
    scenario_id = entry.scenario_id
    messages = entry.messages
    
    # Use passed session_id or fall back to entry's session_id
    trace_session_id = session_id or entry_session_id
    
    if scenario_id is None or messages is None:
        logger.error("async_feedback_missing_context", feedback_id=feedback_id)
        feedback_cache.put_failed(feedback_id, entry_session_id, "Missing scenario_id or messages")
        return
    
    # Use propagate_attributes to ensure session_id is propagated to LLM calls
    with propagate_attributes(
        session_id=trace_session_id,
        tags=["async", "feedback", "inline"],
    ):
        try:
            # Fetch feedback configuration
            feedback_config = await database_service.feedback.get_feedback_by_type("inline", scenario_id)
            
            if feedback_config is None:
                logger.warning("inline_feedback_not_found_async", scenario_id=scenario_id)
                feedback_cache.put_ready(feedback_id, entry_session_id, ["No inline feedback configured for this scenario."])
                return
            
            system_instructions = format_feedback_instructions(
                objective=feedback_config.objective,
                instructions=feedback_config.instructions,
                constraints=feedback_config.constraints,
                context=feedback_config.context,
                output_format=feedback_config.output_format,
            )
            
            # Build messages with system instructions
            llm_messages = [SystemMessage(content=system_instructions)]
            llm_messages.extend(messages)
            
            # Call LLM - traced via propagate_attributes
            response = await llm.with_structured_output(
                GeneralResponse, method="json_schema", include_raw=True
            ).ainvoke(llm_messages)
            
            if response["parsed"] is None:
                logger.error(
                    "async_feedback_generation_failed",
                    feedback_id=feedback_id,
                    session_id=entry_session_id,
                    error=str(response["raw"]),
                )
                feedback_cache.put_failed(feedback_id, entry_session_id, "LLM returned invalid response")
                return
            
            feedback_text = response["parsed"].llm_response
            if not feedback_text or not feedback_text.strip():
                feedback_text = "Unable to generate feedback for this response."
            
            feedback_cache.put_ready(feedback_id, entry_session_id, [feedback_text])
            logger.info("async_feedback_ready", feedback_id=feedback_id, session_id=entry_session_id)
            
        except Exception as e:
            logger.error(
                "async_feedback_generation_failed",
                feedback_id=feedback_id,
                session_id=entry_session_id,
                error=str(e),
                exc_info=True,
            )
            feedback_cache.put_failed(feedback_id, entry_session_id, str(e))
