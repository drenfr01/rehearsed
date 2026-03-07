"""User content endpoints for managing user-local scenarios, agents, personalities, and feedback.

This module provides endpoints for users to manage their own local content.
Users can create, update, delete their local content and copy global content to their local.
"""

from typing import List

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

from app.api.v1.chatbot import agent as langgraph_agent
from app.api.v1.deps import get_database_service
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.user import User
from app.schemas.agent import (
    AgentCreate,
    AgentPersonalityCreate,
    AgentPersonalityResponse,
    AgentPersonalityUpdate,
    AgentResponse,
    AgentUpdate,
    AgentVoiceResponse,
    DeleteAgentPersonalityResponse,
    DeleteAgentResponse,
)
from app.schemas.feedback import (
    DeleteFeedbackResponse,
    FeedbackCreate,
    FeedbackResponse,
    FeedbackUpdate,
)
from app.schemas.scenario import (
    DeleteScenarioResponse,
    ScenarioAdminResponse,
    ScenarioCreateRequest,
    ScenarioUpdateRequest,
)
from app.services.database.base import DatabaseService
from app.utils.auth import verify_token
from app.utils.sanitization import sanitize_string

router = APIRouter()
security = HTTPBearer()


async def get_current_user_from_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database_service: DatabaseService = Depends(get_database_service),
) -> User:
    """Get the current user from the token (supports both session and user tokens).

    Args:
        credentials: The HTTP authorization credentials containing the JWT token.
        database_service: The database service instance.

    Returns:
        User: The authenticated user.

    Raises:
        HTTPException: If the token is invalid or user is not found.
    """
    try:
        token = sanitize_string(credentials.credentials)
        token_subject = verify_token(token)
        
        if token_subject is None:
            logger.error("invalid_token", token_part=token[:10] + "...")
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token_subject = sanitize_string(token_subject)

        # Try to get it as a session first
        session = await database_service.sessions.get_session(token_subject)
        
        if session:
            user = await database_service.users.get_user(session.user_id)
            if user is None:
                logger.error("user_not_found_from_session", session_id=token_subject)
                raise HTTPException(
                    status_code=404,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        else:
            # Token might be a user token
            try:
                user_id = int(token_subject)
                user = await database_service.users.get_user(user_id)
                if user is None:
                    logger.error("user_not_found", user_id=user_id)
                    raise HTTPException(
                        status_code=404,
                        detail="User not found",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
            except ValueError:
                logger.error("invalid_token_subject", subject=token_subject)
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        # Verify user is approved
        if not user.is_approved:
            logger.warning("unapproved_user_access_attempt", user_id=user.id)
            raise HTTPException(
                status_code=403,
                detail="Account pending approval",
            )

        return user
    except HTTPException:
        raise
    except ValueError as ve:
        logger.error("token_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(
            status_code=422,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ========== AgentVoice Endpoints ==========

@router.get("/agent-voices", response_model=List[AgentVoiceResponse], tags=["agents"])
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS.get("get_all_agent_voices", ["10 per minute"])[0])
async def get_agent_voices(
    request: Request,
    user: User = Depends(get_current_user_from_session),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Get all available agent voices.

    This endpoint returns all voice options that can be assigned to agents.

    Args:
        request: The FastAPI request object for rate limiting.
        user: The authenticated user.
        database_service: The database service instance.

    Returns:
        List[AgentVoiceResponse]: List of all available agent voices.
    """
    voices = await database_service.agents.get_all_agent_voices()
    return [
        AgentVoiceResponse(
            id=v.id,
            voice_name=v.voice_name,
        )
        for v in voices
    ]


# ========== Scenario Endpoints ==========

@router.get("/scenarios", response_model=List[ScenarioAdminResponse])
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS.get("get_all_scenarios", ["10 per minute"])[0])
async def list_my_scenarios(
    request: Request,
    user: User = Depends(get_current_user_from_session),
    database_service: DatabaseService = Depends(get_database_service),
):
    """List user's local scenarios only.

    Args:
        request: The FastAPI request object for rate limiting.
        user: The authenticated user.
        database_service: The database service instance.

    Returns:
        List of user's local scenarios.
    """
    try:
        scenarios = await database_service.users.get_user_local_scenarios(user.id)
        return [
            ScenarioAdminResponse(
                id=s.id,
                name=s.name,
                description=s.description,
                overview=s.overview,
                system_instructions=s.system_instructions,
                initial_prompt=s.initial_prompt,
                teaching_objectives=s.teaching_objectives or "",
                created_at=s.created_at,
            )
            for s in scenarios
        ]
    except Exception as e:
        logger.error("list_user_scenarios_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve scenarios")


@router.post("/scenarios", response_model=ScenarioAdminResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS.get("create_scenario", ["10 per minute"])[0])
async def create_scenario(
    request: Request,
    scenario_data: ScenarioCreateRequest,
    user: User = Depends(get_current_user_from_session),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Create a new user-local scenario.

    Args:
        request: The FastAPI request object for rate limiting.
        scenario_data: Scenario creation data.
        user: The authenticated user.
        database_service: The database service instance.

    Returns:
        Created scenario information.
    """
    try:
        name = sanitize_string(scenario_data.name)

        scenario = await database_service.scenarios.create_user_scenario(
            user_id=user.id,
            name=name,
            description=scenario_data.description,
            overview=scenario_data.overview,
            system_instructions=scenario_data.system_instructions,
            initial_prompt=scenario_data.initial_prompt,
            teaching_objectives=scenario_data.teaching_objectives,
        )

        logger.info("user_created_scenario", user_id=user.id, scenario_id=scenario.id, name=name)

        return ScenarioAdminResponse(
            id=scenario.id,
            name=scenario.name,
            description=scenario.description,
            overview=scenario.overview,
            system_instructions=scenario.system_instructions,
            initial_prompt=scenario.initial_prompt,
            teaching_objectives=scenario.teaching_objectives or "",
            created_at=scenario.created_at,
        )
    except HTTPException:
        raise
    except ValueError as ve:
        logger.error("scenario_creation_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error("create_scenario_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create scenario")


@router.put("/scenarios/{scenario_id}", response_model=ScenarioAdminResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS.get("update_scenario", ["10 per minute"])[0])
async def update_scenario(
    request: Request,
    scenario_id: int,
    scenario_data: ScenarioUpdateRequest,
    user: User = Depends(get_current_user_from_session),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Update a user's local scenario.

    Args:
        request: The FastAPI request object for rate limiting.
        scenario_id: The ID of the scenario to update.
        scenario_data: Updated scenario data.
        user: The authenticated user.
        database_service: The database service instance.

    Returns:
        Updated scenario information.
    """
    try:
        name = sanitize_string(scenario_data.name) if scenario_data.name else None

        updated_scenario = await database_service.scenarios.update_user_scenario(
            scenario_id=scenario_id,
            user_id=user.id,
            name=name,
            description=scenario_data.description,
            overview=scenario_data.overview,
            system_instructions=scenario_data.system_instructions,
            initial_prompt=scenario_data.initial_prompt,
            teaching_objectives=scenario_data.teaching_objectives,
        )

        logger.info("user_updated_scenario", user_id=user.id, scenario_id=scenario_id)

        return ScenarioAdminResponse(
            id=updated_scenario.id,
            name=updated_scenario.name,
            description=updated_scenario.description,
            overview=updated_scenario.overview,
            system_instructions=updated_scenario.system_instructions,
            initial_prompt=updated_scenario.initial_prompt,
            teaching_objectives=updated_scenario.teaching_objectives or "",
            created_at=updated_scenario.created_at,
        )
    except HTTPException:
        raise
    except ValueError as ve:
        logger.error("scenario_update_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error("update_scenario_failed", scenario_id=scenario_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update scenario")


@router.delete("/scenarios/{scenario_id}", response_model=DeleteScenarioResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS.get("delete_scenario", ["10 per minute"])[0])
async def delete_scenario(
    request: Request,
    scenario_id: int,
    user: User = Depends(get_current_user_from_session),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Delete a user's local scenario.

    Args:
        request: The FastAPI request object for rate limiting.
        scenario_id: The ID of the scenario to delete.
        user: The authenticated user.
        database_service: The database service instance.

    Returns:
        Success message.
    """
    try:
        await database_service.scenarios.delete_user_scenario(scenario_id, user.id)
        logger.info("user_deleted_scenario", user_id=user.id, scenario_id=scenario_id)
        return DeleteScenarioResponse(message="Scenario deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_scenario_failed", scenario_id=scenario_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete scenario")


@router.post("/scenarios/{scenario_id}/copy", response_model=ScenarioAdminResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS.get("create_scenario", ["10 per minute"])[0])
async def copy_scenario_to_local(
    request: Request,
    scenario_id: int,
    user: User = Depends(get_current_user_from_session),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Copy a global scenario to user's local scenarios.

    Args:
        request: The FastAPI request object for rate limiting.
        scenario_id: The ID of the scenario to copy.
        user: The authenticated user.
        database_service: The database service instance.

    Returns:
        The new local copy of the scenario.
    """
    try:
        new_scenario = await database_service.scenarios.copy_scenario_to_user(scenario_id, user.id, copy_agents=True)
        
        logger.info("user_copied_scenario", user_id=user.id, original_id=scenario_id, new_id=new_scenario.id)

        return ScenarioAdminResponse(
            id=new_scenario.id,
            name=new_scenario.name,
            description=new_scenario.description,
            overview=new_scenario.overview,
            system_instructions=new_scenario.system_instructions,
            initial_prompt=new_scenario.initial_prompt,
            created_at=new_scenario.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("copy_scenario_failed", scenario_id=scenario_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to copy scenario")


# ========== Agent Personality Endpoints ==========

@router.get("/agent-personalities", response_model=List[AgentPersonalityResponse])
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS.get("get_all_agent_personalities", ["10 per minute"])[0])
async def list_my_agent_personalities(
    request: Request,
    user: User = Depends(get_current_user_from_session),
    database_service: DatabaseService = Depends(get_database_service),
):
    """List user's local agent personalities only.

    Args:
        request: The FastAPI request object for rate limiting.
        user: The authenticated user.
        database_service: The database service instance.

    Returns:
        List of user's local agent personalities.
    """
    try:
        personalities = await database_service.users.get_user_local_agent_personalities(user.id)
        return [
            AgentPersonalityResponse(
                id=p.id,
                name=p.name,
                personality_description=p.personality_description,
                created_at=p.created_at,
            )
            for p in personalities
        ]
    except Exception as e:
        logger.error("list_user_agent_personalities_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve agent personalities")


@router.post("/agent-personalities", response_model=AgentPersonalityResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS.get("create_agent_personality", ["10 per minute"])[0])
async def create_agent_personality(
    request: Request,
    personality_data: AgentPersonalityCreate,
    user: User = Depends(get_current_user_from_session),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Create a new user-local agent personality.

    Args:
        request: The FastAPI request object for rate limiting.
        personality_data: Agent personality creation data.
        user: The authenticated user.
        database_service: The database service instance.

    Returns:
        Created agent personality information.
    """
    try:
        name = sanitize_string(personality_data.name)
        description = sanitize_string(personality_data.personality_description)

        personality = await database_service.agents.create_user_agent_personality(
            user_id=user.id,
            name=name,
            personality_description=description,
        )

        logger.info("user_created_agent_personality", user_id=user.id, personality_id=personality.id, name=name)

        return AgentPersonalityResponse(
            id=personality.id,
            name=personality.name,
            personality_description=personality.personality_description,
            created_at=personality.created_at,
        )
    except HTTPException:
        raise
    except ValueError as ve:
        logger.error("agent_personality_creation_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error("create_agent_personality_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create agent personality")


@router.put("/agent-personalities/{personality_id}", response_model=AgentPersonalityResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS.get("update_agent_personality", ["10 per minute"])[0])
async def update_agent_personality(
    request: Request,
    personality_id: int,
    personality_data: AgentPersonalityUpdate,
    user: User = Depends(get_current_user_from_session),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Update a user's local agent personality.

    Args:
        request: The FastAPI request object for rate limiting.
        personality_id: The ID of the personality to update.
        personality_data: Updated personality data.
        user: The authenticated user.
        database_service: The database service instance.

    Returns:
        Updated agent personality information.
    """
    try:
        name = sanitize_string(personality_data.name) if personality_data.name else None
        description = sanitize_string(personality_data.personality_description) if personality_data.personality_description else None

        updated_personality = await database_service.agents.update_user_agent_personality(
            personality_id=personality_id,
            user_id=user.id,
            name=name,
            personality_description=description,
        )

        logger.info("user_updated_agent_personality", user_id=user.id, personality_id=personality_id)

        return AgentPersonalityResponse(
            id=updated_personality.id,
            name=updated_personality.name,
            personality_description=updated_personality.personality_description,
            created_at=updated_personality.created_at,
        )
    except HTTPException:
        raise
    except ValueError as ve:
        logger.error("agent_personality_update_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error("update_agent_personality_failed", personality_id=personality_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update agent personality")


@router.delete("/agent-personalities/{personality_id}", response_model=DeleteAgentPersonalityResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS.get("delete_agent_personality", ["10 per minute"])[0])
async def delete_agent_personality(
    request: Request,
    personality_id: int,
    user: User = Depends(get_current_user_from_session),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Delete a user's local agent personality.

    Args:
        request: The FastAPI request object for rate limiting.
        personality_id: The ID of the personality to delete.
        user: The authenticated user.
        database_service: The database service instance.

    Returns:
        Success message.
    """
    try:
        await database_service.agents.delete_user_agent_personality(personality_id, user.id)
        logger.info("user_deleted_agent_personality", user_id=user.id, personality_id=personality_id)
        return DeleteAgentPersonalityResponse(message="Agent personality deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_agent_personality_failed", personality_id=personality_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete agent personality")


@router.post("/agent-personalities/{personality_id}/copy", response_model=AgentPersonalityResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS.get("create_agent_personality", ["10 per minute"])[0])
async def copy_agent_personality_to_local(
    request: Request,
    personality_id: int,
    user: User = Depends(get_current_user_from_session),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Copy a global agent personality to user's local personalities.

    Args:
        request: The FastAPI request object for rate limiting.
        personality_id: The ID of the personality to copy.
        user: The authenticated user.
        database_service: The database service instance.

    Returns:
        The new local copy of the agent personality.
    """
    try:
        new_personality = await database_service.agents.copy_agent_personality_to_user(personality_id, user.id)
        
        logger.info("user_copied_agent_personality", user_id=user.id, original_id=personality_id, new_id=new_personality.id)

        return AgentPersonalityResponse(
            id=new_personality.id,
            name=new_personality.name,
            personality_description=new_personality.personality_description,
            created_at=new_personality.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("copy_agent_personality_failed", personality_id=personality_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to copy agent personality")


# ========== Agent Endpoints ==========

@router.get("/agents", response_model=List[AgentResponse])
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS.get("get_all_agents", ["10 per minute"])[0])
async def list_my_agents(
    request: Request,
    user: User = Depends(get_current_user_from_session),
    database_service: DatabaseService = Depends(get_database_service),
):
    """List user's local agents only.

    Args:
        request: The FastAPI request object for rate limiting.
        user: The authenticated user.
        database_service: The database service instance.

    Returns:
        List of user's local agents.
    """
    try:
        agents = await database_service.users.get_user_local_agents(user.id)
        return [
            AgentResponse(
                id=a.id,
                name=a.name,
                scenario_id=a.scenario_id,
                agent_personality_id=a.agent_personality_id,
                voice=a.voice.voice_name if a.voice else "",
                display_text_color=a.display_text_color,
                avatar_gcs_uri=a.avatar_gcs_uri,
                objective=a.objective,
                instructions=a.instructions,
                constraints=a.constraints,
                context=a.context,
                created_at=a.created_at,
            )
            for a in agents
        ]
    except Exception as e:
        logger.error("list_user_agents_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve agents")


@router.post("/agents", response_model=AgentResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS.get("create_agent", ["10 per minute"])[0])
async def create_agent(
    request: Request,
    agent_data: AgentCreate,
    user: User = Depends(get_current_user_from_session),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Create a new user-local agent.

    Args:
        request: The FastAPI request object for rate limiting.
        agent_data: Agent creation data.
        user: The authenticated user.
        database_service: The database service instance.

    Returns:
        Created agent information.
    """
    try:
        agent_id = sanitize_string(agent_data.id)
        name = sanitize_string(agent_data.name)
        voice_name = sanitize_string(agent_data.voice) if agent_data.voice else ""
        display_text_color = sanitize_string(agent_data.display_text_color) if agent_data.display_text_color else ""

        # Verify scenario exists and user has access
        scenario = await database_service.scenarios.get_scenario(agent_data.scenario_id)
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        if scenario.owner_id is not None and scenario.owner_id != user.id:
            raise HTTPException(status_code=403, detail="You don't have access to this scenario")

        # Verify personality exists and user has access
        personality = await database_service.agents.get_agent_personality(agent_data.agent_personality_id)
        if not personality:
            raise HTTPException(status_code=404, detail="Agent personality not found")
        if personality.owner_id is not None and personality.owner_id != user.id:
            raise HTTPException(status_code=403, detail="You don't have access to this personality")

        # Look up voice_id from voice name if provided
        voice_id = None
        if voice_name:
            voice = await database_service.agents.get_agent_voice_by_name(voice_name)
            if not voice:
                raise HTTPException(status_code=404, detail=f"Voice '{voice_name}' not found")
            voice_id = voice.id

        agent = await database_service.agents.create_user_agent(
            user_id=user.id,
            agent_id=agent_id,
            name=name,
            scenario_id=agent_data.scenario_id,
            agent_personality_id=agent_data.agent_personality_id,
            voice_id=voice_id,
            display_text_color=display_text_color,
            avatar_gcs_uri=agent_data.avatar_gcs_uri or "",
            objective=agent_data.objective or "",
            instructions=agent_data.instructions or "",
            constraints=agent_data.constraints or "",
            context=agent_data.context or "",
        )

        # Invalidate the graph for this scenario
        await langgraph_agent.invalidate_graph(agent_data.scenario_id)
        logger.info("user_created_agent", user_id=user.id, agent_id=agent.id, name=name)

        return AgentResponse(
            id=agent.id,
            name=agent.name,
            scenario_id=agent.scenario_id,
            agent_personality_id=agent.agent_personality_id,
            voice=agent.voice.voice_name if agent.voice else "",
            display_text_color=agent.display_text_color,
            avatar_gcs_uri=agent.avatar_gcs_uri,
            objective=agent.objective,
            instructions=agent.instructions,
            constraints=agent.constraints,
            context=agent.context,
            created_at=agent.created_at,
        )
    except HTTPException:
        raise
    except ValueError as ve:
        logger.error("agent_creation_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error("create_agent_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create agent")


@router.put("/agents/{agent_id}", response_model=AgentResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS.get("update_agent", ["10 per minute"])[0])
async def update_agent(
    request: Request,
    agent_id: str,
    agent_data: AgentUpdate,
    user: User = Depends(get_current_user_from_session),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Update a user's local agent.

    Args:
        request: The FastAPI request object for rate limiting.
        agent_id: The ID of the agent to update.
        agent_data: Updated agent data.
        user: The authenticated user.
        database_service: The database service instance.

    Returns:
        Updated agent information.
    """
    try:
        # Verify scenario and personality exist if provided
        if agent_data.scenario_id is not None:
            scenario = await database_service.scenarios.get_scenario(agent_data.scenario_id)
            if not scenario:
                raise HTTPException(status_code=404, detail="Scenario not found")
            if scenario.owner_id is not None and scenario.owner_id != user.id:
                raise HTTPException(status_code=403, detail="You don't have access to this scenario")

        if agent_data.agent_personality_id is not None:
            personality = await database_service.agents.get_agent_personality(agent_data.agent_personality_id)
            if not personality:
                raise HTTPException(status_code=404, detail="Agent personality not found")
            if personality.owner_id is not None and personality.owner_id != user.id:
                raise HTTPException(status_code=403, detail="You don't have access to this personality")

        name = sanitize_string(agent_data.name) if agent_data.name else None
        voice_name = sanitize_string(agent_data.voice) if agent_data.voice else None
        display_text_color = sanitize_string(agent_data.display_text_color) if agent_data.display_text_color else None

        # Look up voice_id from voice name if provided
        voice_id = None
        clear_voice = False
        if voice_name:
            voice_obj = await database_service.agents.get_agent_voice_by_name(voice_name)
            if not voice_obj:
                raise HTTPException(status_code=404, detail=f"Voice '{voice_name}' not found")
            voice_id = voice_obj.id
        elif agent_data.voice == "":
            # Explicitly clear the voice if empty string provided
            clear_voice = True

        # Get old scenario_id for graph invalidation
        old_agent = await database_service.agents.get_agent(agent_id)
        old_scenario_id = old_agent.scenario_id if old_agent else None

        updated_agent = await database_service.agents.update_user_agent(
            agent_id=agent_id,
            user_id=user.id,
            name=name,
            voice_id=voice_id,
            display_text_color=display_text_color,
            avatar_gcs_uri=agent_data.avatar_gcs_uri,
            objective=agent_data.objective,
            instructions=agent_data.instructions,
            constraints=agent_data.constraints,
            context=agent_data.context,
            scenario_id=agent_data.scenario_id,
            agent_personality_id=agent_data.agent_personality_id,
            clear_voice=clear_voice,
        )

        # Invalidate affected graphs
        await langgraph_agent.invalidate_graph(updated_agent.scenario_id)
        if agent_data.scenario_id is not None and agent_data.scenario_id != old_scenario_id:
            await langgraph_agent.invalidate_graph(old_scenario_id)

        logger.info("user_updated_agent", user_id=user.id, agent_id=agent_id)

        return AgentResponse(
            id=updated_agent.id,
            name=updated_agent.name,
            scenario_id=updated_agent.scenario_id,
            agent_personality_id=updated_agent.agent_personality_id,
            voice=updated_agent.voice.voice_name if updated_agent.voice else "",
            display_text_color=updated_agent.display_text_color,
            avatar_gcs_uri=updated_agent.avatar_gcs_uri,
            objective=updated_agent.objective,
            instructions=updated_agent.instructions,
            constraints=updated_agent.constraints,
            context=updated_agent.context,
            created_at=updated_agent.created_at,
        )
    except HTTPException:
        raise
    except ValueError as ve:
        logger.error("agent_update_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error("update_agent_failed", agent_id=agent_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update agent")


@router.delete("/agents/{agent_id}", response_model=DeleteAgentResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS.get("delete_agent", ["10 per minute"])[0])
async def delete_agent(
    request: Request,
    agent_id: str,
    user: User = Depends(get_current_user_from_session),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Delete a user's local agent.

    Args:
        request: The FastAPI request object for rate limiting.
        agent_id: The ID of the agent to delete.
        user: The authenticated user.
        database_service: The database service instance.

    Returns:
        Success message.
    """
    try:
        agent = await database_service.agents.get_agent(agent_id)
        scenario_id = agent.scenario_id if agent else None

        await database_service.agents.delete_user_agent(agent_id, user.id)

        if scenario_id:
            await langgraph_agent.invalidate_graph(scenario_id)
        
        logger.info("user_deleted_agent", user_id=user.id, agent_id=agent_id)
        return DeleteAgentResponse(message="Agent deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_agent_failed", agent_id=agent_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete agent")


@router.post("/agents/{agent_id}/copy", response_model=AgentResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS.get("create_agent", ["10 per minute"])[0])
async def copy_agent_to_local(
    request: Request,
    agent_id: str,
    target_scenario_id: int,
    user: User = Depends(get_current_user_from_session),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Copy a global agent to user's local agents.

    Args:
        request: The FastAPI request object for rate limiting.
        agent_id: The ID of the agent to copy.
        target_scenario_id: The scenario ID to assign the copied agent to.
        user: The authenticated user.
        database_service: The database service instance.

    Returns:
        The new local copy of the agent.
    """
    try:
        # Verify target scenario exists and user has access
        scenario = await database_service.scenarios.get_scenario(target_scenario_id)
        if not scenario:
            raise HTTPException(status_code=404, detail="Target scenario not found")
        if scenario.owner_id is not None and scenario.owner_id != user.id:
            raise HTTPException(status_code=403, detail="You don't have access to the target scenario")

        new_agent = await database_service.agents.copy_agent_to_user(agent_id, user.id, target_scenario_id)
        
        await langgraph_agent.invalidate_graph(target_scenario_id)
        logger.info("user_copied_agent", user_id=user.id, original_id=agent_id, new_id=new_agent.id)

        return AgentResponse(
            id=new_agent.id,
            name=new_agent.name,
            scenario_id=new_agent.scenario_id,
            agent_personality_id=new_agent.agent_personality_id,
            voice=new_agent.voice,
            display_text_color=new_agent.display_text_color,
            avatar_gcs_uri=new_agent.avatar_gcs_uri,
            objective=new_agent.objective,
            instructions=new_agent.instructions,
            constraints=new_agent.constraints,
            context=new_agent.context,
            created_at=new_agent.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("copy_agent_failed", agent_id=agent_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to copy agent")


# ========== Feedback Endpoints ==========

@router.get("/feedback", response_model=List[FeedbackResponse])
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS.get("get_all_feedback", ["10 per minute"])[0])
async def list_my_feedback(
    request: Request,
    user: User = Depends(get_current_user_from_session),
    database_service: DatabaseService = Depends(get_database_service),
):
    """List user's local feedback only.

    Args:
        request: The FastAPI request object for rate limiting.
        user: The authenticated user.
        database_service: The database service instance.

    Returns:
        List of user's local feedback.
    """
    try:
        feedbacks = await database_service.users.get_user_local_feedback(user.id)
        return [
            FeedbackResponse(
                id=f.id,
                feedback_type=f.feedback_type,
                scenario_id=f.scenario_id,
                objective=f.objective,
                instructions=f.instructions,
                constraints=f.constraints,
                context=f.context,
                output_format=f.output_format,
                created_at=f.created_at,
            )
            for f in feedbacks
        ]
    except Exception as e:
        logger.error("list_user_feedback_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve feedback")


@router.post("/feedback", response_model=FeedbackResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS.get("create_feedback", ["10 per minute"])[0])
async def create_feedback(
    request: Request,
    feedback_data: FeedbackCreate,
    user: User = Depends(get_current_user_from_session),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Create a new user-local feedback.

    Args:
        request: The FastAPI request object for rate limiting.
        feedback_data: Feedback creation data.
        user: The authenticated user.
        database_service: The database service instance.

    Returns:
        Created feedback information.
    """
    try:
        feedback = await database_service.feedback.create_user_feedback(
            user_id=user.id,
            feedback_type=feedback_data.feedback_type,
            scenario_id=feedback_data.scenario_id,
            objective=feedback_data.objective,
            instructions=feedback_data.instructions,
            constraints=feedback_data.constraints,
            context=feedback_data.context,
            output_format=feedback_data.output_format or "",
        )

        logger.info("user_created_feedback", user_id=user.id, feedback_id=feedback.id, scenario_id=feedback.scenario_id)

        return FeedbackResponse(
            id=feedback.id,
            feedback_type=feedback.feedback_type,
            scenario_id=feedback.scenario_id,
            objective=feedback.objective,
            instructions=feedback.instructions,
            constraints=feedback.constraints,
            context=feedback.context,
            output_format=feedback.output_format,
            created_at=feedback.created_at,
        )
    except HTTPException:
        raise
    except ValueError as ve:
        logger.error("feedback_creation_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error("create_feedback_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create feedback")


@router.put("/feedback/{feedback_id}", response_model=FeedbackResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS.get("update_feedback", ["10 per minute"])[0])
async def update_feedback(
    request: Request,
    feedback_id: int,
    feedback_data: FeedbackUpdate,
    user: User = Depends(get_current_user_from_session),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Update a user's local feedback.

    Args:
        request: The FastAPI request object for rate limiting.
        feedback_id: The ID of the feedback to update.
        feedback_data: Updated feedback data.
        user: The authenticated user.
        database_service: The database service instance.

    Returns:
        Updated feedback information.
    """
    try:
        updated_feedback = await database_service.feedback.update_user_feedback(
            feedback_id=feedback_id,
            user_id=user.id,
            feedback_type=feedback_data.feedback_type,
            scenario_id=feedback_data.scenario_id,
            objective=feedback_data.objective,
            instructions=feedback_data.instructions,
            constraints=feedback_data.constraints,
            context=feedback_data.context,
            output_format=feedback_data.output_format,
        )

        logger.info("user_updated_feedback", user_id=user.id, feedback_id=feedback_id)

        return FeedbackResponse(
            id=updated_feedback.id,
            feedback_type=updated_feedback.feedback_type,
            scenario_id=updated_feedback.scenario_id,
            objective=updated_feedback.objective,
            instructions=updated_feedback.instructions,
            constraints=updated_feedback.constraints,
            context=updated_feedback.context,
            output_format=updated_feedback.output_format,
            created_at=updated_feedback.created_at,
        )
    except HTTPException:
        raise
    except ValueError as ve:
        logger.error("feedback_update_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error("update_feedback_failed", feedback_id=feedback_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update feedback")


@router.delete("/feedback/{feedback_id}", response_model=DeleteFeedbackResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS.get("delete_feedback", ["10 per minute"])[0])
async def delete_feedback(
    request: Request,
    feedback_id: int,
    user: User = Depends(get_current_user_from_session),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Delete a user's local feedback.

    Args:
        request: The FastAPI request object for rate limiting.
        feedback_id: The ID of the feedback to delete.
        user: The authenticated user.
        database_service: The database service instance.

    Returns:
        Success message.
    """
    try:
        await database_service.feedback.delete_user_feedback(feedback_id, user.id)
        logger.info("user_deleted_feedback", user_id=user.id, feedback_id=feedback_id)
        return DeleteFeedbackResponse(message="Feedback deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_feedback_failed", feedback_id=feedback_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete feedback")


@router.post("/feedback/{feedback_id}/copy", response_model=FeedbackResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS.get("create_feedback", ["10 per minute"])[0])
async def copy_feedback_to_local(
    request: Request,
    feedback_id: int,
    user: User = Depends(get_current_user_from_session),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Copy a global feedback to user's local feedback.

    Args:
        request: The FastAPI request object for rate limiting.
        feedback_id: The ID of the feedback to copy.
        user: The authenticated user.
        database_service: The database service instance.

    Returns:
        The new local copy of the feedback.
    """
    try:
        new_feedback = await database_service.feedback.copy_feedback_to_user(feedback_id, user.id)
        
        logger.info("user_copied_feedback", user_id=user.id, original_id=feedback_id, new_id=new_feedback.id)

        return FeedbackResponse(
            id=new_feedback.id,
            feedback_type=new_feedback.feedback_type,
            scenario_id=new_feedback.scenario_id,
            objective=new_feedback.objective,
            instructions=new_feedback.instructions,
            constraints=new_feedback.constraints,
            context=new_feedback.context,
            output_format=new_feedback.output_format,
            created_at=new_feedback.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("copy_feedback_failed", feedback_id=feedback_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to copy feedback")

