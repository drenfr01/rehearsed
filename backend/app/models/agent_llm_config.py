"""Agent-to-LLM configuration database models."""

from datetime import (
    UTC,
    datetime,
)
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Optional,
)

from sqlmodel import (
    Field,
    Relationship,
)

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.llm_model import LlmModel


class AgentType(str, Enum):
    """Enumeration of agent types that use LLMs."""

    STUDENT_AGENT = "student_agent"
    STUDENT_CHOICE_AGENT = "student_choice_agent"
    INLINE_FEEDBACK = "inline_feedback"
    SUMMARY_FEEDBACK = "summary_feedback"


class AgentLlmConfig(BaseModel, table=True):
    """Maps each agent type to its currently configured LLM model."""

    __tablename__ = "agent_llm_config"

    id: int = Field(default=None, primary_key=True, unique=True)
    agent_type: AgentType = Field(..., unique=True, index=True, description="The agent type")
    llm_model_id: int = Field(foreign_key="llm_model.id", description="The LLM model assigned to this agent")
    llm_model: Optional["LlmModel"] = Relationship()

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of last update",
    )
