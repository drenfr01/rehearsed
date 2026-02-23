"""Unit tests for TTS audio cache service."""

import base64
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.tts_audio_cache import (
    TTSAudioCache,
    TTSAudioEntry,
    generate_tts_and_store,
)


@pytest.mark.unit
class TestTTSAudioEntry:
    """Test TTSAudioEntry dataclass."""

    def test_to_api_payload_ready(self):
        audio_bytes = b"fake audio content"
        entry = TTSAudioEntry(
            audio_id="audio-1",
            session_id="sess-1",
            status="ready",
            created_at=time.time(),
            audio_bytes=audio_bytes,
        )
        payload = entry.to_api_payload()
        assert payload["status"] == "ready"
        assert payload["audio_base64"] == base64.b64encode(audio_bytes).decode("utf-8")

    def test_to_api_payload_ready_no_bytes(self):
        entry = TTSAudioEntry(
            audio_id="audio-1",
            session_id="sess-1",
            status="ready",
            created_at=time.time(),
            audio_bytes=None,
        )
        payload = entry.to_api_payload()
        assert payload["status"] == "pending"

    def test_to_api_payload_failed(self):
        entry = TTSAudioEntry(
            audio_id="audio-2",
            session_id="sess-1",
            status="failed",
            created_at=time.time(),
            error="Synthesis error",
        )
        payload = entry.to_api_payload()
        assert payload["status"] == "failed"

    def test_to_api_payload_pending(self):
        entry = TTSAudioEntry(
            audio_id="audio-3",
            session_id="sess-1",
            status="pending",
            created_at=time.time(),
        )
        payload = entry.to_api_payload()
        assert payload["status"] == "pending"


@pytest.mark.unit
class TestTTSAudioCache:
    """Test TTSAudioCache class."""

    def test_put_and_get_pending(self):
        cache = TTSAudioCache()
        entry = cache.put_pending("audio-1", "sess-1")

        assert entry.audio_id == "audio-1"
        assert entry.session_id == "sess-1"
        assert entry.status == "pending"

        retrieved = cache.get("audio-1")
        assert retrieved is not None
        assert retrieved.status == "pending"

    def test_put_and_get_ready(self):
        cache = TTSAudioCache()
        audio_bytes = b"synthesized audio"
        cache.put_ready("audio-1", "sess-1", audio_bytes)

        entry = cache.get("audio-1")
        assert entry is not None
        assert entry.status == "ready"
        assert entry.audio_bytes == audio_bytes

    def test_put_and_get_failed(self):
        cache = TTSAudioCache()
        cache.put_failed("audio-1", "sess-1", "TTS error")

        entry = cache.get("audio-1")
        assert entry is not None
        assert entry.status == "failed"
        assert entry.error == "TTS error"

    def test_get_nonexistent_returns_none(self):
        cache = TTSAudioCache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiration(self):
        cache = TTSAudioCache(ttl_seconds=1)
        cache.put_ready("audio-1", "sess-1", b"audio")
        cache._entries["audio-1"].created_at = time.time() - 2

        assert cache.get("audio-1") is None

    def test_max_entries_eviction(self):
        cache = TTSAudioCache(max_entries=3)
        for i in range(5):
            cache.put_ready(f"audio-{i}", "sess-1", f"audio {i}".encode())
            cache._entries[f"audio-{i}"].created_at = time.time() + i * 0.01

        cache.get("trigger")
        assert len(cache._entries) <= 3


@pytest.mark.unit
class TestGenerateTTSAndStore:
    """Test generate_tts_and_store function."""

    async def test_successful_generation(self):
        """Test successful TTS generation stores audio in cache."""
        mock_tts = AsyncMock()
        mock_tts.synthesize_async = AsyncMock(return_value=b"generated audio bytes")

        with patch("app.services.tts_audio_cache.tts_audio_cache") as mock_cache:
            await generate_tts_and_store(
                audio_id="audio-1",
                session_id="sess-1",
                voice_name="Aoede",
                prompt="Speak naturally",
                text="Hello world",
                tts_service=mock_tts,
            )

            mock_tts.synthesize_async.assert_called_once_with(
                prompt="Speak naturally",
                text="Hello world",
                voice_name="Aoede",
            )
            mock_cache.put_ready.assert_called_once_with(
                "audio-1", "sess-1", b"generated audio bytes"
            )

    async def test_generation_failure_stores_error(self):
        """Test that TTS failure stores error in cache."""
        mock_tts = AsyncMock()
        mock_tts.synthesize_async = AsyncMock(
            side_effect=Exception("TTS synthesis failed")
        )

        with patch("app.services.tts_audio_cache.tts_audio_cache") as mock_cache:
            await generate_tts_and_store(
                audio_id="audio-1",
                session_id="sess-1",
                voice_name="Aoede",
                prompt="Speak naturally",
                text="Hello world",
                tts_service=mock_tts,
            )

            mock_cache.put_failed.assert_called_once()
            assert "TTS synthesis failed" in mock_cache.put_failed.call_args[0][2]
