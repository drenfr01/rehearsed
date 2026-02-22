"""Chatbot API endpoints for handling chat interactions.

This module provides endpoints for chat interactions, including regular chat,
streaming chat, message history management, and chat history clearing.
"""

import asyncio
import base64
import json
import uuid
from typing import List

from asgiref.sync import sync_to_async
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
)
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage as LCHumanMessage
from langgraph.types import StateSnapshot

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
from app.services.feedback_cache import feedback_cache, generate_feedback_and_store
from app.services.gemini_text_to_speech import GeminiTextToSpeech
from app.services.speech_to_text import SpeechToTextService
from app.services.tts_audio_cache import generate_tts_and_store, tts_audio_cache

router = APIRouter()
agent = LangGraphAgent()
speech_to_text_service = SpeechToTextService()


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat"][0])
async def chat(
    request: Request,
    chat_request: ChatRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_current_session),
    database_service: DatabaseService = Depends(get_database_service),
    text_to_speech_service: GeminiTextToSpeech = Depends(get_text_to_speech_service),
):
    """Process a chat request using LangGraph.

    Args:
        request: The FastAPI request object for rate limiting.
        chat_request: The chat request containing messages.
        background_tasks: The background tasks to run.
        session: The current session from the auth token.
        database_service: The database service instance.
        text_to_speech_service: The text-to-speech service instance.

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

        # Background prewarm for TTS (lazy-loaded): generate audio after returning text.
        # We only prewarm the most recent student response (avoids duplicate work).
        try:
            if result.student_responses:
                latest = result.student_responses[-1]
                audio_id = latest.audio_id or ""
                has_audio = bool(latest.audio_base64 or "")
                
                # Extract voice_name safely (voice is Optional on Agent)
                voice_name = ""
                if latest.student_details and latest.student_details.voice:
                    voice_name = latest.student_details.voice.voice_name or ""
                
                # Only generate TTS if we have audio_id, no existing audio, and a voice_name
                if audio_id and not has_audio and voice_name:
                    existing = tts_audio_cache.get(audio_id)
                    if existing is None:
                        # Extract personality safely
                        personality = ""
                        if latest.student_personality:
                            personality = latest.student_personality.personality_description or ""
                        tts_prompt = f"Speak as a {personality or 'helpful and engaged'} student in a classroom setting."
                        
                        tts_audio_cache.put_pending(audio_id, session.id)
                        background_tasks.add_task(
                            generate_tts_and_store,
                            audio_id,
                            session.id,
                            voice_name,
                            tts_prompt,
                            latest.student_response,
                            text_to_speech_service,
                        )
        except Exception as e:
            logger.warning("tts_background_task_schedule_failed", session_id=session.id, error=str(e))

        # Note: Feedback generation is now started immediately in graph_entry.py
        # and runs in parallel with graph execution (no need to schedule here)

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

    Streams student response tokens via Server-Sent Events so the frontend can
    render text progressively.  The final SSE event (``done=True``) carries
    metadata (student name, audio_id, feedback_request_id, interrupt values)
    needed to finalise the message in the UI.

    Args:
        request: The FastAPI request object for rate limiting.
        chat_request: The chat request containing messages.
        background_tasks: FastAPI background tasks for async post-processing.
        session: The current session from the auth token.
        database_service: The database service instance.
        text_to_speech_service: The text-to-speech service instance.

    Returns:
        StreamingResponse: A streaming response of the chat completion.

    Raises:
        HTTPException: If there's an error processing the request.
    """
    try:
        logger.info(
            "stream_chat_request_received",
            session_id=session.id,
            is_resumption=chat_request.is_resumption,
        )

        scenario_id = database_service.scenarios.get_current_scenario().id

        # Resolve resumption text (handles audio transcription if needed)
        resumption_text = chat_request.resumption_text
        transcribed_text: str = ""
        if chat_request.audio_base64:
            logger.info("audio_transcription_started", session_id=session.id)
            try:
                audio_bytes = base64.b64decode(chat_request.audio_base64)
                transcribed = await speech_to_text_service.transcribe_audio(audio_bytes)
                if transcribed:
                    resumption_text = transcribed
                    transcribed_text = transcribed
                    logger.info("audio_transcription_completed", session_id=session.id)
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="Could not transcribe audio. Please try again or type your message.",
                    )
            except base64.binascii.Error as e:
                raise HTTPException(status_code=400, detail="Invalid audio data encoding")

        # Start async feedback generation in parallel with graph execution
        feedback_id = ""
        if chat_request.is_resumption:
            try:
                graph_obj = await agent.create_graph(scenario_id, text_to_speech_service)
                if graph_obj is not None:
                    config_snap = {"configurable": {"thread_id": session.id}}
                    state_snap: StateSnapshot = await sync_to_async(graph_obj.get_state)(config_snap)
                    current_messages = list(state_snap.values.get("messages", [])) if state_snap.values else []
                    current_messages.append(LCHumanMessage(content=resumption_text))
                    feedback_id = uuid.uuid4().hex
                    feedback_cache.put_pending(
                        feedback_id=feedback_id,
                        session_id=session.id,
                        scenario_id=scenario_id,
                        messages=current_messages,
                    )
                    asyncio.create_task(
                        generate_feedback_and_store(feedback_id, agent.llm, session.id)
                    )
                    logger.info("async_feedback_started_early", feedback_id=feedback_id, session_id=session.id)
            except Exception as fb_err:
                logger.warning("stream_early_feedback_start_failed", error=str(fb_err))

        async def event_generator():
            try:
                with llm_stream_duration_seconds.labels(
                    model=getattr(agent.llm, "model", getattr(agent.llm, "model_name", "unknown"))
                ).time():
                    if chat_request.is_resumption:
                        token_stream = agent.get_stream_resumption_response(
                            resumption_text,
                            session.id,
                            user_id=session.user_id,
                            scenario_id=scenario_id,
                            tts_service=text_to_speech_service,
                        )
                    else:
                        token_stream = agent.get_stream_response(
                            chat_request.messages,
                            session.id,
                            user_id=session.user_id,
                            scenario_id=scenario_id,
                            tts_service=text_to_speech_service,
                        )

                    async for chunk in token_stream:
                        yield f"data: {json.dumps(StreamResponse(content=chunk, done=False).model_dump())}\n\n"

                # Retrieve final state to populate metadata for the done event.
                # Guard individually so a state-read failure never drops feedback_request_id.
                student_name: str | None = None
                audio_id: str | None = None
                interrupt_value: str | None = None
                interrupt_value_type: str | None = None

                try:
                    final_result = await agent.get_current_chat_state(session.id, scenario_id, text_to_speech_service)

                    if final_result.student_responses:
                        latest = final_result.student_responses[-1]
                        student_name = latest.student_details.name if latest.student_details else None
                        audio_id = latest.audio_id or None

                        # Schedule TTS via asyncio.create_task — background_tasks.add_task()
                        # added inside a StreamingResponse generator is never executed because
                        # FastAPI snapshots background tasks before the body iterator runs.
                        voice_name = ""
                        if latest.student_details and latest.student_details.voice:
                            voice_name = latest.student_details.voice.voice_name or ""
                        if audio_id and not latest.audio_base64 and voice_name:
                            if tts_audio_cache.get(audio_id) is None:
                                personality = ""
                                if latest.student_personality:
                                    personality = latest.student_personality.personality_description or ""
                                tts_prompt = f"Speak as a {personality or 'helpful and engaged'} student in a classroom setting."
                                tts_audio_cache.put_pending(audio_id, session.id)
                                asyncio.create_task(
                                    generate_tts_and_store(
                                        audio_id,
                                        session.id,
                                        voice_name,
                                        tts_prompt,
                                        latest.student_response,
                                        text_to_speech_service,
                                    )
                                )

                    if final_result.interrupt_task:
                        interrupt_value = final_result.interrupt_value
                        interrupt_value_type = final_result.interrupt_value_type

                except Exception as state_err:
                    logger.warning("stream_final_state_failed", session_id=session.id, error=str(state_err))

                final_event = StreamResponse(
                    content=transcribed_text,
                    done=True,
                    student_name=student_name,
                    audio_id=audio_id,
                    feedback_request_id=feedback_id or None,
                    interrupt_value=interrupt_value,
                    interrupt_value_type=interrupt_value_type,
                )
                yield f"data: {json.dumps(final_event.model_dump())}\n\n"

            except Exception as e:
                logger.error("stream_chat_request_failed", session_id=session.id, error=str(e), exc_info=True)
                yield f"data: {json.dumps(StreamResponse(content=str(e), done=True).model_dump())}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("stream_chat_request_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages", response_model=ChatResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["messages"][0])
