"""Chatbot API endpoints for handling chat interactions.

This module provides endpoints for chat interactions, including regular chat,
streaming chat, message history management, and chat history clearing.
"""

import base64
import json
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)
from fastapi.responses import StreamingResponse

from app.api.v1.auth import get_current_session
from app.api.v1.deps import get_database_service, get_text_to_speech_service
from app.core.config import settings
from app.core.langgraph.graph_entry import LangGraphAgent
from app.core.limiter import limiter
from app.core.logging import logger
from app.core.metrics import llm_stream_duration_seconds
from app.models.session import Session
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    StreamResponse,
)
from app.services.database.base import DatabaseService
from app.services.gemini_text_to_speech import GeminiTextToSpeech
from app.services.speech_to_text import SpeechToTextService

router = APIRouter()
agent = LangGraphAgent()
speech_to_text_service = SpeechToTextService()


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat"][0])
async def chat(
    request: Request,
    chat_request: ChatRequest,
    session: Session = Depends(get_current_session),
    database_service: DatabaseService = Depends(get_database_service),
    text_to_speech_service: GeminiTextToSpeech = Depends(get_text_to_speech_service),
):
    """Process a chat request using LangGraph.

    Args:
        request: The FastAPI request object for rate limiting.
        chat_request: The chat request containing messages.
        session: The current session from the auth token.

    Returns:
        ChatResponse: The processed chat response.

    Raises:
        HTTPException: If there's an error processing the request.
    """
    try:
        logger.info(
            "chat_request_received",
            session_id=session.id,
            message_count=len(chat_request.messages),
        )

        # If audio_base64 is provided, transcribe it to text
        resumption_text = chat_request.resumption_text
        if chat_request.audio_base64:
            logger.info("audio_transcription_started", session_id=session.id)
            try:
                audio_bytes = base64.b64decode(chat_request.audio_base64)
                transcribed_text = await speech_to_text_service.transcribe_audio(audio_bytes)
                if transcribed_text:
                    resumption_text = transcribed_text
                    logger.info(
                        "audio_transcription_completed",
                        session_id=session.id,
                        transcribed_length=len(transcribed_text),
                    )
                else:
                    logger.warning(
                        "audio_transcription_empty",
                        session_id=session.id,
                    )
                    raise HTTPException(
                        status_code=400, 
                        detail="Could not transcribe audio. Please try again or type your message."
                    )
            except base64.binascii.Error as e:
                logger.error(
                    "audio_decode_failed",
                    session_id=session.id,
                    error=str(e),
                )
                raise HTTPException(status_code=400, detail="Invalid audio data encoding")

        if chat_request.is_resumption:
            result: ChatResponse = await agent.get_resumption_response(
                resumption_text, 
                session.id, 
                user_id=session.user_id, 
                scenario_id=database_service.scenarios.get_current_scenario().id,
                tts_service=text_to_speech_service
                )
        else:
            result: ChatResponse = await agent.get_response(
                chat_request.messages, 
                session.id, 
                user_id=session.user_id, 
                scenario_id=database_service.scenarios.get_current_scenario().id,
                tts_service=text_to_speech_service
                )
        
        # Include transcribed text in response if audio was provided
        if chat_request.audio_base64 and resumption_text:
            result.transcribed_text = resumption_text

        logger.info("chat_request_processed", session_id=session.id)

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("chat_request_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat_stream"][0])
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    session: Session = Depends(get_current_session),
    database_service: DatabaseService = Depends(get_database_service),
    text_to_speech_service: GeminiTextToSpeech = Depends(get_text_to_speech_service),
):
    """Process a chat request using LangGraph with streaming response.

    Args:
        request: The FastAPI request object for rate limiting.
        chat_request: The chat request containing messages.
        session: The current session from the auth token.

    Returns:
        StreamingResponse: A streaming response of the chat completion.

    Raises:
        HTTPException: If there's an error processing the request.
    """
    try:
        logger.info(
            "stream_chat_request_received",
            session_id=session.id,
            message_count=len(chat_request.messages),
        )

        async def event_generator():
            """Generate streaming events.

            Yields:
                str: Server-sent events in JSON format.

            Raises:
                Exception: If there's an error during streaming.
            """
            try:
                full_response = ""
                with llm_stream_duration_seconds.labels(model=agent.llm.model_name).time():
                    async for chunk in agent.get_stream_response(
                        chat_request.messages, session.id, user_id=session.user_id, scenario_id=chat_request.scenario_id, tts_service=text_to_speech_service
                    ):
                        full_response += chunk
                        response = StreamResponse(content=chunk, done=False)
                        yield f"data: {json.dumps(response.model_dump())}\n\n"

                # Send final message indicating completion
                final_response = StreamResponse(content="", done=True)
                yield f"data: {json.dumps(final_response.model_dump())}\n\n"

            except Exception as e:
                logger.error(
                    "stream_chat_request_failed",
                    session_id=session.id,
                    error=str(e),
                    exc_info=True,
                )
                error_response = StreamResponse(content=str(e), done=True)
                yield f"data: {json.dumps(error_response.model_dump())}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        logger.error(
            "stream_chat_request_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages", response_model=ChatResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["messages"][0])
async def get_session_messages(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get all messages for a session.

    Args:
        request: The FastAPI request object for rate limiting.
        session: The current session from the auth token.

    Returns:
        ChatResponse: All messages in the session.

    Raises:
        HTTPException: If there's an error retrieving the messages.
    """
    try:
        messages = await agent.get_chat_history(session.id)
        return ChatResponse(messages=messages)
    except Exception as e:
        logger.error("get_messages_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/messages")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["messages"][0])
async def clear_chat_history(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Clear all messages for a session.

    Args:
        request: The FastAPI request object for rate limiting.
        session: The current session from the auth token.

    Returns:
        dict: A message indicating the chat history was cleared.
    """
    try:
        await agent.clear_chat_history(session.id)
        return {"message": "Chat history cleared successfully"}
    except Exception as e:
        logger.error("clear_chat_history_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
