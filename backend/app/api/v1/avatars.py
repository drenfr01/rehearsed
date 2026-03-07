"""Avatar endpoints.

Provides a read-only list of available student avatars.
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

from app.api.v1.deps import get_database_service
from app.core.config import settings
from app.core.limiter import limiter
from app.services.database.base import DatabaseService

router = APIRouter()
security = HTTPBearer()


class AvatarResponse(BaseModel):
    """Response model for avatars."""
    id: int
    name: str
    file_path: str


@router.get("", response_model=List[AvatarResponse])
@limiter.limit("30 per minute")
async def get_avatars(
    request: Request,
    database_service: DatabaseService = Depends(get_database_service),
) -> List[AvatarResponse]:
    """Get all available student avatars."""
    avatars = await database_service.avatars.get_all_avatars()
    return [AvatarResponse(id=a.id, name=a.name, file_path=a.file_path) for a in avatars]
