"""Base models and common imports for all models."""

from datetime import (
    UTC,
    datetime,
)
from typing import (
    List,
    Optional,
)

from sqlmodel import (
    Field,
    Relationship,
    SQLModel,
)


class BaseModel(SQLModel):
    """Base model with common fields."""

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
