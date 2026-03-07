"""Avatar database model."""

from datetime import (
    UTC,
    datetime,
)

from sqlmodel import (
    Field,
)

from app.models.base import BaseModel


class Avatar(BaseModel, table=True):
    """Database model for available student avatars."""

    __tablename__ = "avatar"

    id: int = Field(default=None, primary_key=True, unique=True)
    name: str = Field(..., unique=True, index=True, description="Display name for the avatar")
    file_path: str = Field(..., unique=True, description="Path to the avatar image file relative to frontend/public")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of when the avatar was added",
    )
