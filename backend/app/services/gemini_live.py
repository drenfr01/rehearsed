"""Gemini Live service for real-time voice conversations.

This module provides a service that manages bidirectional audio streaming
sessions with the Gemini Live API, proxying between a WebSocket client
and Gemini's multimodal live endpoint.
"""

import base64
import struct
from typing import AsyncGenerator

from google import genai
from google.genai.types import (
    LiveConnectConfig,
    PrebuiltVoiceConfig,
    SpeechConfig,
    VoiceConfig,
)

from app.core.config import settings
from app.core.logging import logger

GEMINI_LIVE_MODEL = "gemini-live-2.5-flash-native-audio"
GEMINI_LIVE_LOCATION = "us-central1"


class GeminiLiveSession:
    """Manages a single Gemini Live API session for one-on-one voice conversations."""

    def __init__(
        self,
        session_id: str,
        system_instruction: str,
        voice_name: str = "Aoede",
    ):
        self.session_id = session_id
        self.system_instruction = system_instruction
        self.voice_name = voice_name
        self._session = None
        self._context_manager = None
        self._client = None
        self._closed = False

    def _build_config(self) -> LiveConnectConfig:
        return LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=self.system_instruction,
            input_audio_transcription={},
            output_audio_transcription={},
            speech_config=SpeechConfig(
                voice_config=VoiceConfig(
                    prebuilt_voice_config=PrebuiltVoiceConfig(
                        voice_name=self.voice_name,
                    )
                )
            ),
        )

    async def connect(self):
        """Establish connection to Gemini Live API."""
        if settings.GOOGLE_CLOUD_PROJECT:
            self._client = genai.Client(
                vertexai=True,
                project=settings.GOOGLE_CLOUD_PROJECT,
                location=GEMINI_LIVE_LOCATION,
            )
        else:
            self._client = genai.Client(api_key=settings.LLM_API_KEY)

        config = self._build_config()
        self._context_manager = self._client.aio.live.connect(
            model=GEMINI_LIVE_MODEL,
            config=config,
        )
        self._session = await self._context_manager.__aenter__()

        logger.info(
            "gemini_live_session_connected",
            session_id=self.session_id,
            model=GEMINI_LIVE_MODEL,
        )

    _audio_chunk_count = 0

    async def send_audio(self, audio_data: bytes):
        """Send raw PCM audio data to Gemini."""
        if self._session and not self._closed:
            self._audio_chunk_count += 1
            if self._audio_chunk_count <= 5 or self._audio_chunk_count % 100 == 0:
                n_samples = len(audio_data) // 2
                if n_samples > 0:
                    samples = struct.unpack(f"<{n_samples}h", audio_data)
                    max_val = max(abs(s) for s in samples)
                    rms = (sum(s * s for s in samples) / n_samples) ** 0.5
                    logger.info(
                        "gemini_live_audio_level",
                        session_id=self.session_id,
                        chunk=self._audio_chunk_count,
                        bytes_len=len(audio_data),
                        samples=n_samples,
                        max_amplitude=max_val,
                        rms=round(rms, 1),
                    )

            await self._session.send(
                input={"data": audio_data, "mime_type": "audio/pcm"},
            )

    async def send_text(self, text: str):
        """Send a text message to Gemini."""
        if self._session and not self._closed:
            await self._session.send_realtime_input(text=text)

    async def receive_messages(self) -> AsyncGenerator[dict, None]:
        """Yield messages from the Gemini Live session.

        Yields dicts with structure:
          - {"type": "audio", "data": "<base64 pcm>"}
          - {"type": "transcript_user", "text": "..."}
          - {"type": "transcript_agent", "text": "..."}
          - {"type": "turn_complete"}
        """
        if not self._session:
            logger.warning("gemini_live_receive_no_session", session_id=self.session_id)
            return

        logger.info("gemini_live_receive_started", session_id=self.session_id)

        try:
            async for message in self._session.receive():
                if self._closed:
                    break

                logger.debug(
                    "gemini_live_raw_message",
                    session_id=self.session_id,
                    message_type=type(message).__name__,
                    message_keys=str(
                        [k for k in dir(message) if not k.startswith("_")]
                    ),
                )

                server_content = getattr(message, "server_content", None)
                if server_content is None:
                    logger.debug(
                        "gemini_live_skip_no_server_content",
                        session_id=self.session_id,
                    )
                    continue

                # Model turn: audio and text parts
                model_turn = getattr(server_content, "model_turn", None)
                if model_turn and hasattr(model_turn, "parts"):
                    for part in model_turn.parts:
                        inline_data = getattr(part, "inline_data", None)
                        if inline_data and inline_data.data:
                            encoded = base64.b64encode(inline_data.data).decode("utf-8")
                            yield {"type": "audio", "data": encoded}

                        text = getattr(part, "text", None)
                        if text:
                            logger.info("gemini_live_agent_transcript", session_id=self.session_id, text=text[:100])
                            yield {"type": "transcript_agent", "text": text}

                # Input transcription (what the user said)
                input_transcription = getattr(server_content, "input_transcription", None)
                if input_transcription:
                    text = getattr(input_transcription, "text", "")
                    if text:
                        logger.info("gemini_live_user_transcript", session_id=self.session_id, text=text[:100])
                        yield {"type": "transcript_user", "text": text}

                # Turn complete signal
                turn_complete = getattr(server_content, "turn_complete", False)
                if turn_complete:
                    logger.info("gemini_live_turn_complete", session_id=self.session_id)
                    yield {"type": "turn_complete"}

        except Exception as e:
            if not self._closed:
                logger.error(
                    "gemini_live_receive_error",
                    session_id=self.session_id,
                    error=str(e),
                )
                yield {"type": "error", "message": str(e)}

    async def close(self):
        """Close the Gemini Live session."""
        self._closed = True
        if self._context_manager:
            try:
                await self._context_manager.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(
                    "gemini_live_close_error",
                    session_id=self.session_id,
                    error=str(e),
                )
            self._context_manager = None
            self._session = None
        logger.info("gemini_live_session_closed", session_id=self.session_id)


def build_one_on_one_system_prompt(
    scenario_name: str,
    scenario_overview: str,
    scenario_instructions: str,
    agent_name: str,
    agent_personality: str,
    agent_objective: str,
    agent_instructions: str,
    agent_constraints: str,
    agent_context: str,
) -> str:
    """Build a system prompt for a one-on-one conversation from scenario + agent data."""
    return f"""You are {agent_name}, a student in a one-on-one conversation with a teacher.

## Scenario
**{scenario_name}**: {scenario_overview}

## Your Personality
{agent_personality}

## Your Objective
{agent_objective}

## Your Instructions
{agent_instructions}

## Constraints
{agent_constraints}

## Context
{agent_context}

## Scenario Instructions
{scenario_instructions}

## Conversation Guidelines
- You are having a natural, spoken conversation with a teacher
- Respond as your character would, staying in persona at all times
- Keep responses conversational and appropriately sized for spoken dialogue
- React naturally to what the teacher says, ask follow-up questions when appropriate
- If the teacher makes a mistake or says something your character would disagree with, respond authentically"""
