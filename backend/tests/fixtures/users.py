"""User fixture factories for testing."""

from typing import Optional

from sqlmodel import Session

from app.models.user import User


def create_test_user(
    session: Session,
    email: str = "test@example.com",
    password: str = "testpassword123",
    is_approved: bool = True,
    is_admin: bool = False,
) -> User:
    """Create a test user with specified attributes.

    Args:
        session: Database session
        email: User email address
        password: Plain text password (will be hashed)
        is_approved: Whether user is approved
        is_admin: Whether user has admin privileges

    Returns:
        User: Created user instance
    """
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
        user = create_test_user(
            session=session,
            email=f"{prefix}{i}@example.com",
            password=f"password{i}",
            is_approved=is_approved,
        )
        users.append(user)
    return users
