"""Agent, AgentPersonality, and AgentVoice schemas for admin endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ========== AgentVoice Schemas ==========

class AgentVoiceResponse(BaseModel):
    """Response model for agent voice.
    
    Attributes:
        id: Voice ID
        voice_name: Name of the voice
    """
    id: int = Field(..., description="Voice ID")
    voice_name: str = Field(..., description="Name of the voice")


# ========== AgentPersonality Schemas ==========

class AgentPersonalityCreate(BaseModel):
    """Request model for creating an agent personality.
    
    Attributes:
        name: Name of the personality
        personality_description: Description of the personality traits
    """
    name: str = Field(..., description="Name of the personality", min_length=2)
    personality_description: str = Field(..., description="Description of the personality traits", min_length=10)


class AgentPersonalityUpdate(BaseModel):
    """Request model for updating an agent personality.
    
    Attributes:
        name: Optional new name
        personality_description: Optional new description
    """
    name: Optional[str] = Field(None, description="Name of the personality", min_length=2)
    personality_description: Optional[str] = Field(None, description="Description of the personality traits", min_length=10)


class AgentPersonalityResponse(BaseModel):
    """Response model for agent personality operations.
    
    Attributes:
        id: Personality ID
        name: Name of the personality
        personality_description: Description of the personality traits
        created_at: When the personality was created
        owner_id: Owner user ID (None means global)
        is_global: Whether this is a global personality
    """
    id: int = Field(..., description="Personality ID")
    name: str = Field(..., description="Name of the personality")
    personality_description: str = Field(..., description="Description of the personality traits")
    created_at: datetime = Field(..., description="When the personality was created")
    owner_id: Optional[int] = Field(None, description="Owner user ID (None means global)")
    is_global: bool = Field(default=True, description="Whether this is a global personality")


class DeleteAgentPersonalityResponse(BaseModel):
    """Response model for agent personality deletion.
    
    Attributes:
        message: Success message
    """
    message: str = Field(..., description="Success message")


# ========== Agent Schemas ==========

class AgentCreate(BaseModel):
    """Request model for creating an agent.
    
    Attributes:
        id: Agent ID (unique identifier)
        name: Name of the agent
        scenario_id: ID of the scenario this agent belongs to
        agent_personality_id: ID of the agent's personality
        voice: Voice identifier for TTS
        display_text_color: Color for display
        objective: Agent's objective
        instructions: Agent's instructions
        constraints: Agent's constraints
        context: Agent's context
    """
    id: str = Field(..., description="Agent ID (unique identifier)", min_length=2)
    name: str = Field(..., description="Name of the agent", min_length=2)
    scenario_id: int = Field(..., description="ID of the scenario this agent belongs to")
    agent_personality_id: int = Field(..., description="ID of the agent's personality")
    voice: str = Field(default="", description="Voice identifier for TTS")
    display_text_color: str = Field(default="", description="Color for display")
    objective: str = Field(default="", description="Agent's objective")
    instructions: str = Field(default="", description="Agent's instructions")
    constraints: str = Field(default="", description="Agent's constraints")
    context: str = Field(default="", description="Agent's context")


class AgentUpdate(BaseModel):
    """Request model for updating an agent.
    
    Attributes:
        name: Optional new name
        scenario_id: Optional new scenario ID
        agent_personality_id: Optional new personality ID
        voice: Optional new voice
        display_text_color: Optional new display color
        objective: Optional new objective
        instructions: Optional new instructions
        constraints: Optional new constraints
        context: Optional new context
    """
    name: Optional[str] = Field(None, description="Name of the agent", min_length=2)
    scenario_id: Optional[int] = Field(None, description="ID of the scenario this agent belongs to")
    agent_personality_id: Optional[int] = Field(None, description="ID of the agent's personality")
    voice: Optional[str] = Field(None, description="Voice identifier for TTS")
    display_text_color: Optional[str] = Field(None, description="Color for display")
    objective: Optional[str] = Field(None, description="Agent's objective")
    instructions: Optional[str] = Field(None, description="Agent's instructions")
    constraints: Optional[str] = Field(None, description="Agent's constraints")
    context: Optional[str] = Field(None, description="Agent's context")


class AgentResponse(BaseModel):
    """Response model for agent operations.
    
    Attributes:
        id: Agent ID
        name: Name of the agent
        scenario_id: ID of the scenario this agent belongs to
        agent_personality_id: ID of the agent's personality
        voice: Voice identifier for TTS
        display_text_color: Color for display
        objective: Agent's objective
        instructions: Agent's instructions
        constraints: Agent's constraints
        context: Agent's context
        created_at: When the agent was created
        owner_id: Owner user ID (None means global)
        is_global: Whether this is a global agent
    """
    id: str = Field(..., description="Agent ID")
    name: str = Field(..., description="Name of the agent")
    scenario_id: int = Field(..., description="ID of the scenario this agent belongs to")
    agent_personality_id: int = Field(..., description="ID of the agent's personality")
    voice: str = Field(..., description="Voice identifier for TTS")
    display_text_color: str = Field(..., description="Color for display")
    avatar_gcs_uri: str = Field(default="", description="GCS URI for agent avatar image")
    objective: str = Field(..., description="Agent's objective")
    instructions: str = Field(..., description="Agent's instructions")
    constraints: str = Field(..., description="Agent's constraints")
    context: str = Field(..., description="Agent's context")
    created_at: datetime = Field(..., description="When the agent was created")
    owner_id: Optional[int] = Field(None, description="Owner user ID (None means global)")
    is_global: bool = Field(default=True, description="Whether this is a global agent")


class DeleteAgentResponse(BaseModel):
    """Response model for agent deletion.
    
    Attributes:
        message: Success message
    """
    message: str = Field(..., description="Success message")

