"""In-memory cache for generated TTS audio.

This enables lazy-loading / background generation of TTS audio without blocking chat latency.

NOTE: This cache is process-local (single-worker assumption). If you scale to multiple
workers/instances, replace this with a shared store (Redis/GCS/Postgres).
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from typing import Dict, Literal, Optional

from app.core.logging import logger
from app.services.gemini_text_to_speech import GeminiTextToSpeech

TTSStatus = Literal["pending", "ready", "failed"]


@dataclass
class TTSAudioEntry:
    """A single entry in the TTS audio cache."""
    audio_id: str
    session_id: str
    status: TTSStatus
    created_at: float
    audio_bytes: Optional[bytes] = None
    error: str = ""

    def to_api_payload(self) -> dict:
        """Convert the TTS audio entry to an API payload."""
        if self.status == "ready" and self.audio_bytes:
            return {
                "status": "ready",
                "audio_base64": base64.b64encode(self.audio_bytes).decode("utf-8"),
            }
        if self.status == "failed":
            return {"status": "failed"}
        return {"status": "pending"}


class TTSAudioCache:
    """A simple TTL in-memory cache for TTS audio entries."""

    def __init__(self, ttl_seconds: int = 15 * 60, max_entries: int = 2000):
        """Initialize the TTS audio cache."""
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._entries: Dict[str, TTSAudioEntry] = {}

    def _cleanup(self) -> None:
        """Cleanup the TTS audio cache based on both TTL and max size. If the cache is full, evict the oldest entries."""
        now = time.time()
        # TTL cleanup
        expired = [k for k, v in self._entries.items() if now - v.created_at > self._ttl_seconds]
        for k in expired:
            self._entries.pop(k, None)

        # Simple max-size enforcement: evict oldest
        if len(self._entries) <= self._max_entries:
            return
        overflow = len(self._entries) - self._max_entries
        oldest_keys = sorted(self._entries, key=lambda k: self._entries[k].created_at)[:overflow]
        for k in oldest_keys:
            self._entries.pop(k, None)

    def get(self, audio_id: str) -> Optional[TTSAudioEntry]:
        """Get an entry from the TTS audio cache after cleaning up the cache."""
        self._cleanup()
        return self._entries.get(audio_id)

    def put_pending(self, audio_id: str, session_id: str) -> TTSAudioEntry:
        """Put a pending entry into the TTS audio cache after cleaning up the cache."""
        self._cleanup()
        entry = TTSAudioEntry(
            audio_id=audio_id,
            session_id=session_id,
            status="pending",
            created_at=time.time(),
        )
        self._entries[audio_id] = entry
        return entry

    def put_ready(self, audio_id: str, session_id: str, audio_bytes: bytes) -> None:
        """Put a ready entry into the TTS audio cache after cleaning up the cache."""
        self._cleanup()
        self._entries[audio_id] = TTSAudioEntry(
            audio_id=audio_id,
            session_id=session_id,
            status="ready",
            created_at=time.time(),
            audio_bytes=audio_bytes,
        )

    def put_failed(self, audio_id: str, session_id: str, error: str) -> None:
        """Put a failed entry into the TTS audio cache after cleaning up the cache."""
        self._cleanup()
        self._entries[audio_id] = TTSAudioEntry(
            audio_id=audio_id,
            session_id=session_id,
            status="failed",
            created_at=time.time(),
            error=error,
        )


tts_audio_cache = TTSAudioCache()


async def generate_tts_and_store(
    audio_id: str,
    session_id: str,
    voice_name: str,
    prompt: str,
    text: str,
    tts_service: GeminiTextToSpeech,
) -> None:
    """Background task: generate MP3 bytes and store in cache."""
    try:
        audio_bytes = await tts_service.synthesize_async(
            prompt=prompt,
            text=text,
            voice_name=voice_name,
        )
        tts_audio_cache.put_ready(audio_id, session_id, audio_bytes)
        logger.info("tts_audio_ready", audio_id=audio_id, session_id=session_id)
    except Exception as e:
        logger.error("tts_audio_generation_failed", audio_id=audio_id, session_id=session_id, error=str(e))
        tts_audio_cache.put_failed(audio_id, session_id, str(e))
