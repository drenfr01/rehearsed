"""This file contains the agent personality seed data for the application."""

from sqlmodel import Session, select
from app.services.database import database_service
from app.models.agent import AgentPersonality

agent_personalities = [
    AgentPersonality(
        name="Default Student Personality",
        personality_description="A typical 8th-grade student personality",
        owner_id=None  # Global personality (admin-created)
    )
]

def seed_agent_personality_data():
    """Seed the agent personality data into the database."""
    with Session(database_service.engine) as session:
        # Only check for global personalities (owner_id is None)
        # User-created personalities should not prevent seeding global ones
        global_personalities_exist = session.exec(
            select(AgentPersonality).where(AgentPersonality.owner_id.is_(None))
        ).first()
        if global_personalities_exist:
            return
        for personality in agent_personalities:
            session.add(personality)
        session.commit()

