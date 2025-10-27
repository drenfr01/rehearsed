"""This file contains the graph builder for the application."""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
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

from app.core.config import (
    Environment,
    settings,
)
from app.core.logging import logger
from app.core.prompts.students import (
    APPROPRIATE_RESPONSE_INSTRUCTIONS,
    INLINE_FEEDBACK_SYSTEM_INSTRUCTIONS,
    STUDENT_1_SYSTEM_INSTRUCTIONS,
    STUDENT_2_SYSTEM_INSTRUCTIONS,
    STUDENT_3_SYSTEM_INSTRUCTIONS,
    STUDENT_PROFILES,
)
from app.schemas.graph import (
    AppropriateResponse,
    GeneralResponse,
    GraphState,
    StudentChoiceResponse,
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
            {True: "pick_answering_student", False: "gather_new_human_response"},
        )

        graph_builder.add_edge("pick_answering_student", "student_1_agent")
        graph_builder.add_edge("pick_answering_student", "student_2_agent")
        graph_builder.add_edge("pick_answering_student", "student_3_agent")
        graph_builder.add_edge("pick_answering_student", "inline_feedback_agent")

        graph_builder.add_edge(
            ["student_1_agent", "student_2_agent", "student_3_agent", "inline_feedback_agent"], "additional_user_input"
        )
        graph_builder.add_edge("additional_user_input", "check_if_goals_achieved")
        graph_builder.add_conditional_edges(
            "check_if_goals_achieved",
            self._route_if_goals_achieved,
            {True: "generate_summary_feedback", False: "check_appropriate_response"},
        )
        # TODO: add edge to add_messages node
        graph_builder.add_edge("generate_summary_feedback", END)
        return graph_builder

    async def _check_appropriate_response(self, state: GraphState) -> GraphState:
        """This node is used to check if the human response is appropriate for a teacher."""
        last_message = state.messages[-1]

        if not isinstance(last_message, HumanMessage):
            raise ValueError("last message should be the human message input")

        # print("Last message: ", last_message)
        messages = [
            SystemMessage(content=APPROPRIATE_RESPONSE_INSTRUCTIONS),
            HumanMessage(content=last_message.content),
        ]

        structured_llm = self.llm.with_structured_output(AppropriateResponse)
        response = structured_llm.invoke(messages)
        # print("Appopriateness Response: ", response)
        return {
            "appropriate_response": response.appropriate_response,
            "appropriate_explanation": response.appropriate_explanation,
        }

    async def _pick_answering_student(self, state: GraphState) -> GraphState:
        """This node is used to pick the answering student based on the user message."""
        system_message = [
            SystemMessage(
                content=f"Based on the user message {STUDENT_PROFILES}",
            ),
        ]

        structured_llm = self.llm.with_structured_output(StudentChoiceResponse)
        response = structured_llm.invoke(system_message + state.messages)
        return {"answering_student": response.student_number}

    async def _call_general_llm(self, state: GraphState, system_instructions: str) -> GraphState:
        """Helper function to call the student / feedback agent."""
        last_message = state.messages[-1]
        if not isinstance(last_message, HumanMessage):
            raise ValueError("last message should be the human message input")

        response = self.llm.with_structured_output(GeneralResponse).invoke(
            [
                SystemMessage(content=system_instructions),
                HumanMessage(content=last_message.content),
            ]
        )

        return response.llm_response

    async def _student_1_agent(self, state: GraphState) -> GraphState:
        """This node is used to call the student 1 agent."""
        return {"student_responses": [await self._call_general_llm(state, STUDENT_1_SYSTEM_INSTRUCTIONS)]}

    async def _student_2_agent(self, state: GraphState) -> GraphState:
        """This node is used to call the student 2 agent."""
        return {"student_responses": [await self._call_general_llm(state, STUDENT_2_SYSTEM_INSTRUCTIONS)]}

    async def _student_3_agent(self, state: GraphState) -> GraphState:
        """This node is used to call the student 3 agent."""
        return {"student_responses": [await self._call_general_llm(state, STUDENT_3_SYSTEM_INSTRUCTIONS)]}

    async def _inline_feedback_agent(self, state: GraphState) -> GraphState:
        """This node is used to call the inline feedback agent."""
        return {"inline_feedback": [await self._call_general_llm(state, INLINE_FEEDBACK_SYSTEM_INSTRUCTIONS)]}

    async def _gather_new_human_response(self, state: GraphState) -> GraphState:
        """This node is used to gather a new human response after the student agents have responded."""
        return {"summary": "New Human Response"}

    async def _additional_user_input(self, state: GraphState) -> GraphState:
        """This node is used to gather additional user input after the student agents have responded."""
        result = interrupt(
            # TODO: figure out how to restore correct student response
            {
                "task": "Review the student_response",
                "student_response": state.student_responses[state.answering_student - 1],
            }
        )

        # Update the state with the edited text
        return {"messages": HumanMessage(content=result["response"])}

    async def _check_if_goals_achieved(self, state: GraphState) -> GraphState:
        """This node is used to check if the learning goals have been achieved."""
        # TODO: update this with real prompt
        return {"learning_goals_achieved": True}

    async def _generate_summary_feedback(self, state: GraphState) -> GraphState:
        """This node is used to generate a summary feedback for the entire conversation"""
        # TODO: replace with real prompt
        return {"summary_feedback": "Summary feedback"}

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
