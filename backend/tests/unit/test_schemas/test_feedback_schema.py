"""Unit tests for feedback schemas."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models.feedback import FeedbackType
from app.schemas.feedback import (
    DeleteFeedbackResponse,
    FeedbackCreate,
    FeedbackResponse,
    FeedbackUpdate,
)


@pytest.mark.unit
class TestFeedbackCreate:
    """Test FeedbackCreate schema."""

    def test_valid_inline_feedback(self):
        fb = FeedbackCreate(
            feedback_type=FeedbackType.INLINE,
            scenario_id=1,
            objective="Evaluate responses",
            instructions="Provide constructive feedback",
            constraints="Be concise",
            context="Middle school math",
        )
        assert fb.feedback_type == FeedbackType.INLINE
        assert fb.scenario_id == 1
        assert fb.output_format == ""

    def test_valid_summary_feedback(self):
        fb = FeedbackCreate(
            feedback_type=FeedbackType.SUMMARY,
            scenario_id=1,
            objective="Summarize the lesson",
            instructions="Evaluate teaching quality",
            constraints="Focus on positives",
            context="Science class",
            output_format="JSON",
        )
        assert fb.feedback_type == FeedbackType.SUMMARY
        assert fb.output_format == "JSON"

    def test_empty_objective_rejected(self):
        with pytest.raises(ValidationError):
            FeedbackCreate(
                feedback_type=FeedbackType.INLINE,
                scenario_id=1,
                objective="",
                instructions="Instructions",
                constraints="Constraints",
                context="Context",
            )

    def test_empty_instructions_rejected(self):
        with pytest.raises(ValidationError):
            FeedbackCreate(
                feedback_type=FeedbackType.INLINE,
                scenario_id=1,
                objective="Objective",
                instructions="",
                constraints="Constraints",
                context="Context",
            )

    def test_invalid_feedback_type_rejected(self):
        with pytest.raises(ValidationError):
            FeedbackCreate(
                feedback_type="invalid",
                scenario_id=1,
                objective="Objective",
                instructions="Instructions",
                constraints="Constraints",
                context="Context",
            )


@pytest.mark.unit
class TestFeedbackUpdate:
    """Test FeedbackUpdate schema."""

    def test_all_none_defaults(self):
        update = FeedbackUpdate()
        assert update.feedback_type is None
        assert update.scenario_id is None
        assert update.objective is None
        assert update.instructions is None
        assert update.constraints is None
        assert update.context is None
        assert update.output_format is None

    def test_partial_update(self):
        update = FeedbackUpdate(objective="New objective")
        assert update.objective == "New objective"
        assert update.instructions is None

    def test_full_update(self):
        update = FeedbackUpdate(
            feedback_type=FeedbackType.SUMMARY,
            scenario_id=2,
            objective="New objective",
            instructions="New instructions",
            constraints="New constraints",
            context="New context",
            output_format="New format",
        )
        assert update.feedback_type == FeedbackType.SUMMARY
        assert update.scenario_id == 2


@pytest.mark.unit
class TestFeedbackResponse:
    """Test FeedbackResponse schema."""

    def test_valid_response(self):
        resp = FeedbackResponse(
            id=1,
            feedback_type=FeedbackType.INLINE,
            scenario_id=1,
            objective="Objective",
            instructions="Instructions",
            constraints="Constraints",
            context="Context",
            output_format="Format",
            created_at=datetime.now(UTC),
            owner_id=None,
            is_global=True,
        )
        assert resp.id == 1
        assert resp.is_global is True

    def test_user_owned_response(self):
        resp = FeedbackResponse(
            id=2,
            feedback_type=FeedbackType.SUMMARY,
            scenario_id=1,
            objective="Objective",
            instructions="Instructions",
            constraints="Constraints",
            context="Context",
            output_format="",
            created_at=datetime.now(UTC),
            owner_id=42,
            is_global=False,
        )
        assert resp.owner_id == 42
        assert resp.is_global is False


@pytest.mark.unit
class TestDeleteFeedbackResponse:
    """Test DeleteFeedbackResponse schema."""

    def test_valid(self):
        resp = DeleteFeedbackResponse(message="Feedback deleted successfully")
        assert resp.message == "Feedback deleted successfully"
