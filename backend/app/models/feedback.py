from enum import Enum

from sqlmodel import (
    Field,
)

from datetime import (
    UTC,
    datetime,
)
from app.models.base import BaseModel


class FeedbackType(str, Enum):
    INLINE = "inline"
    SUMMARY = "summary"


class Feedback(BaseModel, table=True):
    id: int = Field(..., primary_key=True, unique=True)

    feedback_type: FeedbackType = Field(..., description="Whether the feedback is inline or summary feedback")

    # System instructions for the agent
    objective: str = Field(..., description="The objective of the feedback")
    instructions: str = Field(..., description="The instructions for the feedback")
    constraints: str = Field(..., description="The constraints for the feedback")
    context: str = Field(..., description="The context for the feedback")
    output_format: str = Field(default="", description="The output format for the feedback")

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="The timestamp of when the feedback was created")