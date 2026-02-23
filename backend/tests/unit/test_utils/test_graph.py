"""Unit tests for graph utilities."""

from unittest.mock import MagicMock

import pytest

from app.schemas.chat import Message
from app.utils.graph import dump_messages


@pytest.mark.unit
class TestDumpMessages:
    """Test dump_messages function."""

    def test_empty_list(self):
        result = dump_messages([])
        assert result == []

    def test_single_message(self):
        messages = [Message(role="user", content="Hello")]
        result = dump_messages(messages)

        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hello"

    def test_multiple_messages(self):
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
            Message(role="user", content="How are you?"),
        ]
        result = dump_messages(messages)

        assert len(result) == 3
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"
        assert result[2]["role"] == "user"

    def test_preserves_content(self):
        messages = [
            Message(role="user", content="Test with special chars: <>&\"'"),
        ]
        result = dump_messages(messages)
        assert result[0]["content"] == "Test with special chars: <>&\"'"

    def test_returns_dicts(self):
        messages = [Message(role="user", content="Test")]
        result = dump_messages(messages)

        assert all(isinstance(item, dict) for item in result)
