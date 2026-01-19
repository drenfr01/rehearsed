"""Integration tests for chatbot API endpoints."""

import base64
import json
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.schemas.chat import ChatResponse, Message


@pytest.mark.integration
@pytest.mark.asyncio
class TestChat:
    """Test chat endpoint."""

    async def test_chat_success(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_scenario,
        mock_langgraph_agent,
        mock_text_to_speech_service,
    ):
        """Test successful chat request."""
        # Set the current scenario
        from app.services.database import database_service
        database_service.scenarios.set_scenario(test_scenario.id)

        response = await async_client.post(
            "/api/v1/chatbot/chat",
            headers=authenticated_headers,
            json={
                "messages": [
                    {"role": "user", "content": "Hello, this is a test message"}
                ],
                "is_resumption": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert len(data["messages"]) > 0
        assert data["messages"][0]["role"] == "assistant"

    async def test_chat_with_audio(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_scenario,
        mock_langgraph_agent,
        mock_speech_to_text_service,
        mock_text_to_speech_service,
    ):
        """Test chat request with audio transcription."""
        # Set the current scenario
        from app.services.database import database_service
        database_service.scenarios.set_scenario(test_scenario.id)

        # Create fake audio bytes and encode to base64
        fake_audio = b"fake audio content"
        audio_base64 = base64.b64encode(fake_audio).decode("utf-8")

        # Mock the transcribe_audio to return transcribed text
        mock_speech_to_text_service.transcribe_audio = AsyncMock(
            return_value="transcribed text from audio"
        )

        response = await async_client.post(
            "/api/v1/chatbot/chat",
            headers=authenticated_headers,
            json={
                "messages": [],
                "is_resumption": False,
                "audio_base64": audio_base64,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert data.get("transcribed_text") == "transcribed text from audio"

    async def test_chat_resumption(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_scenario,
        mock_langgraph_agent,
        mock_text_to_speech_service,
    ):
        """Test chat resumption request."""
        # Set the current scenario
        from app.services.database import database_service
        database_service.scenarios.set_scenario(test_scenario.id)

        response = await async_client.post(
            "/api/v1/chatbot/chat",
            headers=authenticated_headers,
            json={
                "messages": [],
                "is_resumption": True,
                "resumption_text": "I want to resume the conversation",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        # Verify that get_resumption_response was called
        mock_langgraph_agent.get_resumption_response.assert_called_once()

    async def test_chat_invalid_audio_encoding(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_scenario,
        mock_langgraph_agent,
        mock_text_to_speech_service,
    ):
        """Test chat request with invalid audio encoding."""
        # Set the current scenario
        from app.services.database import database_service
        database_service.scenarios.set_scenario(test_scenario.id)

        response = await async_client.post(
            "/api/v1/chatbot/chat",
            headers=authenticated_headers,
            json={
                "messages": [{"role": "user", "content": "Test"}],
                "is_resumption": False,
                "audio_base64": "invalid base64!!!",
            },
        )
        assert response.status_code == 400
        assert "Invalid audio data encoding" in response.json()["detail"]

    async def test_chat_empty_transcription(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_scenario,
        mock_langgraph_agent,
        mock_speech_to_text_service,
        mock_text_to_speech_service,
    ):
        """Test chat request with audio that returns empty transcription."""
        # Set the current scenario
        from app.services.database import database_service
        database_service.scenarios.set_scenario(test_scenario.id)

        # Create fake audio bytes and encode to base64
        fake_audio = b"fake audio content"
        audio_base64 = base64.b64encode(fake_audio).decode("utf-8")

        # Mock the transcribe_audio to return None (empty transcription)
        mock_speech_to_text_service.transcribe_audio = AsyncMock(
            return_value=None
        )

        response = await async_client.post(
            "/api/v1/chatbot/chat",
            headers=authenticated_headers,
            json={
                "messages": [],
                "is_resumption": False,
                "audio_base64": audio_base64,
            },
        )
        assert response.status_code == 400
        assert "Could not transcribe audio" in response.json()["detail"]

    async def test_chat_unauthorized(
        self,
        async_client: AsyncClient,
        test_scenario,
        mock_langgraph_agent,
        mock_text_to_speech_service,
    ):
        """Test chat request without authentication."""
        # Set the current scenario
        from app.services.database import database_service
        database_service.scenarios.set_scenario(test_scenario.id)

        response = await async_client.post(
            "/api/v1/chatbot/chat",
            json={
                "messages": [{"role": "user", "content": "Test"}],
                "is_resumption": False,
            },
        )
        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
class TestChatStream:
    """Test streaming chat endpoint."""

    async def test_chat_stream_success(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_scenario,
        mock_langgraph_agent,
        mock_text_to_speech_service,
    ):
        """Test successful streaming chat request."""
        # Set the current scenario
        from app.services.database import database_service
        database_service.scenarios.set_scenario(test_scenario.id)

        response = await async_client.post(
            "/api/v1/chatbot/chat/stream",
            headers=authenticated_headers,
            json={
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Read the stream
        content = b""
        async for chunk in response.aiter_bytes():
            content += chunk

        # Verify we got some content
        assert len(content) > 0

    async def test_chat_stream_unauthorized(
        self,
        async_client: AsyncClient,
        test_scenario,
        mock_langgraph_agent,
        mock_text_to_speech_service,
    ):
        """Test streaming chat request without authentication."""
        # Set the current scenario
        from app.services.database import database_service
        database_service.scenarios.set_scenario(test_scenario.id)

        response = await async_client.post(
            "/api/v1/chatbot/chat/stream",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
class TestGetMessages:
    """Test get messages endpoint."""

    async def test_get_messages_success(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_chat_session,
        mock_langgraph_agent,
    ):
        """Test successful get messages request."""
        response = await async_client.get(
            "/api/v1/chatbot/messages",
            headers=authenticated_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        # Verify that get_chat_history was called
        mock_langgraph_agent.get_chat_history.assert_called_once()

    async def test_get_messages_unauthorized(
        self,
        async_client: AsyncClient,
        mock_langgraph_agent,
    ):
        """Test get messages request without authentication."""
        response = await async_client.get("/api/v1/chatbot/messages")
        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
class TestClearChatHistory:
    """Test clear chat history endpoint."""

    async def test_clear_chat_history_success(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_chat_session,
        mock_langgraph_agent,
    ):
        """Test successful clear chat history request."""
        response = await async_client.delete(
            "/api/v1/chatbot/messages",
            headers=authenticated_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Chat history cleared successfully"
        # Verify that clear_chat_history was called
        mock_langgraph_agent.clear_chat_history.assert_called_once()

    async def test_clear_chat_history_unauthorized(
        self,
        async_client: AsyncClient,
        mock_langgraph_agent,
    ):
        """Test clear chat history request without authentication."""
        response = await async_client.delete("/api/v1/chatbot/messages")
        assert response.status_code == 401
