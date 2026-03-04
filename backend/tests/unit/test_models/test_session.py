"""Unit tests for Session model."""

import pytest

from app.models.session import Session


@pytest.mark.unit
class TestSessionModel:
    """Test Session model."""

    def test_create_session(self):
        session = Session(
            id="test-session-id",
            user_id=1,
            name="My Session",
        )
        assert session.id == "test-session-id"
        assert session.user_id == 1
        assert session.name == "My Session"

    def test_default_name(self):
        session = Session(
            id="test-session-id",
            user_id=1,
        )
        assert session.name == ""

    def test_session_has_created_at(self):
        session = Session(
            id="test-session-id",
            user_id=1,
            name="Test",
        )
        assert session.created_at is not None
