"""Unit tests for auth schemas."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    DeleteUserResponse,
    RegistrationResponse,
    SessionResponse,
    Token,
    TokenResponse,
    UserCreate,
    UserResponse,
)


@pytest.mark.unit
class TestToken:
    """Test Token schema."""

    def test_valid_token(self):
        token = Token(
            access_token="eyJhbGciOi.payload.signature",
            expires_at=datetime.now(UTC),
        )
        assert token.access_token == "eyJhbGciOi.payload.signature"
        assert token.token_type == "bearer"

    def test_default_token_type(self):
        token = Token(
            access_token="token",
            expires_at=datetime.now(UTC),
        )
        assert token.token_type == "bearer"


@pytest.mark.unit
class TestTokenResponse:
    """Test TokenResponse schema."""

    def test_valid_response(self):
        resp = TokenResponse(
            access_token="token",
            expires_at=datetime.now(UTC),
            is_admin=False,
        )
        assert resp.is_admin is False
        assert resp.token_type == "bearer"

    def test_admin_response(self):
        resp = TokenResponse(
            access_token="admin-token",
            expires_at=datetime.now(UTC),
            is_admin=True,
        )
        assert resp.is_admin is True


@pytest.mark.unit
class TestUserCreate:
    """Test UserCreate schema."""

    def test_valid_user_create(self):
        user = UserCreate(
            email="test@example.com",
            password="StrongPass123!",
        )
        assert str(user.email) == "test@example.com"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            UserCreate(email="not-an-email", password="StrongPass123!")

    def test_password_too_short(self):
        with pytest.raises(ValidationError):
            UserCreate(email="test@example.com", password="Ab1!")

    def test_password_no_uppercase(self):
        with pytest.raises(ValidationError):
            UserCreate(email="test@example.com", password="lowercase123!")

    def test_password_no_lowercase(self):
        with pytest.raises(ValidationError):
            UserCreate(email="test@example.com", password="UPPERCASE123!")

    def test_password_no_number(self):
        with pytest.raises(ValidationError):
            UserCreate(email="test@example.com", password="NoNumberHere!")

    def test_password_no_special(self):
        with pytest.raises(ValidationError):
            UserCreate(email="test@example.com", password="NoSpecial123")


@pytest.mark.unit
class TestUserResponse:
    """Test UserResponse schema."""

    def test_valid_response(self):
        resp = UserResponse(
            id=1,
            email="test@example.com",
            is_admin=False,
            is_approved=True,
            created_at=datetime.now(UTC),
        )
        assert resp.id == 1
        assert resp.token is None

    def test_with_token(self):
        token = Token(
            access_token="token",
            expires_at=datetime.now(UTC),
        )
        resp = UserResponse(
            id=1,
            email="test@example.com",
            token=token,
            is_admin=False,
            is_approved=True,
            created_at=datetime.now(UTC),
        )
        assert resp.token is not None


@pytest.mark.unit
class TestRegistrationResponse:
    """Test RegistrationResponse schema."""

    def test_valid(self):
        resp = RegistrationResponse(
            message="Registration successful",
            email="test@example.com",
        )
        assert resp.message == "Registration successful"
        assert resp.email == "test@example.com"


@pytest.mark.unit
class TestSessionResponse:
    """Test SessionResponse schema."""

    def test_valid(self):
        token = Token(
            access_token="token",
            expires_at=datetime.now(UTC),
        )
        resp = SessionResponse(
            session_id="sess-123",
            name="My Session",
            token=token,
        )
        assert resp.session_id == "sess-123"
        assert resp.name == "My Session"

    def test_name_sanitization(self):
        token = Token(
            access_token="token",
            expires_at=datetime.now(UTC),
        )
        resp = SessionResponse(
            session_id="sess-123",
            name="<script>alert('xss')</script>",
            token=token,
        )
        assert "<script>" not in resp.name
        assert ">" not in resp.name

    def test_default_name(self):
        token = Token(
            access_token="token",
            expires_at=datetime.now(UTC),
        )
        resp = SessionResponse(
            session_id="sess-123",
            token=token,
        )
        assert resp.name == ""


@pytest.mark.unit
class TestDeleteUserResponse:
    """Test DeleteUserResponse schema."""

    def test_valid(self):
        resp = DeleteUserResponse(message="User deleted successfully")
        assert resp.message == "User deleted successfully"
