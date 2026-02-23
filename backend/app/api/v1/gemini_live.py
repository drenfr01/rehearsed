"""Gemini Live API WebSocket endpoint for one-on-one voice conversations.

This module provides a WebSocket endpoint that proxies audio between
the frontend client and the Gemini Live API, enabling real-time
voice conversations with AI agents.
"""

import asyncio
import base64
import json
from typing import Union

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.api.v1.auth import get_current_session
from app.api.v1.deps import get_database_service
from app.core.logging import logger
from app.schemas.graph import SummaryFeedbackResponse
from app.services.gemini_live import (
    GeminiLiveSession,
    build_one_on_one_system_prompt,
)
from app.services.summary_feedback import generate_summary_feedback
from app.utils.auth import verify_token
from app.utils.sanitization import sanitize_string

router = APIRouter()


class TranscriptMessage(BaseModel):
    """Message model for Gemini Live conversation transcript."""
    role: str = Field(..., description="'user' or 'agent'")
    text: str


class SummaryFeedbackRequest(BaseModel):
    """Request model for summary feedback endpoint."""
    scenario_id: int
    transcript: list[TranscriptMessage]


class SummaryFeedbackApiResponse(BaseModel):
    """Response model for summary feedback endpoint."""
    summary_feedback: Union[SummaryFeedbackResponse, str]


@router.post("/summary-feedback", response_model=SummaryFeedbackApiResponse)
async def get_summary_feedback(
    request: SummaryFeedbackRequest,
    session=Depends(get_current_session),
):
    """Generate summary feedback for a Gemini Live conversation transcript."""
    conversation = [msg.model_dump() for msg in request.transcript]
    result = await generate_summary_feedback(request.scenario_id, conversation)

    return SummaryFeedbackApiResponse(summary_feedback=result)


async def _authenticate_websocket(websocket: WebSocket) -> tuple[str, int] | None:
    """Validate session token from WebSocket query params.

    Returns (session_id, user_id) on success, or None on failure.
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return None

    try:
        token = sanitize_string(token)
        session_id = verify_token(token)
        if session_id is None:
            await websocket.close(code=4001, reason="Invalid token")
            return None

        session_id = sanitize_string(session_id)
        db = get_database_service()
        session = await db.sessions.get_session(session_id)
        if session is None:
            await websocket.close(code=4001, reason="Session not found")
            return None

        return session.id, session.user_id
    except Exception as e:
        logger.error("ws_auth_failed", error=str(e))
        await websocket.close(code=4001, reason="Authentication failed")
        return None


@router.websocket("/ws")
async def gemini_live_ws(websocket: WebSocket):
    """WebSocket endpoint for Gemini Live one-on-one conversations.

    Protocol:
      Client -> Server:
        { "type": "setup", "scenario_id": int, "agent_id": str }
        { "type": "audio", "data": "<base64 PCM 16-bit 16kHz>" }
        { "type": "text", "content": "..." }
        { "type": "end" }

      Server -> Client:
        { "type": "setup_complete" }
        { "type": "audio", "data": "<base64 PCM 16-bit 24kHz>" }
        { "type": "transcript_user", "text": "..." }
        { "type": "transcript_agent", "text": "..." }
        { "type": "turn_complete" }
        { "type": "error", "message": "..." }
    """
    await websocket.accept()

    auth = await _authenticate_websocket(websocket)
    if auth is None:
        return
    session_id, user_id = auth

    logger.info("gemini_live_ws_connected", session_id=session_id)

    gemini_session: GeminiLiveSession | None = None
    receive_task: asyncio.Task | None = None

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type == "setup":
                scenario_id = msg.get("scenario_id")
                agent_id = msg.get("agent_id")

                if not scenario_id or not agent_id:
                    await websocket.send_json(
                        {"type": "error", "message": "scenario_id and agent_id required"}
                    )
                    continue

                db = get_database_service()
                scenario = await db.scenarios.get_scenario(scenario_id)
                agent = await db.agents.get_agent(agent_id)

                if not scenario or not agent:
                    await websocket.send_json(
                        {"type": "error", "message": "Scenario or agent not found"}
                    )
                    continue

                personality_desc = ""
                if agent.agent_personality:
                    personality_desc = agent.agent_personality.personality_description

                voice_name = "Aoede"
                if agent.voice and agent.voice.voice_name:
                    voice_name = agent.voice.voice_name

                system_prompt = build_one_on_one_system_prompt(
                    scenario_name=scenario.name,
                    scenario_overview=scenario.overview,
                    scenario_instructions=scenario.system_instructions,
                    agent_name=agent.name,
                    agent_personality=personality_desc,
                    agent_objective=agent.objective,
                    agent_instructions=agent.instructions,
                    agent_constraints=agent.constraints,
                    agent_context=agent.context,
                )

                gemini_session = GeminiLiveSession(
                    session_id=session_id,
                    system_instruction=system_prompt,
                    voice_name=voice_name,
                )
                await gemini_session.connect()

                async def _relay_from_gemini(_session=gemini_session):
                    """Forward Gemini responses to the WebSocket client.
                    
                    Note: The _session is passed in to satisfy the type checker.
                    The concern is that if the loop iterates again, 
                    gemini_session could change before the function executes, 
                    causing it to use a different value than intended.
                    
                    Args:
                        _session: The Gemini Live session to relay from.
                    
                    """
                    try:
                        async for gemini_msg in _session.receive_messages():
                            try:
                                await websocket.send_json(gemini_msg)
                            except Exception:
                                break
                    except Exception as e:
                        logger.warning("gemini_relay_error", error=str(e))

                receive_task = asyncio.create_task(_relay_from_gemini())

                initial_prompt = (scenario.initial_prompt or "").strip()
                if not initial_prompt:
                    initial_prompt = "Hi, I'm the teacher. Please introduce yourself briefly."

                await websocket.send_json({
                    "type": "setup_complete",
                    "initial_prompt": initial_prompt,
                })

                await gemini_session.send_text(initial_prompt)

            elif msg_type == "audio":
                if gemini_session:
                    audio_bytes = base64.b64decode(msg["data"])
                    await gemini_session.send_audio(audio_bytes)

            elif msg_type == "text":
                if gemini_session:
                    await gemini_session.send_text(msg["content"])

            elif msg_type == "end":
                break

    except WebSocketDisconnect:
        logger.info("gemini_live_ws_disconnected", session_id=session_id)
    except json.JSONDecodeError:
        logger.warning("gemini_live_ws_invalid_json", session_id=session_id)
    except Exception as e:
        logger.error("gemini_live_ws_error", session_id=session_id, error=str(e))
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        if receive_task and not receive_task.done():
            receive_task.cancel()
            try:
                await receive_task
            except (asyncio.CancelledError, Exception):
                pass
        if gemini_session:
            await gemini_session.close()
