"""This file contains the chat schema for the application."""

import re
from langgraph.types import Interrupt
from typing import (
    List,
    Literal,
    TYPE_CHECKING,
)

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

from app.schemas.graph import StudentResponse

class Message(BaseModel):
    """Message model for chat endpoint.

    Attributes:
        role: The role of the message sender (user or assistant).
        content: The content of the message.
    """

    model_config = {"extra": "ignore"}

    role: Literal["user", "assistant", "system"] = Field(..., description="The role of the message sender")
    content: str = Field(..., description="The content of the message", min_length=1, max_length=3000)

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate the message content.

        Args:
            v: The content to validate

        Returns:
            str: The validated content

        Raises:
            ValueError: If the content contains disallowed patterns
        """
        # Check for potentially harmful content
        if re.search(r"<script.*?>.*?</script>", v, re.IGNORECASE | re.DOTALL):
            raise ValueError("Content contains potentially harmful script tags")

        # Check for null bytes
        if "\0" in v:
            raise ValueError("Content contains null bytes")

        return v


class ChatRequest(BaseModel):
    """Request model for chat endpoint.

    Attributes:
        messages: List of messages in the conversation.
        is_resumption: Whether the conversation is being resumed.
        resumption_text: The text to resume the conversation.
        audio_base64: Optional base64-encoded audio bytes for speech-to-text transcription.
    """

    messages: List[Message] = Field(
        ...,
        description="List of messages in the conversation"
    )
    is_resumption: bool = Field(default=False, description="Whether the conversation is being resumed")
    resumption_text: str = Field(default="", description="The text to resume the conversation")
    audio_base64: str | None = Field(default=None, description="Optional base64-encoded audio bytes for speech-to-text transcription")


class ChatResponse(BaseModel):
    """Response model for chat endpoint.

    Attributes:
        messages: List of messages in the conversation.
    """

    messages: List[Message] = Field(default_factory=list, description="List of messages in the conversation")
    interrupt_task: str = Field(default="", description="The task to interrupt the conversation")
    interrupt_value: str = Field(default="", description="The value to interrupt the conversation")
    interrupt_value_type: Literal['text', 'image', 'audio', 'video'] = Field(default="text", description="The type of the interrupt value")
    # TODO: potentially make this sub model and DRY out this and the GraphState model
    student_responses: List[StudentResponse] = Field(default_factory=list, description="List of student responses")
    inline_feedback: List[str] = Field(default_factory=list, description="List of inline feedback")
    summary_feedback: str = Field(default="", description="The summary feedback for the student responses")
    summary: str = Field(default="", description="The summary of the student responses")
    answering_student: int = Field(default=0, description="The student number that is answering")
    appropriate_response: bool = Field(default=False, description="Whether the response is appropriate")
    appropriate_explanation: str = Field(default="", description="The explanation for why the response is appropriate")
    learning_goals_achieved: bool = Field(default=False, description="Whether the learning goals were achieved")
    transcribed_text: str = Field(default="", description="The transcribed text from audio input")

    interrupt: List[Interrupt] = Field(default_factory=list, description="List of interrupts")


class StreamResponse(BaseModel):
    """Response model for streaming chat endpoint.

    Attributes:
        content: The content of the current chunk.
        done: Whether the stream is complete.
    """

    content: str = Field(default="", description="The content of the current chunk")
    done: bool = Field(default=False, description="Whether the stream is complete")
