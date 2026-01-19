"""User database repository."""

from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.core.logging import logger
from app.models.user import User


class UserRepository:
    """Repository for User model database operations."""
    
    def __init__(self, engine: Engine):
        """Initialize user repository with database engine.
        
        Args:
            engine: The SQLModel Engine instance
        """
        self._engine = engine
    
    @property
    def engine(self) -> Engine:
        """Get the database engine."""
        return self._engine
    
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
            statement = select(User).where(~User.is_approved).order_by(User.created_at)
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
