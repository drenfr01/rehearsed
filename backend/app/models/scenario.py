"""This file contains the scenario model for the application."""

from typing import (
    TYPE_CHECKING,
    List,
)
from sqlmodel import (
    Field,
    SQLModel,
    Relationship,
)

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.agent import Agent

class Scenario(BaseModel, table=True):
    id: int = Field(default=None, primary_key=True, unique=True)
    name: str = Field(default=None)
    description: str = Field(default=None)
    overview: str = Field(default=None)
    system_instructions: str = Field(default=None)
    initial_prompt: str = Field(default=None)
    agents: List["Agent"] = Relationship(back_populates="scenario")