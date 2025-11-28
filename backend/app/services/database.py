"""This file contains the database service for the application."""

from typing import (
    List,
    Optional,
)

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import QueuePool
from sqlmodel import (
    Session,
    SQLModel,
    create_engine,
    select,
)

from app.core.config import (
    Environment,
    settings,
)
from app.core.logging import logger
from app.models.session import Session as ChatSession
# Models: note, you need to import models here so they are created by create_all below
from app.models.user import User
from app.models.scenario import Scenario
from app.models.agent import Agent, AgentPersonality
from app.models.feedback import Feedback, FeedbackType


class DatabaseService:
    """Service class for database operations.

    This class handles all database operations for Users, Sessions, and Messages.
    It uses SQLModel for ORM operations and maintains a connection pool.
    """

    def __init__(self):
        """Initialize database service with connection pool."""
        try:
            # Configure environment-specific database connection pool settings
            pool_size = settings.POSTGRES_POOL_SIZE
            max_overflow = settings.POSTGRES_MAX_OVERFLOW

            # Create engine with appropriate pool configuration
            if settings.ENVIRONMENT == Environment.PRODUCTION:
                connection_url = (
                    f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
                    f"@/rehearsed?host=/cloudsql/{settings.POSTGRES_HOST}"
                )
            else:
                connection_url = (
                    f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
                    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
                )

            self.engine = create_engine(
                connection_url,
                pool_pre_ping=True,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=30,  # Connection timeout (seconds)
                pool_recycle=1800,  # Recycle connections after 30 minutes
            )

            # Create tables (only if they don't exist)
            SQLModel.metadata.create_all(self.engine)

            logger.info(
                "database_initialized",
                environment=settings.ENVIRONMENT.value,
                pool_size=pool_size,
                max_overflow=max_overflow,
            )

            # TODO: potentially move this to a separate service
            self.current_scenario: Scenario | None = None

        except SQLAlchemyError as e:
            logger.error("database_initialization_error", error=str(e), environment=settings.ENVIRONMENT.value)
            # In production, don't raise - allow app to start even with DB issues
            if settings.ENVIRONMENT != Environment.PRODUCTION:
                raise

    async def create_user(self, email: str, password: str, is_approved: bool = False) -> User:
        """Create a new user.

        Args:
            email: User's email address
            password: Hashed password
            is_approved: Whether the user is approved (default False for self-registration)

        Returns:
            User: The created user
        """
        with Session(self.engine) as session:
            user = User(email=email, hashed_password=password, is_approved=is_approved)
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info("user_created", email=email, is_approved=is_approved)
            return user

    async def get_user(self, user_id: int) -> Optional[User]:
        """Get a user by ID.

        Args:
            user_id: The ID of the user to retrieve

        Returns:
            Optional[User]: The user if found, None otherwise
        """
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email.

        Args:
            email: The email of the user to retrieve

        Returns:
            Optional[User]: The user if found, None otherwise
        """
        with Session(self.engine) as session:
            statement = select(User).where(User.email == email)
            user = session.exec(statement).first()
            return user

    async def delete_user_by_email(self, email: str) -> bool:
        """Delete a user by email.

        Args:
            email: The email of the user to delete

        Returns:
            bool: True if deletion was successful, False if user not found
        """
        with Session(self.engine) as session:
            user = session.exec(select(User).where(User.email == email)).first()
            if not user:
                return False

            session.delete(user)
            session.commit()
            logger.info("user_deleted", email=email)
            return True

    async def get_pending_users(self) -> List[User]:
        """Get all users pending approval.

        Returns:
            List[User]: List of unapproved users
        """
        with Session(self.engine) as session:
            statement = select(User).where(User.is_approved == False).order_by(User.created_at)
            users = list(session.exec(statement).all())
            return users

    async def approve_user(self, user_id: int) -> User:
        """Approve a user account.

        Args:
            user_id: The ID of the user to approve

        Returns:
            User: The approved user

        Raises:
            HTTPException: If user is not found
        """
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            user.is_approved = True
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info("user_approved", user_id=user_id, email=user.email)
            return user

    async def create_session(self, session_id: str, user_id: int, name: str = "") -> ChatSession:
        """Create a new chat session.

        Args:
            session_id: The ID for the new session
            user_id: The ID of the user who owns the session
            name: Optional name for the session (defaults to empty string)

        Returns:
            ChatSession: The created session
        """
        with Session(self.engine) as session:
            chat_session = ChatSession(id=session_id, user_id=user_id, name=name)
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            logger.info("session_created", session_id=session_id, user_id=user_id, name=name)
            return chat_session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID.

        Args:
            session_id: The ID of the session to delete

        Returns:
            bool: True if deletion was successful, False if session not found
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session:
                return False

            session.delete(chat_session)
            session.commit()
            logger.info("session_deleted", session_id=session_id)
            return True

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID.

        Args:
            session_id: The ID of the session to retrieve

        Returns:
            Optional[ChatSession]: The session if found, None otherwise
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            return chat_session

    async def get_user_sessions(self, user_id: int) -> List[ChatSession]:
        """Get all sessions for a user.

        Args:
            user_id: The ID of the user

        Returns:
            List[ChatSession]: List of user's sessions
        """
        with Session(self.engine) as session:
            statement = select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.created_at)
            sessions = session.exec(statement).all()
            return sessions

    async def update_session_name(self, session_id: str, name: str) -> ChatSession:
        """Update a session's name.

        Args:
            session_id: The ID of the session to update
            name: The new name for the session

        Returns:
            ChatSession: The updated session

        Raises:
            HTTPException: If session is not found
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session:
                raise HTTPException(status_code=404, detail="Session not found")

            chat_session.name = name
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            logger.info("session_name_updated", session_id=session_id, name=name)
            return chat_session

    def get_session_maker(self):
        """Get a session maker for creating database sessions.

        Returns:
            Session: A SQLModel session maker
        """
        return Session(self.engine)

    async def health_check(self) -> bool:
        """Check database connection health.

        Returns:
            bool: True if database is healthy, False otherwise
        """
        try:
            with Session(self.engine) as session:
                # Execute a simple query to check connection
                session.exec(select(1)).first()
                return True
        except Exception as e:
            logger.error("database_health_check_failed", error=str(e))
            return False

    def get_current_scenario(self) -> Scenario:
        """
        Returns the scenario data for the currently set scenario

        Returns:
            The scenario data for the current scenario
        """
        return self.scenario

    def set_scenario(self, scenario_id: int) -> None:
        """
        Sets the scenario data for the currently set scenario

        Args:
            scenario: The scenario to set
        """
        with Session(self.engine) as session:
            statement = select(Scenario).where(Scenario.id == scenario_id)
            scenario = session.exec(statement).one()
            self.current_scenario = scenario
            return scenario

    async def get_all_scenarios(self) -> list[Scenario]:
        """Get all scenarios in the system.

        Returns:
            List[Scenario]: List of all scenarios
        """
        with Session(self.engine) as session:
            statement = select(Scenario)
            scenarios = session.exec(statement).all()
            return scenarios

    async def get_all_users(self) -> List[User]:
        """Get all users in the system.

        Returns:
            List[User]: List of all users
        """
        with Session(self.engine) as session:
            statement = select(User).order_by(User.created_at)
            users = session.exec(statement).all()
            return users

    async def update_user_email(self, user_id: int, email: str) -> User:
        """Update a user's email address.

        Args:
            user_id: The ID of the user to update
            email: The new email address

        Returns:
            User: The updated user

        Raises:
            HTTPException: If user is not found
        """
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            user.email = email
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info("user_email_updated", user_id=user_id, email=email)
            return user

    async def update_user_admin_status(self, user_id: int, is_admin: bool) -> User:
        """Update a user's admin status.

        Args:
            user_id: The ID of the user to update
            is_admin: The new admin status

        Returns:
            User: The updated user

        Raises:
            HTTPException: If user is not found
        """
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            user.is_admin = is_admin
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info("user_admin_status_updated", user_id=user_id, is_admin=is_admin)
            return user

    async def delete_user(self, user_id: int) -> bool:
        """Delete a user by ID.

        Args:
            user_id: The ID of the user to delete

        Returns:
            bool: True if deletion was successful, False if user not found
        """
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            if not user:
                return False

            session.delete(user)
            session.commit()
            logger.info("user_deleted", user_id=user_id)
            return True

    # ========== Agent Methods ==========
    
    async def create_agent(
        self,
        agent_id: str,
        name: str,
        scenario_id: int,
        agent_personality_id: int,
        voice: str = "",
        display_text_color: str = "",
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
            voice: Voice identifier for TTS
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
                voice=voice,
                display_text_color=display_text_color,
                objective=objective,
                instructions=instructions,
                constraints=constraints,
                context=context,
            )
            session.add(agent)
            session.commit()
            session.refresh(agent)
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
            statement = select(Agent).where(Agent.id == agent_id).options(selectinload(Agent.agent_personality))
            agent = session.exec(statement).first()
            return agent

    async def get_all_agents(self) -> List[Agent]:
        """Get all agents in the system.

        Returns:
            List[Agent]: List of all agents
        """
        with Session(self.engine) as session:
            statement = select(Agent).options(selectinload(Agent.agent_personality)).order_by(Agent.created_at)
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
            statement = select(Agent).where(Agent.scenario_id == scenario_id).options(selectinload(Agent.agent_personality)).order_by(Agent.created_at)
            agents = session.exec(statement).all()
            return agents

    async def update_agent(
        self,
        agent_id: str,
        name: Optional[str] = None,
        voice: Optional[str] = None,
        display_text_color: Optional[str] = None,
        objective: Optional[str] = None,
        instructions: Optional[str] = None,
        constraints: Optional[str] = None,
        context: Optional[str] = None,
        scenario_id: Optional[int] = None,
        agent_personality_id: Optional[int] = None,
    ) -> Agent:
        """Update an agent's attributes.

        Args:
            agent_id: The ID of the agent to update
            name: Optional new name
            voice: Optional new voice
            display_text_color: Optional new display color
            objective: Optional new objective
            instructions: Optional new instructions
            constraints: Optional new constraints
            context: Optional new context
            scenario_id: Optional new scenario ID
            agent_personality_id: Optional new personality ID

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
            if voice is not None:
                agent.voice = voice
            if display_text_color is not None:
                agent.display_text_color = display_text_color
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

    # ========== Scenario Methods ==========

    async def create_scenario(
        self,
        name: str,
        description: str,
        overview: str,
        system_instructions: str,
        initial_prompt: str,
    ) -> Scenario:
        """Create a new scenario.

        Args:
            name: Name of the scenario
            description: Description of the scenario
            overview: Overview of the scenario
            system_instructions: System instructions for the scenario
            initial_prompt: Initial prompt for the scenario

        Returns:
            Scenario: The created scenario
        """
        with Session(self.engine) as session:
            scenario = Scenario(
                name=name,
                description=description,
                overview=overview,
                system_instructions=system_instructions,
                initial_prompt=initial_prompt,
            )
            session.add(scenario)
            session.commit()
            session.refresh(scenario)
            logger.info("scenario_created", scenario_id=scenario.id, name=name)
            return scenario

    async def get_scenario(self, scenario_id: int) -> Optional[Scenario]:
        """Get a scenario by ID.

        Args:
            scenario_id: The ID of the scenario to retrieve

        Returns:
            Optional[Scenario]: The scenario if found, None otherwise
        """
        with Session(self.engine) as session:
            scenario = session.get(Scenario, scenario_id)
            return scenario

    async def update_scenario(
        self,
        scenario_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        overview: Optional[str] = None,
        system_instructions: Optional[str] = None,
        initial_prompt: Optional[str] = None,
    ) -> Scenario:
        """Update a scenario's attributes.

        Args:
            scenario_id: The ID of the scenario to update
            name: Optional new name
            description: Optional new description
            overview: Optional new overview
            system_instructions: Optional new system instructions
            initial_prompt: Optional new initial prompt

        Returns:
            Scenario: The updated scenario

        Raises:
            HTTPException: If scenario is not found
        """
        with Session(self.engine) as session:
            scenario = session.get(Scenario, scenario_id)
            if not scenario:
                raise HTTPException(status_code=404, detail="Scenario not found")

            if name is not None:
                scenario.name = name
            if description is not None:
                scenario.description = description
            if overview is not None:
                scenario.overview = overview
            if system_instructions is not None:
                scenario.system_instructions = system_instructions
            if initial_prompt is not None:
                scenario.initial_prompt = initial_prompt

            session.add(scenario)
            session.commit()
            session.refresh(scenario)
            logger.info("scenario_updated", scenario_id=scenario_id)
            return scenario

    async def delete_scenario(self, scenario_id: int) -> bool:
        """Delete a scenario by ID.

        Args:
            scenario_id: The ID of the scenario to delete

        Returns:
            bool: True if deletion was successful, False if scenario not found
        """
        with Session(self.engine) as session:
            scenario = session.get(Scenario, scenario_id)
            if not scenario:
                return False

            session.delete(scenario)
            session.commit()
            logger.info("scenario_deleted", scenario_id=scenario_id)
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

    # ========== Feedback Methods ==========

    async def get_feedback(self, feedback_id: int) -> Optional[Feedback]:
        """Get a feedback by ID.

        Args:
            feedback_id: The ID of the feedback to retrieve

        Returns:
            Optional[Feedback]: The feedback if found, None otherwise
        """
        with Session(self.engine) as session:
            statement = select(Feedback).where(Feedback.id == feedback_id)
            feedback = session.exec(statement).first()
            return feedback

    async def get_feedback_by_type(self, feedback_type: FeedbackType | str) -> Optional[Feedback]:
        """Get a feedback by type.

        Args:
            feedback_type: The type of feedback to retrieve (FeedbackType.INLINE or FeedbackType.SUMMARY)

        Returns:
            Optional[Feedback]: The feedback if found, None otherwise
        """
        # Convert string to enum if needed
        if isinstance(feedback_type, str):
            feedback_type = FeedbackType(feedback_type)
        with Session(self.engine) as session:
            statement = select(Feedback).where(Feedback.feedback_type == feedback_type)
            feedback = session.exec(statement).first()
            return feedback

    async def get_all_feedback(self) -> List[Feedback]:
        """Get all feedback in the system.

        Returns:
            List[Feedback]: List of all feedback
        """
        with Session(self.engine) as session:
            statement = select(Feedback).order_by(Feedback.created_at)
            feedbacks = session.exec(statement).all()
            return feedbacks

    async def create_feedback(
        self,
        feedback_type: FeedbackType | str,
        objective: str,
        instructions: str,
        constraints: str,
        context: str,
        output_format: str = "",
    ) -> Feedback:
        """Create a new feedback.

        Args:
            feedback_type: Type of feedback ("inline" or "summary")
            objective: The objective of the feedback
            instructions: The instructions for the feedback
            constraints: The constraints for the feedback
            context: The context for the feedback
            output_format: The output format for the feedback

        Returns:
            Feedback: The created feedback
        """
        # Convert string to enum if needed
        if isinstance(feedback_type, str):
            feedback_type = FeedbackType(feedback_type)

        with Session(self.engine) as session:
            feedback = Feedback(
                feedback_type=feedback_type,
                objective=objective,
                instructions=instructions,
                constraints=constraints,
                context=context,
                output_format=output_format,
            )
            session.add(feedback)
            session.commit()
            session.refresh(feedback)
            logger.info("feedback_created", feedback_id=feedback.id, feedback_type=feedback_type.value)
            return feedback

    async def update_feedback(
        self,
        feedback_id: int,
        feedback_type: Optional[FeedbackType | str] = None,
        objective: Optional[str] = None,
        instructions: Optional[str] = None,
        constraints: Optional[str] = None,
        context: Optional[str] = None,
        output_format: Optional[str] = None,
    ) -> Feedback:
        """Update a feedback's attributes.

        Args:
            feedback_id: The ID of the feedback to update
            feedback_type: Optional new feedback type
            objective: Optional new objective
            instructions: Optional new instructions
            constraints: Optional new constraints
            context: Optional new context
            output_format: Optional new output format

        Returns:
            Feedback: The updated feedback

        Raises:
            HTTPException: If feedback is not found
        """
        with Session(self.engine) as session:
            feedback = session.get(Feedback, feedback_id)
            if not feedback:
                raise HTTPException(status_code=404, detail="Feedback not found")

            if feedback_type is not None:
                if isinstance(feedback_type, str):
                    feedback_type = FeedbackType(feedback_type)
                feedback.feedback_type = feedback_type
            if objective is not None:
                feedback.objective = objective
            if instructions is not None:
                feedback.instructions = instructions
            if constraints is not None:
                feedback.constraints = constraints
            if context is not None:
                feedback.context = context
            if output_format is not None:
                feedback.output_format = output_format

            session.add(feedback)
            session.commit()
            session.refresh(feedback)
            logger.info("feedback_updated", feedback_id=feedback_id)
            return feedback

    async def delete_feedback(self, feedback_id: int) -> bool:
        """Delete a feedback by ID.

        Args:
            feedback_id: The ID of the feedback to delete

        Returns:
            bool: True if deletion was successful, False if feedback not found
        """
        with Session(self.engine) as session:
            feedback = session.get(Feedback, feedback_id)
            if not feedback:
                return False

            session.delete(feedback)
            session.commit()
            logger.info("feedback_deleted", feedback_id=feedback_id)
            return True


# Create a singleton instance
database_service = DatabaseService()
