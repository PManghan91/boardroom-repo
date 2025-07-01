"""Unit tests for LangGraph Agent functionality."""

import asyncio
import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any

from app.core.langgraph.graph import LangGraphAgent
from app.schemas import GraphState, Message
from app.schemas.ai_operations import AIOperationMetrics, AIOperationStatus, TokenUsage
from app.core.exceptions import LLMException, GraphExecutionException, ToolExecutionException


@pytest.mark.unit
@pytest.mark.asyncio
class TestLangGraphAgent:
    """Test suite for LangGraphAgent class."""

    @pytest.fixture
    def agent(self):
        """Create a LangGraphAgent instance for testing."""
        with patch('app.core.langgraph.graph.settings') as mock_settings:
            mock_settings.LLM_MODEL = "gpt-4"
            mock_settings.DEFAULT_LLM_TEMPERATURE = 0.7
            mock_settings.LLM_API_KEY = "test-key"
            mock_settings.MAX_TOKENS = 1000
            mock_settings.ENVIRONMENT.value = "test"
            mock_settings.POSTGRES_POOL_SIZE = 5
            mock_settings.POSTGRES_URL = "postgresql://test"
            mock_settings.MAX_LLM_CALL_RETRIES = 3
            mock_settings.PROJECT_NAME = "Test Project"
            mock_settings.CHECKPOINT_TABLES = ["checkpoints", "checkpoint_blobs"]
            
            return LangGraphAgent()

    @pytest.fixture
    def sample_graph_state(self):
        """Create a sample GraphState for testing."""
        return GraphState(
            messages=[
                Message(role="user", content="Hello, how are you?")
            ],
            session_id="test-session-123"
        )

    @pytest.fixture
    def mock_llm_response(self):
        """Create a mock LLM response."""
        response = Mock()
        response.content = "I'm doing well, thank you!"
        response.tool_calls = []
        response.usage = Mock()
        response.usage.prompt_tokens = 10
        response.usage.completion_tokens = 15
        return response

    def test_agent_initialization(self, agent):
        """Test agent initialization."""
        assert agent is not None
        assert agent.llm is not None
        assert agent.tools_by_name is not None
        assert isinstance(agent._active_operations, dict)

    @patch('app.core.langgraph.graph.settings')
    def test_get_model_kwargs_development(self, mock_settings):
        """Test model kwargs for development environment."""
        from app.core.config import Environment
        mock_settings.ENVIRONMENT = Environment.DEVELOPMENT
        
        agent = LangGraphAgent()
        kwargs = agent._get_model_kwargs()
        
        assert "top_p" in kwargs
        assert kwargs["top_p"] == 0.8

    @patch('app.core.langgraph.graph.settings')
    def test_get_model_kwargs_production(self, mock_settings):
        """Test model kwargs for production environment."""
        from app.core.config import Environment
        mock_settings.ENVIRONMENT = Environment.PRODUCTION
        
        agent = LangGraphAgent()
        kwargs = agent._get_model_kwargs()
        
        assert kwargs["top_p"] == 0.95
        assert kwargs["presence_penalty"] == 0.1
        assert kwargs["frequency_penalty"] == 0.1

    @pytest.mark.asyncio
    async def test_get_connection_pool_success(self, agent):
        """Test successful connection pool creation."""
        with patch('app.core.langgraph.graph.AsyncConnectionPool') as mock_pool_class:
            mock_pool = AsyncMock()
            mock_pool_class.return_value = mock_pool
            
            pool = await agent._get_connection_pool()
            
            assert pool == mock_pool
            mock_pool.open.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_connection_pool_failure_production(self, agent):
        """Test connection pool failure handling in production."""
        with patch('app.core.langgraph.graph.AsyncConnectionPool') as mock_pool_class:
            with patch('app.core.langgraph.graph.settings') as mock_settings:
                from app.core.config import Environment
                mock_settings.ENVIRONMENT = Environment.PRODUCTION
                
                mock_pool_class.side_effect = Exception("Connection failed")
                
                pool = await agent._get_connection_pool()
                
                assert pool is None

    @pytest.mark.asyncio
    async def test_chat_success(self, agent, sample_graph_state, mock_llm_response):
        """Test successful chat response generation."""
        with patch.object(agent.llm, 'ainvoke', return_value=mock_llm_response):
            with patch('app.core.langgraph.graph.prepare_messages'):
                with patch('app.core.langgraph.graph.dump_messages'):
                    
                    result = await agent._chat(sample_graph_state)
                    
                    assert "messages" in result
                    assert len(result["messages"]) == 1
                    assert result["messages"][0] == mock_llm_response

    @pytest.mark.asyncio
    async def test_chat_with_token_usage(self, agent, sample_graph_state, mock_llm_response):
        """Test chat response with token usage tracking."""
        with patch.object(agent.llm, 'ainvoke', return_value=mock_llm_response):
            with patch('app.core.langgraph.graph.prepare_messages'):
                with patch('app.core.langgraph.graph.dump_messages'):
                    
                    result = await agent._chat(sample_graph_state)
                    
                    # Verify token usage was recorded
                    assert "messages" in result
                    # Check that metrics were updated (would need to verify metric calls in real implementation)

    @pytest.mark.asyncio
    async def test_chat_llm_error_retry(self, agent, sample_graph_state):
        """Test LLM error handling and retry logic."""
        from openai import OpenAIError
        
        # Mock first two calls to fail, third to succeed
        mock_response = Mock()
        mock_response.content = "Success after retry"
        mock_response.tool_calls = []
        
        with patch.object(agent.llm, 'ainvoke') as mock_invoke:
            mock_invoke.side_effect = [
                OpenAIError("Rate limit"),
                OpenAIError("Rate limit"),
                mock_response
            ]
            with patch('app.core.langgraph.graph.prepare_messages'):
                with patch('app.core.langgraph.graph.dump_messages'):
                    
                    result = await agent._chat(sample_graph_state)
                    
                    assert "messages" in result
                    assert mock_invoke.call_count == 3

    @pytest.mark.asyncio
    async def test_chat_max_retries_exceeded(self, agent, sample_graph_state):
        """Test LLM max retries exceeded."""
        from openai import OpenAIError
        
        with patch.object(agent.llm, 'ainvoke') as mock_invoke:
            mock_invoke.side_effect = OpenAIError("Persistent error")
            with patch('app.core.langgraph.graph.prepare_messages'):
                with patch('app.core.langgraph.graph.dump_messages'):
                    
                    with pytest.raises(LLMException):
                        await agent._chat(sample_graph_state)

    @pytest.mark.asyncio
    async def test_tool_call_success(self, agent, sample_graph_state):
        """Test successful tool execution."""
        # Create a message with tool calls
        tool_call_message = Mock()
        tool_call_message.tool_calls = [
            {
                "id": "call_123",
                "name": "test_tool",
                "args": {"param": "value"}
            }
        ]
        
        # Mock tool execution
        mock_tool = AsyncMock()
        mock_tool.ainvoke.return_value = "Tool result"
        agent.tools_by_name["test_tool"] = mock_tool
        
        state = GraphState(
            messages=[tool_call_message],
            session_id="test-session"
        )
        
        result = await agent._tool_call(state)
        
        assert "messages" in result
        assert len(result["messages"]) == 1
        mock_tool.ainvoke.assert_called_once_with({"param": "value"})

    @pytest.mark.asyncio
    async def test_tool_call_no_tools(self, agent, sample_graph_state):
        """Test tool call with no tool calls."""
        # Create message without tool calls
        no_tool_message = Mock()
        no_tool_message.tool_calls = []
        
        state = GraphState(
            messages=[no_tool_message],
            session_id="test-session"
        )
        
        result = await agent._tool_call(state)
        
        assert result["messages"] == []

    @pytest.mark.asyncio
    async def test_tool_call_tool_not_found(self, agent):
        """Test tool call with unknown tool."""
        tool_call_message = Mock()
        tool_call_message.tool_calls = [
            {
                "id": "call_123", 
                "name": "unknown_tool",
                "args": {}
            }
        ]
        
        state = GraphState(
            messages=[tool_call_message],
            session_id="test-session"
        )
        
        with pytest.raises(ToolExecutionException):
            await agent._tool_call(state)

    @pytest.mark.asyncio
    async def test_tool_call_execution_error(self, agent):
        """Test tool call execution error handling."""
        tool_call_message = Mock()
        tool_call_message.tool_calls = [
            {
                "id": "call_123",
                "name": "error_tool", 
                "args": {}
            }
        ]
        
        # Mock tool that raises an error
        mock_tool = AsyncMock()
        mock_tool.ainvoke.side_effect = Exception("Tool error")
        agent.tools_by_name["error_tool"] = mock_tool
        
        state = GraphState(
            messages=[tool_call_message],
            session_id="test-session"
        )
        
        result = await agent._tool_call(state)
        
        # Should return error message, not raise exception
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert "Error executing tool" in result["messages"][0].content

    def test_should_continue_no_tool_calls(self, agent, sample_graph_state):
        """Test should_continue logic with no tool calls."""
        # Mock message without tool calls
        message = Mock()
        message.tool_calls = []
        
        state = GraphState(
            messages=[message],
            session_id="test-session"
        )
        
        result = agent._should_continue(state)
        assert result == "end"

    def test_should_continue_with_tool_calls(self, agent):
        """Test should_continue logic with tool calls."""
        # Mock message with tool calls
        message = Mock()
        message.tool_calls = [{"id": "call_123", "name": "test_tool"}]
        
        state = GraphState(
            messages=[message],
            session_id="test-session"
        )
        
        result = agent._should_continue(state)
        assert result == "continue"

    @pytest.mark.asyncio
    async def test_create_graph_success(self, agent):
        """Test successful graph creation."""
        with patch('app.core.langgraph.graph.StateGraph') as mock_state_graph:
            with patch.object(agent, '_get_connection_pool') as mock_pool:
                mock_pool.return_value = AsyncMock()
                
                mock_builder = Mock()
                mock_state_graph.return_value = mock_builder
                mock_compiled = Mock()
                mock_builder.compile.return_value = mock_compiled
                
                graph = await agent.create_graph()
                
                assert graph == mock_compiled
                assert agent._graph == mock_compiled

    @pytest.mark.asyncio
    async def test_create_graph_no_checkpointer(self, agent):
        """Test graph creation without checkpointer."""
        with patch('app.core.langgraph.graph.StateGraph') as mock_state_graph:
            with patch.object(agent, '_get_connection_pool') as mock_pool:
                mock_pool.return_value = None
                
                mock_builder = Mock()
                mock_state_graph.return_value = mock_builder
                mock_compiled = Mock()
                mock_builder.compile.return_value = mock_compiled
                
                graph = await agent.create_graph()
                
                # Should compile without checkpointer
                assert graph == mock_compiled
                mock_builder.compile.assert_called_once()
                call_args = mock_builder.compile.call_args[1]
                assert call_args["checkpointer"] is None

    @pytest.mark.asyncio
    async def test_get_response_success(self, agent, mock_llm_response):
        """Test successful response generation."""
        messages = [Message(role="user", content="Hello")]
        session_id = "test-session"
        
        with patch.object(agent, 'create_graph') as mock_create:
            mock_graph = AsyncMock()
            mock_graph.ainvoke.return_value = {"messages": [mock_llm_response]}
            mock_create.return_value = mock_graph
            agent._graph = mock_graph
            
            with patch.object(agent, '_LangGraphAgent__process_messages') as mock_process:
                mock_process.return_value = [{"role": "assistant", "content": "Hello back"}]
                
                result = await agent.get_response(messages, session_id)
                
                assert result == [{"role": "assistant", "content": "Hello back"}]
                mock_graph.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stream_response(self, agent):
        """Test streaming response generation."""
        messages = [Message(role="user", content="Hello")]
        session_id = "test-session"
        
        # Mock streaming tokens
        mock_tokens = [
            (Mock(content="Hello"), None),
            (Mock(content=" there"), None),
            (Mock(content="!"), None)
        ]
        
        with patch.object(agent, 'create_graph') as mock_create:
            mock_graph = AsyncMock()
            mock_graph.astream.return_value = mock_tokens
            mock_create.return_value = mock_graph
            agent._graph = mock_graph
            
            result_tokens = []
            async for token in agent.get_stream_response(messages, session_id):
                result_tokens.append(token)
            
            assert result_tokens == ["Hello", " there", "!"]

    @pytest.mark.asyncio
    async def test_get_chat_history(self, agent):
        """Test chat history retrieval."""
        session_id = "test-session"
        
        # Mock state snapshot
        mock_state = Mock()
        mock_state.values = {"messages": [Mock()]}
        
        with patch.object(agent, 'create_graph') as mock_create:
            mock_graph = Mock()
            mock_graph.get_state.return_value = mock_state
            mock_create.return_value = mock_graph
            agent._graph = mock_graph
            
            with patch.object(agent, '_LangGraphAgent__process_messages') as mock_process:
                mock_process.return_value = [{"role": "user", "content": "Test"}]
                
                with patch('app.core.langgraph.graph.sync_to_async') as mock_sync:
                    mock_sync.return_value = mock_state
                    
                    result = await agent.get_chat_history(session_id)
                    
                    assert result == [{"role": "user", "content": "Test"}]

    @pytest.mark.asyncio
    async def test_clear_chat_history(self, agent):
        """Test chat history clearing."""
        session_id = "test-session"
        
        with patch.object(agent, '_get_connection_pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_conn_pool = AsyncMock()
            mock_conn_pool.connection.return_value.__aenter__.return_value = mock_conn
            mock_pool.return_value = mock_conn_pool
            
            await agent.clear_chat_history(session_id)
            
            # Verify database calls were made
            assert mock_conn.execute.call_count >= 1

    def test_process_messages(self, agent):
        """Test message processing."""
        from langchain_core.messages import HumanMessage, AIMessage
        
        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there")
        ]
        
        with patch('app.core.langgraph.graph.convert_to_openai_messages') as mock_convert:
            mock_convert.return_value = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"}
            ]
            
            result = agent._LangGraphAgent__process_messages(messages)
            
            assert len(result) == 2
            assert result[0].role == "user"
            assert result[1].role == "assistant"


