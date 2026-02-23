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
    DeleteAgentPersonalityResponse,
    DeleteAgentResponse,
)
from app.schemas.auth import (
    DeleteUserResponse,
    UserCreate,
    UserResponse,
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


async def get_current_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    database_service: DatabaseService = Depends(get_database_service),
) -> User:
    """Get the current admin user from the token.

    This function works with both session tokens and user tokens:
    - Session token (most common): Contains session_id, looks up session, then gets user
    - User token (after login, before session): Contains user_id directly

    Args:
        credentials: The HTTP authorization credentials containing the JWT token.
        database_service: The database service instance.

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
        session = await database_service.sessions.get_session(token_subject)
        
        if session:
            # Token is a session token - get user from session
            user = await database_service.users.get_user(session.user_id)
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
                user = await database_service.users.get_user(user_id)
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
async def list_users(
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """List all users in the system.

    Args:
        request: The FastAPI request object for rate limiting.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        List of user information (without passwords).
    """
    try:
        users = await database_service.users.get_all_users()
        return [
            UserResponse(
                id=user.id,
                email=user.email,
                is_admin=user.is_admin,
                is_approved=user.is_approved,
                created_at=user.created_at,
            )
            for user in users
        ]
    except Exception as e:
        logger.error("list_users_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve users")


@router.get("/users/pending", response_model=List[UserResponse])
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["get_pending_users"][0])
async def list_pending_users(
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """List all users pending approval.

    Args:
        request: The FastAPI request object for rate limiting.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        List of pending user information (without passwords).
    """
    try:
        users = await database_service.users.get_pending_users()
        return [
            UserResponse(
                id=user.id,
                email=user.email,
                is_admin=user.is_admin,
                is_approved=user.is_approved,
                created_at=user.created_at,
            )
            for user in users
        ]
    except Exception as e:
        logger.error("list_pending_users_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve pending users")


@router.get("/users/{user_id}", response_model=UserResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["get_user_by_id"][0])
async def get_user(
    request: Request,
    user_id: int,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Get a specific user by ID.

    Args:
        request: The FastAPI request object for rate limiting.
        user_id: The ID of the user to retrieve.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        User information (without password).
    """
    try:
        user = await database_service.users.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return UserResponse(
            id=user.id,
            email=user.email,
            is_admin=user.is_admin,
            is_approved=user.is_approved,
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
    request: Request,
    user_data: UserCreate,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
) -> UserResponse:
    """Create a new user (admin only).

    Users created by an admin are automatically approved.

    Args:
        request: The FastAPI request object for rate limiting.
        user_data: User creation data.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

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
        if await database_service.users.get_user_by_email(sanitized_email):
            raise HTTPException(status_code=400, detail="Email already registered")

        # Create user - admin-created users are automatically approved
        user = await database_service.users.create_user(
            email=sanitized_email,
            password=User.hash_password(password),
            is_approved=True,
        )

        logger.info("admin_created_user", admin_id=admin_user.id, new_user_id=user.id, email=sanitized_email)

        return UserResponse(
            id=user.id,
            email=user.email,
            is_admin=user.is_admin,
            is_approved=user.is_approved,
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
    request: Request,
    user_id: int,
    email: str = None,
    is_admin: bool = None,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
) -> UserResponse:
    """Update a user (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        user_id: The ID of the user to update.
        email: New email address (optional).
        is_admin: New admin status (optional).
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        Updated user information.
    """
    try:
        user = await database_service.users.get_user(user_id)
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
            existing_user = await database_service.users.get_user_by_email(sanitized_email)
            if existing_user and existing_user.id != user_id:
                raise HTTPException(status_code=400, detail="Email already in use")
            user = await database_service.users.update_user_email(user_id, sanitized_email)
            updated = True

        if is_admin is not None and is_admin != user.is_admin:
            user = await database_service.users.update_user_admin_status(user_id, is_admin)
            updated = True

        if updated:
            logger.info("admin_updated_user", admin_id=admin_user.id, updated_user_id=user_id)

        return UserResponse(
            id=user.id,
            email=user.email,
            is_admin=user.is_admin,
            is_approved=user.is_approved,
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


@router.post("/users/{user_id}/approve", response_model=UserResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["approve_user"][0])
async def approve_user(
    request: Request,
    user_id: int,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Approve a pending user account (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        user_id: The ID of the user to approve.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        Approved user information.
    """
    try:
        user = await database_service.users.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.is_approved:
            raise HTTPException(status_code=400, detail="User is already approved")

        user = await database_service.users.approve_user(user_id)

        logger.info("admin_approved_user", admin_id=admin_user.id, approved_user_id=user_id, email=user.email)

        return UserResponse(
            id=user.id,
            email=user.email,
            is_admin=user.is_admin,
            is_approved=user.is_approved,
            created_at=user.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("approve_user_failed", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to approve user")


@router.post("/users/{user_id}/reject", response_model=DeleteUserResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["reject_user"][0])
async def reject_user(
    request: Request,
    user_id: int,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Reject and delete a pending user account (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        user_id: The ID of the user to reject.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        Success message.
    """
    try:
        user = await database_service.users.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.is_approved:
            raise HTTPException(status_code=400, detail="Cannot reject an already approved user. Use delete instead.")

        # Delete the pending user
        success = await database_service.users.delete_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")

        logger.info("admin_rejected_user", admin_id=admin_user.id, rejected_user_id=user_id, email=user.email)

        return DeleteUserResponse(message="User rejected and deleted")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("reject_user_failed", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to reject user")


@router.delete("/users/{user_id}" , response_model=DeleteUserResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["delete_user"][0])
async def delete_user(
    request: Request,
    user_id: int,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Delete a user and all their sessions (admin only).

    This endpoint first deletes all sessions associated with the user,
    then deletes the user account itself.

    Args:
        request: The FastAPI request object for rate limiting.
        user_id: The ID of the user to delete.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        Success message.
    """
    try:
        # Prevent admin from deleting themselves
        if user_id == admin_user.id:
            raise HTTPException(status_code=400, detail="Cannot delete your own account")

        user = await database_service.users.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # First, delete all sessions associated with this user
        user_sessions = await database_service.users.get_user_sessions(user_id)
        sessions_deleted = 0
        for session in user_sessions:
            await database_service.sessions.delete_session(session.id)
            sessions_deleted += 1

        logger.info("admin_deleted_user_sessions", admin_id=admin_user.id, user_id=user_id, sessions_deleted=sessions_deleted)

        # Then delete the user
        success = await database_service.users.delete_user(user_id)
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
async def list_agent_personalities(
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """List all agent personalities in the system.

    Args:
        request: The FastAPI request object for rate limiting.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        List of agent personalities.
    """
    try:
        personalities = await database_service.agents.get_all_agent_personalities()
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
    request: Request,
    personality_id: int,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Get a specific agent personality by ID.

    Args:
        request: The FastAPI request object for rate limiting.
        personality_id: The ID of the personality to retrieve.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        Agent personality information.
    """
    try:
        personality = await database_service.agents.get_agent_personality(personality_id)
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
    request: Request,
    personality_data: AgentPersonalityCreate,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Create a new agent personality (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        personality_data: Agent personality creation data.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        Created agent personality information.
    """
    try:
        # Sanitize inputs
        name = sanitize_string(personality_data.name)

        # Create personality
        personality = await database_service.agents.create_agent_personality(
            name=name,
            personality_description=personality_data.personality_description,
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
    database_service: DatabaseService = Depends(get_database_service),
):
    """Update an agent personality (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        personality_id: The ID of the personality to update.
        personality_data: Updated personality data.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        Updated agent personality information.
    """
    try:
        personality = await database_service.agents.get_agent_personality(personality_id)
        if not personality:
            raise HTTPException(status_code=404, detail="Agent personality not found")

        # Update fields with sanitized values
        name = sanitize_string(personality_data.name) if personality_data.name else None

        updated_personality = await database_service.agents.update_agent_personality(
            personality_id=personality_id,
            name=name,
            personality_description=personality_data.personality_description,
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
    request: Request,
    personality_id: int,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Delete an agent personality (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        personality_id: The ID of the personality to delete.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        Success message.
    """
    try:
        personality = await database_service.agents.get_agent_personality(personality_id)
        if not personality:
            raise HTTPException(status_code=404, detail="Agent personality not found")

        success = await database_service.agents.delete_agent_personality(personality_id)
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
async def list_agents(
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """List all agents in the system.

    Args:
        request: The FastAPI request object for rate limiting.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        List of agents.
    """
    try:
        agents = await database_service.agents.get_all_agents()
        return [
            AgentResponse(
                id=a.id,
                name=a.name,
                scenario_id=a.scenario_id,
                agent_personality_id=a.agent_personality_id,
                voice=a.voice.voice_name if a.voice else "",
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
async def get_agent(
    request: Request,
    agent_id: str,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Get a specific agent by ID.

    Args:
        request: The FastAPI request object for rate limiting.
        agent_id: The ID of the agent to retrieve.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        Agent information.
    """
    try:
        agent = await database_service.agents.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        return AgentResponse(
            id=agent.id,
            name=agent.name,
            scenario_id=agent.scenario_id,
            agent_personality_id=agent.agent_personality_id,
            voice=agent.voice.voice_name if agent.voice else "",
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
    request: Request,
    agent_data: AgentCreate,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Create a new agent (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        agent_data: Agent creation data.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        Created agent information.
    """
    try:
        # Sanitize identifier inputs only
        agent_id = sanitize_string(agent_data.id)
        name = sanitize_string(agent_data.name)
        voice_name = sanitize_string(agent_data.voice) if agent_data.voice else ""
        display_text_color = sanitize_string(agent_data.display_text_color) if agent_data.display_text_color else ""
        
        # Note: Not sanitizing prompt content fields (objective, instructions, etc.)
        # as they are system prompts for LLMs, not user-facing HTML content.
        # HTML escaping would corrupt apostrophes, quotes, and other valid characters.

        # Verify scenario and personality exist
        scenario = await database_service.scenarios.get_scenario(agent_data.scenario_id)
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")

        personality = await database_service.agents.get_agent_personality(agent_data.agent_personality_id)
        if not personality:
            raise HTTPException(status_code=404, detail="Agent personality not found")

        # Look up voice_id from voice name if provided
        voice_id = None
        if voice_name:
            voice = await database_service.agents.get_agent_voice_by_name(voice_name)
            if not voice:
                raise HTTPException(status_code=404, detail=f"Voice '{voice_name}' not found")
            voice_id = voice.id

        # Create agent
        agent = await database_service.agents.create_agent(
            agent_id=agent_id,
            name=name,
            scenario_id=agent_data.scenario_id,
            agent_personality_id=agent_data.agent_personality_id,
            voice_id=voice_id,
            display_text_color=display_text_color,
            objective=agent_data.objective or "",
            instructions=agent_data.instructions or "",
            constraints=agent_data.constraints or "",
            context=agent_data.context or "",
        )

        # Invalidate the graph for this scenario so it gets rebuilt with the new agent
        await langgraph_agent.invalidate_graph(agent_data.scenario_id)
        logger.info("admin_created_agent", admin_id=admin_user.id, agent_id=agent.id, name=name, scenario_id=agent_data.scenario_id)

        return AgentResponse(
            id=agent.id,
            name=agent.name,
            scenario_id=agent.scenario_id,
            agent_personality_id=agent.agent_personality_id,
            voice=agent.voice.voice_name if agent.voice else "",
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
    database_service: DatabaseService = Depends(get_database_service),
):
    """Update an agent (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        agent_id: The ID of the agent to update.
        agent_data: Updated agent data.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        Updated agent information.
    """
    try:
        agent = await database_service.agents.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Verify scenario and personality exist if provided
        if agent_data.scenario_id is not None:
            scenario = await database_service.scenarios.get_scenario(agent_data.scenario_id)
            if not scenario:
                raise HTTPException(status_code=404, detail="Scenario not found")

        if agent_data.agent_personality_id is not None:
            personality = await database_service.agents.get_agent_personality(agent_data.agent_personality_id)
            if not personality:
                raise HTTPException(status_code=404, detail="Agent personality not found")

        # Sanitize identifier fields only
        name = sanitize_string(agent_data.name) if agent_data.name else None
        voice_name = sanitize_string(agent_data.voice) if agent_data.voice else None
        display_text_color = sanitize_string(agent_data.display_text_color) if agent_data.display_text_color else None
        
        # Note: Not sanitizing prompt content fields (objective, instructions, etc.)
        # as they are system prompts for LLMs, not user-facing HTML content.
        # HTML escaping would corrupt apostrophes, quotes, and other valid characters.

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

        # Remember old scenario_id for graph invalidation
        old_scenario_id = agent.scenario_id
        
        updated_agent = await database_service.agents.update_agent(
            agent_id=agent_id,
            name=name,
            voice_id=voice_id,
            display_text_color=display_text_color,
            objective=agent_data.objective,
            instructions=agent_data.instructions,
            constraints=agent_data.constraints,
            context=agent_data.context,
            scenario_id=agent_data.scenario_id,
            agent_personality_id=agent_data.agent_personality_id,
            clear_voice=clear_voice,
        )

        # Invalidate the graph for affected scenarios
        # Always invalidate the current scenario
        await langgraph_agent.invalidate_graph(updated_agent.scenario_id)
        
        # If scenario changed, also invalidate the old scenario's graph
        if agent_data.scenario_id is not None and agent_data.scenario_id != old_scenario_id:
            await langgraph_agent.invalidate_graph(old_scenario_id)
            
        logger.info("admin_updated_agent", admin_id=admin_user.id, agent_id=agent_id, scenario_id=updated_agent.scenario_id)

        return AgentResponse(
            id=updated_agent.id,
            name=updated_agent.name,
            scenario_id=updated_agent.scenario_id,
            agent_personality_id=updated_agent.agent_personality_id,
            voice=updated_agent.voice.voice_name if updated_agent.voice else "",
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
async def delete_agent(
    request: Request,
    agent_id: str,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Delete an agent (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        agent_id: The ID of the agent to delete.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        Success message.
    """
    try:
        agent = await database_service.agents.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Remember scenario_id before deletion for graph invalidation
        scenario_id = agent.scenario_id
        
        success = await database_service.agents.delete_agent(agent_id)
        if not success:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Invalidate the graph for this scenario so it gets rebuilt without the deleted agent
        await langgraph_agent.invalidate_graph(scenario_id)
        logger.info("admin_deleted_agent", admin_id=admin_user.id, agent_id=agent_id, scenario_id=scenario_id)

        return DeleteAgentResponse(message="Agent deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_agent_failed", agent_id=agent_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete agent")


# ========== Scenario Endpoints ==========

@router.get("/scenarios", response_model=List[ScenarioAdminResponse])
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["get_all_scenarios"][0])
async def list_scenarios(
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """List all scenarios in the system.

    Args:
        request: The FastAPI request object for rate limiting.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        List of scenarios.
    """
    try:
        scenarios = await database_service.scenarios.get_all_scenarios()
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
        logger.error("list_scenarios_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve scenarios")


@router.get("/scenarios/{scenario_id}", response_model=ScenarioAdminResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["get_scenario_by_id"][0])
async def get_scenario(
    request: Request,
    scenario_id: int,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Get a specific scenario by ID.

    Args:
        request: The FastAPI request object for rate limiting.
        scenario_id: The ID of the scenario to retrieve.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        Scenario information.
    """
    try:
        scenario = await database_service.scenarios.get_scenario(scenario_id)
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")

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
    except Exception as e:
        logger.error("get_scenario_failed", scenario_id=scenario_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve scenario")


@router.post("/scenarios", response_model=ScenarioAdminResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["create_scenario"][0])
async def create_scenario(
    request: Request,
    scenario_data: ScenarioCreateRequest,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Create a new scenario (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        scenario_data: Scenario creation data.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        Created scenario information.
    """
    try:
        # Sanitize identifier fields only
        name = sanitize_string(scenario_data.name)
        
        # Note: Not sanitizing content fields (description, overview, system_instructions, initial_prompt)
        # as they may contain LLM prompts. HTML escaping would corrupt apostrophes, quotes, and other valid characters.

        # Create scenario
        scenario = await database_service.scenarios.create_scenario(
            name=name,
            description=scenario_data.description,
            overview=scenario_data.overview,
            system_instructions=scenario_data.system_instructions,
            initial_prompt=scenario_data.initial_prompt,
            teaching_objectives=scenario_data.teaching_objectives,
        )

        logger.info("admin_created_scenario", admin_id=admin_user.id, scenario_id=scenario.id, name=name)

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
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["update_scenario"][0])
async def update_scenario(
    request: Request,
    scenario_id: int,
    scenario_data: ScenarioUpdateRequest,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Update a scenario (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        scenario_id: The ID of the scenario to update.
        scenario_data: Updated scenario data.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        Updated scenario information.
    """
    try:
        scenario = await database_service.scenarios.get_scenario(scenario_id)
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")

        # Sanitize identifier fields only
        name = sanitize_string(scenario_data.name) if scenario_data.name else None
        
        # Note: Not sanitizing content fields (description, overview, system_instructions, initial_prompt)
        # as they may contain LLM prompts. HTML escaping would corrupt apostrophes, quotes, and other valid characters.

        updated_scenario = await database_service.scenarios.update_scenario(
            scenario_id=scenario_id,
            name=name,
            description=scenario_data.description,
            overview=scenario_data.overview,
            system_instructions=scenario_data.system_instructions,
            initial_prompt=scenario_data.initial_prompt,
            teaching_objectives=scenario_data.teaching_objectives,
        )

        logger.info("admin_updated_scenario", admin_id=admin_user.id, scenario_id=scenario_id)

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
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["delete_scenario"][0])
async def delete_scenario(
    request: Request,
    scenario_id: int,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Delete a scenario (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        scenario_id: The ID of the scenario to delete.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        Success message.
    """
    try:
        scenario = await database_service.scenarios.get_scenario(scenario_id)
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")

        success = await database_service.scenarios.delete_scenario(scenario_id)
        if not success:
            raise HTTPException(status_code=404, detail="Scenario not found")

        logger.info("admin_deleted_scenario", admin_id=admin_user.id, scenario_id=scenario_id)

        return DeleteScenarioResponse(message="Scenario deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_scenario_failed", scenario_id=scenario_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete scenario")


# ========== Feedback Endpoints ==========

@router.get("/feedback", response_model=List[FeedbackResponse])
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["get_all_feedback"][0])
async def list_feedback(
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """List all feedback in the system.

    Args:
        request: The FastAPI request object for rate limiting.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        List of feedback.
    """
    try:
        feedbacks = await database_service.feedback.get_all_feedback()
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
        logger.error("list_feedback_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve feedback")


@router.get("/feedback/{feedback_id}", response_model=FeedbackResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["get_feedback_by_id"][0])
async def get_feedback(
    request: Request,
    feedback_id: int,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Get a specific feedback by ID.

    Args:
        request: The FastAPI request object for rate limiting.
        feedback_id: The ID of the feedback to retrieve.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        Feedback information.
    """
    try:
        feedback = await database_service.feedback.get_feedback(feedback_id)
        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")

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
    except Exception as e:
        logger.error("get_feedback_failed", feedback_id=feedback_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve feedback")


@router.post("/feedback", response_model=FeedbackResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["create_feedback"][0])
async def create_feedback(
    request: Request,
    feedback_data: FeedbackCreate,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Create a new feedback (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        feedback_data: Feedback creation data.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        Created feedback information.
    """
    try:
        # Note: Not sanitizing prompt content fields (objective, instructions, etc.)
        # as they are system prompts for LLMs, not user-facing HTML content.
        # HTML escaping would corrupt apostrophes, quotes, and other valid characters.

        # Create feedback
        feedback = await database_service.feedback.create_feedback(
            feedback_type=feedback_data.feedback_type,
            scenario_id=feedback_data.scenario_id,
            objective=feedback_data.objective,
            instructions=feedback_data.instructions,
            constraints=feedback_data.constraints,
            context=feedback_data.context,
            output_format=feedback_data.output_format or "",
        )

        logger.info("admin_created_feedback", admin_id=admin_user.id, feedback_id=feedback.id, scenario_id=feedback.scenario_id)

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
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["update_feedback"][0])
async def update_feedback(
    request: Request,
    feedback_id: int,
    feedback_data: FeedbackUpdate,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Update a feedback (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        feedback_id: The ID of the feedback to update.
        feedback_data: Updated feedback data.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        Updated feedback information.
    """
    try:
        feedback = await database_service.feedback.get_feedback(feedback_id)
        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")

        # Note: Not sanitizing prompt content fields (objective, instructions, etc.)
        # as they are system prompts for LLMs, not user-facing HTML content.
        # HTML escaping would corrupt apostrophes, quotes, and other valid characters.

        updated_feedback = await database_service.feedback.update_feedback(
            feedback_id=feedback_id,
            feedback_type=feedback_data.feedback_type,
            scenario_id=feedback_data.scenario_id,
            objective=feedback_data.objective,
            instructions=feedback_data.instructions,
            constraints=feedback_data.constraints,
            context=feedback_data.context,
            output_format=feedback_data.output_format,
        )

        logger.info("admin_updated_feedback", admin_id=admin_user.id, feedback_id=feedback_id)

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
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["delete_feedback"][0])
async def delete_feedback(
    request: Request,
    feedback_id: int,
    admin_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
):
    """Delete a feedback (admin only).

    Args:
        request: The FastAPI request object for rate limiting.
        feedback_id: The ID of the feedback to delete.
        admin_user: The authenticated admin user.
        database_service: The database service instance.

    Returns:
        Success message.
    """
    try:
        feedback = await database_service.feedback.get_feedback(feedback_id)
        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")

        success = await database_service.feedback.delete_feedback(feedback_id)
        if not success:
            raise HTTPException(status_code=404, detail="Feedback not found")

        logger.info("admin_deleted_feedback", admin_id=admin_user.id, feedback_id=feedback_id)

        return DeleteFeedbackResponse(message="Feedback deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_feedback_failed", feedback_id=feedback_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete feedback")

