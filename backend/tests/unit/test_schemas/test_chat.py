"""Unit tests for chat schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    Message,
    StreamResponse,
)


@pytest.mark.unit
class TestMessage:
    """Test Message schema."""

    def test_valid_user_message(self):
        msg = Message(role="user", content="Hello, teacher!")
        assert msg.role == "user"
        assert msg.content == "Hello, teacher!"

    def test_valid_assistant_message(self):
        msg = Message(role="assistant", content="Hello, student!")
        assert msg.role == "assistant"

    def test_valid_system_message(self):
        msg = Message(role="system", content="System prompt")
        assert msg.role == "system"

    def test_invalid_role(self):
        with pytest.raises(ValidationError):
            Message(role="invalid", content="Test")

    def test_empty_content_rejected(self):
        with pytest.raises(ValidationError):
            Message(role="user", content="")

    def test_content_too_long_rejected(self):
        with pytest.raises(ValidationError):
            Message(role="user", content="a" * 3001)

    def test_max_length_content_accepted(self):
        msg = Message(role="user", content="a" * 3000)
        assert len(msg.content) == 3000

    def test_script_tags_rejected(self):
        with pytest.raises(ValidationError, match="script tags"):
            Message(role="user", content="<script>alert('xss')</script>")

    def test_null_bytes_rejected(self):
        with pytest.raises(ValidationError, match="null bytes"):
            Message(role="user", content="Hello\0World")

    def test_extra_fields_ignored(self):
        msg = Message(role="user", content="Hello", extra_field="ignored")
        assert not hasattr(msg, "extra_field")

    def test_normal_html_allowed(self):
        msg = Message(role="user", content="<b>Bold text</b>")
        assert msg.content == "<b>Bold text</b>"

    def test_multiline_content(self):
        msg = Message(role="user", content="Line 1\nLine 2\nLine 3")
        assert "\n" in msg.content


@pytest.mark.unit
class TestChatRequest:
    """Test ChatRequest schema."""

    def test_basic_request(self):
        req = ChatRequest(
            messages=[Message(role="user", content="Hello")]
        )
        assert len(req.messages) == 1
        assert req.is_resumption is False
        assert req.resumption_text == ""
        assert req.audio_base64 is None

    def test_resumption_request(self):
        req = ChatRequest(
            messages=[],
            is_resumption=True,
            resumption_text="Resume from here",
        )
        assert req.is_resumption is True
        assert req.resumption_text == "Resume from here"

    def test_with_audio(self):
        req = ChatRequest(
            messages=[],
            audio_base64="dGVzdCBhdWRpbw==",
        )
        assert req.audio_base64 == "dGVzdCBhdWRpbw=="

    def test_multiple_messages(self):
        req = ChatRequest(
            messages=[
                Message(role="user", content="Hello"),
                Message(role="assistant", content="Hi there"),
                Message(role="user", content="How are you?"),
            ]
        )
        assert len(req.messages) == 3


@pytest.mark.unit
class TestChatResponse:
    """Test ChatResponse schema."""

    def test_default_values(self):
        resp = ChatResponse()
        assert resp.messages == []
        assert resp.interrupt_task == ""
        assert resp.interrupt_value == ""
        assert resp.interrupt_value_type == "text"
        assert resp.student_responses == []
        assert resp.inline_feedback == []
        assert resp.feedback_request_id == ""
        assert resp.summary_feedback == ""
        assert resp.summary == ""
        assert resp.answering_student == 0
        assert resp.appropriate_response is False
        assert resp.appropriate_explanation == ""
        assert resp.learning_goals_achieved is False
        assert resp.transcribed_text == ""
        assert resp.interrupt == []

    def test_with_messages(self):
        resp = ChatResponse(
            messages=[Message(role="assistant", content="Hello!")]
        )
        assert len(resp.messages) == 1
        assert resp.messages[0].content == "Hello!"

    def test_with_feedback_request_id(self):
        resp = ChatResponse(feedback_request_id="fb-123")
        assert resp.feedback_request_id == "fb-123"

    def test_with_transcribed_text(self):
        resp = ChatResponse(transcribed_text="Transcribed audio text")
        assert resp.transcribed_text == "Transcribed audio text"


@pytest.mark.unit
class TestStreamResponse:
    """Test StreamResponse schema."""

    def test_default_values(self):
        resp = StreamResponse()
        assert resp.content == ""
        assert resp.done is False

    def test_with_content(self):
        resp = StreamResponse(content="Hello ", done=False)
        assert resp.content == "Hello "
        assert resp.done is False

    def test_done_response(self):
        resp = StreamResponse(content="", done=True)
        assert resp.done is True
