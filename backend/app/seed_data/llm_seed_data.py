"""Seed data for LLM models and default agent-LLM configurations."""

from sqlmodel import Session, select

from app.models.agent_llm_config import AgentLlmConfig, AgentType
from app.models.llm_model import LlmModel
from app.services.database import database_service

LLM_MODEL_NAMES = [
    "gemini-3.1-pro-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-3-flash-preview",
]

DEFAULT_AGENT_LLM_MAP = {
    AgentType.STUDENT_AGENT: "gemini-3-flash-preview",
    AgentType.STUDENT_CHOICE_AGENT: "gemini-3.1-flash-lite-preview",
    AgentType.INLINE_FEEDBACK: "gemini-3-flash-preview",
    AgentType.SUMMARY_FEEDBACK: "gemini-3.1-pro-preview",
}


def seed_llm_data():
    """Seed LLM models and default agent-LLM configurations."""
    with Session(database_service.engine) as session:
        existing = session.exec(select(LlmModel)).first()
        if existing:
            return

        # Seed models
        models = {}
        for name in LLM_MODEL_NAMES:
            model = LlmModel(name=name)
            session.add(model)
            session.flush()
            models[name] = model

        # Seed default configs
        for agent_type, model_name in DEFAULT_AGENT_LLM_MAP.items():
            config = AgentLlmConfig(
                agent_type=agent_type,
                llm_model_id=models[model_name].id,
            )
            session.add(config)

        session.commit()
