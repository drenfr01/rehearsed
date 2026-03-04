"""This file contains the graph builder for the application."""

import uuid
from typing import Callable, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_google_genai import ChatGoogleGenerativeAI
from langfuse import observe
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import (
    END,
    START,
    CompiledStateGraph,
    StateGraph,
)
from langgraph.types import (
    Command,
    RetryPolicy,
    interrupt,
)
from psycopg_pool import AsyncConnectionPool

from app.core.config import (
    Environment,
    settings,
)
from app.core.logging import logger
from app.core.prompts.feedback import format_feedback_instructions
from app.core.prompts.pick_answering_student import PICK_ANSWERING_STUDENT_SYSTEM_INSTRUCTIONS
from app.core.prompts.students import (
    APPROPRIATE_RESPONSE_INSTRUCTIONS,
    STUDENT_PROFILES,
    STUDENT_SYSTEM_INSTRUCTIONS_TEMPLATE,
)
from app.models.agent import Agent
from app.schemas.graph import (
    AppropriateResponse,
    GeneralResponse,
    GraphState,
    StudentChoiceResponse,
    StudentResponse,
)
from app.services.database import database_service
from app.services.gemini_text_to_speech import GeminiTextToSpeech


class LangGraphBuilder:
    """Builder class for constructing LangGraph workflows."""

    def __init__(
        self,
        llm: BaseChatModel,
        connection_pool: AsyncConnectionPool,
        tts_service: GeminiTextToSpeech,
        llm_answering_student: Optional[BaseChatModel] = None,
    ):
        """Initialize the LangGraph builder.

        Args:
            llm: The language model to use for the graph.
            connection_pool: The async connection pool for database operations.
            tts_service: The text-to-speech service instance.
            llm_answering_student: Optional separate LLM for the pick_answering_student
                node. Falls back to ``llm`` if not provided.
        """
        self.llm = llm
        self.llm_answering_student = llm_answering_student if llm_answering_student is not None else llm
        self._connection_pool = connection_pool
        self._agents: List[Agent] = []
        self._scenario_id: int = 0
        self._tts_service = tts_service

    @observe(name="build_graph")
    async def build_graph(self, scenario_id: int) -> CompiledStateGraph:
        """Build the LangGraph workflow for a specific scenario.
        
        Args:
            scenario_id: The ID of the scenario to build the graph for.
            
        Returns:
            CompiledStateGraph: The compiled LangGraph workflow.
        """
        try:
            # Store scenario_id for use in feedback agents
            self._scenario_id = scenario_id
            
            # Fetch agents for this scenario from the database
            self._agents = await self._fetch_agents(scenario_id)
            
            if not self._agents:
                logger.warning(
                    "no_agents_found_for_scenario",
                    scenario_id=scenario_id,
                    environment=settings.ENVIRONMENT.value,
                )
            
            # Build graph structure
            graph_builder = self._build_graph()
            
            # Setup checkpointer
            checkpointer = await self._setup_checkpointer()

            # Compile graph
            graph = graph_builder.compile(
                checkpointer=checkpointer, name=f"{settings.PROJECT_NAME} Agent - Scenario {scenario_id} ({settings.ENVIRONMENT.value})"
            )

            logger.info(
                "graph_created",
                graph_name=f"{settings.PROJECT_NAME} Agent",
                scenario_id=scenario_id,
                agent_count=len(self._agents),
                environment=settings.ENVIRONMENT.value,
                has_checkpointer=checkpointer is not None,
            )
            return graph

        except Exception as e:
            logger.error("graph_creation_failed", error=str(e), scenario_id=scenario_id, environment=settings.ENVIRONMENT.value)
            # In production, we don't want to crash the app
            if settings.ENVIRONMENT == Environment.PRODUCTION:
                logger.warning("continuing_without_graph")
                return None
            raise e
    
    @observe(name="fetch_agents")
    async def _fetch_agents(self, scenario_id: int) -> List[Agent]:
        """Fetch agents for a scenario from the database."""
        agents = await database_service.agents.get_agents_by_scenario(scenario_id)
        return agents
    
    @observe(name="setup_checkpointer")
    async def _setup_checkpointer(self) -> Optional[AsyncPostgresSaver]:
        """Setup the checkpointer for the graph."""
        if self._connection_pool:
            checkpointer = AsyncPostgresSaver(self._connection_pool)
            await checkpointer.setup()
            return checkpointer
        else:
            # In production, proceed without checkpointer if needed
            if settings.ENVIRONMENT != Environment.PRODUCTION:
                raise Exception("Connection pool initialization failed")
            return None

    def _build_graph(self) -> StateGraph:
        graph_builder = StateGraph(GraphState)
        
        # Configure retry policy: retry once after 1 second
        retry_policy = RetryPolicy(
            max_attempts=2,        # Total attempts: initial + 1 retry
            initial_interval=1.0,  # Wait 1 second before retrying
            backoff_factor=1.0,    # No exponential backoff
            max_interval=1.0,      # Maximum interval between retries
            jitter=False           # No random jitter
        )
        
        # Initial Nodes
        graph_builder.add_node("check_appropriate_response", self._check_appropriate_response, retry_policy=retry_policy)
        graph_builder.add_node("pick_answering_student", self._pick_answering_student, retry_policy=retry_policy)
        graph_builder.add_node("gather_new_human_response", self._gather_new_human_response, retry_policy=retry_policy)

        # Dynamically create student agent nodes based on agents from the database
        student_node_names = []
        for idx, agent in enumerate(self._agents):
            node_name = f"student_{idx + 1}_agent"
            student_node_names.append(node_name)
            # Create a closure to capture the agent for each node
            node_handler = self._create_student_agent_handler(agent, idx + 1)
            graph_builder.add_node(node_name, node_handler, retry_policy=retry_policy)

        # Feedback nodes
        graph_builder.add_node("inline_feedback_agent", self._inline_feedback_agent, retry_policy=retry_policy)
        graph_builder.add_node("additional_user_input", self._additional_user_input, retry_policy=retry_policy)
        graph_builder.add_node("check_if_goals_achieved", self._check_if_goals_achieved, retry_policy=retry_policy)
        graph_builder.add_node("generate_summary_feedback", self._generate_summary_feedback, retry_policy=retry_policy)

        # Edges
        graph_builder.add_edge(START, "check_appropriate_response")
        # TODO: change this node to be HITL
        graph_builder.add_edge("gather_new_human_response", "check_appropriate_response")

        graph_builder.add_conditional_edges(
            "check_appropriate_response",
            self._route_appropriate_response,
            {True: "pick_answering_student", False: "gather_new_human_response"},
        )

        # Note: pick_answering_student uses Command to dynamically route to 
        # the selected student + inline_feedback_agent in parallel
        
        # Add edges from each student agent to additional_user_input (for join after dynamic routing)
        for node_name in student_node_names:
            graph_builder.add_edge(node_name, "additional_user_input")
        graph_builder.add_edge("inline_feedback_agent", "additional_user_input")
        
        graph_builder.add_edge("additional_user_input", "check_if_goals_achieved")
        graph_builder.add_conditional_edges(
            "check_if_goals_achieved",
            self._route_if_goals_achieved,
            {True: "generate_summary_feedback", False: "check_appropriate_response"},
        )
        # TODO: add edge to add_messages node
        graph_builder.add_edge("generate_summary_feedback", END)
        return graph_builder
    
    def _create_student_agent_handler(self, agent: Agent, student_number: int) -> Callable:
        """Create a handler function for a specific student agent.
        
        Args:
            agent: The agent model from the database.
            student_number: The 1-indexed student number.
            
        Returns:
            A coroutine function that handles the student agent node.
        """
        # Capture agent and student_number for use in the decorated handler
        captured_agent = agent
        
        @observe(name=f"student_{student_number}_agent")
        async def handler(state: GraphState) -> GraphState:
            """Handle student agent node execution."""
            personality_description = (
                captured_agent.agent_personality.personality_description 
                if captured_agent.agent_personality 
                else "Helpful and engaged"
            )
            system_instructions = STUDENT_SYSTEM_INSTRUCTIONS_TEMPLATE.format(
                objective_and_persona=captured_agent.objective,
                instructions=captured_agent.instructions,
                constraints=captured_agent.constraints,
                context=captured_agent.context,
                personality=personality_description,
            )
            
            # LLM call
            response = await self._call_general_llm(state, system_instructions)
            
            # Lazy-load TTS: do NOT generate audio here (keeps chat latency low).
            # We include an audio_id for the client/backend to fetch later.
            audio_id = ""
            if captured_agent.voice and captured_agent.voice.voice_name:
                audio_id = uuid.uuid4().hex
            
            return {
                "student_responses": [
                    StudentResponse(
                        student_response=response, 
                        student_details=captured_agent, 
                        student_personality=captured_agent.agent_personality,
                        audio_base64="",
                        audio_id=audio_id,
                    )
                ]
            }
        return handler

    async def _check_appropriate_response(self, state: GraphState) -> GraphState:
        """Check if the human response is appropriate for a teacher."""
        return {
            "appropriate_response": True,
            "appropriate_explanation": "",
        }

    @observe(name="pick_answering_student")
    async def _pick_answering_student(self, state: GraphState) -> Command:
        """This node is used to pick the answering student based on the user message.
        
        Returns a Command that dynamically routes to only the selected student agent
        plus the inline feedback agent in parallel.
        """
        # Build dynamic student profiles from agents
        student_profiles = self._build_student_profiles()
        
        system_message = [
            SystemMessage(
                content=PICK_ANSWERING_STUDENT_SYSTEM_INSTRUCTIONS.format(
                    student_profiles=student_profiles, 
                    student_number_range=len(self._agents),
                    messages=state.messages,
                )
            ),
        ]

        # LLM call to select student
        structured_llm = self.llm_answering_student.with_structured_output(StudentChoiceResponse)
        response = await structured_llm.ainvoke(system_message + state.messages)
        
        # Ensure the student number is within valid range
        student_num = max(1, min(response.student_number, len(self._agents)))
        
        # Dynamically route to only the selected student
        # NOTE: inline_feedback_agent is now computed asynchronously after the response
        # is returned to reduce latency. See feedback_cache.py for the background task.
        student_node = f"student_{student_num}_agent"
        
        return Command(
            update={"answering_student": student_num},
            goto=[student_node]
        )
    
    def _build_student_profiles(self) -> str:
        """Build a string description of all student profiles for the LLM."""
        profiles = []
        for idx, agent in enumerate(self._agents):
            personality = (
                agent.agent_personality.personality_description 
                if agent.agent_personality 
                else "Standard student personality"
            )
            profile = f"Student {idx + 1} ({agent.name}): {personality}"
            profiles.append(profile)
        return "\n".join(profiles)

    @observe(name="call_general_llm")
    async def _call_general_llm(self, state: GraphState, system_instructions: str) -> str:
        """Helper function to call the student / feedback agent.
        
        Args:
            state: The current graph state.
            system_instructions: The system instructions for the LLM.
            
        Returns:
            str: The LLM response text.
        """
        last_message = state.messages[-1]
        if not isinstance(last_message, HumanMessage):
            raise ValueError("last message should be the human message input")

        # Build messages with full conversation history for context
        messages = [SystemMessage(content=system_instructions)]
        messages.extend(state.messages)  # Include full conversation history
        
        # LLM invoke call
        response = await self.llm.with_structured_output(
            GeneralResponse, method="json_schema", include_raw=True
        ).ainvoke(messages)

        if response["parsed"] is None:
            logger.error(
                "general_llm_call_failed",
                error=str(response["raw"]),
                system_instructions_preview=system_instructions[:100],
            )
            return "I'm sorry, I couldn't generate a response. Please try again."
        
        llm_response = response["parsed"].llm_response
        if not llm_response or not llm_response.strip():
            logger.warning(
                "general_llm_returned_empty_response",
                raw_response=str(response["raw"]),
                system_instructions_preview=system_instructions[:100],
            )
            return "I'm sorry, I couldn't generate a response. Please try again."

        return llm_response

    @observe(name="inline_feedback_agent")
    async def _inline_feedback_agent(self, state: GraphState) -> GraphState:
        """This node is used to call the inline feedback agent."""
        # Database query for feedback config
        feedback = await database_service.feedback.get_feedback_by_type("inline", self._scenario_id)
        
        if feedback is None:
            logger.warning("inline_feedback_not_found", scenario_id=self._scenario_id)
            return {"inline_feedback": ["No inline feedback configured for this scenario."]}
        
        system_instructions = format_feedback_instructions(
            objective=feedback.objective,
            instructions=feedback.instructions,
            constraints=feedback.constraints,
            context=feedback.context,
            output_format=feedback.output_format,
        )
        
        # LLM call
        result = await self._call_general_llm(state, system_instructions)
        
        return {"inline_feedback": [result]}

    async def _gather_new_human_response(self, state: GraphState) -> GraphState:
        """This node is used to gather a new human response if the human response is not appropriate."""
        return {"summary": "New Human Response"}

    async def _additional_user_input(self, state: GraphState) -> GraphState:
        """This node is used to gather additional user input after the student agents have responded."""
        # Get the most recent student response (last one added)
        latest_response = state.student_responses[-1]
        student_message = latest_response.student_response
        student_name = latest_response.student_details.name
        result = interrupt(
            {
                "task": "Review the student_response",
                "student_response": student_message,
            }
        )

        # Include student name in AI message so pick_answering_student can track who has spoken
        ai_message_content = f"[{student_name}]: {student_message}"
        
        # Update the state with the edited text
        return {"messages": [
            AIMessage(content=ai_message_content),
            HumanMessage(content=result["response"]),
        ]}

    async def _check_if_goals_achieved(self, state: GraphState) -> GraphState:
        """This node is used to check if the learning goals have been achieved."""
        # TODO: update this with real prompt
        if "goals achieved" in state.messages[-1].content.lower():
            return {"learning_goals_achieved": True}
        else:
            return {"learning_goals_achieved": False}

    @observe(name="generate_summary_feedback")
    async def _generate_summary_feedback(self, state: GraphState) -> GraphState:
        """Generate summary feedback for the entire conversation."""
        from app.services.summary_feedback import generate_summary_feedback

        conversation = []
        for msg in state.messages:
            if isinstance(msg, HumanMessage):
                conversation.append({"role": "user", "text": msg.content})
            elif isinstance(msg, AIMessage):
                conversation.append({"role": "agent", "text": msg.content})

        result = await generate_summary_feedback(self._scenario_id, conversation)
        return {"summary_feedback": result}

    async def _route_appropriate_response(self, state: GraphState) -> GraphState:
        """This node is used to route the conversation based on if the human response is appropriate.

        Note: having a routing function + a node is redundant here. But I can't figure out how to make a conditional edge either route to
        a single node or a list of nodes as two distinct paths. So this is a hack for now
        """
        if state.appropriate_response:
            return True
        else:
            return False

    async def _route_if_goals_achieved(self, state: GraphState) -> GraphState:
        """This node is used to route the conversation based on if the learning goals have been achieved."""
        if state.learning_goals_achieved:
            return True
        else:
            return False
