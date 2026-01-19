"""End-to-end tests for complete user workflows."""

import uuid

import pytest
from httpx import AsyncClient


def unique_email(prefix: str = "test") -> str:
    """Generate a unique email address for testing."""
    unique_id = str(uuid.uuid4()).replace("-", "")[:8]
    return f"{prefix}-{unique_id}@example.com"


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
class TestUserRegistrationFlow:
    """Test complete user registration and approval flow."""

    async def test_user_registration_to_approval_flow(self, async_client: AsyncClient, admin_headers):
        """Test complete flow: register -> admin approval -> login."""
        email = unique_email("newflow")
        # Step 1: Register new user
        register_response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "SecurePassword123!",
            },
        )
        assert register_response.status_code == 201
        user_data = register_response.json()
        assert user_data["message"] == "Registration successful. Your account is pending admin approval."
        assert user_data["email"] == email

        # Step 2: Admin gets pending users to find the newly registered user
        pending_users_response = await async_client.get(
            "/api/v1/admin/users/pending",
            headers=admin_headers,
        )
        assert pending_users_response.status_code == 200
        pending_users = pending_users_response.json()
        
        # Find the user we just registered
        new_user = next((u for u in pending_users if u["email"] == email), None)
        assert new_user is not None, f"Newly registered user {email} not found in pending users"
        user_id = new_user["id"]

        # Step 3: Admin approves user
        approve_response = await async_client.post(
            f"/api/v1/admin/users/{user_id}/approve",
            headers=admin_headers,
        )
        assert approve_response.status_code == 200
        approved_user = approve_response.json()
        assert approved_user["is_approved"] is True
        assert approved_user["email"] == email

        # Step 4: User logs in after approval
        login_response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": email,
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
