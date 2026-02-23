"""This file contains the scenario model for the application."""

from typing import (
    TYPE_CHECKING,
    List,
    Optional,
)

from sqlmodel import (
    Field,
    Relationship,
    SQLModel,
)

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.feedback import Feedback
    from app.models.user import User

class Scenario(BaseModel, table=True):
    """Database model for scenario configurations."""
    id: int = Field(default=None, primary_key=True, unique=True)
    name: str = Field(default=None)
    description: str = Field(default=None)
    overview: str = Field(default=None)
    system_instructions: str = Field(default=None)
    initial_prompt: str = Field(default=None)
    teaching_objectives: str = Field(default=None)
    
    # Owner ID: NULL means global (admin-created), user_id means user-local
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    owner: Optional["User"] = Relationship()
    
    agents: List["Agent"] = Relationship(back_populates="scenario")
    feedbacks: List["Feedback"] = Relationship(back_populates="scenario")