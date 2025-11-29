"""Scenario API endpoints for handling scenario selection and management.

This module provides endpoints for scenario interactions, including getting
all scenarios available to a user (global + user-local).
"""

from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.user import User
from app.services.database import DatabaseService
from app.schemas.scenario import (
    ScenarioRequest,
    ScenarioResponse,
    AddScenarioRequest,
    AddScenarioResponse,
    ScenarioWithOwnerResponse,
)
from app.models.scenario import Scenario
from app.utils.auth import verify_token
from app.utils.sanitization import sanitize_string
from app.services.database import database_service

router = APIRouter()
security = HTTPBearer(auto_error=False)  # auto_error=False allows unauthenticated requests


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[User]:
    """Get the current user from the token if provided, otherwise return None.

    Args:
        credentials: The optional HTTP authorization credentials.

    Returns:
        Optional[User]: The authenticated user if token is valid, None otherwise.
    """
    if credentials is None:
        return None
    
    try:
        token = sanitize_string(credentials.credentials)
        token_subject = verify_token(token)
        
        if token_subject is None:
            return None

        token_subject = sanitize_string(token_subject)

        # Try to get it as a session first
        session = await database_service.get_session(token_subject)
        
        if session:
            user = await database_service.get_user(session.user_id)
            return user
        else:
            # Token might be a user token
            try:
                user_id = int(token_subject)
                user = await database_service.get_user(user_id)
                return user
            except ValueError:
                return None
    except Exception:
        return None


@router.get("/get-all", response_model=List[ScenarioWithOwnerResponse])
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["get_all_scenarios"][0])
async def get_all_scenarios(
    request: Request,
    user: Optional[User] = Depends(get_optional_user),
) -> List[ScenarioWithOwnerResponse]:
    """Return a list of all scenarios available to the user.
    
    If user is authenticated, returns global scenarios + user's local scenarios.
    If user is not authenticated, returns only global scenarios.

    Args:
        request: The FastAPI request object for rate limiting.
        user: The optional authenticated user.

    Returns:
        List[ScenarioWithOwnerResponse]: A list of scenarios with ownership info.

    Raises:
        HTTPException: If there's an error processing the request.
    """
    try:
        logger.info(
            "get_all_scenarios_request_received",
            user_id=user.id if user else None,
        )

        if user:
            # Return global + user's local scenarios
            scenarios = await database_service.get_scenarios_for_user(user.id)
        else:
            # Return only global scenarios
            scenarios = await database_service.get_all_scenarios()
        
        return [
            ScenarioWithOwnerResponse(
                id=s.id,
                name=s.name,
                description=s.description,
                overview=s.overview,
                system_instructions=s.system_instructions,
                initial_prompt=s.initial_prompt,
                created_at=s.created_at,
                owner_id=s.owner_id,
                is_global=s.owner_id is None,
            )
            for s in scenarios
        ]
        
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


