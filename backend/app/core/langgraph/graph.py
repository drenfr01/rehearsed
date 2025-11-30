"""This file contains the graph builder for the application."""

from typing import Callable, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    AIMessage,
)
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import (
    END,
    START,
    CompiledStateGraph,
    StateGraph,
)
from langgraph.types import (
    Command,
    interrupt,
)
from psycopg_pool import AsyncConnectionPool

from app.models.agent import Agent
from app.services.database import database_service
from app.core.config import (
    Environment,
    settings,
)
from app.core.logging import logger
from app.core.prompts.students import (
    APPROPRIATE_RESPONSE_INSTRUCTIONS,
    STUDENT_PROFILES,
    STUDENT_SYSTEM_INSTRUCTIONS_TEMPLATE,
)
from app.core.prompts.feedback import format_feedback_instructions
from app.schemas.graph import (
    AppropriateResponse,
    GeneralResponse,
    StudentResponse,
    GraphState,
    StudentChoiceResponse,
)


class LangGraphBuilder:
    def __init__(self, llm: BaseChatModel, connection_pool: AsyncConnectionPool):
        self.llm = llm
        self._connection_pool = connection_pool
        self._agents: List[Agent] = []

    async def build_graph(self, scenario_id: int) -> CompiledStateGraph:
        """Build the LangGraph workflow for a specific scenario.
        
        Args:
            scenario_id: The ID of the scenario to build the graph for.
            
        Returns:
            CompiledStateGraph: The compiled LangGraph workflow.
        """
        try:
            # Fetch agents for this scenario from the database
            self._agents = await database_service.get_agents_by_scenario(scenario_id)
            
            if not self._agents:
                logger.warning(
                    "no_agents_found_for_scenario",
                    scenario_id=scenario_id,
                    environment=settings.ENVIRONMENT.value,
                )
            
            graph_builder = self._build_graph()
            if self._connection_pool:
                checkpointer = AsyncPostgresSaver(self._connection_pool)
                await checkpointer.setup()
            else:
                # In production, proceed without checkpointer if needed
                checkpointer = None
                if settings.ENVIRONMENT != Environment.PRODUCTION:
                    raise Exception("Connection pool initialization failed")

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

    def _build_graph(self) -> StateGraph:
        graph_builder = StateGraph(GraphState)
        
        # Initial Nodes
        graph_builder.add_node("check_appropriate_response", self._check_appropriate_response)
        graph_builder.add_node("pick_answering_student", self._pick_answering_student)
        graph_builder.add_node("gather_new_human_response", self._gather_new_human_response)

        # Dynamically create student agent nodes based on agents from the database
        student_node_names = []
        for idx, agent in enumerate(self._agents):
            node_name = f"student_{idx + 1}_agent"
            student_node_names.append(node_name)
            # Create a closure to capture the agent for each node
            node_handler = self._create_student_agent_handler(agent, idx + 1)
            graph_builder.add_node(node_name, node_handler)

        # Feedback nodes
        graph_builder.add_node("inline_feedback_agent", self._inline_feedback_agent)
        graph_builder.add_node("additional_user_input", self._additional_user_input)
        graph_builder.add_node("check_if_goals_achieved", self._check_if_goals_achieved)
        graph_builder.add_node("generate_summary_feedback", self._generate_summary_feedback)

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
        async def handler(state: GraphState) -> GraphState:
            """Handle student agent node execution."""
            personality_description = (
                agent.agent_personality.personality_description 
                if agent.agent_personality 
                else "Helpful and engaged"
            )
            system_instructions = STUDENT_SYSTEM_INSTRUCTIONS_TEMPLATE.format(
                objective_and_persona=agent.objective,
                instructions=agent.instructions,
                constraints=agent.constraints,
                context=agent.context,
                personality=personality_description,
            )
            response = await self._call_general_llm(state, system_instructions)
            return {
                "student_responses": [
                    StudentResponse(
                        student_response=response, 
                        student_details=agent, 
                        student_personality=agent.agent_personality
                    )
                ]
            }
        return handler

    async def _check_appropriate_response(self, state: GraphState) -> GraphState:
        """This node is used to check if the human response is appropriate for a teacher."""
        # last_message = state.messages[-1]

        # if not isinstance(last_message, HumanMessage):
        #     raise ValueError("last message should be the human message input")

        # # print("Last message: ", last_message)
        # messages = [
        #     SystemMessage(content=APPROPRIATE_RESPONSE_INSTRUCTIONS),
        #     HumanMessage(content=last_message.content),
        # ]

        # structured_llm = self.llm.with_structured_output(AppropriateResponse)
        # response = structured_llm.invoke(messages)
        return {
            "appropriate_response": True,
            "appropriate_explanation": "",
        }

    async def _pick_answering_student(self, state: GraphState) -> Command:
        """This node is used to pick the answering student based on the user message.
        
        Returns a Command that dynamically routes to only the selected student agent
        plus the inline feedback agent in parallel.
        """
        # Build dynamic student profiles from agents
        student_profiles = self._build_student_profiles()
        
        system_message = [
            SystemMessage(
                content=f"Based on the user message and these student profiles, pick which student (1-{len(self._agents)}) should respond:\n\n{student_profiles}",
            ),
        ]

        structured_llm = self.llm.with_structured_output(StudentChoiceResponse)
        response = structured_llm.invoke(system_message + state.messages)
        # Ensure the student number is within valid range
        student_num = max(1, min(response.student_number, len(self._agents)))
        
        # Dynamically route to only the selected student + inline feedback
        student_node = f"student_{student_num}_agent"
        return Command(
            update={"answering_student": student_num},
            goto=[student_node, "inline_feedback_agent"]
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
        
        response = self.llm.with_structured_output(GeneralResponse).invoke(messages)

        return response.llm_response

    async def _inline_feedback_agent(self, state: GraphState) -> GraphState:
        """This node is used to call the inline feedback agent."""
        feedback = await database_service.get_feedback_by_type("inline")
        system_instructions = format_feedback_instructions(
            objective=feedback.objective,
            instructions=feedback.instructions,
            constraints=feedback.constraints,
            context=feedback.context,
            output_format=feedback.output_format,
        )
        return {"inline_feedback": [await self._call_general_llm(state, system_instructions)]}

    async def _gather_new_human_response(self, state: GraphState) -> GraphState:
        """This node is used to gather a new human response if the human response is not appropriate."""
        return {"summary": "New Human Response"}

    async def _additional_user_input(self, state: GraphState) -> GraphState:
        """This node is used to gather additional user input after the student agents have responded."""
        # Get the most recent student response (last one added)
        student_message = state.student_responses[-1].student_response
        result = interrupt(
            {
                "task": "Review the student_response",
                "student_response": student_message,
            }
        )

        # Update the state with the edited text
        return {"messages": [
            AIMessage(content=student_message),
            HumanMessage(content=result["response"]),
        ]}

    async def _check_if_goals_achieved(self, state: GraphState) -> GraphState:
        """This node is used to check if the learning goals have been achieved."""
        # TODO: update this with real prompt
        if "goals achieved" in state.messages[-1].content.lower():
            return {"learning_goals_achieved": True}
        else:
            return {"learning_goals_achieved": False}

    async def _generate_summary_feedback(self, state: GraphState) -> GraphState:
        """This node is used to generate a summary feedback for the entire conversation"""
        feedback = await database_service.get_feedback_by_type("summary")
        system_instructions = format_feedback_instructions(
            objective=feedback.objective,
            instructions=feedback.instructions,
            constraints=feedback.constraints,
            context=feedback.context,
            output_format=feedback.output_format,
        )

        prompt = [
            SystemMessage(content=system_instructions),
            *state.messages,
        ]
        response = self.llm.with_structured_output(GeneralResponse, method="json_schema", include_raw=True).invoke(prompt)
        if response["parsed"] is None:
            logger.error("summary_feedback_generation_failed", error=response["raw"], exc_info=True)
            return {"summary_feedback": "Could not generate summary feedback"}

        return {"summary_feedback": response["parsed"].llm_response}

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
