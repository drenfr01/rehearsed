from enum import Enum
from typing import (
    TYPE_CHECKING,
    Optional,
)

from sqlmodel import (
    Field,
    Relationship,
)

from datetime import (
    UTC,
    datetime,
)
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.scenario import Scenario


class FeedbackType(str, Enum):
    INLINE = "inline"
    SUMMARY = "summary"


class Feedback(BaseModel, table=True):
    id: int = Field(default=None, primary_key=True, unique=True)

    feedback_type: FeedbackType = Field(..., description="Whether the feedback is inline or summary feedback")

    # Link to scenario
    scenario_id: int = Field(foreign_key="scenario.id", description="The scenario this feedback belongs to")
    scenario: "Scenario" = Relationship(back_populates="feedbacks")

    # System instructions for the agent
    objective: str = Field(..., description="The objective of the feedback")
    instructions: str = Field(..., description="The instructions for the feedback")
    constraints: str = Field(..., description="The constraints for the feedback")
    context: str = Field(..., description="The context for the feedback")
    output_format: str = Field(default="", description="The output format for the feedback")

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="The timestamp of when the feedback was created")
    
    # Owner ID: NULL means global (admin-created), user_id means user-local
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    owner: Optional["User"] = Relationship()