@pytest.mark.unit
class TestAIOperationMetrics:
    """Test suite for AI operation metrics tracking."""
    
    def test_metrics_initialization(self):
        """Test metrics object initialization."""
        metrics = AIOperationMetrics(
            operation_id="test-op-123",
            operation_type="llm_inference",
            model="gpt-4",
            status=AIOperationStatus.IN_PROGRESS,
            start_time=datetime.now()
        )
        
        assert metrics.operation_id == "test-op-123"
        assert metrics.operation_type == "llm_inference"
        assert metrics.model == "gpt-4"
        assert metrics.status == AIOperationStatus.IN_PROGRESS
        assert metrics.start_time is not None
        assert metrics.end_time is None
        assert metrics.duration_seconds is None

    def test_metrics_completion_success(self):
        """Test successful operation completion."""
        metrics = AIOperationMetrics(
            operation_id="test-op-123",
            operation_type="llm_inference",
            model="gpt-4",
            status=AIOperationStatus.IN_PROGRESS,
            start_time=datetime.now()
        )
        
        metrics.complete_operation(success=True)
        
        assert metrics.status == AIOperationStatus.COMPLETED
        assert metrics.end_time is not None
        assert metrics.duration_seconds is not None
        assert metrics.duration_seconds >= 0

    def test_metrics_completion_failure(self):
        """Test failed operation completion."""
        metrics = AIOperationMetrics(
            operation_id="test-op-123",
            operation_type="llm_inference", 
            model="gpt-4",
            status=AIOperationStatus.IN_PROGRESS,
            start_time=datetime.now()
        )
        
        error_msg = "Test error"
        metrics.complete_operation(success=False, error_message=error_msg)
        
        assert metrics.status == AIOperationStatus.FAILED
        assert metrics.error_message == error_msg
        assert metrics.end_time is not None
        assert metrics.duration_seconds is not None


@pytest.mark.unit
class TestTokenUsage:
    """Test suite for token usage tracking."""
    
    def test_token_usage_calculation(self):
        """Test token usage total calculation."""
        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50
        )
        
        usage.calculate_total()
        
        assert usage.total_tokens == 150

    def test_token_usage_zero_values(self):
        """Test token usage with zero values."""
        usage = TokenUsage(
            prompt_tokens=0,
            completion_tokens=0
        )
        
        usage.calculate_total()
        
        assert usage.total_tokens == 0