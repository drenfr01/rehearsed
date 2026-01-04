"""Agent fixture factories for testing."""

import uuid
from typing import Optional

from sqlmodel import Session

from app.models.agent import Agent, AgentPersonality, AgentVoice


def create_test_agent_personality(
    session: Session,
    name: str = "Test Personality",
    personality_description: str = "Test personality description",
    owner_id: Optional[int] = None,
) -> AgentPersonality:
    """Create a test agent personality.

    Args:
        session: Database session
        name: Personality name
        personality_description: Personality description
        owner_id: Optional owner user ID (None for global personalities)

    Returns:
        AgentPersonality: Created agent personality instance
    """
    personality = AgentPersonality(
        name=name,
        personality_description=personality_description,
        owner_id=owner_id,
    )
    session.add(personality)
    session.commit()
    session.refresh(personality)
    return personality


def create_test_agent_voice(
    session: Session,
    voice_name: str = "test-voice",
) -> AgentVoice:
    """Create a test agent voice.

    Args:
        session: Database session
        voice_name: Voice name

    Returns:
        AgentVoice: Created agent voice instance
    """
    voice = AgentVoice(voice_name=voice_name)
    session.add(voice)
    session.commit()
    session.refresh(voice)
    return voice


def create_test_agent(
    session: Session,
    scenario_id: int,
    agent_personality_id: int,
    agent_id: Optional[str] = None,
    name: str = "Test Agent",
    voice_id: Optional[int] = None,
    display_text_color: str = "#000000",
    objective: str = "Test objective",
    instructions: str = "Test instructions",
    constraints: str = "Test constraints",
    context: str = "Test context",
    owner_id: Optional[int] = None,
) -> Agent:
    """Create a test agent with specified attributes.

    Args:
        session: Database session
        scenario_id: ID of the scenario this agent belongs to
        agent_personality_id: ID of the agent's personality
        agent_id: Optional agent ID (generated if not provided)
        name: Agent name
        voice_id: Optional voice ID
        display_text_color: Display text color
        objective: Agent objective
        instructions: Agent instructions
        constraints: Agent constraints
        context: Agent context
        owner_id: Optional owner user ID (None for global agents)

    Returns:
        Agent: Created agent instance
    """
    if agent_id is None:
        agent_id = str(uuid.uuid4())

    agent = Agent(
        id=agent_id,
        name=name,
        scenario_id=scenario_id,
        agent_personality_id=agent_personality_id,
        voice_id=voice_id,
        display_text_color=display_text_color,
        objective=objective,
        instructions=instructions,
        constraints=constraints,
        context=context,
        owner_id=owner_id,
    )
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


def create_test_agents_batch(
    session: Session,
    scenario_id: int,
    agent_personality_id: int,
    count: int = 3,
    prefix: str = "Test Agent",
) -> list[Agent]:
    """Create a batch of test agents.

    Args:
        session: Database session
        scenario_id: ID of the scenario agents belong to
        agent_personality_id: ID of the agent personality
        count: Number of agents to create
        prefix: Name prefix for agents

    Returns:
        list[Agent]: List of created agents
    """
    agents = []
    for i in range(1, count + 1):
        agent = create_test_agent(
            session=session,
            scenario_id=scenario_id,
            agent_personality_id=agent_personality_id,
            name=f"{prefix} {i}",
        )
        agents.append(agent)
    return agents
