"""This file contains the scenario model for the application."""

from sqlmodel import (
    Field,
    SQLModel,
)

from app.models.base import BaseModel

class Scenario(BaseModel, table=True):
    id: int = Field(default=None, primary_key=True, unique=True)
    name: str = Field(default=None)
    description: str = Field(default=None)
    overview: str = Field(default=None)
    system_instructions: str = Field(default=None)
    initial_prompt: str = Field(default=None)