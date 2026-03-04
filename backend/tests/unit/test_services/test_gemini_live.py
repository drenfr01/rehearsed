"""Unit tests for Gemini Live service."""

import base64
import struct
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.gemini_live import (
    GEMINI_LIVE_LOCATION,
    GEMINI_LIVE_MODEL,
    GeminiLiveSession,
    build_one_on_one_system_prompt,
)


@pytest.mark.unit
class TestBuildOneOnOneSystemPrompt:
    """Test build_one_on_one_system_prompt function."""

    def test_returns_formatted_prompt(self):
        result = build_one_on_one_system_prompt(
            scenario_name="Math Class",
            scenario_overview="A math lesson about fractions",
            scenario_instructions="Guide students through problems",
            agent_name="Alex",
            agent_personality="Curious and eager",
            agent_objective="Learn fractions",
            agent_instructions="Ask questions when confused",
            agent_constraints="Stay in character",
            agent_context="8th grade student",
        )

        assert "You are Alex" in result
        assert "Math Class" in result
        assert "A math lesson about fractions" in result
        assert "Curious and eager" in result
        assert "Learn fractions" in result
        assert "Ask questions when confused" in result
        assert "Stay in character" in result
        assert "8th grade student" in result
        assert "Guide students through problems" in result

    def test_handles_empty_strings(self):
        result = build_one_on_one_system_prompt(
            scenario_name="",
            scenario_overview="",
            scenario_instructions="",
            agent_name="Student",
            agent_personality="",
            agent_objective="",
            agent_instructions="",
            agent_constraints="",
            agent_context="",
        )

        assert "You are Student" in result
        assert "Conversation Guidelines" in result

    def test_all_sections_present(self):
        result = build_one_on_one_system_prompt(
            scenario_name="Test",
            scenario_overview="Overview",
            scenario_instructions="Instructions",
            agent_name="Agent",
            agent_personality="Personality",
            agent_objective="Objective",
            agent_instructions="Agent Instructions",
            agent_constraints="Constraints",
            agent_context="Context",
        )

        expected_sections = [
            "## Scenario",
            "## Your Personality",
            "## Your Objective",
            "## Your Instructions",
            "## Constraints",
            "## Context",
            "## Scenario Instructions",
            "## Conversation Guidelines",
        ]
        for section in expected_sections:
            assert section in result


