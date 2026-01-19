"""Integration tests for database queries."""

import uuid

import pytest
from sqlmodel import Session

from app.models.user import User


def unique_email(prefix: str = "test") -> str:
    """Generate a unique email address for testing."""
    unique_id = str(uuid.uuid4()).replace("-", "")[:8]
    return f"{prefix}-{unique_id}@example.com"


@pytest.mark.integration
@pytest.mark.asyncio
class TestDatabaseService:
    """Test database service methods."""

    async def test_create_user(self, db_session: Session, test_engine):
        """Test creating a user via database service."""
        # Set engine before creating service for lazy loading
        from app.services.database import database_service
        database_service.engine = test_engine

        email = unique_email("dbservice")
        user = await database_service.users.create_user(
            email=email,
            password=User.hash_password("password123"),
            is_approved=True,
        )

        assert user.email == email
        assert user.is_approved is True

    async def test_get_user_by_email(self, db_session: Session, test_user: User, test_engine):
        """Test getting a user by email."""
        # Set engine before creating service for lazy loading
        from app.services.database import database_service
        database_service.engine = test_engine

        user = await database_service.users.get_user_by_email(test_user.email)

        assert user is not None
        assert user.email == test_user.email
        assert user.id == test_user.id

    async def test_get_user_by_email_nonexistent(self, db_session: Session, test_engine):
        """Test getting a non-existent user by email."""
        # Set engine before creating service for lazy loading
        from app.services.database import database_service
        database_service.engine = test_engine

        user = await database_service.users.get_user_by_email("nonexistent@example.com")

        assert user is None

    async def test_delete_user(self, db_session: Session, test_user: User, test_engine):
        """Test deleting a user."""
        # Set engine before creating service for lazy loading
        from app.services.database import database_service
        database_service.engine = test_engine

        result = await database_service.users.delete_user(test_user.id)

        assert result is True

        # Verify user is deleted
        deleted_user = await database_service.users.get_user(test_user.id)
        assert deleted_user is None
