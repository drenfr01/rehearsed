"""Agent-LLM configuration database repository."""

from datetime import UTC, datetime
from typing import Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.core.logging import logger
from app.models.agent_llm_config import AgentLlmConfig, AgentType
from app.models.llm_model import LlmModel


class AgentLlmConfigRepository:
    """Repository for AgentLlmConfig database operations."""

    def __init__(self, engine: Engine):
        self._engine = engine

    @property
    def engine(self) -> Engine:
        return self._engine

    async def get_all_configs(self) -> List[AgentLlmConfig]:
        """Get all agent-to-LLM configurations."""
        with Session(self.engine) as session:
            statement = select(AgentLlmConfig).order_by(AgentLlmConfig.agent_type)
            return list(session.exec(statement).all())

    async def get_config(self, agent_type: AgentType | str) -> Optional[AgentLlmConfig]:
        """Get the LLM configuration for a specific agent type."""
        if isinstance(agent_type, str):
            agent_type = AgentType(agent_type)
        with Session(self.engine) as session:
            statement = select(AgentLlmConfig).where(AgentLlmConfig.agent_type == agent_type)
            return session.exec(statement).first()

    async def get_model_name_for_agent(self, agent_type: AgentType | str) -> Optional[str]:
        """Get the LLM model name for a specific agent type.
        
        Returns None if no configuration exists.
        """
        if isinstance(agent_type, str):
            agent_type = AgentType(agent_type)
        with Session(self.engine) as session:
            statement = (
                select(LlmModel.name)
                .join(AgentLlmConfig, AgentLlmConfig.llm_model_id == LlmModel.id)
                .where(AgentLlmConfig.agent_type == agent_type)
            )
            return session.exec(statement).first()

    async def get_all_model_names(self) -> Dict[str, str]:
        """Get a mapping of agent_type -> model_name for all configured agents."""
        with Session(self.engine) as session:
            statement = (
                select(AgentLlmConfig.agent_type, LlmModel.name)
                .join(LlmModel, AgentLlmConfig.llm_model_id == LlmModel.id)
            )
            results = session.exec(statement).all()
            return {row[0].value: row[1] for row in results}

    async def update_config(self, agent_type: AgentType | str, llm_model_id: int) -> AgentLlmConfig:
        """Update (or create) the LLM mapping for an agent type.

        Returns:
            The updated or newly created AgentLlmConfig.

        Raises:
            HTTPException: If the LLM model doesn't exist.
        """
        if isinstance(agent_type, str):
            agent_type = AgentType(agent_type)

        with Session(self.engine) as session:
            # Verify the model exists
            llm_model = session.get(LlmModel, llm_model_id)
            if not llm_model:
                raise HTTPException(status_code=404, detail="LLM model not found")

            # Upsert
            statement = select(AgentLlmConfig).where(AgentLlmConfig.agent_type == agent_type)
            config = session.exec(statement).first()

            if config:
                config.llm_model_id = llm_model_id
                config.updated_at = datetime.now(UTC)
            else:
                config = AgentLlmConfig(
                    agent_type=agent_type,
                    llm_model_id=llm_model_id,
                )
                session.add(config)

            session.add(config)
            session.commit()
            session.refresh(config)

            logger.info(
                "agent_llm_config_updated",
                agent_type=agent_type.value,
                llm_model_id=llm_model_id,
                model_name=llm_model.name,
            )
            return config
