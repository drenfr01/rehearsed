"""Unit tests for Feedback model."""

from datetime import UTC, datetime

import pytest

from app.models.feedback import Feedback, FeedbackType


@pytest.mark.unit
class TestFeedbackTypeEnum:
    """Test FeedbackType enum."""

    def test_inline_value(self):
        assert FeedbackType.INLINE.value == "inline"

    def test_summary_value(self):
        assert FeedbackType.SUMMARY.value == "summary"

    def test_is_string(self):
        assert isinstance(FeedbackType.INLINE, str)
        assert FeedbackType.SUMMARY == "summary"

    def test_from_string(self):
        assert FeedbackType("inline") == FeedbackType.INLINE
        assert FeedbackType("summary") == FeedbackType.SUMMARY

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            FeedbackType("invalid")


@pytest.mark.unit
class TestFeedbackModel:
    """Test Feedback model."""

    def test_create_inline_feedback(self):
        fb = Feedback(
            feedback_type=FeedbackType.INLINE,
            scenario_id=1,
            objective="Evaluate teacher responses",
            instructions="Provide constructive feedback",
            constraints="Be concise and actionable",
            context="Middle school math class",
            output_format="JSON",
        )
        assert fb.feedback_type == FeedbackType.INLINE
        assert fb.scenario_id == 1
        assert fb.objective == "Evaluate teacher responses"
        assert fb.output_format == "JSON"
        assert fb.owner_id is None

    def test_create_summary_feedback(self):
        fb = Feedback(
            feedback_type=FeedbackType.SUMMARY,
            scenario_id=2,
            objective="Summarize the lesson",
            instructions="Highlight strengths and areas for growth",
            constraints="Maximum 500 words",
            context="High school science class",
        )
        assert fb.feedback_type == FeedbackType.SUMMARY
        assert fb.scenario_id == 2

    def test_default_output_format(self):
        fb = Feedback(
            feedback_type=FeedbackType.INLINE,
            scenario_id=1,
            objective="obj",
            instructions="instr",
            constraints="constr",
            context="ctx",
        )
        assert fb.output_format == ""

    def test_user_owned_feedback(self):
        fb = Feedback(
            feedback_type=FeedbackType.INLINE,
            scenario_id=1,
            objective="obj",
            instructions="instr",
            constraints="constr",
            context="ctx",
            owner_id=42,
        )
        assert fb.owner_id == 42

    def test_has_created_at(self):
        fb = Feedback(
            feedback_type=FeedbackType.INLINE,
            scenario_id=1,
            objective="obj",
            instructions="instr",
            constraints="constr",
            context="ctx",
        )
        assert fb.created_at is not None
        assert isinstance(fb.created_at, datetime)
