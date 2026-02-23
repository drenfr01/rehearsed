"""Unit tests for Agent-related models."""

import pytest

from app.models.agent import Agent, AgentPersonality, AgentVoice


@pytest.mark.unit
class TestAgentVoiceModel:
    """Test AgentVoice model."""

    def test_create_voice(self):
        voice = AgentVoice(voice_name="Aoede")
        assert voice.voice_name == "Aoede"

    def test_voice_has_created_at(self):
        voice = AgentVoice(voice_name="Kore")
        assert voice.created_at is not None


@pytest.mark.unit
class TestAgentPersonalityModel:
    """Test AgentPersonality model."""

    def test_create_personality(self):
        personality = AgentPersonality(
            name="Curious Student",
            personality_description="A student who is naturally curious and asks lots of questions.",
        )
        assert personality.name == "Curious Student"
        assert "curious" in personality.personality_description.lower()
        assert personality.owner_id is None

    def test_user_owned_personality(self):
        personality = AgentPersonality(
            name="Custom Personality",
            personality_description="Custom description",
            owner_id=42,
        )
        assert personality.owner_id == 42


@pytest.mark.unit
class TestAgentModel:
    """Test Agent model."""

    def test_create_agent(self):
        agent = Agent(
            id="agent-123",
            name="Alex",
            scenario_id=1,
            agent_personality_id=1,
            objective="Learn fractions",
            instructions="Ask questions when confused",
            constraints="Stay in character",
            context="8th grade student",
        )
        assert agent.id == "agent-123"
        assert agent.name == "Alex"
        assert agent.scenario_id == 1
        assert agent.agent_personality_id == 1
        assert agent.objective == "Learn fractions"
        assert agent.owner_id is None

    def test_agent_defaults(self):
        agent = Agent(
            id="agent-456",
            scenario_id=1,
            agent_personality_id=1,
        )
        assert agent.name == ""
        assert agent.objective == ""
        assert agent.instructions == ""
        assert agent.constraints == ""
        assert agent.context == ""
        assert agent.display_text_color == ""
        assert agent.avatar_gcs_uri == ""
        assert agent.voice_id is None
        assert agent.owner_id is None

    def test_user_owned_agent(self):
        agent = Agent(
            id="agent-789",
            name="Jordan",
            scenario_id=1,
            agent_personality_id=1,
            owner_id=42,
        )
        assert agent.owner_id == 42

    def test_agent_display_attributes(self):
        agent = Agent(
            id="agent-display",
            scenario_id=1,
            agent_personality_id=1,
            voice_id=1,
            display_text_color="#FF5733",
            avatar_gcs_uri="gs://bucket/avatar.png",
        )
        assert agent.voice_id == 1
        assert agent.display_text_color == "#FF5733"
        assert agent.avatar_gcs_uri == "gs://bucket/avatar.png"
