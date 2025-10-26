"""This file contains the graph builder for the application."""

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import CompiledStateGraph
from langgraph.graph.state import (
    START,
    END,
    StateGraph,
)
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
)
from psycopg_pool import AsyncConnectionPool

from app.core.config import (
    Environment,
    settings,
)
from app.core.logging import logger
from app.schemas.graph import GraphState, GeneralResponse, StudentChoiceResponse, AppropriateResponse
from app.core.prompts.students import (
    STUDENT_PROFILES,
    STUDENT_1_SYSTEM_INSTRUCTIONS,
    STUDENT_2_SYSTEM_INSTRUCTIONS,
    STUDENT_3_SYSTEM_INSTRUCTIONS,
    INLINE_FEEDBACK_SYSTEM_INSTRUCTIONS,
)

class LangGraphBuilder:
    def __init__(self, llm: BaseChatModel, connection_pool: AsyncConnectionPool):
        self.llm = llm
        self._connection_pool = connection_pool

    async def build_graph(self) -> CompiledStateGraph:
        """Build the LangGraph workflow."""
        try:
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
                checkpointer=checkpointer, name=f"{settings.PROJECT_NAME} Agent ({settings.ENVIRONMENT.value})"
            )

            logger.info(
                "graph_created",
                graph_name=f"{settings.PROJECT_NAME} Agent",
                environment=settings.ENVIRONMENT.value,
                has_checkpointer=checkpointer is not None,
            )
            return graph

        except Exception as e:
            logger.error("graph_creation_failed", error=str(e), environment=settings.ENVIRONMENT.value)
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

        # Students & Feedback
        graph_builder.add_node("student_1_agent", self._student_1_agent)
        graph_builder.add_node("student_2_agent", self._student_2_agent)
        graph_builder.add_node("student_3_agent", self._student_3_agent)
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
            {True: "pick_answering_student", False: "gather_new_human_response"}
        )

        graph_builder.add_edge("pick_answering_student", "student_1_agent")
        graph_builder.add_edge("pick_answering_student", "student_2_agent")
        graph_builder.add_edge("pick_answering_student", "student_3_agent")
        graph_builder.add_edge("pick_answering_student", "inline_feedback_agent")

        graph_builder.add_edge(["student_1_agent", "student_2_agent", "student_3_agent", "inline_feedback_agent"], "additional_user_input")
        graph_builder.add_edge("additional_user_input", "check_if_goals_achieved")
        graph_builder.add_conditional_edges(
            "check_if_goals_achieved", 
            self._route_if_goals_achieved,
            {True: "generate_summary_feedback", False: "check_appropriate_response"} 
        )
        # TODO: add edge to add_messages node
        graph_builder.add_edge("generate_summary_feedback", END)

    async def _student_agent(self, state: GraphState, system_instructions: str) -> GraphState:
        last_message = state.messages[-1]
        if last_message.role != "user":
            raise ValueError("Last message must be a user message")

        return await self.llm.with_structured_output(GeneralResponse).ainvoke([
            SystemMessage(content=STUDENT_1_SYSTEM_INSTRUCTIONS),
            HumanMessage(content=last_message.content),
        ]).llm_response

    async def _student_1_agent(self, state: GraphState) -> GraphState:
        return {"student_responses": [await self._student_agent(state, STUDENT_1_SYSTEM_INSTRUCTIONS)]}

    async def _student_2_agent(self, state: GraphState) -> GraphState:
        return {"student_responses": [await self._student_agent(state, STUDENT_2_SYSTEM_INSTRUCTIONS).llm_response]}

    async def _student_3_agent(self, state: GraphState) -> GraphState:
        return {"student_responses": [await self._student_agent(state, STUDENT_3_SYSTEM_INSTRUCTIONS).llm_response]}

    async def _inline_feedback_agent(self, state: GraphState) -> GraphState:
        return {"inline_feedback": [await self._student_agent(state, INLINE_FEEDBACK_SYSTEM_INSTRUCTIONS).llm_response]}

    async def _additional_user_input(self, state: GraphState) -> GraphState:
        pass

    async def _check_if_goals_achieved(self, state: GraphState) -> GraphState:
        pass

    async def _generate_summary_feedback(self, state: GraphState) -> GraphState:
        pass

    async def _route_appropriate_response(self, state: GraphState) -> GraphState:
        pass

    async def _route_if_goals_achieved(self, state: GraphState) -> GraphState:
        pass