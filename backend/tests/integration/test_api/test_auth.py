"""Integration tests for authentication API endpoints."""

import uuid

import pytest
from httpx import AsyncClient


def unique_email(prefix: str = "test") -> str:
    """Generate a unique email address for testing."""
    unique_id = str(uuid.uuid4()).replace("-", "")[:8]
    return f"{prefix}-{unique_id}@example.com"


@pytest.mark.integration
@pytest.mark.asyncio
class TestRegistration:
    """Test user registration endpoint."""

    async def test_register_success(self, async_client: AsyncClient):
        """Test successful user registration."""
        email = unique_email("register")
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "SecurePassword123!",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Registration successful. Your account is pending admin approval."
        assert data["email"] == email

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
                "email": unique_email("weakpass"),
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
