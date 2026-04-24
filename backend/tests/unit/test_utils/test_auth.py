"""Unit tests for authentication utilities."""

import pytest
from datetime import timedelta
from jose import jwt

from app.core.config import settings
from app.utils.auth import create_access_token, verify_token, verify_token_any_type


@pytest.mark.unit
class TestCreateAccessToken:

    def test_default_expiry(self):
        token = create_access_token("test-123", token_type="session")
        assert token.access_token is not None
        assert token.expires_at is not None

    def test_custom_expiry(self):
        token = create_access_token(
            "test-123", token_type="user", expires_delta=timedelta(hours=1)
        )
        assert token.access_token is not None

    def test_payload_contains_subject_and_type(self):
        token = create_access_token("user-456", token_type="user")
        payload = jwt.decode(
            token.access_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert payload["sub"] == "user-456"
        assert payload["type"] == "user"
        assert "jti" in payload

    def test_extra_claims_embedded(self):
        token = create_access_token(
            "sess-1",
            token_type="session",
            extra_claims={"is_admin": True},
        )
        payload = jwt.decode(
            token.access_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert payload["is_admin"] is True

    def test_disallowed_extra_claims_rejected(self):
        with pytest.raises(ValueError, match="extra_claims keys must be in"):
            create_access_token(
                "sess-1",
                token_type="session",
                extra_claims={"sub": "evil"},
            )

    def test_invalid_token_type_rejected(self):
        with pytest.raises(ValueError, match="token_type must be one of"):
            create_access_token("test-123", token_type="admin")


@pytest.mark.unit
class TestVerifyToken:

    def test_valid_token_correct_type(self):
        token = create_access_token("sess-789", token_type="session")
        assert verify_token(token.access_token, expected_type="session") == "sess-789"

    def test_valid_token_wrong_type(self):
        token = create_access_token("sess-789", token_type="session")
        assert verify_token(token.access_token, expected_type="user") is None

    def test_expired_token(self):
        token = create_access_token(
            "sess-old",
            token_type="session",
            expires_delta=timedelta(seconds=-1),
        )
        assert verify_token(token.access_token, expected_type="session") is None

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="Token format is invalid"):
            verify_token("not-a-jwt", expected_type="session")

    def test_empty_string(self):
        with pytest.raises(ValueError, match="Token must be a non-empty string"):
            verify_token("", expected_type="session")

    def test_none(self):
        with pytest.raises(ValueError):
            verify_token(None, expected_type="session")


@pytest.mark.unit
class TestVerifyTokenAnyType:

    def test_returns_subject_and_type_for_user(self):
        token = create_access_token("42", token_type="user")
        result = verify_token_any_type(token.access_token)
        assert result == ("42", "user")

    def test_returns_subject_and_type_for_session(self):
        token = create_access_token("abc-def", token_type="session")
        result = verify_token_any_type(token.access_token)
        assert result == ("abc-def", "session")

    def test_expired_token_returns_none(self):
        token = create_access_token(
            "old",
            token_type="session",
            expires_delta=timedelta(seconds=-1),
        )
        assert verify_token_any_type(token.access_token) is None

    def test_unknown_type_returns_none(self):
        """Tokens with fabricated type claims are rejected at the utility layer."""
        from jose import jwt as jose_jwt

        payload = {"sub": "42", "type": "admin", "exp": 9999999999}
        forged = jose_jwt.encode(
            payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        assert verify_token_any_type(forged) is None

    def test_missing_type_returns_none(self):
        """Tokens without a type claim are rejected."""
        from jose import jwt as jose_jwt

        payload = {"sub": "42", "exp": 9999999999}
        forged = jose_jwt.encode(
            payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        assert verify_token_any_type(forged) is None

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            verify_token_any_type("bad-token")
