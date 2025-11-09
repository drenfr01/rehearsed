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

@router.get("/get-all", response_model=List[Scenario])
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["get_all_scenarios"][0])
async def get_all_scenarios(
    request: Request,
) -> List[Scenario]:
    """Returna list of all scenarios.

    Args:
        request: The FastAPI request object for rate limiting.

    Returns:
        List[Scenario]: A list of all scenarios.

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


@router.get("/get-by-id/{scenario_id}", response_model=Scenario)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["get_scenario_by_id"][0])
async def get_scenario_by_id(
    request: Request,
    scenario_id: int,
) -> Scenario:
    """Return a scenario by its ID.

    Args:
        request: The FastAPI request object for rate limiting.
        scenario_id: The ID of the scenario to get .
    Returns:
        Scenario: The scenario with the given ID.

    Raises:
        HTTPException: If there's an error processing the request.
    """
    try:
        logger.info(
            "get_scenario_by_id_request_received",
        )

        return database_service.get_scenario_by_id(scenario_id)
        
    except Exception as e:
        logger.error("get_scenario_by_id_request_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/set-current-by-id", response_model=Scenario)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["set_scenario_by_id"][0])
async def set_current_scenario_by_id(
    request: Request,
    scenario_request: ScenarioRequest,
) -> Scenario:
    """Return a scenario by its ID.

    Args:
        request: The FastAPI request object for rate limiting.
        scenario_request: The request object containing the scenario ID.
    Returns:
        Scenario: The scenario that was set.

    Raises:
        HTTPException: If there's an error processing the request.
    """
    try:
        logger.info(
            "set_current_scenario_by_id_request_received",
        )

        return database_service.set_scenario(scenario_request.scenario_id)
        
    except Exception as e:
        logger.error("set_current_scenario_by_id_request_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


