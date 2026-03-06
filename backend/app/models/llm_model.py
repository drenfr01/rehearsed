"""LLM model database models."""

from datetime import (
    UTC,
    datetime,
)

from sqlmodel import (
    Field,
)

from app.models.base import BaseModel


class LlmModel(BaseModel, table=True):
    """Database model for available LLM models."""

    __tablename__ = "llm_model"

    id: int = Field(default=None, primary_key=True, unique=True)
    name: str = Field(..., unique=True, index=True, description="The model identifier (e.g. gemini-3.1-pro-preview)")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of when the model was added",
    )
