"""API v1 router configuration.

This module sets up the main API router and includes all sub-routers for different
endpoints like authentication and chatbot functionality.
"""

from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.avatars import router as avatars_router
from app.api.v1.chatbot import router as chatbot_router
from app.api.v1.gemini_live import router as gemini_live_router
from app.api.v1.llm_config import router as llm_config_router
from app.api.v1.llm_models import router as llm_models_router
from app.api.v1.scenario import router as scenario_router
from app.api.v1.tts import router as tts_router
from app.api.v1.user_content import router as user_content_router
from app.core.logging import logger

api_router = APIRouter()

# Include routers
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(chatbot_router, prefix="/chatbot", tags=["chatbot"])
api_router.include_router(gemini_live_router, prefix="/gemini-live", tags=["gemini-live"])
api_router.include_router(scenario_router, prefix="/scenario", tags=["scenario"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(user_content_router, prefix="/user-content", tags=["user-content"])
api_router.include_router(tts_router, prefix="/tts", tags=["tts"])
api_router.include_router(llm_models_router, prefix="/llm-models", tags=["llm-models"])
api_router.include_router(llm_config_router, prefix="/llm-config", tags=["llm-config"])
api_router.include_router(avatars_router, prefix="/avatars", tags=["avatars"])


@api_router.get("/health")
async def health_check():
    """Health check endpoint.

    Returns:
        dict: Health status information.
    """
    logger.info("health_check_called")
    return {"status": "healthy", "version": "1.0.0"}
