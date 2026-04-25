"""Centralized LLM chat model factory.

All ChatGoogleGenerativeAI construction goes through create_chat_llm
so that Vertex kwargs, environment-specific tuning, and tool binding
are configured in one place.
"""

from typing import Any, Dict

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import Environment, settings
from app.core.langgraph.tools import tools


def _get_model_kwargs() -> Dict[str, Any]:
    """Return environment-specific model kwargs."""
    if settings.ENVIRONMENT == Environment.DEVELOPMENT:
        return {"top_p": 0.8}
    if settings.ENVIRONMENT == Environment.PRODUCTION:
        return {
            "top_p": 0.95,
            "presence_penalty": 0.1,
            "frequency_penalty": 0.1,
        }
    return {}


def create_chat_llm(
    model_name: str,
    *,
    bind_tools: bool = False,
) -> BaseChatModel:
    """Create a configured ChatGoogleGenerativeAI instance.

    Args:
        model_name: The Gemini model name (e.g. "gemini-3-flash-preview").
        bind_tools: If True, bind the LangGraph tool definitions to the model.

    Returns:
        A BaseChatModel ready for invocation.
    """
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=settings.DEFAULT_LLM_TEMPERATURE,
        project=settings.GOOGLE_CLOUD_PROJECT,
        location=settings.GOOGLE_CLOUD_LOCATION,
        max_tokens=settings.MAX_TOKENS,
        vertexai=True,
        google_api_key=None,
        **_get_model_kwargs(),
    )
    if bind_tools:
        llm = llm.bind_tools(tools)
    return llm
