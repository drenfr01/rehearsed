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
    
    return agent_data_yaml

def seed_agent_data():
    """Seed the agent data into the database."""
    with Session(database_service.engine) as session:
        data_exists = session.exec(select(Agent)).all()
        if data_exists:
            return
        for agent in load_agent_data():
            session.add(agent)
        session.commit()