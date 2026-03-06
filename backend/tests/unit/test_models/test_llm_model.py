"""Unit tests for LlmModel and AgentLlmConfig models."""

from datetime import datetime

import pytest

from app.models.agent_llm_config import AgentLlmConfig, AgentType
from app.models.llm_model import LlmModel


@pytest.mark.unit
class TestLlmModel:
    """Test LlmModel model."""

    def test_create_llm_model(self):
        model = LlmModel(name="gemini-3.1-pro-preview")
        assert model.name == "gemini-3.1-pro-preview"
        assert model.id is None

    def test_has_created_at(self):
        model = LlmModel(name="gemini-3-flash-preview")
        assert model.created_at is not None
        assert isinstance(model.created_at, datetime)


@pytest.mark.unit
class TestAgentTypeEnum:
    """Test AgentType enum."""

    def test_student_agent_value(self):
        assert AgentType.STUDENT_AGENT.value == "student_agent"

    def test_student_choice_agent_value(self):
        assert AgentType.STUDENT_CHOICE_AGENT.value == "student_choice_agent"

    def test_inline_feedback_value(self):
        assert AgentType.INLINE_FEEDBACK.value == "inline_feedback"

    def test_summary_feedback_value(self):
        assert AgentType.SUMMARY_FEEDBACK.value == "summary_feedback"

    def test_is_string(self):
        assert isinstance(AgentType.STUDENT_AGENT, str)
        assert AgentType.STUDENT_AGENT == "student_agent"

    def test_from_string(self):
        assert AgentType("student_agent") == AgentType.STUDENT_AGENT
        assert AgentType("summary_feedback") == AgentType.SUMMARY_FEEDBACK

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            AgentType("invalid_agent")


@pytest.mark.unit
class TestAgentLlmConfig:
    """Test AgentLlmConfig model."""

    def test_create_config(self):
        config = AgentLlmConfig(
            agent_type=AgentType.STUDENT_AGENT,
            llm_model_id=1,
        )
        assert config.agent_type == AgentType.STUDENT_AGENT
        assert config.llm_model_id == 1

    def test_has_updated_at(self):
        config = AgentLlmConfig(
            agent_type=AgentType.INLINE_FEEDBACK,
            llm_model_id=2,
        )
        assert config.updated_at is not None
        assert isinstance(config.updated_at, datetime)

    def test_all_agent_types(self):
        for agent_type in AgentType:
            config = AgentLlmConfig(agent_type=agent_type, llm_model_id=1)
            assert config.agent_type == agent_type
