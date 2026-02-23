"""Agent-related database models."""

from typing import (
    TYPE_CHECKING,
    List,
    Optional,
)

from sqlmodel import (
    Field,
    Relationship,
)

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.scenario import Scenario
    from app.models.user import User

class AgentVoice(BaseModel, table=True):
    """Database model for agent voice configurations."""
    __tablename__ = "agent_voice"
    
    id: int = Field(default=None, primary_key=True, unique=True)
    voice_name: str = Field(...)
    

class AgentPersonality(BaseModel, table=True):
    """Database model for agent personality configurations."""
    __tablename__ = "agent_personality"
    
    id: int = Field(default=None, primary_key=True, unique=True)
    name: str = Field(...)
    personality_description: str = Field(...)
    
    # Owner ID: NULL means global (admin-created), user_id means user-local
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    owner: Optional["User"] = Relationship()
    
    agents: List["Agent"] = Relationship(back_populates="agent_personality")

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
    voice_id: Optional[int] = Field(default=None, foreign_key="agent_voice.id")
    voice: Optional["AgentVoice"] = Relationship()
    display_text_color: str = Field(default="")
    avatar_gcs_uri: str = Field(default="")

    # System instructions for the agent
    objective: str = Field(default="")
    instructions: str = Field(default="")
    constraints: str = Field(default="")
    context: str = Field(default="")

    agent_personality_id: int = Field(foreign_key="agent_personality.id")
    agent_personality: "AgentPersonality" = Relationship(back_populates="agents")
    
    # Owner ID: NULL means global (admin-created), user_id means user-local
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    owner: Optional["User"] = Relationship()