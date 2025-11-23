"""This file contains the graph schema for the application."""

import operator
import re
import uuid
from typing import Annotated

from langgraph.graph.message import add_messages
from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

from app.models.agent import Agent, AgentPersonality

class StudentResponse(BaseModel):
    """Model for the student response."""

    student_response: str = Field(..., description="The response from the student")
    student_details: "Agent"
    student_personality: "AgentPersonality"


class GraphState(BaseModel):
    """State definition for the LangGraph Agent/Workflow."""

    messages: Annotated[list, add_messages] = Field(
        default_factory=list, description="The messages in the conversation"
    )
    session_id: str = Field(..., description="The unique identifier for the conversation session")

    student_responses: Annotated[list[StudentResponse], operator.add] = Field(
        default_factory=list, description="The student responses"
    )
    inline_feedback: Annotated[list[str], operator.add] = Field(
        default_factory=list, description="The inline feedback for the student responses"
    )
    summary_feedback: str = Field(default="", description="The summary feedback for the student responses")
    summary: str = Field(default="", description="The summary of the student responses")
    answering_student: int = Field(default=0, description="The student number that is answering")
    appropriate_response: bool = Field(default=False, description="Whether the response is appropriate")
    appropriate_explanation: str = Field(default="", description="The explanation for why the response is appropriate")
    learning_goals_achieved: bool = Field(default=False, description="Whether the learning goals were achieved")

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """Validate that the session ID is a valid UUID or follows safe pattern.

        Args:
            v: The thread ID to validate

        Returns:
            str: The validated session ID

        Raises:
            ValueError: If the session ID is not valid
        """
        # Try to validate as UUID
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            # If not a UUID, check for safe characters only
            if not re.match(r"^[a-zA-Z0-9_\-]+$", v):
                raise ValueError("Session ID must contain only alphanumeric characters, underscores, and hyphens")
            return v


class GeneralResponse(BaseModel):
    """Model for the student response."""

    llm_response: str = Field(..., description="The response from the LLM")


class StudentChoiceResponse(BaseModel):
    """Model for the student choice response."""

    student_number: int = Field(..., description="The student number that is answering")


class AppropriateResponse(BaseModel):
    """Model for the appropriate response."""

    appropriate_response: bool = Field(..., description="Whether the response is appropriate")
    appropriate_explanation: str = Field(..., description="The explanation for why the response is appropriate")
