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

