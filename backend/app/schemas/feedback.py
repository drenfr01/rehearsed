"""Feedback schemas for API request/response models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.feedback import FeedbackType


# ========== Feedback Schemas ==========

class FeedbackCreate(BaseModel):
    """Request model for creating a feedback.
    
    Attributes:
        feedback_type: Type of feedback ("inline" or "summary")
        scenario_id: The scenario this feedback belongs to
        objective: The objective of the feedback
        instructions: The instructions for the feedback
        constraints: The constraints for the feedback
        context: The context for the feedback
        output_format: The output format for the feedback (optional)
    """
    feedback_type: FeedbackType = Field(..., description="Type of feedback (inline or summary)")
    scenario_id: int = Field(..., description="The scenario this feedback belongs to")
    objective: str = Field(..., description="The objective of the feedback", min_length=1)
    instructions: str = Field(..., description="The instructions for the feedback", min_length=1)
    constraints: str = Field(..., description="The constraints for the feedback", min_length=1)
    context: str = Field(..., description="The context for the feedback", min_length=1)
    output_format: str = Field(default="", description="The output format for the feedback")


class FeedbackUpdate(BaseModel):
    """Request model for updating a feedback.
    
    Attributes:
        feedback_type: Optional new feedback type
        scenario_id: Optional new scenario ID
        objective: Optional new objective
        instructions: Optional new instructions
        constraints: Optional new constraints
        context: Optional new context
        output_format: Optional new output format
    """
    feedback_type: Optional[FeedbackType] = Field(None, description="Type of feedback (inline or summary)")
    scenario_id: Optional[int] = Field(None, description="The scenario this feedback belongs to")
    objective: Optional[str] = Field(None, description="The objective of the feedback")
    instructions: Optional[str] = Field(None, description="The instructions for the feedback")
    constraints: Optional[str] = Field(None, description="The constraints for the feedback")
    context: Optional[str] = Field(None, description="The context for the feedback")
    output_format: Optional[str] = Field(None, description="The output format for the feedback")


class FeedbackResponse(BaseModel):
    """Response model for feedback operations.
    
    Attributes:
        id: Feedback ID
        feedback_type: Type of feedback
        scenario_id: The scenario this feedback belongs to
        objective: The objective of the feedback
        instructions: The instructions for the feedback
        constraints: The constraints for the feedback
        context: The context for the feedback
        output_format: The output format for the feedback
        created_at: When the feedback was created
        owner_id: Owner user ID (None means global)
        is_global: Whether this is global feedback
    """
    id: int = Field(..., description="Feedback ID")
    feedback_type: FeedbackType = Field(..., description="Type of feedback")
    scenario_id: int = Field(..., description="The scenario this feedback belongs to")
    objective: str = Field(..., description="The objective of the feedback")
    instructions: str = Field(..., description="The instructions for the feedback")
    constraints: str = Field(..., description="The constraints for the feedback")
    context: str = Field(..., description="The context for the feedback")
    output_format: str = Field(..., description="The output format for the feedback")
    created_at: datetime = Field(..., description="When the feedback was created")
    owner_id: Optional[int] = Field(None, description="Owner user ID (None means global)")
    is_global: bool = Field(default=True, description="Whether this is global feedback")


class DeleteFeedbackResponse(BaseModel):
    """Response model for feedback deletion.
    
    Attributes:
        message: Success message
    """
    message: str = Field(..., description="Success message")

