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
    from app.models.agent import Agent

class AgentPersonality(BaseModel, table=True):
    id: int = Field(..., primary_key=True, unique=True)
    name: str = Field(...)
    personality_description: str = Field(...)
    agents: List["Agent"] = Relationship(back_populates="agent_personality")