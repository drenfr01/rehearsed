
from typing import (
    TYPE_CHECKING,
    List,
)

from sqlmodel import (
    Field,
    Relationship,
)

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.scenario import Scenario
    from app.models.agent_personality import AgentPersonality

class Agent(BaseModel, table=True):
    """Agent model for storing chat agent prompts and metadata.

    Attributes:
        id: The primary key
        name: Name of the session (defaults to empty string)
        created_at: When the session was created
        messages: Relationship to session messages
        user: Relationship to the session owner
    """

    id: str = Field(primary_key=True)
    name: str = Field(default="")

    scenario_id: int = Field(foreign_key="scenario.id")
    scenario: "Scenario" = Relationship(back_populates="agents")

    # Display Attributes
    # TODO: make this a lookup table for gemini TTS voices
    voice: str = Field(default="")
    display_text_color: str = Field(default="")

    # System instructions for the agent
    objective: str = Field(default="")
    instructions: str = Field(default="")
    constraints: str = Field(default="")
    context: str = Field(default="")

    agent_personality_id: int = Field(foreign_key="agent_personality.id")
    agent_personality: "AgentPersonality" = Relationship(back_populates="agents")