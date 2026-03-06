"""Integration tests for LLM models and agent LLM config API endpoints."""

import pytest
from sqlmodel import Session, select

from app.models.agent_llm_config import AgentLlmConfig, AgentType
from app.models.llm_model import LlmModel


@pytest.fixture
def seed_llm_models(db_session: Session):
    """Seed LLM models for testing."""
    for name in ["gemini-3.1-pro-preview", "gemini-3.1-flash-lite-preview", "gemini-3-flash-preview"]:
        m = LlmModel(name=name)
        db_session.add(m)
    db_session.commit()

    # Re-query to get IDs
    return list(db_session.exec(select(LlmModel).order_by(LlmModel.name)).all())


@pytest.fixture
def seed_llm_configs(db_session: Session, seed_llm_models):
    """Seed default agent-LLM configs."""
    models_by_name = {m.name: m for m in seed_llm_models}
    configs = [
        AgentLlmConfig(agent_type=AgentType.STUDENT_AGENT, llm_model_id=models_by_name["gemini-3-flash-preview"].id),
        AgentLlmConfig(agent_type=AgentType.STUDENT_CHOICE_AGENT, llm_model_id=models_by_name["gemini-3.1-flash-lite-preview"].id),
        AgentLlmConfig(agent_type=AgentType.INLINE_FEEDBACK, llm_model_id=models_by_name["gemini-3-flash-preview"].id),
        AgentLlmConfig(agent_type=AgentType.SUMMARY_FEEDBACK, llm_model_id=models_by_name["gemini-3.1-pro-preview"].id),
    ]
    for c in configs:
        db_session.add(c)
    db_session.commit()
    return configs


@pytest.mark.integration
@pytest.mark.asyncio
class TestGetLlmModels:
    """Test GET /api/v1/llm-models."""

    async def test_unauthenticated_returns_403(self, async_client):
        response = await async_client.get("/api/v1/llm-models")
        assert response.status_code == 403

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

    async def test_unauthenticated_returns_403(self, async_client):
        response = await async_client.get("/api/v1/llm-config")
        assert response.status_code == 403

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

    async def test_unauthenticated_returns_403(self, async_client):
        response = await async_client.post("/api/v1/llm-config", json={
            "agent_type": "student_agent",
            "llm_model_id": 1,
        })
        assert response.status_code == 403

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
