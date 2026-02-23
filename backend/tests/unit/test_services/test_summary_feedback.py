"""Unit tests for summary feedback service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.graph import SummaryFeedbackResponse


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
                "app.services.summary_feedback.ChatGoogleGenerativeAI"
            ) as mock_llm_class,
        ):
            mock_db.feedback.get_feedback_by_type = AsyncMock(
                return_value=mock_feedback_config
            )

            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(
                return_value={"parsed": mock_summary_response, "raw": ""}
            )
            mock_llm_instance = MagicMock()
            mock_llm_instance.with_structured_output.return_value = mock_chain
            mock_llm_class.return_value = mock_llm_instance

            from app.services.summary_feedback import generate_summary_feedback

            result = await generate_summary_feedback(1, sample_conversation)

            assert isinstance(result, SummaryFeedbackResponse)
            assert result.lesson_summary == mock_summary_response.lesson_summary
            assert result.key_moments == mock_summary_response.key_moments
            mock_db.feedback.get_feedback_by_type.assert_called_once_with("summary", 1)

    async def test_generate_summary_feedback_no_feedback_config(self, sample_conversation):
        """Test fallback when no feedback configuration exists."""
        with patch("app.services.summary_feedback.database_service") as mock_db:
            mock_db.feedback.get_feedback_by_type = AsyncMock(return_value=None)

            from app.services.summary_feedback import generate_summary_feedback

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
                "app.services.summary_feedback.ChatGoogleGenerativeAI"
            ) as mock_llm_class,
        ):
            mock_db.feedback.get_feedback_by_type = AsyncMock(
                return_value=mock_feedback_config
            )

            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(
                return_value={"parsed": None, "raw": "invalid output"}
            )
            mock_llm_instance = MagicMock()
            mock_llm_instance.with_structured_output.return_value = mock_chain
            mock_llm_class.return_value = mock_llm_instance

            from app.services.summary_feedback import generate_summary_feedback

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
                "app.services.summary_feedback.ChatGoogleGenerativeAI"
            ) as mock_llm_class,
        ):
            mock_db.feedback.get_feedback_by_type = AsyncMock(
                return_value=mock_feedback_config
            )

            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(
                return_value={"parsed": mock_summary_response, "raw": ""}
            )
            mock_llm_instance = MagicMock()
            mock_llm_instance.with_structured_output.return_value = mock_chain
            mock_llm_class.return_value = mock_llm_instance

            from app.services.summary_feedback import generate_summary_feedback

            result = await generate_summary_feedback(1, conversation_with_empty)

            assert isinstance(result, SummaryFeedbackResponse)
            call_args = mock_chain.ainvoke.call_args[0][0]
            # SystemMessage + HumanMessage("Hello") + AIMessage("Hi there") = 3 messages
            assert len(call_args) == 3

    async def test_generate_summary_feedback_uses_correct_llm_params(
        self, mock_feedback_config, sample_conversation, mock_summary_response
    ):
        """Test that the LLM is configured with correct parameters."""
        with (
            patch(
                "app.services.summary_feedback.database_service"
            ) as mock_db,
            patch(
                "app.services.summary_feedback.ChatGoogleGenerativeAI"
            ) as mock_llm_class,
            patch("app.services.summary_feedback.settings") as mock_settings,
        ):
            mock_settings.DEFAULT_LLM_TEMPERATURE = 0.2
            mock_settings.GOOGLE_CLOUD_PROJECT = "test-project"
            mock_settings.GOOGLE_CLOUD_LOCATION = "us-central1"
            mock_settings.MAX_TOKENS = 200000

            mock_db.feedback.get_feedback_by_type = AsyncMock(
                return_value=mock_feedback_config
            )

            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(
                return_value={"parsed": mock_summary_response, "raw": ""}
            )
            mock_llm_instance = MagicMock()
            mock_llm_instance.with_structured_output.return_value = mock_chain
            mock_llm_class.return_value = mock_llm_instance

            from app.services.summary_feedback import generate_summary_feedback

            await generate_summary_feedback(1, sample_conversation)

            mock_llm_class.assert_called_once_with(
                model="gemini-3-pro-preview",
                temperature=0.2,
                project="test-project",
                location="us-central1",
                max_tokens=200000,
                vertexai=True,
                google_api_key=None,
            )
