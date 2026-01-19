"""Shared pytest configuration and fixtures."""

import os
import uuid
from typing import (
    AsyncGenerator,
    Generator,
)
from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch,
)

import pytest
from httpx import (
    ASGITransport,
    AsyncClient,
)
from sqlalchemy import text
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
from app.main import app
from app.models.agent import Agent, AgentPersonality, AgentVoice
from app.models.feedback import Feedback
from app.models.scenario import Scenario
from app.models.session import Session as ChatSession
from app.models.user import User
from app.services.database import DatabaseService


# Set test environment
os.environ["APP_ENV"] = "test"


def unique_email(prefix: str = "test") -> str:
    """Generate a unique email address for testing.
    
    Args:
        prefix: Email prefix (default: "test")
        
    Returns:
        str: Unique email address in format {prefix}-{uuid}@example.com
    """
    unique_id = str(uuid.uuid4()).replace("-", "")[:8]
    return f"{prefix}-{unique_id}@example.com"


@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine.

    For unit tests, this can use an in-memory SQLite database.
    For integration tests, this should use a test PostgreSQL database.
    """
    # Use in-memory SQLite for fast unit tests
    # For integration tests, you may want to use a separate test PostgreSQL database
    test_db_url = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine(test_db_url, connect_args={"check_same_thread": False} if "sqlite" in test_db_url else {})

    # Create all tables
    SQLModel.metadata.create_all(engine)
    
    # Clean up any existing data at the start of the test session
    with Session(engine) as session:
        for model in [ChatSession, Agent, AgentVoice, AgentPersonality, Feedback, Scenario, User]:
            statement = select(model)
            records = session.exec(statement).all()
            for record in records:
                session.delete(record)
        session.commit()
    
    yield engine
    
    # Clean up all data at the end of the test session
    with Session(engine) as session:
        for model in [ChatSession, Agent, AgentVoice, AgentPersonality, Feedback, Scenario, User]:
            statement = select(model)
            records = session.exec(statement).all()
            for record in records:
                session.delete(record)
        session.commit()
    
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine) -> Generator[Session, None, None]:
    """Create a database session for testing."""
    with Session(test_engine) as session:
        yield session
        session.rollback()


@pytest.fixture
async def async_client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing FastAPI endpoints."""
    # Configure database service to use test engine
    from app.services.database import database_service
    database_service.engine = test_engine
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user."""
    from app.models.user import User

    user = User(
        email=unique_email("test"),
        hashed_password=User.hash_password("testpassword123"),
        is_approved=True,
        is_admin=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_admin_user(db_session: Session) -> User:
    """Create a test admin user."""
    from app.models.user import User

    user = User(
        email=unique_email("admin"),
        hashed_password=User.hash_password("adminpassword123"),
        is_approved=True,
        is_admin=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_unauthorized_user(db_session: Session) -> User:
    """Create a test user that is not approved."""
    from app.models.user import User

    user = User(
        email=unique_email("unauthorized"),
        hashed_password=User.hash_password("testpassword123"),
        is_approved=False,
        is_admin=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(test_chat_session: ChatSession) -> str:
    """Create a JWT token for a test user using session ID."""
    from app.utils.auth import create_access_token

    token = create_access_token(str(test_chat_session.id))
    return token.access_token


@pytest.fixture
def admin_token(test_admin_user: User, db_session: Session) -> str:
    """Create a JWT token for a test admin user using session ID."""
    from app.utils.auth import create_access_token
    import uuid

    # Create a session for the admin user
    admin_session = ChatSession(id=str(uuid.uuid4()), user_id=test_admin_user.id, name="Admin Session")
    db_session.add(admin_session)
    db_session.commit()
    db_session.refresh(admin_session)

    token = create_access_token(str(admin_session.id))
    return token.access_token


@pytest.fixture
def authenticated_headers(auth_token: str) -> dict:
    """Create authenticated request headers."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def admin_headers(admin_token: str) -> dict:
    """Create authenticated request headers for admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def mock_langfuse():
    """Mock Langfuse client."""
    with patch("app.main.langfuse") as mock:
        mock.capture = MagicMock()
        mock.score = MagicMock()
        yield mock


@pytest.fixture
def mock_google_cloud_text_to_speech():
    """Mock Google Cloud Text-to-Speech client."""
    with patch("app.services.gemini_text_to_speech.TextToSpeechClient") as mock:
        mock_instance = AsyncMock()
        mock.return_value = mock_instance
        mock_instance.synthesize_speech = AsyncMock(return_value=MagicMock(audio_content=b"fake audio"))
        yield mock_instance


@pytest.fixture
def mock_google_cloud_speech():
    """Mock Google Cloud Speech client."""
    with patch("app.services.speech_to_text.SpeechClient") as mock:
        mock_instance = AsyncMock()
        mock.return_value = mock_instance
        mock_instance.recognize = AsyncMock(return_value=MagicMock(results=[]))
        yield mock_instance


@pytest.fixture
def mock_langgraph_agent():
    """Mock LangGraphAgent instance methods."""
    from app.schemas.chat import ChatResponse, Message
    
    mock_agent = AsyncMock()
    mock_agent.llm = MagicMock()
    mock_agent.llm.model_name = "test-model"
    mock_agent.llm.model = "test-model"
    
    # Mock get_response to return a ChatResponse
    mock_agent.get_response = AsyncMock(return_value=ChatResponse(
        messages=[Message(role="assistant", content="Test response")]
    ))
    
    # Mock get_resumption_response
    mock_agent.get_resumption_response = AsyncMock(return_value=ChatResponse(
        messages=[Message(role="assistant", content="Test resumption response")]
    ))
    
    # Mock get_stream_response as an async generator
    async def mock_stream():
        yield "Test "
        yield "stream "
        yield "response"
    mock_agent.get_stream_response = mock_stream
    
    # Mock get_chat_history
    mock_agent.get_chat_history = AsyncMock(return_value=[
        Message(role="user", content="Test message"),
        Message(role="assistant", content="Test response")
    ])
    
    # Mock clear_chat_history
    mock_agent.clear_chat_history = AsyncMock(return_value=None)
    
    with patch("app.api.v1.chatbot.agent", mock_agent):
        yield mock_agent


@pytest.fixture
def mock_speech_to_text_service():
    """Mock SpeechToTextService instance and transcribe_audio method."""
    mock_service = AsyncMock()
    mock_service.transcribe_audio = AsyncMock(return_value="transcribed text")
    
    with patch("app.api.v1.chatbot.speech_to_text_service", mock_service):
        yield mock_service


@pytest.fixture
def mock_text_to_speech_service():
    """Mock GeminiTextToSpeech instance and synthesize method."""
    mock_service = MagicMock()
    mock_service.synthesize = MagicMock(return_value=b"fake audio bytes")
    
    with patch("app.api.v1.deps.text_to_speech_service", mock_service):
        with patch("app.api.v1.deps.get_text_to_speech_service", return_value=mock_service):
            yield mock_service


@pytest.fixture
def test_scenario(db_session: Session) -> Scenario:
    """Create a test scenario."""
    scenario = Scenario(
        name="Test Scenario",
        description="Test scenario description",
        overview="Test overview",
        system_instructions="Test system instructions",
        initial_prompt="Test initial prompt",
        teaching_objectives="Test teaching objectives",
    )
    db_session.add(scenario)
    db_session.commit()
    db_session.refresh(scenario)
    return scenario


@pytest.fixture
def test_agent_personality(db_session: Session) -> AgentPersonality:
    """Create a test agent personality."""
    personality = AgentPersonality(
        name="Test Personality",
        personality_description="Test personality description",
    )
    db_session.add(personality)
    db_session.commit()
    db_session.refresh(personality)
    return personality


@pytest.fixture
def test_agent(db_session: Session, test_scenario: Scenario, test_agent_personality: AgentPersonality) -> Agent:
    """Create a test agent."""
    import uuid

    agent = Agent(
        id=str(uuid.uuid4()),
        name="Test Agent",
        scenario_id=test_scenario.id,
        agent_personality_id=test_agent_personality.id,
        objective="Test objective",
        instructions="Test instructions",
        constraints="Test constraints",
        context="Test context",
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


@pytest.fixture
def test_chat_session(db_session: Session, test_user: User) -> ChatSession:
    """Create a test chat session."""
    import uuid

    session = ChatSession(id=str(uuid.uuid4()), user_id=test_user.id, name="Test Session")
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session

@pytest.fixture(autouse=True)
def reset_settings():
    """Reset settings to test environment before each test."""
    original_env = os.environ.get("APP_ENV")
    os.environ["APP_ENV"] = "test"
    yield
    if original_env:
        os.environ["APP_ENV"] = original_env
    elif "APP_ENV" in os.environ:
        del os.environ["APP_ENV"]
