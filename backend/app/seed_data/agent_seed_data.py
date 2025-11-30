"""This file contains the agent seed data for the application."""

import os
from typing import Optional
from yaml import safe_load
from sqlmodel import Session, select
from app.services.database import database_service
from app.models.agent import Agent, AgentPersonality, AgentVoice
from app.models.scenario import Scenario

def load_agent_data(session: Session) -> list[Agent]:
    """Load the agent data from the file.
    
    Args:
        session: Database session to look up scenario, personality, and voice IDs by name
    """
    with open(os.path.join(os.path.dirname(__file__), "agent_data.yaml"), "r") as f:
        agent_data_yaml = safe_load(f)
    
    # Build caches of names to IDs
    scenarios = session.exec(select(Scenario)).all()
    scenario_name_to_id = {s.name: s.id for s in scenarios}
    
    personalities = session.exec(select(AgentPersonality)).all()
    personality_name_to_id = {p.name: p.id for p in personalities}
    
    voices = session.exec(select(AgentVoice)).all()
    voice_name_to_id = {v.voice_name: v.id for v in voices}
    
    agents = []
    for agent_data in agent_data_yaml:
        scenario_name = agent_data["scenario_name"]
        scenario_id = scenario_name_to_id.get(scenario_name)
        if scenario_id is None:
            raise ValueError(f"Scenario '{scenario_name}' not found. Make sure scenarios are seeded first.")
        
        personality_name = agent_data["agent_personality_name"]
        personality_id = personality_name_to_id.get(personality_name)
        if personality_id is None:
            raise ValueError(f"AgentPersonality '{personality_name}' not found. Make sure personalities are seeded first.")
        
        # Look up voice_id from voice_name (optional field)
        voice_name = agent_data.get("voice_name", "")
        voice_id: Optional[int] = None
        if voice_name:
            voice_id = voice_name_to_id.get(voice_name)
            if voice_id is None:
                raise ValueError(f"AgentVoice '{voice_name}' not found. Make sure voices are seeded first.")
        
        agent = Agent(
            id=agent_data["id"],
            name=agent_data["name"],
            scenario_id=scenario_id,
            voice_id=voice_id,
            display_text_color=agent_data["display_text_color"],
            objective=agent_data["objective"],
            instructions=agent_data["instructions"],
            constraints=agent_data["constraints"],
            context=agent_data["context"],
            agent_personality_id=personality_id,
        )
        agents.append(agent)
    
    return agents

def seed_agent_data():
    """Seed the agent data into the database."""
    with Session(database_service.engine) as session:
        # Only check for global agents (owner_id is None)
        # User-created agents should not prevent seeding global ones
        global_agents_exist = session.exec(
            select(Agent).where(Agent.owner_id == None)
        ).first()
        if global_agents_exist:
            return
        for agent in load_agent_data(session):
            session.add(agent)
        session.commit()