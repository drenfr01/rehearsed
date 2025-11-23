from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

from app.models.scenario import Scenario

class ScenarioRequest(BaseModel):
    """Request model for scenario endpoint.

    Attributes:
        scenario_id: The ID of the scenario to get.
    """

    scenario_id: int = Field(default=None, description="The ID of the scenario to get")

class ScenarioResponse(BaseModel):
    """Response model for scenario endpoint.

    Attributes:
        scenario: The scenario to get.
    """

    scenarios: Scenario = Field(default=None, description="A scenario")

class AddScenarioRequest(BaseModel):
    """Request model for scenario endpoint.

    Attributes:
        scenario: The scenario to add.
    """

    scenario: Scenario = Field(default=None, description="The scenario to add")

class AddScenarioResponse(BaseModel):
    """Response model for scenario endpoint.

    Attributes:
        scenario: The scenario to add.
    """

    scenario_id: int = Field(default=None, description="The ID of the scenario that was added")


# ========== Admin Scenario Schemas ==========

class ScenarioCreateRequest(BaseModel):
    """Request model for creating a scenario.
    
    Attributes:
        name: Name of the scenario
        description: Description of the scenario
        overview: Overview of the scenario
        system_instructions: System instructions for the scenario
        initial_prompt: Initial prompt for the scenario
    """
    name: str = Field(..., description="Name of the scenario", min_length=2)
    description: str = Field(..., description="Description of the scenario", min_length=10)
    overview: str = Field(..., description="Overview of the scenario", min_length=10)
    system_instructions: str = Field(..., description="System instructions for the scenario", min_length=10)
    initial_prompt: str = Field(..., description="Initial prompt for the scenario", min_length=5)


class ScenarioUpdateRequest(BaseModel):
    """Request model for updating a scenario.
    
    Attributes:
        name: Optional new name
        description: Optional new description
        overview: Optional new overview
        system_instructions: Optional new system instructions
        initial_prompt: Optional new initial prompt
    """
    name: Optional[str] = Field(None, description="Name of the scenario", min_length=2)
    description: Optional[str] = Field(None, description="Description of the scenario", min_length=10)
    overview: Optional[str] = Field(None, description="Overview of the scenario", min_length=10)
    system_instructions: Optional[str] = Field(None, description="System instructions for the scenario", min_length=10)
    initial_prompt: Optional[str] = Field(None, description="Initial prompt for the scenario", min_length=5)


class ScenarioAdminResponse(BaseModel):
    """Response model for scenario operations.
    
    Attributes:
        id: Scenario ID
        name: Name of the scenario
        description: Description of the scenario
        overview: Overview of the scenario
        system_instructions: System instructions for the scenario
        initial_prompt: Initial prompt for the scenario
        created_at: When the scenario was created
    """
    id: int = Field(..., description="Scenario ID")
    name: str = Field(..., description="Name of the scenario")
    description: str = Field(..., description="Description of the scenario")
    overview: str = Field(..., description="Overview of the scenario")
    system_instructions: str = Field(..., description="System instructions for the scenario")
    initial_prompt: str = Field(..., description="Initial prompt for the scenario")
    created_at: datetime = Field(..., description="When the scenario was created")


class DeleteScenarioResponse(BaseModel):
    """Response model for scenario deletion.
    
    Attributes:
        message: Success message
    """
    message: str = Field(..., description="Success message")
