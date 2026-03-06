"""Integration tests for LLM models and agent LLM config API endpoints."""

import pytest
from sqlmodel import Session, select

from app.models.agent_llm_config import AgentLlmConfig, AgentType
from app.models.llm_model import LlmModel


@pytest.fixture
def seed_llm_models(db_session: Session):
    """Seed LLM models for testing (idempotent)."""
    for name in ["gemini-3.1-pro-preview", "gemini-3.1-flash-lite-preview", "gemini-3-flash-preview"]:
        existing = db_session.exec(select(LlmModel).where(LlmModel.name == name)).first()
        if not existing:
            db_session.add(LlmModel(name=name))
    db_session.commit()

    return list(db_session.exec(select(LlmModel).order_by(LlmModel.name)).all())


@pytest.fixture
def seed_llm_configs(db_session: Session, seed_llm_models):
    """Seed default agent-LLM configs (idempotent)."""
    models_by_name = {m.name: m for m in seed_llm_models}
    mappings = [
        (AgentType.STUDENT_AGENT, models_by_name["gemini-3-flash-preview"].id),
        (AgentType.STUDENT_CHOICE_AGENT, models_by_name["gemini-3.1-flash-lite-preview"].id),
        (AgentType.INLINE_FEEDBACK, models_by_name["gemini-3-flash-preview"].id),
        (AgentType.SUMMARY_FEEDBACK, models_by_name["gemini-3.1-pro-preview"].id),
    ]
    for agent_type, model_id in mappings:
        existing = db_session.exec(
            select(AgentLlmConfig).where(AgentLlmConfig.agent_type == agent_type)
        ).first()
        if not existing:
            db_session.add(AgentLlmConfig(agent_type=agent_type, llm_model_id=model_id))
    db_session.commit()
    return list(db_session.exec(select(AgentLlmConfig)).all())


@pytest.mark.integration
@pytest.mark.asyncio
class TestGetLlmModels:
    """Test GET /api/v1/llm-models."""

    async def test_unauthenticated_returns_401(self, async_client):
        response = await async_client.get("/api/v1/llm-models")
        assert response.status_code == 401

    async def test_returns_models(self, async_client, admin_headers, seed_llm_models):
        response = await async_client.get("/api/v1/llm-models", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        names = [m["name"] for m in data]
        assert "gemini-3.1-pro-preview" in names
        assert "gemini-3.1-flash-lite-preview" in names
        assert "gemini-3-flash-preview" in names


@pytest.mark.integration
@pytest.mark.asyncio
class TestGetAgentLlmConfigs:
    """Test GET /api/v1/llm-config."""

    async def test_unauthenticated_returns_401(self, async_client):
        response = await async_client.get("/api/v1/llm-config")
        assert response.status_code == 401

    async def test_returns_configs(self, async_client, admin_headers, seed_llm_configs):
        response = await async_client.get("/api/v1/llm-config", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
        agent_types = {c["agent_type"] for c in data}
        assert agent_types == {"student_agent", "student_choice_agent", "inline_feedback", "summary_feedback"}


@pytest.mark.integration
@pytest.mark.asyncio
class TestUpdateAgentLlmConfig:
    """Test POST /api/v1/llm-config."""

    async def test_unauthenticated_returns_401(self, async_client):
        response = await async_client.post("/api/v1/llm-config", json={
            "agent_type": "student_agent",
            "llm_model_id": 1,
        })
        assert response.status_code == 401

    async def test_update_config(self, async_client, admin_headers, seed_llm_configs, seed_llm_models, mock_langgraph_agent):
        pro_model = next(m for m in seed_llm_models if m.name == "gemini-3.1-pro-preview")
        response = await async_client.post(
            "/api/v1/llm-config",
            headers=admin_headers,
            json={
                "agent_type": "student_agent",
                "llm_model_id": pro_model.id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["agent_type"] == "student_agent"
        assert data["llm_model_name"] == "gemini-3.1-pro-preview"

    async def test_update_nonexistent_model_returns_404(self, async_client, admin_headers, seed_llm_configs, mock_langgraph_agent):
        response = await async_client.post(
            "/api/v1/llm-config",
            headers=admin_headers,
            json={
                "agent_type": "student_agent",
                "llm_model_id": 99999,
            },
        )
        assert response.status_code == 404
