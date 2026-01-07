"""Scenario fixture factories for testing."""

from typing import Optional

from sqlmodel import Session

from app.models.scenario import Scenario


def create_test_scenario(
    session: Session,
    name: str = "Test Scenario",
    description: str = "Test scenario description",
    overview: str = "Test overview",
    system_instructions: str = "Test system instructions",
    initial_prompt: str = "Test initial prompt",
    teaching_objectives: str = "Test teaching objectives",
    owner_id: Optional[int] = None,
) -> Scenario:
    """Create a test scenario with specified attributes.

    Args:
        session: Database session
        name: Scenario name
        description: Scenario description
        overview: Scenario overview
        system_instructions: System instructions for the scenario
        initial_prompt: Initial prompt for the scenario
        teaching_objectives: Teaching objectives
        owner_id: Optional owner user ID (None for global scenarios)

    Returns:
        Scenario: Created scenario instance
    """
    scenario = Scenario(
        name=name,
        description=description,
        overview=overview,
        system_instructions=system_instructions,
        initial_prompt=initial_prompt,
        teaching_objectives=teaching_objectives,
        owner_id=owner_id,
    )
    session.add(scenario)
    session.commit()
    session.refresh(scenario)
    return scenario


def create_test_scenarios_batch(
    session: Session,
    count: int = 3,
    prefix: str = "Test Scenario",
) -> list[Scenario]:
    """Create a batch of test scenarios.

    Args:
        session: Database session
        count: Number of scenarios to create
        prefix: Name prefix for scenarios

    Returns:
        list[Scenario]: List of created scenarios
    """
    scenarios = []
    for i in range(1, count + 1):
        scenario = create_test_scenario(
            session=session,
            name=f"{prefix} {i}",
            description=f"Description for {prefix} {i}",
        )
        scenarios.append(scenario)
    return scenarios
