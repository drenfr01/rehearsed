"""This file contains the scenario seed data for the application."""
import os

from sqlmodel import Session, select
from yaml import safe_load

from app.models.scenario import Scenario
from app.services.database import database_service

scenarios = [
    Scenario(
        name="Scenario 1",
        description="Scenario 1 description",
        overview="Scenario 1 overview",
        system_instructions="Scenario 1 system instructions",
        initial_prompt="Scenario 1 initial prompt",
        owner_id=None  # Global scenario (admin-created)
    )
]

def load_scenario_data() -> list[Scenario]:
    """Load the scenario data from the file."""
    with open(os.path.join(os.path.dirname(__file__), "scenario_data.yaml"), "r") as f:
        scenario_data_yaml = safe_load(f)
    
    scenarios = []
    for scenario_data in scenario_data_yaml:
        scenario = Scenario(
            name=scenario_data["name"],
            description=scenario_data["description"],
            overview=scenario_data["overview"],
            system_instructions=scenario_data["system_instructions"],
            initial_prompt=scenario_data["initial_prompt"],
            teaching_objectives=scenario_data.get("teaching_objectives", ""),
            owner_id=scenario_data.get("owner_id"),  # None for global scenarios
        )
        scenarios.append(scenario)
    
    return scenarios

def seed_scenario_data():
    """Seed the scenario data into the database."""
    with Session(database_service.engine) as session:
        # Only check for global scenarios (owner_id is None)
        # User-created scenarios should not prevent seeding global ones
        global_scenarios_exist = session.exec(
            select(Scenario).where(Scenario.owner_id.is_(None))
        ).first()
        if global_scenarios_exist:
            return
        for scenario in load_scenario_data():
            session.add(scenario)
        session.commit()