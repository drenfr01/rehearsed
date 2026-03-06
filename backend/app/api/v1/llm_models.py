"""LLM model endpoints.

Provides a read-only list of available LLM models.
Requires admin authentication.
"""

from typing import List

from fastapi import (
    APIRouter,
    Depends,
    Request,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from pydantic import BaseModel

from app.api.v1.admin import get_current_admin_user
from app.api.v1.deps import get_database_service
from app.core.config import settings
from app.core.limiter import limiter
from app.models.user import User
from app.services.database.base import DatabaseService

router = APIRouter()
security = HTTPBearer()


class LlmModelResponse(BaseModel):
    """Response model for LLM models."""
    id: int
    name: str


@router.get("", response_model=List[LlmModelResponse])
@limiter.limit("30 per minute")
async def get_llm_models(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
) -> List[LlmModelResponse]:
    """Get all available LLM models."""
    models = await database_service.llm_models.get_all_models()
    return [LlmModelResponse(id=m.id, name=m.name) for m in models]
