"""Base database service with connection pool management and model registry."""

import os
from typing import Optional

from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool
from sqlmodel import SQLModel, create_engine

from app.core.config import Environment, settings
from app.core.logging import logger
from app.services.database.agent import AgentRepository
from app.services.database.feedback import FeedbackRepository
from app.services.database.scenario import ScenarioRepository
from app.services.database.session import SessionRepository
from app.services.database.user import UserRepository


class DatabaseService:
    """Database service with connection pool management and model registry.
    
    This class manages:
    - Lazy loading of the database engine for easier testing
    - Connection pool configuration
    - Repository instances for each model
    """
    
    def __init__(self):
        """Initialize database service with repositories."""
        self._engine: Optional[Engine] = None
        
        # Attach repositories as instance variables
        self._users = None
        self._sessions = None
        self._scenarios = None
        self._agents = None
        self._feedback = None
        
        logger.info("database_service_initialized", repositories=["users", "sessions", "scenarios", "agents", "feedback"])
    
    def _get_connection_url(self) -> str:
        """Get the database connection URL based on environment.
        
        Returns:
            Connection URL string
        """
        # Check for test database URL first (for testing with SQLite)
        test_db_url = os.getenv("TEST_DATABASE_URL")
        if test_db_url:
            return test_db_url
        
        if settings.ENVIRONMENT == Environment.PRODUCTION:
            return (
                f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
                f"@/rehearsed?host=/cloudsql/{settings.POSTGRES_HOST}"
            )
        else:
            return (
                f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
                f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
            )
    
    def _initialize_engine(self) -> None:
        """Initialize the database engine if it hasn't been initialized yet."""
        if self._engine is not None:
            return
        
        try:
            connection_url = self._get_connection_url()
            
            # Use different pool settings for SQLite vs PostgreSQL
            test_db_url = os.getenv("TEST_DATABASE_URL", "")
            is_sqlite = "sqlite" in connection_url or (test_db_url and test_db_url.startswith("sqlite"))
            
            if is_sqlite:
                # SQLite doesn't support connection pooling the same way
                self._engine = create_engine(
                    connection_url,
                    connect_args={"check_same_thread": False},
                    echo=False,
                )
            else:
                pool_size = settings.POSTGRES_POOL_SIZE
                max_overflow = settings.POSTGRES_MAX_OVERFLOW
                
                self._engine = create_engine(
                    connection_url,
                    pool_pre_ping=True,
                    poolclass=QueuePool,
                    pool_size=pool_size,
                    max_overflow=max_overflow,
                    pool_timeout=30,  # Connection timeout (seconds)
                    pool_recycle=1800,  # Recycle connections after 30 minutes
                )
            
            # Create tables for all registered models
            SQLModel.metadata.create_all(self._engine)
            
            self._users = UserRepository(self._engine)
            self._sessions = SessionRepository(self._engine)
            self._scenarios = ScenarioRepository(self._engine)
            self._agents = AgentRepository(self._engine)
            self._feedback = FeedbackRepository(self._engine)
            
            logger.info(
                "database_engine_initialized",
                environment=settings.ENVIRONMENT.value,
                pool_size=pool_size,
                max_overflow=max_overflow,
            )
        except SQLAlchemyError as e:
            logger.error("database_initialization_error", error=str(e), environment=settings.ENVIRONMENT.value)
            raise SQLAlchemyError(f"Database initialization error: {str(e)}")

    @property
    def engine(self) -> Engine:
        """Get or create the database engine (lazy loading).
        
        Returns:
            SQLModel Engine instance
        """
        self._initialize_engine()
        return self._engine
    
    @engine.setter
    def engine(self, engine: Optional[Engine]) -> None:
        """Set the database engine and update all repositories (useful for testing).
        
        Args:
            engine: The engine to use, or None to reset to lazy loading
        """
        self._engine = engine
        
        # Update all repositories with the new engine
        if engine:
            self._users = UserRepository(engine)
            self._sessions = SessionRepository(engine)
            self._scenarios = ScenarioRepository(engine)
            self._agents = AgentRepository(engine)
            self._feedback = FeedbackRepository(engine)
    
    def reset_engine(self) -> None:
        """Reset the engine to None, forcing recreation on next access."""
        if self._engine is not None:
            self._engine.dispose()
        self._engine = None
    
    @property
    def users(self):
        """Get the users repository."""
        return self._users
    
    @property
    def sessions(self):
        """Get the sessions repository."""
        return self._sessions
    
    @property
    def scenarios(self):
        """Get the scenarios repository."""
        return self._scenarios
    
    @property
    def agents(self):
        """Get the agents repository."""
        return self._agents
    
    @property
    def feedback(self):
        """Get the feedback repository."""
        return self._feedback
    
    def get_session_maker(self):
        """Get a session maker for creating database sessions.

        Returns:
            Session: A SQLModel session maker
        """
        from sqlmodel import Session
        return Session(self.engine)
    
    async def health_check(self) -> bool:
        """Check database connection health.

        Returns:
            bool: True if database is healthy, False otherwise
        """
        try:
            from sqlmodel import Session, select
            with Session(self.engine) as session:
                # Execute a simple query to check connection
                session.exec(select(1)).first()
                return True
        except Exception as e:
            logger.error("database_health_check_failed", error=str(e))
            return False