async def get_session_messages(
    request: Request,
    session: Session = Depends(get_current_session),
    database_service: DatabaseService = Depends(get_database_service),
    text_to_speech_service: GeminiTextToSpeech = Depends(get_text_to_speech_service),
):
    """Get all messages for a session.

    Args:
        request: The FastAPI request object for rate limiting.
        session: The current session from the auth token.
        database_service: The database service instance.
        text_to_speech_service: The text-to-speech service instance.

    Returns:
        ChatResponse: All messages in the session.

    Raises:
        HTTPException: If there's an error retrieving the messages.
    """
    try:
        # Get scenario_id from the current scenario
        current_scenario = database_service.scenarios.get_current_scenario()
        if current_scenario is None:
            raise ValueError("No scenario is currently set. Please set a scenario before retrieving messages.")
        scenario_id = current_scenario.id
        messages = await agent.get_chat_history(
            session.id, 
            scenario_id=scenario_id,
            tts_service=text_to_speech_service
        )
        return ChatResponse(messages=messages)
    except ValueError as e:
        logger.error("get_messages_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
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


@router.get("/feedback/{feedback_id}")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["messages"][0])
async def get_feedback(
    request: Request,
    feedback_id: str,
    session: Session = Depends(get_current_session),
):
    """Get async inline feedback by ID.

    This endpoint is used for polling feedback that is generated asynchronously
    after the chat response is returned.

    Args:
        request: The FastAPI request object for rate limiting.
        feedback_id: The unique ID of the feedback request.
        session: The current session from the auth token.

    Returns:
        dict: The feedback status and content if ready.
            - status: "pending" | "ready" | "failed"
            - feedback: List of feedback strings (empty if not ready)
    """
    entry = feedback_cache.get(feedback_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Feedback request not found")
    
    # Verify the feedback belongs to this session
    if entry.session_id != session.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this feedback")
    
    return entry.to_api_payload()
