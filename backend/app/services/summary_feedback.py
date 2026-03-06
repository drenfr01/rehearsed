"""Shared summary feedback generation service.

Used by both the langgraph classroom flow and one-on-one Gemini Live sessions.
"""

from typing import Union

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.core.logging import logger
from app.core.prompts.feedback import format_feedback_instructions
from app.schemas.graph import SummaryFeedbackResponse
from app.services.database import database_service


async def generate_summary_feedback(
    scenario_id: int,
    conversation_messages: list[dict],
    llm=None,
) -> Union[SummaryFeedbackResponse, str]:
    """Generate summary feedback for a conversation.

    Args:
        scenario_id: The scenario ID to look up feedback configuration.
        conversation_messages: List of dicts with "role" ('user' | 'agent')
            and "text" keys representing the conversation transcript.
        llm: Optional pre-configured LLM instance. If not provided, a default
            is created for backward compatibility.

    Returns:
        A SummaryFeedbackResponse on success, or a fallback string on failure.
    """
    feedback = await database_service.feedback.get_feedback_by_type(
        "summary", scenario_id
    )

    if feedback is None:
        logger.warning("summary_feedback_not_found", scenario_id=scenario_id)
        return "No summary feedback configured for this scenario."

    system_instructions = format_feedback_instructions(
        objective=feedback.objective,
        instructions=feedback.instructions,
        constraints=feedback.constraints,
        context=feedback.context,
        output_format=feedback.output_format,
    )

    langchain_messages = [SystemMessage(content=system_instructions)]
    for msg in conversation_messages:
        text = msg.get("text", "")
        if not text:
            continue
        if msg.get("role") == "user":
            langchain_messages.append(HumanMessage(content=text))
        else:
            langchain_messages.append(AIMessage(content=text))

    if llm is None:
        llm = ChatGoogleGenerativeAI(
            model="gemini-3-pro-preview",
            temperature=settings.DEFAULT_LLM_TEMPERATURE,
            project=settings.GOOGLE_CLOUD_PROJECT,
            location=settings.GOOGLE_CLOUD_LOCATION,
            max_tokens=settings.MAX_TOKENS,
            vertexai=True,
            google_api_key=None,
        )

    response = await llm.with_structured_output(
        SummaryFeedbackResponse, method="json_schema", include_raw=True
    ).ainvoke(langchain_messages)

    if response["parsed"] is None:
        logger.error(
            "summary_feedback_generation_failed",
            error=response["raw"],
            exc_info=True,
        )
        return "Could not generate summary feedback"

    return response["parsed"]