@pytest.mark.unit
class TestGeminiLiveSession:
    """Test GeminiLiveSession class."""

    def test_initialization(self):
        session = GeminiLiveSession(
            session_id="test-session",
            system_instruction="You are a student.",
            voice_name="Aoede",
        )

        assert session.session_id == "test-session"
        assert session.system_instruction == "You are a student."
        assert session.voice_name == "Aoede"
        assert session._session is None
        assert session._closed is False

    def test_initialization_default_voice(self):
        session = GeminiLiveSession(
            session_id="test-session",
            system_instruction="You are a student.",
        )
        assert session.voice_name == "Aoede"

    def test_build_config(self):
        session = GeminiLiveSession(
            session_id="test-session",
            system_instruction="You are a student.",
            voice_name="Kore",
        )
        config = session._build_config()

        assert config.response_modalities == ["AUDIO"]
        assert config.system_instruction == "You are a student."

    async def test_connect_with_google_cloud_project(self):
        """Test connect uses vertex AI when GOOGLE_CLOUD_PROJECT is set."""
        session = GeminiLiveSession(
            session_id="test-session",
            system_instruction="Test instruction",
        )

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=MagicMock())

        with (
            patch("app.services.gemini_live.settings") as mock_settings,
            patch("app.services.gemini_live.genai") as mock_genai,
        ):
            mock_settings.GOOGLE_CLOUD_PROJECT = "my-project"
            mock_client = MagicMock()
            mock_client.aio.live.connect.return_value = mock_context_manager
            mock_genai.Client.return_value = mock_client

            await session.connect()

            mock_genai.Client.assert_called_once_with(
                vertexai=True,
                project="my-project",
                location=GEMINI_LIVE_LOCATION,
            )

    async def test_connect_with_api_key(self):
        """Test connect uses API key when no GOOGLE_CLOUD_PROJECT."""
        session = GeminiLiveSession(
            session_id="test-session",
            system_instruction="Test instruction",
        )

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=MagicMock())

        with (
            patch("app.services.gemini_live.settings") as mock_settings,
            patch("app.services.gemini_live.genai") as mock_genai,
        ):
            mock_settings.GOOGLE_CLOUD_PROJECT = ""
            mock_settings.LLM_API_KEY = "test-api-key"
            mock_client = MagicMock()
            mock_client.aio.live.connect.return_value = mock_context_manager
            mock_genai.Client.return_value = mock_client

            await session.connect()

            mock_genai.Client.assert_called_once_with(api_key="test-api-key")

    async def test_send_audio_when_session_active(self):
        session = GeminiLiveSession(
            session_id="test-session",
            system_instruction="Test",
        )
        session._session = AsyncMock()
        session._closed = False

        audio_data = struct.pack("<10h", *range(10))
        await session.send_audio(audio_data)

        session._session.send_realtime_input.assert_called_once()

    async def test_send_audio_when_closed(self):
        session = GeminiLiveSession(
            session_id="test-session",
            system_instruction="Test",
        )
        session._session = AsyncMock()
        session._closed = True

        await session.send_audio(b"audio data")

        session._session.send_realtime_input.assert_not_called()

    async def test_send_audio_when_no_session(self):
        session = GeminiLiveSession(
            session_id="test-session",
            system_instruction="Test",
        )
        session._session = None

        # Should not raise
        await session.send_audio(b"audio data")

    async def test_send_text_when_session_active(self):
        session = GeminiLiveSession(
            session_id="test-session",
            system_instruction="Test",
        )
        session._session = AsyncMock()
        session._closed = False

        await session.send_text("Hello teacher!")

        session._session.send_client_content.assert_called_once()

    async def test_send_text_when_closed(self):
        session = GeminiLiveSession(
            session_id="test-session",
            system_instruction="Test",
        )
        session._session = AsyncMock()
        session._closed = True

        await session.send_text("Hello")

        session._session.send_client_content.assert_not_called()

    async def test_receive_messages_no_session(self):
        session = GeminiLiveSession(
            session_id="test-session",
            system_instruction="Test",
        )
        session._session = None

        messages = []
        async for msg in session.receive_messages():
            messages.append(msg)

        assert messages == []

    async def test_close_session(self):
        session = GeminiLiveSession(
            session_id="test-session",
            system_instruction="Test",
        )
        session._context_manager = AsyncMock()
        session._session = MagicMock()

        await session.close()

        assert session._closed is True
        assert session._context_manager is None
        assert session._session is None

    async def test_close_handles_exception(self):
        session = GeminiLiveSession(
            session_id="test-session",
            system_instruction="Test",
        )
        session._context_manager = AsyncMock()
        session._context_manager.__aexit__ = AsyncMock(
            side_effect=Exception("Close error")
        )

        await session.close()

        assert session._closed is True
        assert session._context_manager is None

    def test_log_audio_debug_first_chunk(self):
        session = GeminiLiveSession(
            session_id="test-session",
            system_instruction="Test",
        )
        session._audio_chunk_count = 0

        # 10 samples of 16-bit audio
        audio_data = struct.pack("<10h", *[100, -200, 300, -400, 500, 600, -700, 800, -900, 1000])
        session._log_audio_debug(audio_data)

    def test_log_audio_debug_empty_data(self):
        session = GeminiLiveSession(
            session_id="test-session",
            system_instruction="Test",
        )
        session._audio_chunk_count = 0
        session._log_audio_debug(b"")

    def test_constants(self):
        assert GEMINI_LIVE_MODEL == "gemini-live-2.5-flash-native-audio"
        assert GEMINI_LIVE_LOCATION == "us-central1"
