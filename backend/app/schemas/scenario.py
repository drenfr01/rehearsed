
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
