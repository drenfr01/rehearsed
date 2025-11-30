"""API v1 router configuration.

This module sets up the main API router and includes all sub-routers for different
endpoints like authentication and chatbot functionality.
"""

from typing import List

from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.chatbot import router as chatbot_router
from app.api.v1.scenario import router as scenario_router
from app.api.v1.user_content import router as user_content_router
from app.core.logging import logger
from app.schemas.agent import AgentVoiceResponse
from app.services.database import database_service

api_router = APIRouter()

# Include routers
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(chatbot_router, prefix="/chatbot", tags=["chatbot"])
api_router.include_router(scenario_router, prefix="/scenario", tags=["scenario"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(user_content_router, prefix="/user-content", tags=["user-content"])


@api_router.get("/health")
async def health_check():
    """Health check endpoint.

    Returns:
        dict: Health status information.
    """
    logger.info("health_check_called")
    return {"status": "healthy", "version": "1.0.0"}


@api_router.get("/agent-voices", response_model=List[AgentVoiceResponse], tags=["agents"])
async def get_agent_voices():
    """Get all available agent voices.

    This endpoint returns all voice options that can be assigned to agents.
    No authentication required as this is reference data.

    Returns:
        List[AgentVoiceResponse]: List of all available agent voices.
    """
    voices = await database_service.get_all_agent_voices()
    return [
        AgentVoiceResponse(
            id=v.id,
            voice_name=v.voice_name,
        )
        for v in voices
    ]
