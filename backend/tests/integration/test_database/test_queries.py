"""Integration tests for database queries."""

import pytest
from sqlmodel import Session

from app.models.user import User
from app.services.database import DatabaseService


@pytest.mark.integration
@pytest.mark.asyncio
class TestDatabaseService:
    """Test database service methods."""

    async def test_create_user(self, db_session: Session):
        """Test creating a user via database service."""
        service = DatabaseService()
        service.engine = db_session.bind

        user = await service.create_user(
            email="dbservice@example.com",
            password=User.hash_password("password123"),
            is_approved=True,
        )

        assert user.email == "dbservice@example.com"
        assert user.is_approved is True

    async def test_get_user_by_email(self, db_session: Session, test_user: User):
        """Test getting a user by email."""
        service = DatabaseService()
        service.engine = db_session.bind

        user = await service.get_user_by_email(test_user.email)

        assert user is not None
        assert user.email == test_user.email
        assert user.id == test_user.id

    async def test_get_user_by_email_nonexistent(self, db_session: Session):
        """Test getting a non-existent user by email."""
        service = DatabaseService()
        service.engine = db_session.bind

        user = await service.get_user_by_email("nonexistent@example.com")

        assert user is None

    async def test_delete_user(self, db_session: Session, test_user: User):
        """Test deleting a user."""
        service = DatabaseService()
        service.engine = db_session.bind

        result = await service.delete_user(test_user.id)

        assert result is True

        # Verify user is deleted
        deleted_user = await service.get_user(test_user.id)
        assert deleted_user is None
