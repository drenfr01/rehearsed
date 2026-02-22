"""This file contains the LangGraph Agent/workflow and interactions with the LLM."""

import asyncio
import uuid
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Literal,
    Optional,
)
from urllib.parse import quote_plus

from asgiref.sync import sync_to_async
from langchain_core.messages import (
    BaseMessage,
    ToolMessage,
    convert_to_openai_messages,
)
from langchain_google_genai import ChatGoogleGenerativeAI
from langfuse import propagate_attributes, observe
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StateSnapshot, Command
from psycopg_pool import AsyncConnectionPool

from app.core.config import (
    Environment,
    settings,
)
from app.core.langgraph.graph import LangGraphBuilder
from app.core.langgraph.tools import tools
from app.core.logging import logger
from app.core.metrics import llm_inference_duration_seconds
from app.core.prompts import SYSTEM_PROMPT
from app.schemas import (
    ChatResponse,
    GraphState,
    Message,
)
from app.services.feedback_cache import feedback_cache, generate_feedback_and_store
from app.services.gemini_text_to_speech import GeminiTextToSpeech
from app.utils import (
    dump_messages,
    prepare_messages,
)


def _extract_token_text(content: str | list) -> str:
    """Normalise a LangChain message chunk's content to a plain string.

    Gemini's LangChain adapter can return ``content`` as either a plain ``str``
    or a list of content-part dicts such as ``[{"type": "text", "text": "…"}]``.
    This helper handles both shapes so callers can always concatenate safely.
    """
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return content or ""


