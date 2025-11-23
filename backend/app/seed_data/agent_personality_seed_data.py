"""This file contains the agent personality seed data for the application."""

from sqlmodel import Session, select
from app.services.database import database_service
from app.models.agent import AgentPersonality

agent_personalities = [
    AgentPersonality(
        id=1,
        name="Default Student Personality",
        personality_description="A typical 8th-grade student personality",
    )
]

def seed_agent_personality_data():
    """Seed the agent personality data into the database."""
    with Session(database_service.engine) as session:
        data_exists = session.exec(select(AgentPersonality)).all()
        if data_exists:
            return
        for personality in agent_personalities:
            session.add(personality)
        session.commit()

