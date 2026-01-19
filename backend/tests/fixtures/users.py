"""User fixture factories for testing."""

import uuid
from typing import Optional

from sqlmodel import Session

from app.models.user import User


def unique_email(prefix: str = "test") -> str:
    """Generate a unique email address for testing."""
    unique_id = str(uuid.uuid4()).replace("-", "")[:8]
    return f"{prefix}-{unique_id}@example.com"


def create_test_user(
    session: Session,
    email: Optional[str] = None,
    password: str = "testpassword123",
    is_approved: bool = True,
    is_admin: bool = False,
) -> User:
    """Create a test user with specified attributes.

    Args:
        session: Database session
        email: User email address (if None, generates unique email)
        password: Plain text password (will be hashed)
        is_approved: Whether user is approved
        is_admin: Whether user has admin privileges

    Returns:
        User: Created user instance
    """
    if email is None:
        email = unique_email("test")
    user = User(
        email=email,
        hashed_password=User.hash_password(password),
        is_approved=is_approved,
        is_admin=is_admin,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_test_users_batch(
    session: Session,
    count: int = 5,
    prefix: str = "test",
    is_approved: bool = True,
) -> list[User]:
    """Create a batch of test users.

    Args:
        session: Database session
        count: Number of users to create
        prefix: Email prefix for users (e.g., "test" -> "test1@example.com")
        is_approved: Whether users are approved

    Returns:
        list[User]: List of created users
    """
    users = []
    for i in range(1, count + 1):
        # Generate unique email for each user in batch
        user_email = unique_email(f"{prefix}{i}")
        user = create_test_user(
            session=session,
            email=user_email,
            password=f"password{i}",
            is_approved=is_approved,
        )
        users.append(user)
    return users
