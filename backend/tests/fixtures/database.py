"""Database fixtures for testing."""

import os
from typing import Generator

import pytest
from sqlmodel import (
    Session,
    SQLModel,
    create_engine,
)

from app.models.agent import Agent, AgentPersonality, AgentVoice
from app.models.feedback import Feedback
from app.models.scenario import Scenario
from app.models.session import Session as ChatSession
from app.models.user import User


@pytest.fixture(scope="function")
def test_db_session():
    """Create a test database session with transaction rollback.

    This fixture creates a temporary database session that automatically
    rolls back all changes after each test, ensuring test isolation.

    Yields:
        Session: SQLModel database session for testing
    """
    # Use in-memory SQLite for fast unit tests
    # For integration tests, use TEST_DATABASE_URL environment variable
    test_db_url = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")

    engine = create_engine(
        test_db_url,
        connect_args={"check_same_thread": False} if "sqlite" in test_db_url else {},
        echo=False,
    )

    # Create all tables
    SQLModel.metadata.create_all(engine)

    # Create session
    with Session(engine) as session:
        yield session
        session.rollback()

    # Drop all tables after test
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def clean_db(test_db_session: Session):
    """Ensure database is clean before each test.

    This fixture can be used to explicitly clean the database,
    though test_db_session already handles rollback.

    Args:
        test_db_session: Database session fixture
    """
    # Database is already clean due to transaction rollback
    yield test_db_session
