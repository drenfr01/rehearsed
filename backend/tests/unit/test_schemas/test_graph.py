"""Unit tests for graph schemas."""

import uuid

import pytest
from pydantic import ValidationError

from app.schemas.graph import (
    AppropriateResponse,
    GeneralResponse,
    GraphState,
    StudentChoiceResponse,
    StudentResponse,
    SummaryFeedbackResponse,
)


@pytest.mark.unit
class TestGraphState:
    """Test GraphState schema."""

    def test_valid_uuid_session_id(self):
        session_id = str(uuid.uuid4())
        state = GraphState(session_id=session_id)

        assert state.session_id == session_id
        assert state.messages == []
        assert state.student_responses == []
        assert state.inline_feedback == []
        assert state.summary_feedback == ""
        assert state.answering_student == 0
        assert state.appropriate_response is False
        assert state.learning_goals_achieved is False

    def test_valid_alphanumeric_session_id(self):
        state = GraphState(session_id="test-session_123")
        assert state.session_id == "test-session_123"

    def test_invalid_session_id_special_chars(self):
        with pytest.raises(ValidationError):
            GraphState(session_id="session id with spaces")

    def test_invalid_session_id_injection(self):
        with pytest.raises(ValidationError):
            GraphState(session_id="session'; DROP TABLE users;--")

    def test_session_id_with_dots_rejected(self):
        with pytest.raises(ValidationError):
            GraphState(session_id="session.with.dots")

    def test_defaults(self):
        state = GraphState(session_id="test-123")
        assert state.summary == ""
        assert state.appropriate_explanation == ""


@pytest.mark.unit
class TestSummaryFeedbackResponse:
    """Test SummaryFeedbackResponse schema."""

    def test_valid_response(self):
        resp = SummaryFeedbackResponse(
            lesson_summary="The lesson covered fractions.",
            key_moments="Good questioning technique",
            overall_feedback="Well done overall",
            your_strengths="Clear explanations",
            areas_for_growth="More examples needed",
            next_steps="Try open-ended questions",
            celebration="Great engagement!",
        )

        assert resp.lesson_summary == "The lesson covered fractions."
        assert resp.key_moments == "Good questioning technique"
        assert resp.overall_feedback == "Well done overall"
        assert resp.your_strengths == "Clear explanations"
        assert resp.areas_for_growth == "More examples needed"
        assert resp.next_steps == "Try open-ended questions"
        assert resp.celebration == "Great engagement!"

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            SummaryFeedbackResponse(
                lesson_summary="Summary",
                # missing all other fields
            )

    def test_all_fields_required(self):
        required_fields = [
            "lesson_summary",
            "key_moments",
            "overall_feedback",
            "your_strengths",
            "areas_for_growth",
            "next_steps",
            "celebration",
        ]
        for field in required_fields:
            kwargs = {f: "test" for f in required_fields}
            del kwargs[field]
            with pytest.raises(ValidationError):
                SummaryFeedbackResponse(**kwargs)


@pytest.mark.unit
class TestGeneralResponse:
    """Test GeneralResponse schema."""

    def test_valid_response(self):
        resp = GeneralResponse(llm_response="This is a detailed response.")
        assert resp.llm_response == "This is a detailed response."

    def test_missing_llm_response(self):
        with pytest.raises(ValidationError):
            GeneralResponse()


@pytest.mark.unit
class TestStudentChoiceResponse:
    """Test StudentChoiceResponse schema."""

    def test_valid_choice(self):
        resp = StudentChoiceResponse(student_number=1)
        assert resp.student_number == 1

    def test_missing_student_number(self):
        with pytest.raises(ValidationError):
            StudentChoiceResponse()


@pytest.mark.unit
class TestAppropriateResponse:
    """Test AppropriateResponse schema."""

    def test_appropriate(self):
        resp = AppropriateResponse(
            appropriate_response=True,
            appropriate_explanation="The response was professional.",
        )
        assert resp.appropriate_response is True
        assert resp.appropriate_explanation == "The response was professional."

    def test_inappropriate(self):
        resp = AppropriateResponse(
            appropriate_response=False,
            appropriate_explanation="The response was unprofessional.",
        )
        assert resp.appropriate_response is False

    def test_missing_fields(self):
        with pytest.raises(ValidationError):
            AppropriateResponse(appropriate_response=True)


@pytest.mark.unit
class TestStudentResponse:
    """Test StudentResponse schema."""

    def test_defaults(self):
        from app.models.agent import Agent, AgentPersonality

        personality = AgentPersonality(
            id=1,
            name="Curious",
            personality_description="A curious student",
        )
        agent = Agent(
            id="agent-1",
            name="Alex",
            scenario_id=1,
            agent_personality_id=1,
        )

        resp = StudentResponse(
            student_response="I think the answer is 42.",
            student_details=agent,
            student_personality=personality,
        )

        assert resp.student_response == "I think the answer is 42."
        assert resp.audio_base64 == ""
        assert resp.audio_id == ""
