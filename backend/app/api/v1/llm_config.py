"""Agent-LLM configuration endpoints.

Allows admins to view and update which LLM model each agent type uses.
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
from app.core.logging import logger
from app.models.agent_llm_config import AgentType
from app.models.user import User
from app.services.database.base import DatabaseService
from app.api.v1.chatbot import agent as langgraph_agent

router = APIRouter()
security = HTTPBearer()


class AgentLlmConfigResponse(BaseModel):
    agent_type: str
    llm_model_id: int
    llm_model_name: str


class AgentLlmConfigUpdateRequest(BaseModel):
    agent_type: str
    llm_model_id: int


@router.get("", response_model=List[AgentLlmConfigResponse])
@limiter.limit("30 per minute")
async def get_agent_llm_configs(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
) -> List[AgentLlmConfigResponse]:
    """Get all agent-to-LLM configurations."""
    configs = await database_service.agent_llm_config.get_all_configs()
    result = []
    for c in configs:
        model = await database_service.llm_models.get_model(c.llm_model_id)
        result.append(AgentLlmConfigResponse(
            agent_type=c.agent_type.value,
            llm_model_id=c.llm_model_id,
            llm_model_name=model.name if model else "unknown",
        ))
    return result


@router.post("", response_model=AgentLlmConfigResponse)
@limiter.limit("30 per minute")
async def update_agent_llm_config(
    request: Request,
    body: AgentLlmConfigUpdateRequest,
    current_user: User = Depends(get_current_admin_user),
    database_service: DatabaseService = Depends(get_database_service),
) -> AgentLlmConfigResponse:
    """Update the LLM model for a specific agent type.
    
    This also invalidates any cached LLM instances so the change
    takes effect on the next request.
    """
    config = await database_service.agent_llm_config.update_config(
        agent_type=body.agent_type,
        llm_model_id=body.llm_model_id,
    )
    model = await database_service.llm_models.get_model(config.llm_model_id)

    # Invalidate cached LLMs so the new model is picked up
    langgraph_agent.invalidate_llms()
    logger.info(
        "llm_config_updated_by_admin",
        admin_user_id=current_user.id,
        agent_type=body.agent_type,
        new_model=model.name if model else "unknown",
    )

    return AgentLlmConfigResponse(
        agent_type=config.agent_type.value,
        llm_model_id=config.llm_model_id,
        llm_model_name=model.name if model else "unknown",
    )
