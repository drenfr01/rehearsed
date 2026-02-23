"""Unit tests for agent schemas."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.agent import (
    AgentCreate,
    AgentPersonalityCreate,
    AgentPersonalityResponse,
    AgentPersonalityUpdate,
    AgentResponse,
    AgentUpdate,
    AgentVoiceResponse,
    DeleteAgentPersonalityResponse,
    DeleteAgentResponse,
)


@pytest.mark.unit
class TestAgentVoiceResponse:
    """Test AgentVoiceResponse schema."""

    def test_valid(self):
        resp = AgentVoiceResponse(id=1, voice_name="Aoede")
        assert resp.id == 1
        assert resp.voice_name == "Aoede"


@pytest.mark.unit
class TestAgentPersonalityCreate:
    """Test AgentPersonalityCreate schema."""

    def test_valid(self):
        p = AgentPersonalityCreate(
            name="Curious",
            personality_description="A very curious and engaged student.",
        )
        assert p.name == "Curious"

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            AgentPersonalityCreate(
                name="A",
                personality_description="Valid description",
            )

    def test_description_too_short(self):
        with pytest.raises(ValidationError):
            AgentPersonalityCreate(
                name="Valid",
                personality_description="Short",
            )


@pytest.mark.unit
class TestAgentPersonalityUpdate:
    """Test AgentPersonalityUpdate schema."""

    def test_all_none(self):
        update = AgentPersonalityUpdate()
        assert update.name is None
        assert update.personality_description is None

    def test_partial_update(self):
        update = AgentPersonalityUpdate(name="New Name")
        assert update.name == "New Name"
        assert update.personality_description is None


@pytest.mark.unit
class TestAgentPersonalityResponse:
    """Test AgentPersonalityResponse schema."""

    def test_valid(self):
        resp = AgentPersonalityResponse(
            id=1,
            name="Curious",
            personality_description="A curious student",
            created_at=datetime.now(UTC),
        )
        assert resp.id == 1
        assert resp.is_global is True
        assert resp.owner_id is None


@pytest.mark.unit
class TestAgentCreate:
    """Test AgentCreate schema."""

    def test_valid(self):
        agent = AgentCreate(
            id="agent-123",
            name="Alex",
            scenario_id=1,
            agent_personality_id=1,
        )
        assert agent.id == "agent-123"
        assert agent.objective == ""

    def test_id_too_short(self):
        with pytest.raises(ValidationError):
            AgentCreate(
                id="a",
                name="Alex",
                scenario_id=1,
                agent_personality_id=1,
            )


@pytest.mark.unit
class TestAgentUpdate:
    """Test AgentUpdate schema."""

    def test_all_none(self):
        update = AgentUpdate()
        assert update.name is None
        assert update.scenario_id is None

    def test_partial_update(self):
        update = AgentUpdate(name="New Name", objective="New objective")
        assert update.name == "New Name"
        assert update.objective == "New objective"


@pytest.mark.unit
class TestAgentResponse:
    """Test AgentResponse schema."""

    def test_valid(self):
        resp = AgentResponse(
            id="agent-1",
            name="Alex",
            scenario_id=1,
            agent_personality_id=1,
            voice="Aoede",
            display_text_color="#FF0000",
            objective="Learn math",
            instructions="Ask questions",
            constraints="Stay in role",
            context="8th grade",
            created_at=datetime.now(UTC),
        )
        assert resp.id == "agent-1"
        assert resp.is_global is True

    def test_with_personality(self):
        personality = AgentPersonalityResponse(
            id=1,
            name="Curious",
            personality_description="Curious student",
            created_at=datetime.now(UTC),
        )
        resp = AgentResponse(
            id="agent-1",
            name="Alex",
            scenario_id=1,
            agent_personality_id=1,
            agent_personality=personality,
            voice="Aoede",
            display_text_color="#FF0000",
            objective="Learn",
            instructions="Ask",
            constraints="Stay",
            context="Context",
            created_at=datetime.now(UTC),
        )
        assert resp.agent_personality is not None
        assert resp.agent_personality.name == "Curious"


@pytest.mark.unit
class TestDeleteResponses:
    """Test delete response schemas."""

    def test_delete_personality_response(self):
        resp = DeleteAgentPersonalityResponse(message="Deleted")
        assert resp.message == "Deleted"

    def test_delete_agent_response(self):
        resp = DeleteAgentResponse(message="Deleted")
        assert resp.message == "Deleted"
