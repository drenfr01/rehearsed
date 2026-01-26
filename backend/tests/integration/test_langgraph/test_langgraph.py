"""Integration tests for LangGraph graph_entry.py class."""

import uuid
from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch,
)

import pytest
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
)
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StateSnapshot

from app.core.langgraph.graph_entry import LangGraphAgent
from app.schemas.chat import Message
from app.schemas.graph import GraphState


@pytest.fixture
def mock_llm():
    """Mock the LLM for LangGraphAgent."""
    mock_llm = AsyncMock()
    mock_llm.model = "test-model"
    mock_llm.model_name = "test-model"
    
    # Mock ainvoke to return a message
    mock_message = AIMessage(content="Test LLM response")
    mock_llm.ainvoke = AsyncMock(return_value=mock_message)
    
    # Mock bind_tools to return self
    mock_llm.bind_tools = MagicMock(return_value=mock_llm)
    
    # Mock with_structured_output
    mock_structured = MagicMock()
    mock_structured.invoke = MagicMock(return_value=MagicMock(
        student_number=1,
        llm_response="Test structured response"
    ))
    mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
    
    return mock_llm


@pytest.fixture
def mock_connection_pool():
    """Mock the PostgreSQL connection pool."""
    mock_pool = AsyncMock()
    mock_pool.connection = MagicMock()
    mock_pool.connection.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
    mock_pool.connection.return_value.__aexit__ = AsyncMock(return_value=None)
    mock_pool.open = AsyncMock()
    
    # Mock connection execute
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_pool.connection.return_value.__aenter__.return_value = mock_conn
    
    return mock_pool


@pytest.fixture
def mock_tts_service():
    """Mock the text-to-speech service."""
    mock_tts = MagicMock()
    mock_tts.synthesize = MagicMock(return_value=b"fake audio bytes")
    return mock_tts


@pytest.fixture
def mock_graph():
    """Mock a CompiledStateGraph."""
    mock_graph = AsyncMock(spec=CompiledStateGraph)
    
    # Mock ainvoke to return a dict (as _hydrate_chat_response expects a dict-like object)
    mock_state_dict = {
        "session_id": "test-session",
        "messages": [AIMessage(content="Test response")],
        "inline_feedback": ["Test feedback"],
        "student_responses": [],
        "answering_student": 0,
        "summary_feedback": "",
    }
    mock_graph.ainvoke = AsyncMock(return_value=mock_state_dict)
    
    # Mock astream
    async def mock_stream(*args, **kwargs):
        mock_message = AIMessage(content="stream")
        yield (mock_message, None)
    mock_graph.astream = mock_stream
    
    # Mock get_state
    mock_snapshot = MagicMock(spec=StateSnapshot)
    mock_snapshot.values = {
        "messages": [HumanMessage(content="Test"), AIMessage(content="Response")]
    }
    mock_graph.get_state = MagicMock(return_value=mock_snapshot)
    
    return mock_graph


@pytest.fixture
def langgraph_agent_with_mocked_llm(mock_llm):
    """Create a LangGraphAgent instance with mocked LLM."""
    with patch("app.core.langgraph.graph_entry.ChatGoogleGenerativeAI") as mock_llm_class:
        mock_llm_class.return_value.bind_tools.return_value = mock_llm
        
        agent = LangGraphAgent()
        # Directly set the mocked LLM
        agent._llm = mock_llm
        return agent


