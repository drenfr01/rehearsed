"""Avatar database repository."""

from typing import List, Optional

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.models.avatar import Avatar


class AvatarRepository:
    """Repository for Avatar database operations."""

    def __init__(self, engine: Engine):
        """Initialize Avatar repository with database engine."""
        self._engine = engine

    @property
    def engine(self) -> Engine:
        """Get the database engine from private attribute."""
        return self._engine

    async def get_all_avatars(self) -> List[Avatar]:
        """Get all available avatars ordered by name."""
        with Session(self.engine) as session:
            statement = select(Avatar).order_by(Avatar.name)
            return list(session.exec(statement).all())

    async def get_avatar(self, avatar_id: int) -> Optional[Avatar]:
        """Get a specific avatar by ID."""
        with Session(self.engine) as session:
            return session.get(Avatar, avatar_id)

    async def get_avatar_by_name(self, name: str) -> Optional[Avatar]:
        """Get a specific avatar by name."""
        with Session(self.engine) as session:
            statement = select(Avatar).where(Avatar.name == name)
            return session.exec(statement).first()
