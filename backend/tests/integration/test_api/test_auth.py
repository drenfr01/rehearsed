"""Integration tests for authentication API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestRegistration:
    """Test user registration endpoint."""

    async def test_register_success(self, async_client: AsyncClient):
        """Test successful user registration."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePassword123!",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["email"] == "newuser@example.com"

    async def test_register_duplicate_email(self, async_client: AsyncClient, test_user):
        """Test registration with duplicate email."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "SecurePassword123!",
            },
        )
        assert response.status_code == 400

    async def test_register_weak_password(self, async_client: AsyncClient):
        """Test registration with weak password."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "weakpass@example.com",
                "password": "123",
            },
        )
        assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
class TestLogin:
    """Test user login endpoint."""

    async def test_login_success(self, async_client: AsyncClient, test_user):
        """Test successful login."""
        response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    async def test_login_invalid_credentials(self, async_client: AsyncClient, test_user):
        """Test login with invalid password."""
        response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        """Test login with non-existent user."""
        response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "SomePassword123!",
            },
        )
        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
class TestGetCurrentUser:
    """Test get current user endpoint."""

    async def test_get_current_user_success(self, async_client: AsyncClient, authenticated_headers):
        """Test getting current user with valid token."""
        response = await async_client.get("/api/v1/auth/me", headers=authenticated_headers)
        assert response.status_code == 200
        data = response.json()
        assert "email" in data

    async def test_get_current_user_no_token(self, async_client: AsyncClient):
        """Test getting current user without token."""
        response = await async_client.get("/api/v1/auth/me")
        assert response.status_code == 403

    async def test_get_current_user_invalid_token(self, async_client: AsyncClient):
        """Test getting current user with invalid token."""
        headers = {"Authorization": "Bearer invalid-token"}
        response = await async_client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code in [401, 422]
