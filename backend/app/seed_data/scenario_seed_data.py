"""This file contains the scenario seed data for the application."""
from sqlmodel import Session, select
from app.services.database import database_service
from app.models.scenario import Scenario
import os
from yaml import safe_load

scenarios = [
    Scenario(
        id=1,
        name="Scenario 1",
        description="Scenario 1 description",
        overview="Scenario 1 overview",
        system_instructions="Scenario 1 system instructions",
        initial_prompt="Scenario 1 initial prompt"
    )
]

def load_scenario_data() -> list[Scenario]:
    """Load the scenario data from the file."""
    with open(os.path.join(os.path.dirname(__file__), "scenario_data.yaml"), "r") as f:
        scenario_data_yaml = safe_load(f)
    
    scenarios = []
    for scenario_id, scenario_data in enumerate(scenario_data_yaml, start=1):
        scenario = Scenario(
            id=scenario_id,
            name=scenario_data["name"],
            description=scenario_data["description"],
            overview=scenario_data["overview"],
            system_instructions=scenario_data["system_instructions"],
            initial_prompt=scenario_data["initial_prompt"],
        )
        scenarios.append(scenario)
    
    return scenarios

def seed_scenario_data():
    """Seed the scenario data into the database."""
    with Session(database_service.engine) as session:
        data_exists = session.exec(select(Scenario)).all()
        if data_exists:
            return
        for scenario in load_scenario_data():
            session.add(scenario)
        session.commit()