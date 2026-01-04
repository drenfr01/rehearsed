"""Unit tests for User model."""

import pytest

from app.models.user import User


@pytest.mark.unit
class TestUserModel:
    """Test User model methods."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "testpassword123"
        hashed = User.hash_password(password)

        assert hashed != password
        assert len(hashed) > 0
        assert isinstance(hashed, str)

    def test_hash_password_different_hashes(self):
        """Test that same password produces different hashes (due to salt)."""
        password = "testpassword123"
        hash1 = User.hash_password(password)
        hash2 = User.hash_password(password)

        # Hashes should be different due to random salt
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "testpassword123"
        hashed = User.hash_password(password)

        user = User(email="test@example.com", hashed_password=hashed)
        assert user.verify_password(password) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "testpassword123"
        hashed = User.hash_password(password)

        user = User(email="test@example.com", hashed_password=hashed)
        assert user.verify_password("wrongpassword") is False
