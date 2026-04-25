"""Unit tests for summary feedback service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.graph import SummaryFeedbackResponse
from app.services.summary_feedback import generate_summary_feedback


@pytest.mark.unit
class TestGenerateSummaryFeedback:
    """Test generate_summary_feedback function."""

    @pytest.fixture
    def mock_feedback_config(self):
        """Create a mock feedback config."""
        fb = MagicMock()
        fb.objective = "Evaluate the teacher"
        fb.instructions = "Give constructive feedback"
        fb.constraints = "Be concise"
        fb.context = "Middle school classroom"
        fb.output_format = "JSON"
        return fb

    @pytest.fixture
    def sample_conversation(self):
        return [
            {"role": "user", "text": "Hello class, today we'll discuss fractions."},
            {"role": "agent", "text": "That sounds interesting, teacher!"},
            {"role": "user", "text": "Can you tell me what 1/2 + 1/4 is?"},
            {"role": "agent", "text": "I think it's 3/4."},
        ]

    @pytest.fixture
    def mock_summary_response(self):
        return SummaryFeedbackResponse(
            lesson_summary="The teacher discussed fractions with the student.",
            key_moments="Excellent questioning technique, good scaffolding",
            overall_feedback="The teacher performed well overall.",
            your_strengths="Clear explanations and patience",
            areas_for_growth="Could provide more examples",
            next_steps="Try more open-ended questions",
            celebration="Great job keeping the student engaged!",
        )

    async def test_generate_summary_feedback_success(
        self, mock_feedback_config, sample_conversation, mock_summary_response
    ):
        """Test successful summary feedback generation."""
        with (
            patch(
                "app.services.summary_feedback.database_service"
            ) as mock_db,
            patch(
                "app.services.summary_feedback.create_chat_llm"
            ) as mock_factory,
        ):
            mock_db.feedback.get_feedback_by_type = AsyncMock(
                return_value=mock_feedback_config
            )
            mock_db.agent_llm_config.get_model_name_for_agent = AsyncMock(
                return_value=None
            )

            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(
                return_value={"parsed": mock_summary_response, "raw": ""}
            )
            mock_llm_instance = MagicMock()
            mock_llm_instance.with_structured_output.return_value = mock_chain
            mock_factory.return_value = mock_llm_instance

            result = await generate_summary_feedback(1, sample_conversation)

            assert isinstance(result, SummaryFeedbackResponse)
            assert result.lesson_summary == mock_summary_response.lesson_summary
            assert result.key_moments == mock_summary_response.key_moments
            mock_db.feedback.get_feedback_by_type.assert_called_once_with("summary", 1)

    async def test_generate_summary_feedback_no_feedback_config(self, sample_conversation):
        """Test fallback when no feedback configuration exists."""
        with patch("app.services.summary_feedback.database_service") as mock_db:
            mock_db.feedback.get_feedback_by_type = AsyncMock(return_value=None)

            result = await generate_summary_feedback(999, sample_conversation)

            assert isinstance(result, str)
            assert "No summary feedback configured" in result

    async def test_generate_summary_feedback_llm_parse_failure(
        self, mock_feedback_config, sample_conversation
    ):
        """Test fallback when LLM returns unparseable response."""
        with (
            patch(
                "app.services.summary_feedback.database_service"
            ) as mock_db,
            patch(
                "app.services.summary_feedback.create_chat_llm"
            ) as mock_factory,
        ):
            mock_db.feedback.get_feedback_by_type = AsyncMock(
                return_value=mock_feedback_config
            )
            mock_db.agent_llm_config.get_model_name_for_agent = AsyncMock(
                return_value=None
            )

            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(
                return_value={"parsed": None, "raw": "invalid output"}
            )
            mock_llm_instance = MagicMock()
            mock_llm_instance.with_structured_output.return_value = mock_chain
            mock_factory.return_value = mock_llm_instance

            result = await generate_summary_feedback(1, sample_conversation)

            assert isinstance(result, str)
            assert "Could not generate summary feedback" in result

    async def test_generate_summary_feedback_filters_empty_messages(
        self, mock_feedback_config, mock_summary_response
    ):
        """Test that messages with empty text are filtered out."""
        conversation_with_empty = [
            {"role": "user", "text": "Hello"},
            {"role": "agent", "text": ""},
            {"role": "user", "text": ""},
            {"role": "agent", "text": "Hi there"},
        ]

        with (
            patch(
                "app.services.summary_feedback.database_service"
            ) as mock_db,
            patch(
                "app.services.summary_feedback.create_chat_llm"
            ) as mock_factory,
        ):
            mock_db.feedback.get_feedback_by_type = AsyncMock(
                return_value=mock_feedback_config
            )
            mock_db.agent_llm_config.get_model_name_for_agent = AsyncMock(
                return_value=None
            )

            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(
                return_value={"parsed": mock_summary_response, "raw": ""}
            )
            mock_llm_instance = MagicMock()
            mock_llm_instance.with_structured_output.return_value = mock_chain
            mock_factory.return_value = mock_llm_instance

            result = await generate_summary_feedback(1, conversation_with_empty)

            assert isinstance(result, SummaryFeedbackResponse)
            call_args = mock_chain.ainvoke.call_args[0][0]
            # SystemMessage + HumanMessage("Hello") + AIMessage("Hi there") = 3 messages
            assert len(call_args) == 3

    async def test_generate_summary_feedback_uses_correct_llm_params(
        self, mock_feedback_config, sample_conversation, mock_summary_response
    ):
        """Test that the factory is called with the DB-resolved model name."""
        with (
            patch("app.services.summary_feedback.database_service") as mock_db,
            patch("app.services.summary_feedback.create_chat_llm") as mock_factory,
        ):
            mock_db.feedback.get_feedback_by_type = AsyncMock(
                return_value=mock_feedback_config
            )
            mock_db.agent_llm_config.get_model_name_for_agent = AsyncMock(
                return_value="gemini-3.1-pro-preview"
            )

            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(
                return_value={"parsed": mock_summary_response, "raw": ""}
            )
            mock_llm_instance = MagicMock()
            mock_llm_instance.with_structured_output.return_value = mock_chain
            mock_factory.return_value = mock_llm_instance

            await generate_summary_feedback(1, sample_conversation)

            mock_factory.assert_called_once_with("gemini-3.1-pro-preview")
            mock_db.agent_llm_config.get_model_name_for_agent.assert_called_once_with(
                "summary_feedback"
            )

    async def test_generate_summary_feedback_falls_back_on_db_error(
        self, mock_feedback_config, sample_conversation, mock_summary_response
    ):
        """Test that settings.LLM_MODEL is used when DB resolution fails."""
        with (
            patch("app.services.summary_feedback.database_service") as mock_db,
            patch("app.services.summary_feedback.create_chat_llm") as mock_factory,
            patch("app.services.summary_feedback.settings") as mock_settings,
        ):
            mock_settings.LLM_MODEL = "gemini-3-flash-preview"

            mock_db.feedback.get_feedback_by_type = AsyncMock(
                return_value=mock_feedback_config
            )
            mock_db.agent_llm_config.get_model_name_for_agent = AsyncMock(
                side_effect=Exception("DB error")
            )

            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(
                return_value={"parsed": mock_summary_response, "raw": ""}
            )
            mock_llm_instance = MagicMock()
            mock_llm_instance.with_structured_output.return_value = mock_chain
            mock_factory.return_value = mock_llm_instance

            await generate_summary_feedback(1, sample_conversation)

            mock_factory.assert_called_once_with("gemini-3-flash-preview")
