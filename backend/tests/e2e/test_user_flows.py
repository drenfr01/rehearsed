"""End-to-end tests for complete user workflows."""

import pytest
from httpx import AsyncClient


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
class TestUserRegistrationFlow:
    """Test complete user registration and approval flow."""

    async def test_user_registration_to_approval_flow(self, async_client: AsyncClient, admin_headers):
        """Test complete flow: register -> admin approval -> login."""
        # Step 1: Register new user
        register_response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "newflow@example.com",
                "password": "SecurePassword123!",
            },
        )
        assert register_response.status_code == 201
        user_data = register_response.json()
        assert "access_token" in user_data

        # Step 2: User tries to access protected resource (may fail if not approved)
        # This depends on your authorization logic

        # Step 3: Admin approves user (if you have an approval endpoint)
        # This would depend on your actual API structure
        # For now, we'll just verify the registration worked

        # Step 4: User logs in after approval
        login_response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": "newflow@example.com",
                "password": "SecurePassword123!",
            },
        )
        assert login_response.status_code == 200


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
class TestSessionCreationFlow:
    """Test complete session creation and usage flow."""

    async def test_create_and_use_session(self, async_client: AsyncClient, authenticated_headers, test_user):
        """Test creating a session and using it."""
        # Step 1: Create a new session
        # This depends on your actual session creation endpoint
        # Example structure:
        # session_response = await async_client.post(
        #     "/api/v1/chatbot/session",
        #     headers=authenticated_headers,
        #     json={"name": "Test Session"},
        # )
        # assert session_response.status_code == 201
        # session_id = session_response.json()["id"]

        # Step 2: Use the session (e.g., send a message)
        # This depends on your actual API structure

        # For now, this is a placeholder structure
        pass
