"""Admin endpoints for user management.

This module provides endpoints for administrators to manage users.
All endpoints require admin authentication.
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

from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.user import User
from app.schemas.auth import (
    UserCreate,
    UserResponse,
    DeleteUserResponse,
)
from app.schemas.agent import (
    AgentPersonalityCreate,
    AgentPersonalityUpdate,
    AgentPersonalityResponse,
    DeleteAgentPersonalityResponse,
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    DeleteAgentResponse,
)
from app.schemas.scenario import (
    ScenarioCreateRequest,
    ScenarioUpdateRequest,
    ScenarioAdminResponse,
    DeleteScenarioResponse,
)
from app.services.database import DatabaseService
from app.utils.auth import (
    create_access_token,
    verify_token,
)
from app.utils.sanitization import (
    sanitize_email,
    sanitize_string,
    validate_password_strength,
)

router = APIRouter()
security = HTTPBearer()
db_service = DatabaseService()


async def get_current_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Get the current admin user from the token.

    This function works with both session tokens and user tokens:
    - Session token (most common): Contains session_id, looks up session, then gets user
    - User token (after login, before session): Contains user_id directly

    Args:
        credentials: The HTTP authorization credentials containing the JWT token.

    Returns:
        User: The authenticated admin user.

    Raises:
        HTTPException: If the token is invalid, session/user is not found, or user is not an admin.
    """
    try:
        # Sanitize token
        token = sanitize_string(credentials.credentials)

        # The token contains either a user_id (from login) or session_id (from create_session)
        # Most requests use session tokens, so we'll try that first
        token_subject = verify_token(token)
        if token_subject is None:
            logger.error("invalid_token", token_part=token[:10] + "...")
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Sanitize the token subject
        token_subject = sanitize_string(token_subject)

        # Try to get it as a session first (most common case after login)
        session = await db_service.get_session(token_subject)
        
        if session:
            # Token is a session token - get user from session
            user = await db_service.get_user(session.user_id)
            if user is None:
                logger.error("user_not_found_from_session", session_id=token_subject, user_id=session.user_id)
                raise HTTPException(
                    status_code=404,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        else:
            # Token might be a user token (from login, before session created)
            # Try to parse it as a user_id
            try:
                user_id = int(token_subject)
                user = await db_service.get_user(user_id)
                if user is None:
                    logger.error("user_not_found", user_id=user_id)
                    raise HTTPException(
                        status_code=404,
                        detail="User not found",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
            except ValueError:
                # Not a session and not a valid user_id
                logger.error("invalid_token_subject", subject=token_subject)
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        # Verify user is an admin
        if not user.is_admin:
            logger.warning("unauthorized_admin_access_attempt", user_id=user.id)
            raise HTTPException(
                status_code=403,
                detail="Admin access required",
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


@router.get("/users", response_model=List[UserResponse])
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["get_all_users"][0])
async def list_users(request: Request, admin_user: User = Depends(get_current_admin_user)):
    """List all users in the system.

    Args:
        request: The FastAPI request object for rate limiting.
        admin_user: The authenticated admin user.

    Returns:
        List of user information (without passwords).
    """
    try:
        users = await db_service.get_all_users()
        return [
            UserResponse(
                id=user.id,
                email=user.email,
                is_admin=user.is_admin,
                created_at=user.created_at,
            )
            for user in users
        ]
    except Exception as e:
        logger.error("list_users_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve users")


@router.get("/users/{user_id}", response_model=UserResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["get_user_by_id"][0])
async def get_user(request: Request, user_id: int, admin_user: User = Depends(get_current_admin_user)):
    """Get a specific user by ID.

    Args:
        request: The FastAPI request object for rate limiting.
        user_id: The ID of the user to retrieve.
        admin_user: The authenticated admin user.

    Returns:
        User information (without password).
    """
    try:
        user = await db_service.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return UserResponse(
            id=user.id,
            email=user.email,
            is_admin=user.is_admin,
            created_at=user.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_user_failed", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve user")


@router.post("/users", response_model=UserResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["create_user"][0])
async def create_user(
    request: Request, user_data: UserCreate, admin_user: User = Depends(get_current_admin_user)
) -> UserResponse:
    """Create a new user (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        user_data: User creation data.
        admin_user: The authenticated admin user.

    Returns:
        Created user information.
    """
    try:
        # Sanitize email
        sanitized_email = sanitize_email(user_data.email)

        # Extract and validate password
        password = user_data.password.get_secret_value()
        validate_password_strength(password)

        # Check if user exists
        if await db_service.get_user_by_email(sanitized_email):
            raise HTTPException(status_code=400, detail="Email already registered")

        # Create user
        user = await db_service.create_user(email=sanitized_email, password=User.hash_password(password))

        logger.info("admin_created_user", admin_id=admin_user.id, new_user_id=user.id, email=sanitized_email)

        return UserResponse(
            id=user.id,
            email=user.email,
            is_admin=user.is_admin,
            created_at=user.created_at,
            token=create_access_token(str(user.id)),
        )
    except HTTPException:
        raise
    except ValueError as ve:
        logger.error("user_creation_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error("create_user_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create user")


@router.put("/users/{user_id}", response_model=UserResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["update_user"][0])
async def update_user(
    request: Request, user_id: int, email: str = None, is_admin: bool = None, admin_user: User = Depends(get_current_admin_user)
) -> UserResponse:
    """Update a user (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        user_id: The ID of the user to update.
        email: New email address (optional).
        is_admin: New admin status (optional).
        admin_user: The authenticated admin user.

    Returns:
        Updated user information.
    """
    try:
        user = await db_service.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Prevent admin from demoting themselves
        if user_id == admin_user.id and is_admin is False:
            raise HTTPException(status_code=400, detail="Cannot remove admin status from yourself")

        # Update fields
        updated = False
        if email is not None and email != user.email:
            sanitized_email = sanitize_email(email)
            # Check if new email is already taken
            existing_user = await db_service.get_user_by_email(sanitized_email)
            if existing_user and existing_user.id != user_id:
                raise HTTPException(status_code=400, detail="Email already in use")
            user = await db_service.update_user_email(user_id, sanitized_email)
            updated = True

        if is_admin is not None and is_admin != user.is_admin:
            user = await db_service.update_user_admin_status(user_id, is_admin)
            updated = True

        if updated:
            logger.info("admin_updated_user", admin_id=admin_user.id, updated_user_id=user_id)

        return UserResponse(
            id=user.id,
            email=user.email,
            is_admin=user.is_admin,
            created_at=user.created_at,
        )
    except HTTPException:
        raise
    except ValueError as ve:
        logger.error("user_update_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error("update_user_failed", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update user")


@router.delete("/users/{user_id}" , response_model=DeleteUserResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["delete_user"][0])
async def delete_user(request: Request, user_id: int, admin_user: User = Depends(get_current_admin_user)):
    """Delete a user and all their sessions (admin only).

    This endpoint first deletes all sessions associated with the user,
    then deletes the user account itself.

    Args:
        request: The FastAPI request object for rate limiting.
        user_id: The ID of the user to delete.
        admin_user: The authenticated admin user.

    Returns:
        Success message.
    """
    try:
        # Prevent admin from deleting themselves
        if user_id == admin_user.id:
            raise HTTPException(status_code=400, detail="Cannot delete your own account")

        user = await db_service.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # First, delete all sessions associated with this user
        user_sessions = await db_service.get_user_sessions(user_id)
        sessions_deleted = 0
        for session in user_sessions:
            await db_service.delete_session(session.id)
            sessions_deleted += 1

        logger.info("admin_deleted_user_sessions", admin_id=admin_user.id, user_id=user_id, sessions_deleted=sessions_deleted)

        # Then delete the user
        success = await db_service.delete_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")

        logger.info("admin_deleted_user", admin_id=admin_user.id, deleted_user_id=user_id, sessions_deleted=sessions_deleted)

        return DeleteUserResponse(message="User deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_user_failed", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete user")


# ========== AgentPersonality Endpoints ==========

@router.get("/agent-personalities", response_model=List[AgentPersonalityResponse])
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["get_all_agent_personalities"][0])
async def list_agent_personalities(request: Request, admin_user: User = Depends(get_current_admin_user)):
    """List all agent personalities in the system.

    Args:
        request: The FastAPI request object for rate limiting.
        admin_user: The authenticated admin user.

    Returns:
        List of agent personalities.
    """
    try:
        personalities = await db_service.get_all_agent_personalities()
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
        logger.error("list_agent_personalities_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve agent personalities")


@router.get("/agent-personalities/{personality_id}", response_model=AgentPersonalityResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["get_agent_personality_by_id"][0])
async def get_agent_personality(
    request: Request, personality_id: int, admin_user: User = Depends(get_current_admin_user)
):
    """Get a specific agent personality by ID.

    Args:
        request: The FastAPI request object for rate limiting.
        personality_id: The ID of the personality to retrieve.
        admin_user: The authenticated admin user.

    Returns:
        Agent personality information.
    """
    try:
        personality = await db_service.get_agent_personality(personality_id)
        if not personality:
            raise HTTPException(status_code=404, detail="Agent personality not found")

        return AgentPersonalityResponse(
            id=personality.id,
            name=personality.name,
            personality_description=personality.personality_description,
            created_at=personality.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_agent_personality_failed", personality_id=personality_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve agent personality")


@router.post("/agent-personalities", response_model=AgentPersonalityResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["create_agent_personality"][0])
async def create_agent_personality(
    request: Request, personality_data: AgentPersonalityCreate, admin_user: User = Depends(get_current_admin_user)
):
    """Create a new agent personality (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        personality_data: Agent personality creation data.
        admin_user: The authenticated admin user.

    Returns:
        Created agent personality information.
    """
    try:
        # Sanitize inputs
        name = sanitize_string(personality_data.name)
        description = sanitize_string(personality_data.personality_description)

        # Create personality
        personality = await db_service.create_agent_personality(
            name=name,
            personality_description=description,
        )

        logger.info("admin_created_agent_personality", admin_id=admin_user.id, personality_id=personality.id, name=name)

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
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["update_agent_personality"][0])
async def update_agent_personality(
    request: Request,
    personality_id: int,
    personality_data: AgentPersonalityUpdate,
    admin_user: User = Depends(get_current_admin_user),
):
    """Update an agent personality (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        personality_id: The ID of the personality to update.
        personality_data: Updated personality data.
        admin_user: The authenticated admin user.

    Returns:
        Updated agent personality information.
    """
    try:
        personality = await db_service.get_agent_personality(personality_id)
        if not personality:
            raise HTTPException(status_code=404, detail="Agent personality not found")

        # Update fields with sanitized values
        name = sanitize_string(personality_data.name) if personality_data.name else None
        description = sanitize_string(personality_data.personality_description) if personality_data.personality_description else None

        updated_personality = await db_service.update_agent_personality(
            personality_id=personality_id,
            name=name,
            personality_description=description,
        )

        logger.info("admin_updated_agent_personality", admin_id=admin_user.id, personality_id=personality_id)

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
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["delete_agent_personality"][0])
async def delete_agent_personality(
    request: Request, personality_id: int, admin_user: User = Depends(get_current_admin_user)
):
    """Delete an agent personality (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        personality_id: The ID of the personality to delete.
        admin_user: The authenticated admin user.

    Returns:
        Success message.
    """
    try:
        personality = await db_service.get_agent_personality(personality_id)
        if not personality:
            raise HTTPException(status_code=404, detail="Agent personality not found")

        success = await db_service.delete_agent_personality(personality_id)
        if not success:
            raise HTTPException(status_code=404, detail="Agent personality not found")

        logger.info("admin_deleted_agent_personality", admin_id=admin_user.id, personality_id=personality_id)

        return DeleteAgentPersonalityResponse(message="Agent personality deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_agent_personality_failed", personality_id=personality_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete agent personality")


# ========== Agent Endpoints ==========

@router.get("/agents", response_model=List[AgentResponse])
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["get_all_agents"][0])
async def list_agents(request: Request, admin_user: User = Depends(get_current_admin_user)):
    """List all agents in the system.

    Args:
        request: The FastAPI request object for rate limiting.
        admin_user: The authenticated admin user.

    Returns:
        List of agents.
    """
    try:
        agents = await db_service.get_all_agents()
        return [
            AgentResponse(
                id=a.id,
                name=a.name,
                scenario_id=a.scenario_id,
                agent_personality_id=a.agent_personality_id,
                voice=a.voice,
                display_text_color=a.display_text_color,
                objective=a.objective,
                instructions=a.instructions,
                constraints=a.constraints,
                context=a.context,
                created_at=a.created_at,
            )
            for a in agents
        ]
    except Exception as e:
        logger.error("list_agents_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve agents")


@router.get("/agents/{agent_id}", response_model=AgentResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["get_agent_by_id"][0])
async def get_agent(request: Request, agent_id: str, admin_user: User = Depends(get_current_admin_user)):
    """Get a specific agent by ID.

    Args:
        request: The FastAPI request object for rate limiting.
        agent_id: The ID of the agent to retrieve.
        admin_user: The authenticated admin user.

    Returns:
        Agent information.
    """
    try:
        agent = await db_service.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        return AgentResponse(
            id=agent.id,
            name=agent.name,
            scenario_id=agent.scenario_id,
            agent_personality_id=agent.agent_personality_id,
            voice=agent.voice,
            display_text_color=agent.display_text_color,
            objective=agent.objective,
            instructions=agent.instructions,
            constraints=agent.constraints,
            context=agent.context,
            created_at=agent.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_agent_failed", agent_id=agent_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve agent")


@router.post("/agents", response_model=AgentResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["create_agent"][0])
async def create_agent(
    request: Request, agent_data: AgentCreate, admin_user: User = Depends(get_current_admin_user)
):
    """Create a new agent (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        agent_data: Agent creation data.
        admin_user: The authenticated admin user.

    Returns:
        Created agent information.
    """
    try:
        # Sanitize inputs
        agent_id = sanitize_string(agent_data.id)
        name = sanitize_string(agent_data.name)
        voice = sanitize_string(agent_data.voice) if agent_data.voice else ""
        display_text_color = sanitize_string(agent_data.display_text_color) if agent_data.display_text_color else ""
        objective = sanitize_string(agent_data.objective) if agent_data.objective else ""
        instructions = sanitize_string(agent_data.instructions) if agent_data.instructions else ""
        constraints = sanitize_string(agent_data.constraints) if agent_data.constraints else ""
        context = sanitize_string(agent_data.context) if agent_data.context else ""

        # Verify scenario and personality exist
        scenario = await db_service.get_scenario(agent_data.scenario_id)
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")

        personality = await db_service.get_agent_personality(agent_data.agent_personality_id)
        if not personality:
            raise HTTPException(status_code=404, detail="Agent personality not found")

        # Create agent
        agent = await db_service.create_agent(
            agent_id=agent_id,
            name=name,
            scenario_id=agent_data.scenario_id,
            agent_personality_id=agent_data.agent_personality_id,
            voice=voice,
            display_text_color=display_text_color,
            objective=objective,
            instructions=instructions,
            constraints=constraints,
            context=context,
        )

        logger.info("admin_created_agent", admin_id=admin_user.id, agent_id=agent.id, name=name)

        return AgentResponse(
            id=agent.id,
            name=agent.name,
            scenario_id=agent.scenario_id,
            agent_personality_id=agent.agent_personality_id,
            voice=agent.voice,
            display_text_color=agent.display_text_color,
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
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["update_agent"][0])
async def update_agent(
    request: Request,
    agent_id: str,
    agent_data: AgentUpdate,
    admin_user: User = Depends(get_current_admin_user),
):
    """Update an agent (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        agent_id: The ID of the agent to update.
        agent_data: Updated agent data.
        admin_user: The authenticated admin user.

    Returns:
        Updated agent information.
    """
    try:
        agent = await db_service.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Verify scenario and personality exist if provided
        if agent_data.scenario_id is not None:
            scenario = await db_service.get_scenario(agent_data.scenario_id)
            if not scenario:
                raise HTTPException(status_code=404, detail="Scenario not found")

        if agent_data.agent_personality_id is not None:
            personality = await db_service.get_agent_personality(agent_data.agent_personality_id)
            if not personality:
                raise HTTPException(status_code=404, detail="Agent personality not found")

        # Update fields with sanitized values
        name = sanitize_string(agent_data.name) if agent_data.name else None
        voice = sanitize_string(agent_data.voice) if agent_data.voice else None
        display_text_color = sanitize_string(agent_data.display_text_color) if agent_data.display_text_color else None
        objective = sanitize_string(agent_data.objective) if agent_data.objective else None
        instructions = sanitize_string(agent_data.instructions) if agent_data.instructions else None
        constraints = sanitize_string(agent_data.constraints) if agent_data.constraints else None
        context = sanitize_string(agent_data.context) if agent_data.context else None

        updated_agent = await db_service.update_agent(
            agent_id=agent_id,
            name=name,
            voice=voice,
            display_text_color=display_text_color,
            objective=objective,
            instructions=instructions,
            constraints=constraints,
            context=context,
            scenario_id=agent_data.scenario_id,
            agent_personality_id=agent_data.agent_personality_id,
        )

        logger.info("admin_updated_agent", admin_id=admin_user.id, agent_id=agent_id)

        return AgentResponse(
            id=updated_agent.id,
            name=updated_agent.name,
            scenario_id=updated_agent.scenario_id,
            agent_personality_id=updated_agent.agent_personality_id,
            voice=updated_agent.voice,
            display_text_color=updated_agent.display_text_color,
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
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["delete_agent"][0])
async def delete_agent(request: Request, agent_id: str, admin_user: User = Depends(get_current_admin_user)):
    """Delete an agent (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        agent_id: The ID of the agent to delete.
        admin_user: The authenticated admin user.

    Returns:
        Success message.
    """
    try:
        agent = await db_service.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        success = await db_service.delete_agent(agent_id)
        if not success:
            raise HTTPException(status_code=404, detail="Agent not found")

        logger.info("admin_deleted_agent", admin_id=admin_user.id, agent_id=agent_id)

        return DeleteAgentResponse(message="Agent deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_agent_failed", agent_id=agent_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete agent")


# ========== Scenario Endpoints ==========

@router.get("/scenarios", response_model=List[ScenarioAdminResponse])
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["get_all_scenarios"][0])
async def list_scenarios(request: Request, admin_user: User = Depends(get_current_admin_user)):
    """List all scenarios in the system.

    Args:
        request: The FastAPI request object for rate limiting.
        admin_user: The authenticated admin user.

    Returns:
        List of scenarios.
    """
    try:
        scenarios = await db_service.get_all_scenarios()
        return [
            ScenarioAdminResponse(
                id=s.id,
                name=s.name,
                description=s.description,
                overview=s.overview,
                system_instructions=s.system_instructions,
                initial_prompt=s.initial_prompt,
                created_at=s.created_at,
            )
            for s in scenarios
        ]
    except Exception as e:
        logger.error("list_scenarios_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve scenarios")


@router.get("/scenarios/{scenario_id}", response_model=ScenarioAdminResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["get_scenario_by_id"][0])
async def get_scenario(request: Request, scenario_id: int, admin_user: User = Depends(get_current_admin_user)):
    """Get a specific scenario by ID.

    Args:
        request: The FastAPI request object for rate limiting.
        scenario_id: The ID of the scenario to retrieve.
        admin_user: The authenticated admin user.

    Returns:
        Scenario information.
    """
    try:
        scenario = await db_service.get_scenario(scenario_id)
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")

        return ScenarioAdminResponse(
            id=scenario.id,
            name=scenario.name,
            description=scenario.description,
            overview=scenario.overview,
            system_instructions=scenario.system_instructions,
            initial_prompt=scenario.initial_prompt,
            created_at=scenario.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_scenario_failed", scenario_id=scenario_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve scenario")


@router.post("/scenarios", response_model=ScenarioAdminResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["create_scenario"][0])
async def create_scenario(
    request: Request, scenario_data: ScenarioCreateRequest, admin_user: User = Depends(get_current_admin_user)
):
    """Create a new scenario (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        scenario_data: Scenario creation data.
        admin_user: The authenticated admin user.

    Returns:
        Created scenario information.
    """
    try:
        # Sanitize inputs
        name = sanitize_string(scenario_data.name)
        description = sanitize_string(scenario_data.description)
        overview = sanitize_string(scenario_data.overview)
        system_instructions = sanitize_string(scenario_data.system_instructions)
        initial_prompt = sanitize_string(scenario_data.initial_prompt)

        # Create scenario
        scenario = await db_service.create_scenario(
            name=name,
            description=description,
            overview=overview,
            system_instructions=system_instructions,
            initial_prompt=initial_prompt,
        )

        logger.info("admin_created_scenario", admin_id=admin_user.id, scenario_id=scenario.id, name=name)

        return ScenarioAdminResponse(
            id=scenario.id,
            name=scenario.name,
            description=scenario.description,
            overview=scenario.overview,
            system_instructions=scenario.system_instructions,
            initial_prompt=scenario.initial_prompt,
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
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["update_scenario"][0])
async def update_scenario(
    request: Request,
    scenario_id: int,
    scenario_data: ScenarioUpdateRequest,
    admin_user: User = Depends(get_current_admin_user),
):
    """Update a scenario (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        scenario_id: The ID of the scenario to update.
        scenario_data: Updated scenario data.
        admin_user: The authenticated admin user.

    Returns:
        Updated scenario information.
    """
    try:
        scenario = await db_service.get_scenario(scenario_id)
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")

        # Update fields with sanitized values
        name = sanitize_string(scenario_data.name) if scenario_data.name else None
        description = sanitize_string(scenario_data.description) if scenario_data.description else None
        overview = sanitize_string(scenario_data.overview) if scenario_data.overview else None
        system_instructions = sanitize_string(scenario_data.system_instructions) if scenario_data.system_instructions else None
        initial_prompt = sanitize_string(scenario_data.initial_prompt) if scenario_data.initial_prompt else None

        updated_scenario = await db_service.update_scenario(
            scenario_id=scenario_id,
            name=name,
            description=description,
            overview=overview,
            system_instructions=system_instructions,
            initial_prompt=initial_prompt,
        )

        logger.info("admin_updated_scenario", admin_id=admin_user.id, scenario_id=scenario_id)

        return ScenarioAdminResponse(
            id=updated_scenario.id,
            name=updated_scenario.name,
            description=updated_scenario.description,
            overview=updated_scenario.overview,
            system_instructions=updated_scenario.system_instructions,
            initial_prompt=updated_scenario.initial_prompt,
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
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["delete_scenario"][0])
async def delete_scenario(request: Request, scenario_id: int, admin_user: User = Depends(get_current_admin_user)):
    """Delete a scenario (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        scenario_id: The ID of the scenario to delete.
        admin_user: The authenticated admin user.

    Returns:
        Success message.
    """
    try:
        scenario = await db_service.get_scenario(scenario_id)
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")

        success = await db_service.delete_scenario(scenario_id)
        if not success:
            raise HTTPException(status_code=404, detail="Scenario not found")

        logger.info("admin_deleted_scenario", admin_id=admin_user.id, scenario_id=scenario_id)

        return DeleteScenarioResponse(message="Scenario deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_scenario_failed", scenario_id=scenario_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete scenario")

