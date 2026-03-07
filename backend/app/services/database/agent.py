"""Agent database repository."""

from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.engine import Engine
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.core.logging import logger
from app.models.agent import Agent, AgentPersonality, AgentVoice


class AgentRepository:
    """Repository for Agent, AgentVoice, and AgentPersonality model database operations."""
    
    def __init__(self, engine: Engine):
        """Initialize agent repository with database engine.
        
        Args:
            engine: The SQLModel Engine instance
        """
        self._engine = engine
    
    @property
    def engine(self) -> Engine:
        """Get the database engine."""
        return self._engine
    
    # ========== AgentVoice Methods ==========

    async def get_all_agent_voices(self) -> List[AgentVoice]:
        """Get all agent voices in the system.

        Returns:
            List[AgentVoice]: List of all agent voices
        """
        with Session(self.engine) as session:
            statement = select(AgentVoice).order_by(AgentVoice.voice_name)
            voices = session.exec(statement).all()
            return voices

    async def get_agent_voice_by_name(self, voice_name: str) -> Optional[AgentVoice]:
        """Get an agent voice by name.

        Args:
            voice_name: The name of the voice to retrieve

        Returns:
            Optional[AgentVoice]: The agent voice if found, None otherwise
        """
        with Session(self.engine) as session:
            statement = select(AgentVoice).where(AgentVoice.voice_name == voice_name)
            voice = session.exec(statement).first()
            return voice

    # ========== Agent Methods ==========
    
    async def create_agent(
        self,
        agent_id: str,
        name: str,
        scenario_id: int,
        agent_personality_id: int,
        voice_id: Optional[int] = None,
        display_text_color: str = "",
        avatar_gcs_uri: str = "",
        objective: str = "",
        instructions: str = "",
        constraints: str = "",
        context: str = "",
    ) -> Agent:
        """Create a new agent.

        Args:
            agent_id: The ID for the agent
            name: Name of the agent
            scenario_id: ID of the scenario this agent belongs to
            agent_personality_id: ID of the agent's personality
            voice_id: ID of the agent voice for TTS (optional)
            display_text_color: Color for display
            objective: Agent's objective
            instructions: Agent's instructions
            constraints: Agent's constraints
            context: Agent's context

        Returns:
            Agent: The created agent
        """
        with Session(self.engine) as session:
            agent = Agent(
                id=agent_id,
                name=name,
                scenario_id=scenario_id,
                agent_personality_id=agent_personality_id,
                voice_id=voice_id,
                display_text_color=display_text_color,
                avatar_gcs_uri=avatar_gcs_uri,
                objective=objective,
                instructions=instructions,
                constraints=constraints,
                context=context,
            )
            session.add(agent)
            session.commit()
            session.refresh(agent)
            # Eagerly load voice relationship before session closes
            _ = agent.voice
            logger.info("agent_created", agent_id=agent_id, name=name)
            return agent

    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID.

        Args:
            agent_id: The ID of the agent to retrieve

        Returns:
            Optional[Agent]: The agent if found, None otherwise
        """
        with Session(self.engine) as session:
            statement = select(Agent).where(Agent.id == agent_id).options(
                selectinload(Agent.agent_personality),
                selectinload(Agent.voice)
            )
            agent = session.exec(statement).first()
            return agent

    async def get_all_agents(self) -> List[Agent]:
        """Get all agents in the system.

        Returns:
            List[Agent]: List of all agents
        """
        with Session(self.engine) as session:
            statement = select(Agent).options(
                selectinload(Agent.agent_personality),
                selectinload(Agent.voice)
            ).order_by(Agent.created_at)
            agents = session.exec(statement).all()
            return agents

    async def get_agents_by_scenario(self, scenario_id: int) -> List[Agent]:
        """Get all agents for a specific scenario.

        Args:
            scenario_id: The ID of the scenario

        Returns:
            List[Agent]: List of agents for the scenario
        """
        with Session(self.engine) as session:
            statement = select(Agent).where(Agent.scenario_id == scenario_id).options(
                selectinload(Agent.agent_personality),
                selectinload(Agent.voice)
            ).order_by(Agent.created_at)
            agents = session.exec(statement).all()
            return agents

    async def update_agent(
        self,
        agent_id: str,
        name: Optional[str] = None,
        voice_id: Optional[int] = None,
        display_text_color: Optional[str] = None,
        avatar_gcs_uri: Optional[str] = None,
        objective: Optional[str] = None,
        instructions: Optional[str] = None,
        constraints: Optional[str] = None,
        context: Optional[str] = None,
        scenario_id: Optional[int] = None,
        agent_personality_id: Optional[int] = None,
        clear_voice: bool = False,
    ) -> Agent:
        """Update an agent's attributes.

        Args:
            agent_id: The ID of the agent to update
            name: Optional new name
            voice_id: Optional new voice ID
            display_text_color: Optional new display color
            objective: Optional new objective
            instructions: Optional new instructions
            constraints: Optional new constraints
            context: Optional new context
            scenario_id: Optional new scenario ID
            agent_personality_id: Optional new personality ID
            clear_voice: If True, explicitly set voice_id to None

        Returns:
            Agent: The updated agent

        Raises:
            HTTPException: If agent is not found
        """
        with Session(self.engine) as session:
            agent = session.get(Agent, agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")

            if name is not None:
                agent.name = name
            if voice_id is not None:
                agent.voice_id = voice_id
            elif clear_voice:
                agent.voice_id = None
            if display_text_color is not None:
                agent.display_text_color = display_text_color
            if avatar_gcs_uri is not None:
                agent.avatar_gcs_uri = avatar_gcs_uri
            if objective is not None:
                agent.objective = objective
            if instructions is not None:
                agent.instructions = instructions
            if constraints is not None:
                agent.constraints = constraints
            if context is not None:
                agent.context = context
            if scenario_id is not None:
                agent.scenario_id = scenario_id
            if agent_personality_id is not None:
                agent.agent_personality_id = agent_personality_id

            session.add(agent)
            session.commit()
            session.refresh(agent)
            # Eagerly load voice relationship before session closes
            _ = agent.voice
            logger.info("agent_updated", agent_id=agent_id)
            return agent

    async def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent by ID.

        Args:
            agent_id: The ID of the agent to delete

        Returns:
            bool: True if deletion was successful, False if agent not found
        """
        with Session(self.engine) as session:
            agent = session.get(Agent, agent_id)
            if not agent:
                return False

            session.delete(agent)
            session.commit()
            logger.info("agent_deleted", agent_id=agent_id)
            return True

    async def get_agents_for_user(self, user_id: int) -> List[Agent]:
        """Get all agents available to a user (global + user's local).

        Args:
            user_id: The ID of the user

        Returns:
            List[Agent]: List of global agents and user's local agents
        """
        with Session(self.engine) as session:
            statement = select(Agent).where(
                or_(Agent.owner_id.is_(None), Agent.owner_id == user_id)
            ).options(
                selectinload(Agent.agent_personality),
                selectinload(Agent.voice)
            ).order_by(Agent.created_at)
            agents = session.exec(statement).all()
            return list(agents)

    async def get_user_local_agents(self, user_id: int) -> List[Agent]:
        """Get only user's local agents (not global).

        Args:
            user_id: The ID of the user

        Returns:
            List[Agent]: List of user's local agents only
        """
        with Session(self.engine) as session:
            statement = select(Agent).where(
                Agent.owner_id == user_id
            ).options(
                selectinload(Agent.agent_personality),
                selectinload(Agent.voice)
            ).order_by(Agent.created_at)
            agents = session.exec(statement).all()
            return list(agents)

    async def copy_agent_to_user(self, agent_id: str, user_id: int, target_scenario_id: int) -> Agent:
        """Copy a global agent to a user's local agents.

        Args:
            agent_id: The ID of the agent to copy
            user_id: The ID of the user to copy to
            target_scenario_id: The scenario ID to assign the new agent to

        Returns:
            Agent: The new local copy of the agent

        Raises:
            HTTPException: If agent is not found
        """
        with Session(self.engine) as session:
            original = session.get(Agent, agent_id)
            if not original:
                raise HTTPException(status_code=404, detail="Agent not found")

            import uuid
            new_agent = Agent(
                id=str(uuid.uuid4()),
                name=f"{original.name} (Copy)",
                scenario_id=target_scenario_id,
                agent_personality_id=original.agent_personality_id,
                voice_id=original.voice_id,
                display_text_color=original.display_text_color,
                objective=original.objective,
                instructions=original.instructions,
                constraints=original.constraints,
                context=original.context,
                owner_id=user_id,
            )
            session.add(new_agent)
            session.commit()
            session.refresh(new_agent)

            logger.info("agent_copied_to_user", 
                       original_id=agent_id, 
                       new_id=new_agent.id, 
                       user_id=user_id)
            return new_agent

    async def create_user_agent(
        self,
        user_id: int,
        agent_id: str,
        name: str,
        scenario_id: int,
        agent_personality_id: int,
        voice_id: Optional[int] = None,
        display_text_color: str = "",
        avatar_gcs_uri: str = "",
        objective: str = "",
        instructions: str = "",
        constraints: str = "",
        context: str = "",
    ) -> Agent:
        """Create a new user-local agent.

        Args:
            user_id: The owner user's ID
            agent_id: The ID for the agent
            name: Name of the agent
            scenario_id: ID of the scenario this agent belongs to
            agent_personality_id: ID of the agent's personality
            voice_id: ID of the agent voice for TTS (optional)
            display_text_color: Color for display
            avatar_gcs_uri: Avatar image file path
            objective: Agent's objective
            instructions: Agent's instructions
            constraints: Agent's constraints
            context: Agent's context

        Returns:
            Agent: The created agent
        """
        with Session(self.engine) as session:
            agent = Agent(
                id=agent_id,
                name=name,
                scenario_id=scenario_id,
                agent_personality_id=agent_personality_id,
                voice_id=voice_id,
                display_text_color=display_text_color,
                avatar_gcs_uri=avatar_gcs_uri,
                objective=objective,
                instructions=instructions,
                constraints=constraints,
                context=context,
                owner_id=user_id,
            )
            session.add(agent)
            session.commit()
            session.refresh(agent)
            logger.info("user_agent_created", agent_id=agent_id, name=name, user_id=user_id)
            return agent

    async def update_user_agent(
        self,
        agent_id: str,
        user_id: int,
        name: Optional[str] = None,
        voice_id: Optional[int] = None,
        display_text_color: Optional[str] = None,
        avatar_gcs_uri: Optional[str] = None,
        objective: Optional[str] = None,
        instructions: Optional[str] = None,
        constraints: Optional[str] = None,
        context: Optional[str] = None,
        scenario_id: Optional[int] = None,
        agent_personality_id: Optional[int] = None,
        clear_voice: bool = False,
    ) -> Agent:
        """Update a user's local agent (with ownership check).

        Args:
            agent_id: The ID of the agent to update.
            user_id: The ID of the user (for ownership verification).
            name: Optional new name for the agent.
            voice_id: Optional new voice ID.
            display_text_color: Optional new display text color.
            objective: Optional new objective.
            instructions: Optional new instructions.
            constraints: Optional new constraints.
            context: Optional new context.
            scenario_id: Optional new scenario ID.
            agent_personality_id: Optional new agent personality ID.
            clear_voice: If True, explicitly set voice_id to None.

        Returns:
            Agent: The updated agent.

        Raises:
            HTTPException: If agent is not found or user doesn't own it.
        """
        with Session(self.engine) as session:
            agent = session.get(Agent, agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            if agent.owner_id != user_id:
                raise HTTPException(status_code=403, detail="You don't have permission to edit this agent")

            if name is not None:
                agent.name = name
            if voice_id is not None:
                agent.voice_id = voice_id
            elif clear_voice:
                agent.voice_id = None
            if display_text_color is not None:
                agent.display_text_color = display_text_color
            if avatar_gcs_uri is not None:
                agent.avatar_gcs_uri = avatar_gcs_uri
            if objective is not None:
                agent.objective = objective
            if instructions is not None:
                agent.instructions = instructions
            if constraints is not None:
                agent.constraints = constraints
            if context is not None:
                agent.context = context
            if scenario_id is not None:
                agent.scenario_id = scenario_id
            if agent_personality_id is not None:
                agent.agent_personality_id = agent_personality_id

            session.add(agent)
            session.commit()
            # Re-query with eager loading to avoid lazy load issues after session closes
            statement = select(Agent).where(Agent.id == agent_id).options(
                selectinload(Agent.voice),
                selectinload(Agent.agent_personality)
            )
            updated_agent = session.exec(statement).first()
            logger.info("user_agent_updated", agent_id=agent_id, user_id=user_id)
            return updated_agent

    async def delete_user_agent(self, agent_id: str, user_id: int) -> bool:
        """Delete a user's local agent (with ownership check).

        Args:
            agent_id: The ID of the agent to delete
            user_id: The ID of the user (for ownership verification)

        Returns:
            bool: True if deletion was successful

        Raises:
            HTTPException: If agent is not found or user doesn't own it
        """
        with Session(self.engine) as session:
            agent = session.get(Agent, agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            if agent.owner_id != user_id:
                raise HTTPException(status_code=403, detail="You don't have permission to delete this agent")

            session.delete(agent)
            session.commit()
            logger.info("user_agent_deleted", agent_id=agent_id, user_id=user_id)
            return True

    # ========== AgentPersonality Methods ==========

    async def create_agent_personality(
        self,
        name: str,
        personality_description: str,
    ) -> AgentPersonality:
        """Create a new agent personality.

        Args:
            name: Name of the personality
            personality_description: Description of the personality

        Returns:
            AgentPersonality: The created agent personality
        """
        with Session(self.engine) as session:
            agent_personality = AgentPersonality(
                name=name,
                personality_description=personality_description,
            )
            session.add(agent_personality)
            session.commit()
            session.refresh(agent_personality)
            logger.info("agent_personality_created", personality_id=agent_personality.id, name=name)
            return agent_personality

    async def get_agent_personality(self, personality_id: int) -> Optional[AgentPersonality]:
        """Get an agent personality by ID.

        Args:
            personality_id: The ID of the agent personality to retrieve

        Returns:
            Optional[AgentPersonality]: The agent personality if found, None otherwise
        """
        with Session(self.engine) as session:
            agent_personality = session.get(AgentPersonality, personality_id)
            return agent_personality

    async def get_all_agent_personalities(self) -> List[AgentPersonality]:
        """Get all agent personalities in the system.

        Returns:
            List[AgentPersonality]: List of all agent personalities
        """
        with Session(self.engine) as session:
            statement = select(AgentPersonality).order_by(AgentPersonality.created_at)
            agent_personalities = session.exec(statement).all()
            return agent_personalities

    async def update_agent_personality(
        self,
        personality_id: int,
        name: Optional[str] = None,
        personality_description: Optional[str] = None,
    ) -> AgentPersonality:
        """Update an agent personality's attributes.

        Args:
            personality_id: The ID of the agent personality to update
            name: Optional new name
            personality_description: Optional new personality description

        Returns:
            AgentPersonality: The updated agent personality

        Raises:
            HTTPException: If agent personality is not found
        """
        with Session(self.engine) as session:
            agent_personality = session.get(AgentPersonality, personality_id)
            if not agent_personality:
                raise HTTPException(status_code=404, detail="Agent personality not found")

            if name is not None:
                agent_personality.name = name
            if personality_description is not None:
                agent_personality.personality_description = personality_description

            session.add(agent_personality)
            session.commit()
            session.refresh(agent_personality)
            logger.info("agent_personality_updated", personality_id=personality_id)
            return agent_personality

    async def delete_agent_personality(self, personality_id: int) -> bool:
        """Delete an agent personality by ID.

        Args:
            personality_id: The ID of the agent personality to delete

        Returns:
            bool: True if deletion was successful, False if agent personality not found
        """
        with Session(self.engine) as session:
            agent_personality = session.get(AgentPersonality, personality_id)
            if not agent_personality:
                return False

            session.delete(agent_personality)
            session.commit()
            logger.info("agent_personality_deleted", personality_id=personality_id)
            return True

    async def get_agent_personalities_for_user(self, user_id: int) -> List[AgentPersonality]:
        """Get all agent personalities available to a user (global + user's local).

        Args:
            user_id: The ID of the user

        Returns:
            List[AgentPersonality]: List of global and user's local agent personalities
        """
        with Session(self.engine) as session:
            statement = select(AgentPersonality).where(
                or_(AgentPersonality.owner_id.is_(None), AgentPersonality.owner_id == user_id)
            ).order_by(AgentPersonality.created_at)
            personalities = session.exec(statement).all()
            return list(personalities)

    async def get_user_local_agent_personalities(self, user_id: int) -> List[AgentPersonality]:
        """Get only user's local agent personalities (not global).

        Args:
            user_id: The ID of the user

        Returns:
            List[AgentPersonality]: List of user's local agent personalities only
        """
        with Session(self.engine) as session:
            statement = select(AgentPersonality).where(
                AgentPersonality.owner_id == user_id
            ).order_by(AgentPersonality.created_at)
            personalities = session.exec(statement).all()
            return list(personalities)

    async def copy_agent_personality_to_user(self, personality_id: int, user_id: int) -> AgentPersonality:
        """Copy a global agent personality to a user's local agent personalities.

        Args:
            personality_id: The ID of the agent personality to copy
            user_id: The ID of the user to copy to

        Returns:
            AgentPersonality: The new local copy of the agent personality

        Raises:
            HTTPException: If agent personality is not found
        """
        with Session(self.engine) as session:
            original = session.get(AgentPersonality, personality_id)
            if not original:
                raise HTTPException(status_code=404, detail="Agent personality not found")

            new_personality = AgentPersonality(
                name=f"{original.name} (Copy)",
                personality_description=original.personality_description,
                owner_id=user_id,
            )
            session.add(new_personality)
            session.commit()
            session.refresh(new_personality)

            logger.info("agent_personality_copied_to_user", 
                       original_id=personality_id, 
                       new_id=new_personality.id, 
                       user_id=user_id)
            return new_personality

    async def create_user_agent_personality(
        self,
        user_id: int,
        name: str,
        personality_description: str,
    ) -> AgentPersonality:
        """Create a new user-local agent personality.

        Args:
            user_id: The owner user's ID
            name: Name of the personality
            personality_description: Description of the personality

        Returns:
            AgentPersonality: The created agent personality
        """
        with Session(self.engine) as session:
            personality = AgentPersonality(
                name=name,
                personality_description=personality_description,
                owner_id=user_id,
            )
            session.add(personality)
            session.commit()
            session.refresh(personality)
            logger.info("user_agent_personality_created", personality_id=personality.id, name=name, user_id=user_id)
            return personality

    async def update_user_agent_personality(
        self,
        personality_id: int,
        user_id: int,
        name: Optional[str] = None,
        personality_description: Optional[str] = None,
    ) -> AgentPersonality:
        """Update a user's local agent personality (with ownership check).

        Args:
            personality_id: The ID of the personality to update
            user_id: The ID of the user (for ownership verification)
            name: Optional new name
            personality_description: Optional new description

        Returns:
            AgentPersonality: The updated agent personality

        Raises:
            HTTPException: If personality is not found or user doesn't own it
        """
        with Session(self.engine) as session:
            personality = session.get(AgentPersonality, personality_id)
            if not personality:
                raise HTTPException(status_code=404, detail="Agent personality not found")
            if personality.owner_id != user_id:
                raise HTTPException(status_code=403, detail="You don't have permission to edit this personality")

            if name is not None:
                personality.name = name
            if personality_description is not None:
                personality.personality_description = personality_description

            session.add(personality)
            session.commit()
            session.refresh(personality)
            logger.info("user_agent_personality_updated", personality_id=personality_id, user_id=user_id)
            return personality

    async def delete_user_agent_personality(self, personality_id: int, user_id: int) -> bool:
        """Delete a user's local agent personality (with ownership check).

        Args:
            personality_id: The ID of the personality to delete
            user_id: The ID of the user (for ownership verification)

        Returns:
            bool: True if deletion was successful

        Raises:
            HTTPException: If personality is not found or user doesn't own it
        """
        with Session(self.engine) as session:
            personality = session.get(AgentPersonality, personality_id)
            if not personality:
                raise HTTPException(status_code=404, detail="Agent personality not found")
            if personality.owner_id != user_id:
                raise HTTPException(status_code=403, detail="You don't have permission to delete this personality")

            session.delete(personality)
            session.commit()
            logger.info("user_agent_personality_deleted", personality_id=personality_id, user_id=user_id)
            return True
