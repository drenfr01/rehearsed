"""LLM model database repository."""

from typing import List, Optional

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.core.logging import logger
from app.models.llm_model import LlmModel


class LlmModelRepository:
    """Repository for LlmModel database operations."""

    def __init__(self, engine: Engine):
        self._engine = engine

    @property
    def engine(self) -> Engine:
        return self._engine

    async def get_all_models(self) -> List[LlmModel]:
        """Get all available LLM models."""
        with Session(self.engine) as session:
            statement = select(LlmModel).order_by(LlmModel.name)
            return list(session.exec(statement).all())

    async def get_model(self, model_id: int) -> Optional[LlmModel]:
        """Get a specific LLM model by ID."""
        with Session(self.engine) as session:
            return session.get(LlmModel, model_id)

    async def get_model_by_name(self, name: str) -> Optional[LlmModel]:
        """Get a specific LLM model by name."""
        with Session(self.engine) as session:
            statement = select(LlmModel).where(LlmModel.name == name)
            return session.exec(statement).first()
