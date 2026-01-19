"""Integration tests for TTS lazy audio endpoint."""

import base64
import uuid

import pytest
from httpx import AsyncClient

from app.services.tts_audio_cache import tts_audio_cache


@pytest.mark.integration
@pytest.mark.asyncio
class TestTTS:
    async def test_tts_pending_then_ready(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_chat_session,
    ):
        audio_id = uuid.uuid4().hex
        tts_audio_cache.put_pending(audio_id, test_chat_session.id)

        pending = await async_client.get(
            f"/api/v1/tts/{audio_id}",
            headers=authenticated_headers,
        )
        assert pending.status_code == 202
        assert pending.json()["status"] == "pending"

        raw = b"fake mp3 bytes"
        tts_audio_cache.put_ready(audio_id, test_chat_session.id, raw)

        ready = await async_client.get(
            f"/api/v1/tts/{audio_id}",
            headers=authenticated_headers,
        )
        assert ready.status_code == 200
        body = ready.json()
        assert body["status"] == "ready"
        assert body["audio_base64"] == base64.b64encode(raw).decode("utf-8")

    async def test_tts_not_found_for_other_session(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
    ):
        audio_id = uuid.uuid4().hex
        tts_audio_cache.put_pending(audio_id, session_id="some-other-session-id")

        res = await async_client.get(
            f"/api/v1/tts/{audio_id}",
            headers=authenticated_headers,
        )
        assert res.status_code == 404

