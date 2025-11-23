"""This file contains the agent seed data for the application."""

import os
from yaml import safe_load
from sqlmodel import Session, select
from app.services.database import database_service
from app.models.agent import Agent

def load_agent_data() -> list[Agent]:
    """Load the agent data from the file."""
    with open(os.path.join(os.path.dirname(__file__), "agent_data.yaml"), "r") as f:
        agent_data_yaml = safe_load(f)
    
    agents = []
    for agent_data in agent_data_yaml:
        agent = Agent(
            id=agent_data["id"],
            name=agent_data["name"],
            scenario_id=agent_data["scenario_id"],
            voice=agent_data["voice"],
            display_text_color=agent_data["display_text_color"],
            objective=agent_data["objective"],
            instructions=agent_data["instructions"],
            constraints=agent_data["constraints"],
            context=agent_data["context"],
            agent_personality_id=agent_data["agent_personality_id"],
        )
        agents.append(agent)
    
    return agents

def seed_agent_data():
    """Seed the agent data into the database."""
    with Session(database_service.engine) as session:
        data_exists = session.exec(select(Agent)).all()
        if data_exists:
            return
        for agent in load_agent_data():
            session.add(agent)
        session.commit()