"""Unit tests for authentication utilities."""

import pytest
from datetime import timedelta
from jose import jwt

from app.core.config import settings
from app.utils.auth import create_access_token, verify_token


@pytest.mark.unit
class TestCreateAccessToken:
    """Test create_access_token function."""

    def test_create_access_token_default_expiry(self):
        """Test token creation with default expiry."""
        thread_id = "test-thread-123"
        token = create_access_token(thread_id)

        assert token.access_token is not None
        assert token.expires_at is not None
        assert isinstance(token.access_token, str)

    def test_create_access_token_custom_expiry(self):
        """Test token creation with custom expiry."""
        thread_id = "test-thread-123"
        expires_delta = timedelta(hours=1)
        token = create_access_token(thread_id, expires_delta=expires_delta)

        assert token.access_token is not None
        assert token.expires_at is not None

    def test_create_access_token_contains_thread_id(self):
        """Test that token contains the thread ID."""
        thread_id = "test-thread-456"
        token = create_access_token(thread_id)

        # Decode token to verify payload
        payload = jwt.decode(token.access_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == thread_id


@pytest.mark.unit
class TestVerifyToken:
    """Test verify_token function."""

    def test_verify_token_valid(self):
        """Test verification of a valid token."""
        thread_id = "test-thread-789"
        token = create_access_token(thread_id)

        result = verify_token(token.access_token)
        assert result == thread_id

    def test_verify_token_invalid_format(self):
        """Test verification of an invalid token format."""
        invalid_token = "not-a-valid-token"

        with pytest.raises(ValueError, match="Token format is invalid"):
            verify_token(invalid_token)

    def test_verify_token_empty_string(self):
        """Test verification of an empty token."""
        with pytest.raises(ValueError, match="Token must be a non-empty string"):
            verify_token("")

    def test_verify_token_none(self):
        """Test verification of None token."""
        with pytest.raises(ValueError):
            verify_token(None)

    def test_verify_token_expired(self):
        """Test verification of an expired token."""
        thread_id = "test-thread-expired"
        # Create token with negative expiry (already expired)
        expires_delta = timedelta(seconds=-1)
        token = create_access_token(thread_id, expires_delta=expires_delta)

        result = verify_token(token.access_token)
        assert result is None
