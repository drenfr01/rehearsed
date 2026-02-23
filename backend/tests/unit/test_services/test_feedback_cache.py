"""Unit tests for feedback cache service."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from app.services.feedback_cache import (
    FeedbackCache,
    FeedbackEntry,
    feedback_cache,
    generate_feedback_and_store,
)


@pytest.mark.unit
class TestFeedbackEntry:
    """Test FeedbackEntry dataclass."""

    def test_to_api_payload_ready(self):
        entry = FeedbackEntry(
            feedback_id="fb-1",
            session_id="sess-1",
            status="ready",
            created_at=time.time(),
            feedback=["Great job!", "Consider more examples."],
        )
        payload = entry.to_api_payload()
        assert payload["status"] == "ready"
        assert payload["feedback"] == ["Great job!", "Consider more examples."]

    def test_to_api_payload_failed(self):
        entry = FeedbackEntry(
            feedback_id="fb-2",
            session_id="sess-1",
            status="failed",
            created_at=time.time(),
            error="LLM timeout",
        )
        payload = entry.to_api_payload()
        assert payload["status"] == "failed"
        assert payload["feedback"] == []

    def test_to_api_payload_pending(self):
        entry = FeedbackEntry(
            feedback_id="fb-3",
            session_id="sess-1",
            status="pending",
            created_at=time.time(),
        )
        payload = entry.to_api_payload()
        assert payload["status"] == "pending"
        assert payload["feedback"] == []


@pytest.mark.unit
class TestFeedbackCache:
    """Test FeedbackCache class."""

    def test_put_and_get_pending(self):
        cache = FeedbackCache()
        messages = [HumanMessage(content="Hello")]
        entry = cache.put_pending("fb-1", "sess-1", 1, messages)

        assert entry.feedback_id == "fb-1"
        assert entry.session_id == "sess-1"
        assert entry.status == "pending"
        assert entry.scenario_id == 1
        assert entry.messages == messages

        retrieved = cache.get("fb-1")
        assert retrieved is not None
        assert retrieved.feedback_id == "fb-1"

    def test_put_and_get_ready(self):
        cache = FeedbackCache()
        cache.put_ready("fb-1", "sess-1", ["Good feedback"])

        entry = cache.get("fb-1")
        assert entry is not None
        assert entry.status == "ready"
        assert entry.feedback == ["Good feedback"]

    def test_put_and_get_failed(self):
        cache = FeedbackCache()
        cache.put_failed("fb-1", "sess-1", "Connection error")

        entry = cache.get("fb-1")
        assert entry is not None
        assert entry.status == "failed"
        assert entry.error == "Connection error"

    def test_get_nonexistent_returns_none(self):
        cache = FeedbackCache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiration(self):
        cache = FeedbackCache(ttl_seconds=1)
        cache.put_ready("fb-1", "sess-1", ["feedback"])

        # Manually age the entry
        cache._entries["fb-1"].created_at = time.time() - 2

        assert cache.get("fb-1") is None

    def test_max_entries_eviction(self):
        cache = FeedbackCache(max_entries=3)

        for i in range(5):
            cache.put_ready(f"fb-{i}", "sess-1", [f"feedback {i}"])
            # Stagger creation times so eviction ordering is deterministic
            cache._entries[f"fb-{i}"].created_at = time.time() + i * 0.01

        # Trigger cleanup
        cache.get("trigger")

        assert len(cache._entries) <= 3
        # Oldest entries should have been evicted
        assert cache.get("fb-0") is None
        assert cache.get("fb-1") is None

    def test_put_pending_overwrites_existing(self):
        cache = FeedbackCache()
        messages = [HumanMessage(content="test")]
        cache.put_ready("fb-1", "sess-1", ["old feedback"])
        cache.put_pending("fb-1", "sess-1", 1, messages)

        entry = cache.get("fb-1")
        assert entry.status == "pending"

    def test_ready_overwrites_pending(self):
        cache = FeedbackCache()
        messages = [HumanMessage(content="test")]
        cache.put_pending("fb-1", "sess-1", 1, messages)
        cache.put_ready("fb-1", "sess-1", ["final feedback"])

        entry = cache.get("fb-1")
        assert entry.status == "ready"
        assert entry.feedback == ["final feedback"]


@pytest.mark.unit
class TestGenerateFeedbackAndStore:
    """Test generate_feedback_and_store function."""

    async def test_entry_not_found_returns_early(self):
        """Test graceful handling when feedback entry doesn't exist in cache."""
        with patch("app.services.feedback_cache.feedback_cache") as mock_cache:
            mock_cache.get.return_value = None

            await generate_feedback_and_store("nonexistent-id", MagicMock())

            mock_cache.put_failed.assert_not_called()
            mock_cache.put_ready.assert_not_called()

    async def test_missing_context_marks_failed(self):
        """Test that missing scenario_id or messages marks entry as failed."""
        entry = FeedbackEntry(
            feedback_id="fb-1",
            session_id="sess-1",
            status="pending",
            created_at=time.time(),
            scenario_id=None,
            messages=None,
        )

        with patch("app.services.feedback_cache.feedback_cache") as mock_cache:
            mock_cache.get.return_value = entry

            await generate_feedback_and_store("fb-1", MagicMock())

            mock_cache.put_failed.assert_called_once()
            args = mock_cache.put_failed.call_args
            assert "Missing scenario_id or messages" in args[0][2]

    async def test_no_inline_feedback_config(self):
        """Test handling when no inline feedback config exists for scenario."""
        messages = [HumanMessage(content="Hello")]
        entry = FeedbackEntry(
            feedback_id="fb-1",
            session_id="sess-1",
            status="pending",
            created_at=time.time(),
            scenario_id=1,
            messages=messages,
        )

        with (
            patch("app.services.feedback_cache.feedback_cache") as mock_cache,
            patch("app.services.database.database_service") as mock_db,
        ):
            mock_cache.get.return_value = entry
            mock_db.feedback.get_feedback_by_type = AsyncMock(return_value=None)

            await generate_feedback_and_store("fb-1", MagicMock())

            mock_cache.put_ready.assert_called_once()
            feedback_text = mock_cache.put_ready.call_args[0][2]
            assert "No inline feedback configured" in feedback_text[0]

    async def test_successful_feedback_generation(self):
        """Test successful inline feedback generation and storage."""
        messages = [HumanMessage(content="Hello")]
        entry = FeedbackEntry(
            feedback_id="fb-1",
            session_id="sess-1",
            status="pending",
            created_at=time.time(),
            scenario_id=1,
            messages=messages,
        )

        feedback_config = MagicMock()
        feedback_config.objective = "obj"
        feedback_config.instructions = "instr"
        feedback_config.constraints = "constr"
        feedback_config.context = "ctx"
        feedback_config.output_format = "fmt"

        mock_parsed = MagicMock()
        mock_parsed.llm_response = "Good job asking that question!"

        mock_llm = MagicMock()
        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(
            return_value={"parsed": mock_parsed, "raw": ""}
        )
        mock_llm.with_structured_output.return_value = mock_chain

        with (
            patch("app.services.feedback_cache.feedback_cache") as mock_cache,
            patch("app.services.database.database_service") as mock_db,
        ):
            mock_cache.get.return_value = entry
            mock_db.feedback.get_feedback_by_type = AsyncMock(
                return_value=feedback_config
            )

            await generate_feedback_and_store("fb-1", mock_llm)

            mock_cache.put_ready.assert_called_once()
            feedback_result = mock_cache.put_ready.call_args[0][2]
            assert feedback_result == ["Good job asking that question!"]

    async def test_llm_returns_none_parsed(self):
        """Test handling when LLM returns null parsed response."""
        messages = [HumanMessage(content="Hello")]
        entry = FeedbackEntry(
            feedback_id="fb-1",
            session_id="sess-1",
            status="pending",
            created_at=time.time(),
            scenario_id=1,
            messages=messages,
        )

        feedback_config = MagicMock()
        feedback_config.objective = "obj"
        feedback_config.instructions = "instr"
        feedback_config.constraints = "constr"
        feedback_config.context = "ctx"
        feedback_config.output_format = "fmt"

        mock_llm = MagicMock()
        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(
            return_value={"parsed": None, "raw": "bad output"}
        )
        mock_llm.with_structured_output.return_value = mock_chain

        with (
            patch("app.services.feedback_cache.feedback_cache") as mock_cache,
            patch("app.services.database.database_service") as mock_db,
        ):
            mock_cache.get.return_value = entry
            mock_db.feedback.get_feedback_by_type = AsyncMock(
                return_value=feedback_config
            )

            await generate_feedback_and_store("fb-1", mock_llm)

            mock_cache.put_failed.assert_called_once()

    async def test_llm_exception_marks_failed(self):
        """Test that exceptions during LLM call mark entry as failed."""
        messages = [HumanMessage(content="Hello")]
        entry = FeedbackEntry(
            feedback_id="fb-1",
            session_id="sess-1",
            status="pending",
            created_at=time.time(),
            scenario_id=1,
            messages=messages,
        )

        feedback_config = MagicMock()
        feedback_config.objective = "obj"
        feedback_config.instructions = "instr"
        feedback_config.constraints = "constr"
        feedback_config.context = "ctx"
        feedback_config.output_format = "fmt"

        mock_llm = MagicMock()
        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(side_effect=Exception("LLM timeout"))
        mock_llm.with_structured_output.return_value = mock_chain

        with (
            patch("app.services.feedback_cache.feedback_cache") as mock_cache,
            patch("app.services.database.database_service") as mock_db,
        ):
            mock_cache.get.return_value = entry
            mock_db.feedback.get_feedback_by_type = AsyncMock(
                return_value=feedback_config
            )

            await generate_feedback_and_store("fb-1", mock_llm)

            mock_cache.put_failed.assert_called_once()
            assert "LLM timeout" in mock_cache.put_failed.call_args[0][2]

    async def test_empty_feedback_text_uses_fallback(self):
        """Test that empty LLM response text falls back to default message."""
        messages = [HumanMessage(content="Hello")]
        entry = FeedbackEntry(
            feedback_id="fb-1",
            session_id="sess-1",
            status="pending",
            created_at=time.time(),
            scenario_id=1,
            messages=messages,
        )

        feedback_config = MagicMock()
        feedback_config.objective = "obj"
        feedback_config.instructions = "instr"
        feedback_config.constraints = "constr"
        feedback_config.context = "ctx"
        feedback_config.output_format = "fmt"

        mock_parsed = MagicMock()
        mock_parsed.llm_response = ""

        mock_llm = MagicMock()
        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(
            return_value={"parsed": mock_parsed, "raw": ""}
        )
        mock_llm.with_structured_output.return_value = mock_chain

        with (
            patch("app.services.feedback_cache.feedback_cache") as mock_cache,
            patch("app.services.database.database_service") as mock_db,
        ):
            mock_cache.get.return_value = entry
            mock_db.feedback.get_feedback_by_type = AsyncMock(
                return_value=feedback_config
            )

            await generate_feedback_and_store("fb-1", mock_llm)

            mock_cache.put_ready.assert_called_once()
            feedback_result = mock_cache.put_ready.call_args[0][2]
            assert "Unable to generate feedback" in feedback_result[0]
