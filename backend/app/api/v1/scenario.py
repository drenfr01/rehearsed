"""Chatbot API endpoints for handling chat interactions.

This module provides endpoints for chat interactions, including regular chat,
streaming chat, message history management, and chat history clearing.
"""

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
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.core.metrics import llm_stream_duration_seconds
from app.models.session import Session
from app.services.database import DatabaseService
from app.schemas.scenario import (
    ScenarioRequest,
    ScenarioResponse,
    AddScenarioRequest,
    AddScenarioResponse,
)
from app.models.scenario import Scenario

router = APIRouter()
database_service = DatabaseService()

@router.post("/get-all", response_model=List[Scenario])
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["get_all_scenarios"][0])
async def get_all_scenarios(
    request: Request,
) -> List[Scenario]:
    """Returna list of all scenarios.

    Args:
        request: The FastAPI request object for rate limiting.

    Returns:
        ChatResponse: The processed chat response.

    Raises:
        HTTPException: If there's an error processing the request.
    """
    try:
        logger.info(
            "get_all_scenarios_request_received",
        )

        return database_service.get_all_scenarios()
        
    except Exception as e:
        logger.error("get_all_scenarios_request_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