class LangGraphAgent:
    """Manages the LangGraph Agent/workflow and interactions with the LLM.

    This class handles the creation and management of the LangGraph workflow,
    including LLM interactions, database connections, and response processing.
    Graphs are created per-scenario to support dynamic student agents.
    """

    def __init__(self):
        """Initialize the LangGraph Agent with necessary components."""
        self._llm = None
        self.tools_by_name = {tool.name: tool for tool in tools}
        self._connection_pool: Optional[AsyncConnectionPool] = None
        # Store graphs per scenario_id for dynamic agent support
        self._graphs: Dict[int, CompiledStateGraph] = {}
        # Keep _graph for backwards compatibility (default scenario)
        self._current_scenario_id: Optional[int] = None

    @property
    def llm(self):
        """Lazy-load the LLM on first access."""
        if self._llm is None:
            # Use environment-specific LLM model
            # Explicitly set google_api_key=None when using Vertex AI to prevent
            # the library from falling back to Generative Language API
            self._llm = ChatGoogleGenerativeAI(
                model=settings.LLM_MODEL,
                temperature=settings.DEFAULT_LLM_TEMPERATURE,
                project=settings.GOOGLE_CLOUD_PROJECT,
                location=settings.GOOGLE_CLOUD_LOCATION,
                max_tokens=settings.MAX_TOKENS,
                vertexai=True,
                google_api_key=None,  # Explicitly disable API key to force Vertex AI usage
                **self._get_model_kwargs(),
            ).bind_tools(tools)
            logger.info("llm_initialized", model=settings.LLM_MODEL, environment=settings.ENVIRONMENT.value)
        return self._llm

    def _get_model_kwargs(self) -> Dict[str, Any]:
        """Get environment-specific model kwargs.

        Returns:
            Dict[str, Any]: Additional model arguments based on environment
        """
        model_kwargs = {}

        # Development - we can use lower speeds for cost savings
        if settings.ENVIRONMENT == Environment.DEVELOPMENT:
            model_kwargs["top_p"] = 0.8

        # Production - use higher quality settings
        elif settings.ENVIRONMENT == Environment.PRODUCTION:
            model_kwargs["top_p"] = 0.95
            model_kwargs["presence_penalty"] = 0.1
            model_kwargs["frequency_penalty"] = 0.1

        return model_kwargs

    @observe(name="get_connection_pool")
    async def _get_connection_pool(self) -> AsyncConnectionPool:
        """Get a PostgreSQL connection pool using environment-specific settings.

        Returns:
            AsyncConnectionPool: A connection pool for PostgreSQL database.
        """
        if self._connection_pool is None:
            try:
                # Configure pool size based on environment
                max_size = settings.POSTGRES_POOL_SIZE

                if settings.ENVIRONMENT == Environment.PRODUCTION:
                    # Note: psycopg_pool uses libpq connection strings, NOT SQLAlchemy URLs
                    # So we use 'postgresql://' here, not 'postgresql+psycopg2://'
                    connection_url = (
                    f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
                    f"@/rehearsed?host=/cloudsql/{settings.POSTGRES_HOST}"
                    )

                else:
                    connection_url = (
                        "postgresql://"
                        f"{quote_plus(settings.POSTGRES_USER)}:{quote_plus(settings.POSTGRES_PASSWORD)}"
                        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
                    )

                self._connection_pool = AsyncConnectionPool(
                    connection_url,
                    open=False,
                    max_size=max_size,
                    kwargs={
                        "autocommit": True,
                        "connect_timeout": 5,
                        "prepare_threshold": None,
                    },
                )
                await self._connection_pool.open()
                logger.info("connection_pool_created", max_size=max_size, environment=settings.ENVIRONMENT.value)
            except Exception as e:
                logger.error("connection_pool_creation_failed", error=str(e), environment=settings.ENVIRONMENT.value)
                # In production, we might want to degrade gracefully
                if settings.ENVIRONMENT == Environment.PRODUCTION:
                    logger.warning("continuing_without_connection_pool", environment=settings.ENVIRONMENT.value)
                    return None
                raise e
        return self._connection_pool

    @observe(name="chat_llm_call")
    async def _chat(self, state: GraphState) -> dict:
        """Process the chat state and generate a response.

        Args:
            state (GraphState): The current state of the conversation.

        Returns:
            dict: Updated state with new messages.
        """
        messages = prepare_messages(state.messages, self.llm)

        llm_calls_num = 0

        # Configure retry attempts based on environment
        max_retries = settings.MAX_LLM_CALL_RETRIES

        for attempt in range(max_retries):
            try:
                with llm_inference_duration_seconds.labels(model=self.llm.model).time():
                    generated_state = {"messages": [await self.llm.ainvoke(dump_messages(messages))]}
                logger.info(
                    "llm_response_generated",
                    session_id=state.session_id,
                    llm_calls_num=llm_calls_num + 1,
                    model=settings.LLM_MODEL,
                    environment=settings.ENVIRONMENT.value,
                )
                return generated_state
            # TODO: make this a specific exception
            except Exception as e:
                logger.error(
                    "llm_call_failed",
                    llm_calls_num=llm_calls_num,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e),
                    environment=settings.ENVIRONMENT.value,
                )
                llm_calls_num += 1

                # In production, we might want to fall back to a more reliable model
                if settings.ENVIRONMENT == Environment.PRODUCTION and attempt == max_retries - 2:
                    fallback_model = "models/gemini-3-flash-preview"
                    logger.warning(
                        "using_fallback_model", model=fallback_model, environment=settings.ENVIRONMENT.value
                    )
                    self.llm.model = fallback_model

                continue

        raise Exception(f"Failed to get a response from the LLM after {max_retries} attempts")

    # Define our tool node
    async def _tool_call(self, state: GraphState) -> GraphState:
        """Process tool calls from the last message.

        Args:
            state: The current agent state containing messages and tool calls.

        Returns:
            Dict with updated messages containing tool responses.
        """
        outputs = []
        for tool_call in state.messages[-1].tool_calls:
            tool_result = await self.tools_by_name[tool_call["name"]].ainvoke(tool_call["args"])
            outputs.append(
                ToolMessage(
                    content=tool_result,
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        return {"messages": outputs}

    def _should_continue(self, state: GraphState) -> Literal["end", "continue"]:
        """Determine if the agent should continue or end based on the last message.

        Args:
            state: The current agent state containing messages.

        Returns:
            Literal["end", "continue"]: "end" if there are no tool calls, "continue" otherwise.
        """
        messages = state.messages
        last_message = messages[-1]
        # If there is no function call, then we finish
        if not last_message.tool_calls:
            return "end"
        # Otherwise if there is, we continue
        else:
            return "continue"

    @observe(name="create_graph")
    async def create_graph(self, scenario_id: int, tts_service: GeminiTextToSpeech) -> Optional[CompiledStateGraph]:
        """Create and configure the LangGraph workflow for a specific scenario.

        Args:
            scenario_id: The ID of the scenario to create the graph for.
            tts_service: The text-to-speech service instance.

        Returns:
            Optional[CompiledStateGraph]: The configured LangGraph instance or None if init fails
        """
        # Check if we already have a graph for this scenario
        if scenario_id in self._graphs:
            logger.info("graph_cache_hit", scenario_id=scenario_id)
            return self._graphs[scenario_id]
        
        # Build a new graph for this scenario
        connection_pool = await self._get_connection_pool()
        
        # Access LLM property (triggers lazy init if needed)
        llm = self.llm
        
        # Build graph
        langgraph_builder = LangGraphBuilder(llm, connection_pool, tts_service)
        graph = await langgraph_builder.build_graph(scenario_id)
        
        # Cache the graph
        self._graphs[scenario_id] = graph
        self._current_scenario_id = scenario_id
        
        return graph
    
    async def rebuild_graph(self, scenario_id: int, tts_service: GeminiTextToSpeech) -> Optional[CompiledStateGraph]:
        """Rebuild the graph for a specific scenario.
        
        This should be called when agents are added, updated, or deleted
        to ensure the graph reflects the current state of agents.

        Args:
            scenario_id: The ID of the scenario to rebuild the graph for.
            tts_service: The text-to-speech service instance.

        Returns:
            Optional[CompiledStateGraph]: The rebuilt LangGraph instance or None if build fails
        """
        # Remove the cached graph for this scenario
        if scenario_id in self._graphs:
            del self._graphs[scenario_id]
            logger.info("graph_cache_invalidated", scenario_id=scenario_id)
        
        # Rebuild the graph
        connection_pool = await self._get_connection_pool()
        langgraph_builder = LangGraphBuilder(self.llm, connection_pool, tts_service)
        graph = await langgraph_builder.build_graph(scenario_id)
        
        # Cache the new graph
        self._graphs[scenario_id] = graph
        
        
        logger.info("graph_rebuilt", scenario_id=scenario_id)
        return graph
    
    async def invalidate_graph(self, scenario_id: int) -> None:
        """Invalidate the cached graph for a specific scenario.
        
        The graph will be rebuilt on next use.

        Args:
            scenario_id: The ID of the scenario whose graph should be invalidated.
        """
        if scenario_id in self._graphs:
            del self._graphs[scenario_id]
            logger.info("graph_cache_invalidated", scenario_id=scenario_id)
            

    def _hydrate_chat_response(self, response: GraphState) -> ChatResponse:
        response_interrupt = response.get('__interrupt__')
        chat_response = ChatResponse(
            messages = self.__process_messages(response['messages']),
            inline_feedback = response.get('inline_feedback', []),
            student_responses = response.get('student_responses', []),
            answering_student = response.get('answering_student', 0),
            summary_feedback = response.get('summary_feedback', ''),
        )
        if response_interrupt:
            interrupt_value = response_interrupt[0].value
            chat_response.interrupt_task = interrupt_value.get('task', '')
            chat_response.interrupt_value = interrupt_value.get('student_response', '')

        return chat_response

    # TODO: can probably combine this with the get_response function
    @observe(name="get_resumption_response")
    async def get_resumption_response(
        self,
        resumption_text: str,
        session_id: str,
        user_id: str,
        scenario_id: int,
        tts_service: GeminiTextToSpeech,
    ) -> ChatResponse:
        """Get a resumption response from the LLM.
        
        Args:
            resumption_text: The text to resume with.
            session_id: The session ID for Langfuse tracking.
            user_id: The user ID for Langfuse tracking.
            scenario_id: The scenario ID to use for the graph.
            tts_service: The text-to-speech service instance.
            
        Returns:
            ChatResponse: The response from the LLM.
        """
        # Use propagate_attributes to set session_id and tags for all nested traces
        with propagate_attributes(
            session_id=session_id,
            user_id=user_id,
            tags=["resumption", "graph_execution"],
        ):
            try:
                graph = await self.create_graph(scenario_id, tts_service)
                
                if graph is None:
                    raise Exception("Failed to create graph")
                    
                config = {
                    "configurable": {"thread_id": session_id},
                    "metadata": {
                        "user_id": user_id,
                        "session_id": session_id,
                        "scenario_id": scenario_id,
                        "environment": settings.ENVIRONMENT.value,
                        "debug": False,
                    },
                }
                
                # Get current conversation state and start feedback immediately
                # This allows feedback to run in parallel with graph execution
                feedback_id = uuid.uuid4().hex
                feedback_started_early = False
                try:
                    from langchain_core.messages import HumanMessage
                    state: StateSnapshot = await sync_to_async(graph.get_state)(config)
                    current_messages = list(state.values.get("messages", [])) if state.values else []
                    # Add the new user message to context for feedback
                    current_messages.append(HumanMessage(content=resumption_text))
                    feedback_cache.put_pending(
                        feedback_id=feedback_id,
                        session_id=session_id,
                        scenario_id=scenario_id,
                        messages=current_messages,
                    )
                    # Fire feedback task immediately (runs in parallel with graph)
                    asyncio.create_task(
                        generate_feedback_and_store(feedback_id, self.llm, session_id)
                    )
                    feedback_started_early = True
                    logger.info("async_feedback_started_early", feedback_id=feedback_id, session_id=session_id)
                except Exception as e:
                    logger.warning("early_feedback_start_failed", error=str(e), feedback_id=feedback_id)
                    # Will fall back to starting feedback after execution
                
                # Execute graph (feedback may be running in parallel)
                response: GraphState = await graph.ainvoke(
                    Command(
                        resume={"response": resumption_text}
                    ), config
                )
                
                # Hydrate response
                result = self._hydrate_chat_response(response)
                
                # If early feedback start failed, start it now with full response messages
                if not feedback_started_early:
                    feedback_cache.put_pending(
                        feedback_id=feedback_id,
                        session_id=session_id,
                        scenario_id=scenario_id,
                        messages=response["messages"],
                    )
                    asyncio.create_task(
                        generate_feedback_and_store(feedback_id, self.llm, session_id)
                    )
                    logger.info("async_feedback_started_fallback", feedback_id=feedback_id, session_id=session_id)
                
                # Attach the feedback_id
                result.feedback_request_id = feedback_id
                
                return result
            except Exception as e:
                logger.error(f"Error getting response: {str(e)}")
                raise e

    @observe(name="get_response")
    async def get_response(
        self,
        messages: list[Message],
        session_id: str,
        user_id: str,
        scenario_id: int,
        tts_service: GeminiTextToSpeech,
    ) -> ChatResponse:
        """Get a response from the LLM.

        Args:
            messages (list[Message]): The messages to send to the LLM.
            session_id (str): The session ID for Langfuse tracking.
            user_id (str): The user ID for Langfuse tracking.
            scenario_id (int): The scenario ID to use for the graph.
            tts_service: The text-to-speech service instance.

        Returns:
            ChatResponse: The response from the LLM.
        """
        # Use propagate_attributes to set session_id and tags for all nested traces
        with propagate_attributes(
            session_id=session_id,
            user_id=user_id,
            tags=["chat", "graph_execution"],
        ):
            # Generate feedback_id and start feedback generation immediately
            # This runs in parallel with graph execution for faster feedback
            feedback_id = uuid.uuid4().hex
            langchain_messages = dump_messages(messages)
            feedback_cache.put_pending(
                feedback_id=feedback_id,
                session_id=session_id,
                scenario_id=scenario_id,
                messages=langchain_messages,
            )
            # Fire feedback task immediately (runs in parallel with graph)
            _ = asyncio.create_task(
                generate_feedback_and_store(feedback_id, self.llm, session_id)
            )
            logger.info("async_feedback_started_early", feedback_id=feedback_id, session_id=session_id)
            
            try:
                graph = await self.create_graph(scenario_id, tts_service)
                
                if graph is None:
                    raise Exception("Failed to create graph")
                    
                config = {
                    "configurable": {"thread_id": session_id},
                    "metadata": {
                        "user_id": user_id,
                        "session_id": session_id,
                        "scenario_id": scenario_id,
                        "environment": settings.ENVIRONMENT.value,
                        "debug": False,
                    },
                }
                
                # Execute graph (feedback is running in parallel)
                response: GraphState = await graph.ainvoke(
                    {"messages": langchain_messages, "session_id": session_id}, config
                )
                
                # Hydrate response
                result = self._hydrate_chat_response(response)
                
                # Attach the feedback_id that was started earlier
                result.feedback_request_id = feedback_id
                
                return result
            except Exception as e:
                logger.error(f"Error getting response: {str(e)}")
                raise e

    async def get_stream_response(
        self, 
        messages: list[Message], 
        session_id: str, 
        user_id: Optional[str] = None,
        scenario_id: Optional[int] = None,
        tts_service: Optional[GeminiTextToSpeech] = None,
    ) -> AsyncGenerator[str, None]:
        """Get a stream response from the LLM.

        Args:
            messages (list[Message]): The messages to send to the LLM.
            session_id (str): The session ID for the conversation.
            user_id (Optional[str]): The user ID for the conversation.
            scenario_id (Optional[int]): The scenario ID to use for the graph.
            tts_service: The text-to-speech service instance.

        Yields:
            str: Tokens of the LLM response.
        """
        with propagate_attributes(
            session_id=session_id,
            user_id=user_id,
            tags=["stream", "graph_execution"],
        ):
            config = {
                "configurable": {"thread_id": session_id},
            }
            if scenario_id is None or tts_service is None:
                raise ValueError("scenario_id and tts_service are required for get_stream_response")
            graph = await self.create_graph(scenario_id, tts_service)
            if graph is None:
                raise Exception("Failed to create graph")

            try:
                async for token, metadata in graph.astream(
                    {"messages": dump_messages(messages), "session_id": session_id}, config, stream_mode="messages"
                ):
                    try:
                        node_name = metadata.get("langgraph_node", "")
                        if node_name.startswith("student_"):
                            text = _extract_token_text(token.content)
                            if text:
                                yield text
                    except Exception as token_error:
                        logger.error("Error processing token", error=str(token_error), session_id=session_id)
                        continue
            except Exception as stream_error:
                logger.error("Error in stream processing", error=str(stream_error), session_id=session_id)
                raise stream_error

    async def get_stream_resumption_response(
        self,
        resumption_text: str,
        session_id: str,
        user_id: Optional[str] = None,
        scenario_id: Optional[int] = None,
        tts_service: Optional[GeminiTextToSpeech] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from a graph resumption (the primary classroom chat flow).

        Resumes the paused graph with the teacher's input and yields each student
        response token as it is generated, enabling time-to-first-token improvements.

        Args:
            resumption_text: The teacher's response text to resume the graph with.
            session_id: The session ID for the conversation.
            user_id: The user ID for Langfuse tracking.
            scenario_id: The scenario ID to use for the graph.
            tts_service: The text-to-speech service instance.

        Yields:
            str: Individual text tokens from the student agent response.
        """
        with propagate_attributes(
            session_id=session_id,
            user_id=user_id,
            tags=["stream", "resumption", "graph_execution"],
        ):
            config = {
                "configurable": {"thread_id": session_id},
            }
            if scenario_id is None or tts_service is None:
                raise ValueError("scenario_id and tts_service are required for get_stream_resumption_response")
            graph = await self.create_graph(scenario_id, tts_service)
            if graph is None:
                raise Exception("Failed to create graph")

            try:
                async for token, metadata in graph.astream(
                    Command(resume={"response": resumption_text}),
                    config,
                    stream_mode="messages",
                ):
                    try:
                        node_name = metadata.get("langgraph_node", "")
                        if node_name.startswith("student_"):
                            text = _extract_token_text(token.content)
                            if text:
                                yield text
                    except Exception as token_error:
                        logger.error("Error processing token", error=str(token_error), session_id=session_id)
                        continue
            except Exception as stream_error:
                logger.error("Error in stream resumption", error=str(stream_error), session_id=session_id)
                raise stream_error

    async def get_current_chat_state(
        self,
        session_id: str,
        scenario_id: int,
        tts_service: GeminiTextToSpeech,
    ) -> ChatResponse:
        """Return the current graph state as a ChatResponse.

        Called after streaming completes to retrieve student metadata (name,
        audio_id, interrupt values) that cannot be reconstructed from raw tokens.

        Args:
            session_id: The session ID whose checkpoint to read.
            scenario_id: The scenario ID used to look up the correct graph.
            tts_service: The text-to-speech service instance.

        Returns:
            ChatResponse: Hydrated response built from the latest checkpoint state.
        """
        graph = await self.create_graph(scenario_id, tts_service)
        if graph is None:
            raise Exception("Failed to create graph")
        config = {"configurable": {"thread_id": session_id}}
        state: StateSnapshot = await sync_to_async(graph.get_state)(config)
        if state.values:
            return self._hydrate_chat_response(state.values)
        return ChatResponse()

    async def get_chat_history(
        self, 
        session_id: str, 
        scenario_id: Optional[int] = None,
        tts_service: Optional[GeminiTextToSpeech] = None,
    ) -> list[Message]:
        """Get the chat history for a given thread ID.

        Args:
            session_id (str): The session ID for the conversation.
            scenario_id (Optional[int]): The scenario ID to use for the graph.
            tts_service (Optional[GeminiTextToSpeech]): The text-to-speech service instance.

        Returns:
            list[Message]: The chat history.
        """
        if tts_service is None:
            raise ValueError("tts_service is required for get_chat_history")
        
        graph = await self.create_graph(scenario_id, tts_service)
        if graph is None:
            return []

        state: StateSnapshot = await sync_to_async(graph.get_state)(
            config={"configurable": {"thread_id": session_id}}
        )
        return self.__process_messages(state.values["messages"]) if state.values else []

    def __process_messages(self, messages: list[BaseMessage]) -> list[Message]:
        openai_style_messages = convert_to_openai_messages(messages)
        # keep just assistant and user messages
        return [
            Message(**message)
            for message in openai_style_messages
            if message["role"] in ["assistant", "user"] and message["content"]
        ]

    async def clear_chat_history(self, session_id: str) -> None:
        """Clear all chat history for a given thread ID.

        Args:
            session_id: The ID of the session to clear history for.

        Raises:
            Exception: If there's an error clearing the chat history.
        """
        try:
            # Make sure the pool is initialized in the current event loop
            conn_pool = await self._get_connection_pool()

            # Use a new connection for this specific operation
            async with conn_pool.connection() as conn:
                for table in settings.CHECKPOINT_TABLES:
                    try:
                        await conn.execute(f"DELETE FROM {table} WHERE thread_id = %s", (session_id,))
                        logger.info(f"Cleared {table} for session {session_id}")
                    except Exception as e:
                        logger.error(f"Error clearing {table}", error=str(e))
                        raise

        except Exception as e:
            logger.error("Failed to clear chat history", error=str(e))
            raise