@pytest.mark.integration
@pytest.mark.asyncio
class TestLangGraphAgent:
    """Test LangGraphAgent class methods."""

    async def test_llm_property_lazy_loading(self, mock_llm):
        """Test that LLM is lazy-loaded on first access."""
        with patch("app.core.langgraph.graph_entry.ChatGoogleGenerativeAI") as mock_llm_class:
            mock_llm_class.return_value.bind_tools.return_value = mock_llm
            
            agent = LangGraphAgent()
            assert agent._llm is None
            
            # Access llm property should initialize it
            llm = agent.llm
            assert llm == mock_llm
            assert agent._llm == mock_llm

    async def test_get_response_success(
        self,
        langgraph_agent_with_mocked_llm,
        mock_connection_pool,
        mock_tts_service,
        mock_graph,
        test_scenario,
    ):
        """Test successful get_response call."""
        agent = langgraph_agent_with_mocked_llm
        
        # Mock connection pool and graph creation
        agent._get_connection_pool = AsyncMock(return_value=mock_connection_pool)
        
        with patch("app.core.langgraph.graph_entry.LangGraphBuilder") as mock_builder_class:
            
            mock_builder = AsyncMock()
            mock_builder.build_graph = AsyncMock(return_value=mock_graph)
            mock_builder_class.return_value = mock_builder
            
            messages = [Message(role="user", content="Hello")]
            session_id = str(uuid.uuid4())
            user_id = str(uuid.uuid4())
            
            response = await agent.get_response(
                messages=messages,
                session_id=session_id,
                user_id=user_id,
                scenario_id=test_scenario.id,
                tts_service=mock_tts_service,
            )
            
            assert response is not None
            assert hasattr(response, "messages")
            assert mock_graph.ainvoke.called

    async def test_get_response_graph_creation_failure(
        self,
        langgraph_agent_with_mocked_llm,
        mock_connection_pool,
        mock_tts_service,
        test_scenario,
    ):
        """Test get_response when graph creation fails."""
        agent = langgraph_agent_with_mocked_llm
        agent._get_connection_pool = AsyncMock(return_value=mock_connection_pool)
        
        with patch("app.core.langgraph.graph_entry.LangGraphBuilder") as mock_builder_class:
            mock_builder = AsyncMock()
            mock_builder.build_graph = AsyncMock(return_value=None)
            mock_builder_class.return_value = mock_builder
            
            messages = [Message(role="user", content="Hello")]
            session_id = str(uuid.uuid4())
            user_id = str(uuid.uuid4())
            
            with pytest.raises(Exception, match="Failed to create graph"):
                await agent.get_response(
                    messages=messages,
                    session_id=session_id,
                    user_id=user_id,
                    scenario_id=test_scenario.id,
                    tts_service=mock_tts_service,
                )

    async def test_get_resumption_response_success(
        self,
        langgraph_agent_with_mocked_llm,
        mock_connection_pool,
        mock_tts_service,
        mock_graph,
        test_scenario,
    ):
        """Test successful get_resumption_response call."""
        agent = langgraph_agent_with_mocked_llm
        agent._get_connection_pool = AsyncMock(return_value=mock_connection_pool)
        
        with patch("app.core.langgraph.graph_entry.LangGraphBuilder") as mock_builder_class:
            
            mock_builder = AsyncMock()
            mock_builder.build_graph = AsyncMock(return_value=mock_graph)
            mock_builder_class.return_value = mock_builder
            
            resumption_text = "I want to continue"
            session_id = str(uuid.uuid4())
            user_id = str(uuid.uuid4())
            
            response = await agent.get_resumption_response(
                resumption_text=resumption_text,
                session_id=session_id,
                user_id=user_id,
                scenario_id=test_scenario.id,
                tts_service=mock_tts_service,
            )
            
            assert response is not None
            assert hasattr(response, "messages")
            assert mock_graph.ainvoke.called

    async def test_get_stream_response_success(
        self,
        langgraph_agent_with_mocked_llm,
        mock_connection_pool,
        mock_tts_service,
        mock_graph,
        test_scenario,
    ):
        """Test successful get_stream_response call."""
        agent = langgraph_agent_with_mocked_llm
        agent._get_connection_pool = AsyncMock(return_value=mock_connection_pool)
        
        with patch("app.core.langgraph.graph_entry.LangGraphBuilder") as mock_builder_class:
            
            mock_builder = AsyncMock()
            mock_builder.build_graph = AsyncMock(return_value=mock_graph)
            mock_builder_class.return_value = mock_builder
            
            messages = [Message(role="user", content="Hello")]
            session_id = str(uuid.uuid4())
            user_id = str(uuid.uuid4())
            
            tokens = []
            async for token in agent.get_stream_response(
                messages=messages,
                session_id=session_id,
                user_id=user_id,
                scenario_id=test_scenario.id,
                tts_service=mock_tts_service,
            ):
                tokens.append(token)
            
            assert len(tokens) > 0

    async def test_get_stream_response_missing_params(
        self,
        langgraph_agent_with_mocked_llm,
    ):
        """Test get_stream_response with missing required parameters."""
        agent = langgraph_agent_with_mocked_llm
        messages = [Message(role="user", content="Hello")]
        session_id = str(uuid.uuid4())
        
        with pytest.raises(ValueError, match="scenario_id and tts_service are required"):
            async for _ in agent.get_stream_response(
                messages=messages,
                session_id=session_id,
                user_id=None,
                scenario_id=None,
                tts_service=None,
            ):
                pass

    async def test_get_chat_history_success(
        self,
        langgraph_agent_with_mocked_llm,
        mock_connection_pool,
        mock_tts_service,
        mock_graph,
        test_scenario,
    ):
        """Test successful get_chat_history call."""
        agent = langgraph_agent_with_mocked_llm
        agent._get_connection_pool = AsyncMock(return_value=mock_connection_pool)
        
        with patch("app.core.langgraph.graph_entry.LangGraphBuilder") as mock_builder_class, \
             patch("app.core.langgraph.graph_entry.sync_to_async") as mock_sync_to_async:
            mock_builder = AsyncMock()
            mock_builder.build_graph = AsyncMock(return_value=mock_graph)
            mock_builder_class.return_value = mock_builder
            
            # Mock sync_to_async to return the state directly
            mock_sync_to_async.return_value = AsyncMock(return_value=mock_graph.get_state.return_value)
            
            session_id = str(uuid.uuid4())
            
            history = await agent.get_chat_history(
                session_id=session_id,
                scenario_id=test_scenario.id,
                tts_service=mock_tts_service,
            )
            
            assert isinstance(history, list)
            # Should have processed messages from the mock snapshot
            assert len(history) > 0

    async def test_get_chat_history_no_graph(
        self,
        langgraph_agent_with_mocked_llm,
        mock_connection_pool,
        mock_tts_service,
        test_scenario,
    ):
        """Test get_chat_history when graph creation fails."""
        agent = langgraph_agent_with_mocked_llm
        agent._get_connection_pool = AsyncMock(return_value=mock_connection_pool)
        
        with patch("app.core.langgraph.graph_entry.LangGraphBuilder") as mock_builder_class:
            mock_builder = AsyncMock()
            mock_builder.build_graph = AsyncMock(return_value=None)
            mock_builder_class.return_value = mock_builder
            
            session_id = str(uuid.uuid4())
            
            # Should return empty list when graph is None
            history = await agent.get_chat_history(
                session_id=session_id,
                scenario_id=test_scenario.id,
                tts_service=mock_tts_service,
            )
            
            assert history == []

    async def test_get_chat_history_missing_tts_service(
        self,
        langgraph_agent_with_mocked_llm,
        test_scenario,
    ):
        """Test get_chat_history when tts_service is not provided."""
        agent = langgraph_agent_with_mocked_llm
        
        session_id = str(uuid.uuid4())
        
        # Should raise ValueError when tts_service is None
        with pytest.raises(ValueError, match="tts_service is required"):
            await agent.get_chat_history(
                session_id=session_id,
                scenario_id=test_scenario.id,
                tts_service=None,
            )

    async def test_clear_chat_history_success(
        self,
        langgraph_agent_with_mocked_llm,
        mock_connection_pool,
    ):
        """Test successful clear_chat_history call."""
        agent = langgraph_agent_with_mocked_llm
        agent._get_connection_pool = AsyncMock(return_value=mock_connection_pool)
        
        session_id = str(uuid.uuid4())
        
        # Mock the connection context manager properly
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        
        # Create a proper async context manager
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_connection_pool.connection = MagicMock(return_value=mock_context)
        
        await agent.clear_chat_history(session_id=session_id)
        
        # Verify that execute was called for each checkpoint table
        # There are 3 checkpoint tables by default
        assert mock_conn.execute.call_count >= 1

    async def test_create_graph_success(
        self,
        langgraph_agent_with_mocked_llm,
        mock_connection_pool,
        mock_tts_service,
        mock_graph,
        test_scenario,
    ):
        """Test successful create_graph call."""
        agent = langgraph_agent_with_mocked_llm
        agent._get_connection_pool = AsyncMock(return_value=mock_connection_pool)
        
        with patch("app.core.langgraph.graph_entry.LangGraphBuilder") as mock_builder_class:
            mock_builder = AsyncMock()
            mock_builder.build_graph = AsyncMock(return_value=mock_graph)
            mock_builder_class.return_value = mock_builder
            
            graph = await agent.create_graph(
                scenario_id=test_scenario.id,
                tts_service=mock_tts_service,
            )
            
            assert graph == mock_graph
            assert test_scenario.id in agent._graphs
            assert agent._graphs[test_scenario.id] == mock_graph

    async def test_create_graph_caching(
        self,
        langgraph_agent_with_mocked_llm,
        mock_connection_pool,
        mock_tts_service,
        mock_graph,
        test_scenario,
    ):
        """Test that create_graph caches graphs."""
        agent = langgraph_agent_with_mocked_llm
        agent._get_connection_pool = AsyncMock(return_value=mock_connection_pool)
        
        with patch("app.core.langgraph.graph_entry.LangGraphBuilder") as mock_builder_class:
            mock_builder = AsyncMock()
            mock_builder.build_graph = AsyncMock(return_value=mock_graph)
            mock_builder_class.return_value = mock_builder
            
            # First call should create the graph
            graph1 = await agent.create_graph(
                scenario_id=test_scenario.id,
                tts_service=mock_tts_service,
            )
            
            # Second call should return cached graph
            graph2 = await agent.create_graph(
                scenario_id=test_scenario.id,
                tts_service=mock_tts_service,
            )
            
            assert graph1 == graph2
            # build_graph should only be called once
            assert mock_builder.build_graph.call_count == 1

    async def test_rebuild_graph_success(
        self,
        langgraph_agent_with_mocked_llm,
        mock_connection_pool,
        mock_tts_service,
        mock_graph,
        test_scenario,
    ):
        """Test successful rebuild_graph call."""
        agent = langgraph_agent_with_mocked_llm
        agent._get_connection_pool = AsyncMock(return_value=mock_connection_pool)
        
        # First create a cached graph
        with patch("app.core.langgraph.graph_entry.LangGraphBuilder") as mock_builder_class:
            mock_builder = AsyncMock()
            mock_builder.build_graph = AsyncMock(return_value=mock_graph)
            mock_builder_class.return_value = mock_builder
            
            await agent.create_graph(
                scenario_id=test_scenario.id,
                tts_service=mock_tts_service,
            )
            
            # Reset the mock call count to track only rebuild calls
            mock_builder.build_graph.reset_mock()
            
            # Create a new mock graph for rebuild
            new_mock_graph = AsyncMock(spec=CompiledStateGraph)
            mock_builder.build_graph = AsyncMock(return_value=new_mock_graph)
            
            # Rebuild should create a new graph
            rebuilt_graph = await agent.rebuild_graph(
                scenario_id=test_scenario.id,
                tts_service=mock_tts_service,
            )
            
            assert rebuilt_graph == new_mock_graph
            assert agent._graphs[test_scenario.id] == new_mock_graph
            # build_graph should be called once for rebuild (after reset)
            assert mock_builder.build_graph.call_count == 1

    async def test_invalidate_graph_success(
        self,
        langgraph_agent_with_mocked_llm,
        mock_connection_pool,
        mock_tts_service,
        mock_graph,
        test_scenario,
    ):
        """Test successful invalidate_graph call."""
        agent = langgraph_agent_with_mocked_llm
        agent._get_connection_pool = AsyncMock(return_value=mock_connection_pool)
        
        # First create a cached graph
        with patch("app.core.langgraph.graph_entry.LangGraphBuilder") as mock_builder_class:
            mock_builder = AsyncMock()
            mock_builder.build_graph = AsyncMock(return_value=mock_graph)
            mock_builder_class.return_value = mock_builder
            
            await agent.create_graph(
                scenario_id=test_scenario.id,
                tts_service=mock_tts_service,
            )
            
            assert test_scenario.id in agent._graphs
            
            # Invalidate should remove the graph
            await agent.invalidate_graph(scenario_id=test_scenario.id)
            
            assert test_scenario.id not in agent._graphs

    async def test_invalidate_graph_not_cached(
        self,
        langgraph_agent_with_mocked_llm,
        test_scenario,
    ):
        """Test invalidate_graph when graph is not cached."""
        agent = langgraph_agent_with_mocked_llm
        
        # Should not raise an error if graph is not cached
        await agent.invalidate_graph(scenario_id=test_scenario.id)
        
        assert test_scenario.id not in agent._graphs

    async def test_tool_call_processing(
        self,
        langgraph_agent_with_mocked_llm,
    ):
        """Test _tool_call method processes tool calls correctly."""
        agent = langgraph_agent_with_mocked_llm
        
        # Mock a tool
        mock_tool = AsyncMock()
        mock_tool.ainvoke = AsyncMock(return_value="tool result")
        agent.tools_by_name = {"test_tool": mock_tool}
        
        # Create a state with tool calls
        from langchain_core.messages import AIMessage
        
        tool_call_message = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "test_tool",
                    "args": {"arg1": "value1"},
                    "id": "call_123",
                }
            ],
        )
        
        state = GraphState(
            session_id="test-session",
            messages=[tool_call_message],
        )
        
        result = await agent._tool_call(state)
        
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert mock_tool.ainvoke.called
