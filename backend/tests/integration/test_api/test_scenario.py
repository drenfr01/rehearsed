"""Integration tests for scenario API endpoints."""

import pytest
from httpx import AsyncClient

from app.models.scenario import Scenario
from app.models.session import Session as ChatSession


@pytest.mark.integration
@pytest.mark.asyncio
class TestSetCurrentScenario:
    """Test set-current-by-id endpoint."""

    async def test_set_current_scenario_unauthenticated(
        self,
        async_client: AsyncClient,
        test_scenario,
    ):
        """Setting the current scenario without auth is rejected."""
        response = await async_client.post(
            "/api/v1/scenario/set-current-by-id",
            json={"scenario_id": test_scenario.id},
        )
        assert response.status_code in (401, 403)

    async def test_set_current_scenario_persists_on_session(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        db_session,
        test_user,
        test_chat_session,
    ):
        """Setting a scenario stores it on the authenticated session row."""
        scenario = Scenario(
            name="Another Scenario",
            description="desc",
            overview="overview",
            system_instructions="instructions",
            initial_prompt="prompt",
            teaching_objectives="objectives",
        )
        db_session.add(scenario)
        db_session.commit()
        db_session.refresh(scenario)

        response = await async_client.post(
            "/api/v1/scenario/set-current-by-id",
            headers=authenticated_headers,
            json={"scenario_id": scenario.id},
        )
        assert response.status_code == 200
        assert response.json()["id"] == scenario.id

        db_session.expire_all()
        updated = db_session.get(ChatSession, test_chat_session.id)
        assert updated.scenario_id == scenario.id

    async def test_set_current_scenario_not_found(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_chat_session,
    ):
        """Setting a nonexistent scenario returns 404."""
        response = await async_client.post(
            "/api/v1/scenario/set-current-by-id",
            headers=authenticated_headers,
            json={"scenario_id": 999999},
        )
        assert response.status_code == 404

    async def test_set_current_scenario_forbidden_for_other_users_scenario(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        db_session,
        test_admin_user,
        test_chat_session,
    ):
        """A user cannot select another user's local scenario."""
        other_users_scenario = Scenario(
            name="Private Scenario",
            description="desc",
            overview="overview",
            system_instructions="instructions",
            initial_prompt="prompt",
            teaching_objectives="objectives",
            owner_id=test_admin_user.id,
        )
        db_session.add(other_users_scenario)
        db_session.commit()
        db_session.refresh(other_users_scenario)

        response = await async_client.post(
            "/api/v1/scenario/set-current-by-id",
            headers=authenticated_headers,
            json={"scenario_id": other_users_scenario.id},
        )
        assert response.status_code == 403
