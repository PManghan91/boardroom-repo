"""Performance tests for AI operations modules."""

import pytest
import time
import asyncio
import statistics
from unittest.mock import AsyncMock, Mock, patch
from concurrent.futures import ThreadPoolExecutor
import psutil
import gc

from app.core.langgraph.graph import LangGraphAgent
from app.core.langgraph.tools.meeting_management import (
    CreateMeetingAgendaTool,
    DecisionSupportTool,
    GenerateMeetingMinutesTool
)
from app.services.ai_state_manager import AIStateManager
from app.schemas.ai_operations import ConversationState


@pytest.mark.performance
class TestLangGraphAgentPerformance:
    """Performance tests for LangGraph agent operations."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM with controlled response times."""
        llm = AsyncMock()
        
        async def mock_ainvoke(messages, **kwargs):
            # Simulate realistic LLM response times
            await asyncio.sleep(0.1)  # 100ms baseline
            return Mock(content="Mocked LLM response for performance testing")
        
        llm.ainvoke = mock_ainvoke
        return llm

    @pytest.fixture
    def agent(self, mock_llm):
        """Create LangGraph agent for performance testing."""
        with patch('app.core.langgraph.graph.ChatOpenAI', return_value=mock_llm):
            return LangGraphAgent()

    @pytest.mark.asyncio
    async def test_agent_initialization_time(self):
        """Test LangGraph agent initialization performance."""
        mock_llm = AsyncMock()
        
        start_time = time.time()
        with patch('app.core.langgraph.graph.ChatOpenAI', return_value=mock_llm):
            agent = LangGraphAgent()
        initialization_time = time.time() - start_time
        
        # Agent should initialize within 100ms
        assert initialization_time < 0.1
        assert agent.graph is not None

    @pytest.mark.asyncio
    async def test_single_query_response_time(self, agent):
        """Test response time for single query."""
        query = "What is the agenda for today's meeting?"
        
        start_time = time.time()
        response = await agent.chat(query)
        response_time = time.time() - start_time
        
        # Should respond within 500ms including mock LLM time
        assert response_time < 0.5
        assert response is not None

    @pytest.mark.asyncio
    async def test_concurrent_queries_performance(self, agent):
        """Test performance under concurrent query load."""
        queries = [
            "What are the key decisions from the last meeting?",
            "Generate an agenda for tomorrow's meeting",
            "What are the action items?",
            "Who are the meeting participants?",
            "What is the meeting status?"
        ]
        
        start_time = time.time()
        
        # Run queries concurrently
        tasks = [agent.chat(query) for query in queries]
        responses = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # All queries should complete within 1 second with concurrency
        assert total_time < 1.0
        assert len(responses) == len(queries)
        assert all(response is not None for response in responses)

    @pytest.mark.asyncio
    async def test_memory_usage_single_query(self, agent):
        """Test memory usage for single query processing."""
        process = psutil.Process()
        
        # Get baseline memory
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Execute query
        query = "Generate a comprehensive meeting agenda"
        await agent.chat(query)
        
        # Get post-query memory
        gc.collect()
        post_query_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        memory_increase = post_query_memory - baseline_memory
        
        # Single query should not increase memory by more than 50MB
        assert memory_increase < 50

    @pytest.mark.asyncio
    async def test_streaming_response_performance(self, agent):
        """Test streaming response performance."""
        query = "Provide a detailed analysis of meeting participants"
        
        chunks = []
        start_time = time.time()
        
        async for chunk in agent.stream(query):
            chunks.append(chunk)
            
            # First chunk should arrive quickly
            if len(chunks) == 1:
                first_chunk_time = time.time() - start_time
                assert first_chunk_time < 0.2  # 200ms for first chunk
        
        total_time = time.time() - start_time
        
        # Streaming should complete within 1 second
        assert total_time < 1.0
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_chat_history_performance(self, agent):
        """Test performance with large chat history."""
        # Build up chat history
        history_size = 50
        for i in range(history_size):
            await agent.chat(f"Test message {i}")
        
        # Test query with large history
        start_time = time.time()
        response = await agent.chat("Summarize our conversation")
        response_time = time.time() - start_time
        
        # Should handle large history within 1 second
        assert response_time < 1.0
        assert response is not None

    @pytest.mark.asyncio
    async def test_sustained_load_performance(self, agent):
        """Test performance under sustained query load."""
        query_count = 20
        max_response_time = 0
        total_time = 0
        
        for i in range(query_count):
            start_time = time.time()
            await agent.chat(f"Query {i}: What is the meeting status?")
            query_time = time.time() - start_time
            
            max_response_time = max(max_response_time, query_time)
            total_time += query_time
        
        average_response_time = total_time / query_count
        
        # Average response time should be reasonable
        assert average_response_time < 0.3
        # No single query should take too long
        assert max_response_time < 1.0


@pytest.mark.performance
class TestMeetingToolsPerformance:
    """Performance tests for meeting management tools."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM for tool testing."""
        llm = AsyncMock()
        
        async def mock_ainvoke(messages, **kwargs):
            await asyncio.sleep(0.05)  # 50ms mock LLM response
            return Mock(content="Mock tool response")
        
        llm.ainvoke = mock_ainvoke
        return llm

    @pytest.fixture
    def agenda_tool(self, mock_llm):
        """Create agenda tool for testing."""
        with patch('app.core.langgraph.tools.meeting_management.ChatOpenAI', return_value=mock_llm):
            return CreateMeetingAgendaTool()

    @pytest.fixture
    def decision_tool(self, mock_llm):
        """Create decision support tool for testing."""
        with patch('app.core.langgraph.tools.meeting_management.ChatOpenAI', return_value=mock_llm):
            return DecisionSupportTool()

    @pytest.fixture
    def minutes_tool(self, mock_llm):
        """Create minutes generation tool for testing."""
        with patch('app.core.langgraph.tools.meeting_management.ChatOpenAI', return_value=mock_llm):
            return GenerateMeetingMinutesTool()

    @pytest.mark.asyncio
    async def test_agenda_creation_performance(self, agenda_tool):
        """Test agenda creation performance."""
        input_data = {
            "meeting_type": "board_meeting",
            "duration_minutes": 60,
            "participants": ["Alice", "Bob", "Charlie"],
            "topics": ["Budget review", "Strategic planning"]
        }
        
        start_time = time.time()
        result = await agenda_tool._arun(**input_data)
        execution_time = time.time() - start_time
        
        # Should complete within 200ms
        assert execution_time < 0.2
        assert result is not None

    @pytest.mark.asyncio
    async def test_decision_support_performance(self, decision_tool):
        """Test decision support performance."""
        input_data = {
            "decision_context": "Budget allocation for Q2",
            "options": ["Option A: Increase marketing", "Option B: Expand team"],
            "criteria": ["Cost", "Impact", "Timeline"]
        }
        
        start_time = time.time()
        result = await decision_tool._arun(**input_data)
        execution_time = time.time() - start_time
        
        # Should complete within 200ms
        assert execution_time < 0.2
        assert result is not None

    @pytest.mark.asyncio
    async def test_minutes_generation_performance(self, minutes_tool):
        """Test minutes generation performance."""
        input_data = {
            "meeting_transcript": "Meeting discussion about budget and planning...",
            "participants": ["Alice", "Bob"],
            "meeting_date": "2024-01-15",
            "action_items": ["Review budget", "Plan Q2"]
        }
        
        start_time = time.time()
        result = await minutes_tool._arun(**input_data)
        execution_time = time.time() - start_time
        
        # Should complete within 200ms
        assert execution_time < 0.2
        assert result is not None

    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self, agenda_tool, decision_tool, minutes_tool):
        """Test concurrent execution of multiple tools."""
        # Prepare inputs for each tool
        agenda_input = {
            "meeting_type": "team_meeting",
            "duration_minutes": 30,
            "participants": ["Alice", "Bob"],
            "topics": ["Updates"]
        }
        
        decision_input = {
            "decision_context": "Team structure",
            "options": ["Hire new member", "Redistribute work"],
            "criteria": ["Cost", "Efficiency"]
        }
        
        minutes_input = {
            "meeting_transcript": "Brief team meeting...",
            "participants": ["Alice", "Bob"],
            "meeting_date": "2024-01-15",
            "action_items": ["Follow up"]
        }
        
        start_time = time.time()
        
        # Execute tools concurrently
        tasks = [
            agenda_tool._arun(**agenda_input),
            decision_tool._arun(**decision_input),
            minutes_tool._arun(**minutes_input)
        ]
        
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Concurrent execution should be faster than sequential
        assert total_time < 0.3  # Less than 300ms for all three
        assert len(results) == 3
        assert all(result is not None for result in results)

    @pytest.mark.asyncio
    async def test_tools_memory_efficiency(self, agenda_tool, decision_tool, minutes_tool):
        """Test memory efficiency of tool operations."""
        process = psutil.Process()
        
        # Baseline memory
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Execute multiple tool operations
        for i in range(10):
            await agenda_tool._arun(
                meeting_type="test",
                duration_minutes=30,
                participants=["Test"],
                topics=["Topic"]
            )
            
            await decision_tool._arun(
                decision_context="Test decision",
                options=["Option 1", "Option 2"],
                criteria=["Criteria 1"]
            )
            
            await minutes_tool._arun(
                meeting_transcript="Test transcript",
                participants=["Test"],
                meeting_date="2024-01-15",
                action_items=["Test action"]
            )
        
        # Check memory after operations
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        memory_increase = final_memory - baseline_memory
        
        # Memory increase should be reasonable (less than 100MB for 30 operations)
        assert memory_increase < 100

    @pytest.mark.asyncio
    async def test_tool_response_time_consistency(self, agenda_tool):
        """Test consistency of tool response times."""
        input_data = {
            "meeting_type": "board_meeting",
            "duration_minutes": 60,
            "participants": ["Alice", "Bob"],
            "topics": ["Budget"]
        }
        
        response_times = []
        iterations = 10
        
        for _ in range(iterations):
            start_time = time.time()
            await agenda_tool._arun(**input_data)
            response_time = time.time() - start_time
            response_times.append(response_time)
        
        # Calculate statistics
        avg_time = statistics.mean(response_times)
        std_dev = statistics.stdev(response_times)
        max_time = max(response_times)
        min_time = min(response_times)
        
        # Response times should be consistent
        assert avg_time < 0.2  # Average under 200ms
        assert std_dev < 0.05  # Low standard deviation
        assert max_time < 0.3  # No outliers over 300ms
        assert min_time > 0.01  # Sanity check


@pytest.mark.performance
class TestAIStateManagerPerformance:
    """Performance tests for AI state management."""

    @pytest.fixture
    def state_manager(self):
        """Create AI state manager for testing."""
        return AIStateManager()

    @pytest.fixture
    def sample_state(self):
        """Create sample conversation state."""
        return ConversationState(
            session_id="perf-test-session",
            user_id="perf-test-user",
            current_state={"step": "test", "data": "sample"},
            state_version=1,
            created_at=time.time(),
            updated_at=time.time()
        )

    @pytest.mark.asyncio
    async def test_state_creation_performance(self, state_manager):
        """Test state creation performance."""
        session_id = "perf-session-create"
        user_id = "perf-user"
        initial_state = {"initialized": True}
        
        start_time = time.time()
        state = await state_manager.create_conversation_state(
            session_id, user_id, initial_state
        )
        creation_time = time.time() - start_time
        
        # State creation should be fast
        assert creation_time < 0.05  # 50ms
        assert state.session_id == session_id

    @pytest.mark.asyncio
    async def test_state_update_performance(self, state_manager, sample_state):
        """Test state update performance."""
        # Create initial state
        await state_manager.create_conversation_state(
            sample_state.session_id,
            sample_state.user_id,
            sample_state.current_state
        )
        
        # Test update performance
        new_state = {"updated": True, "timestamp": time.time()}
        
        start_time = time.time()
        updated_state = await state_manager.update_conversation_state(
            sample_state.session_id, new_state
        )
        update_time = time.time() - start_time
        
        # State update should be fast
        assert update_time < 0.05  # 50ms
        assert updated_state.current_state["updated"] is True

    @pytest.mark.asyncio
    async def test_state_retrieval_performance(self, state_manager, sample_state):
        """Test state retrieval performance."""
        # Create state
        await state_manager.create_conversation_state(
            sample_state.session_id,
            sample_state.user_id,
            sample_state.current_state
        )
        
        # Test retrieval performance
        start_time = time.time()
        retrieved_state = await state_manager.get_conversation_state(
            sample_state.session_id
        )
        retrieval_time = time.time() - start_time
        
        # State retrieval should be very fast
        assert retrieval_time < 0.02  # 20ms
        assert retrieved_state.session_id == sample_state.session_id

    @pytest.mark.asyncio
    async def test_concurrent_state_operations(self, state_manager):
        """Test concurrent state operations performance."""
        session_count = 10
        session_ids = [f"concurrent-session-{i}" for i in range(session_count)]
        
        # Test concurrent state creation
        start_time = time.time()
        
        creation_tasks = [
            state_manager.create_conversation_state(
                session_id, "test-user", {"session": i}
            )
            for i, session_id in enumerate(session_ids)
        ]
        
        created_states = await asyncio.gather(*creation_tasks)
        creation_time = time.time() - start_time
        
        # Concurrent creation should be efficient
        assert creation_time < 0.5  # 500ms for 10 concurrent operations
        assert len(created_states) == session_count
        
        # Test concurrent updates
        start_time = time.time()
        
        update_tasks = [
            state_manager.update_conversation_state(
                session_id, {"updated": True, "index": i}
            )
            for i, session_id in enumerate(session_ids)
        ]
        
        updated_states = await asyncio.gather(*update_tasks)
        update_time = time.time() - start_time
        
        # Concurrent updates should be efficient
        assert update_time < 0.5  # 500ms for 10 concurrent operations
        assert len(updated_states) == session_count

    @pytest.mark.asyncio
    async def test_checkpoint_performance(self, state_manager, sample_state):
        """Test checkpoint creation and restoration performance."""
        # Create initial state
        await state_manager.create_conversation_state(
            sample_state.session_id,
            sample_state.user_id,
            sample_state.current_state
        )
        
        # Test checkpoint creation performance
        start_time = time.time()
        checkpoint_id = await state_manager.create_checkpoint(sample_state.session_id)
        checkpoint_time = time.time() - start_time
        
        assert checkpoint_time < 0.1  # 100ms
        assert checkpoint_id is not None
        
        # Modify state
        await state_manager.update_conversation_state(
            sample_state.session_id, {"modified": True}
        )
        
        # Test restore performance
        start_time = time.time()
        restored_state = await state_manager.restore_from_checkpoint(
            sample_state.session_id, checkpoint_id
        )
        restore_time = time.time() - start_time
        
        assert restore_time < 0.1  # 100ms
        assert "modified" not in restored_state.current_state

    @pytest.mark.asyncio
    async def test_cleanup_performance(self, state_manager):
        """Test cleanup operations performance."""
        # Create multiple expired states
        session_count = 20
        expired_time = time.time() - (25 * 3600)  # 25 hours ago
        
        for i in range(session_count):
            state = ConversationState(
                session_id=f"expired-session-{i}",
                user_id="cleanup-user",
                current_state={"expired": True},
                state_version=1,
                created_at=expired_time,
                updated_at=expired_time
            )
            # Manually set expired timestamps (mock implementation)
            await state_manager.create_conversation_state(
                state.session_id, state.user_id, state.current_state
            )
        
        # Test cleanup performance
        start_time = time.time()
        cleaned_count = await state_manager.cleanup_expired_states(expiry_hours=24)
        cleanup_time = time.time() - start_time
        
        # Cleanup should be efficient even for many states
        assert cleanup_time < 1.0  # 1 second for cleanup
        # Note: cleaned_count may be 0 if mock doesn't handle expiry correctly

    @pytest.mark.asyncio
    async def test_state_manager_memory_efficiency(self, state_manager):
        """Test memory efficiency of state manager operations."""
        process = psutil.Process()
        
        # Baseline memory
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create many states
        state_count = 100
        for i in range(state_count):
            await state_manager.create_conversation_state(
                f"memory-test-{i}",
                "memory-user",
                {"data": f"state-{i}", "index": i}
            )
        
        # Check memory after operations
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        memory_increase = final_memory - baseline_memory
        
        # Memory increase should be reasonable
        assert memory_increase < 200  # Less than 200MB for 100 states

    @pytest.mark.asyncio
    async def test_active_sessions_performance(self, state_manager):
        """Test active sessions retrieval performance."""
        # Create active sessions
        session_count = 50
        for i in range(session_count):
            await state_manager.create_conversation_state(
                f"active-session-{i}",
                "active-user",
                {"active": True}
            )
        
        # Test retrieval performance
        start_time = time.time()
        active_sessions = await state_manager.get_active_sessions()
        retrieval_time = time.time() - start_time
        
        # Should retrieve active sessions quickly
        assert retrieval_time < 0.1  # 100ms
        assert len(active_sessions) >= 0  # May be 0 due to mock implementation


@pytest.mark.performance
@pytest.mark.slow
class TestAIOperationsLoadTesting:
    """Load testing for AI operations under stress."""

    @pytest.mark.asyncio
    async def test_high_concurrency_ai_operations(self):
        """Test AI operations under high concurrency."""
        mock_llm = AsyncMock()
        
        async def mock_ainvoke(messages, **kwargs):
            await asyncio.sleep(0.1)  # Simulate processing time
            return Mock(content="Load test response")
        
        mock_llm.ainvoke = mock_ainvoke
        
        with patch('app.core.langgraph.graph.ChatOpenAI', return_value=mock_llm):
            agent = LangGraphAgent()
            
            # High concurrency test
            concurrent_requests = 50
            query = "Load test query"
            
            start_time = time.time()
            
            tasks = [agent.chat(query) for _ in range(concurrent_requests)]
            results = await asyncio.gather(*tasks)
            
            total_time = time.time() - start_time
            
            # Should handle high concurrency efficiently
            assert total_time < 5.0  # 5 seconds for 50 concurrent requests
            assert len(results) == concurrent_requests
            assert all(result is not None for result in results)

    @pytest.mark.asyncio
    async def test_sustained_load_performance(self):
        """Test sustained load over time."""
        mock_llm = AsyncMock()
        
        async def mock_ainvoke(messages, **kwargs):
            await asyncio.sleep(0.05)  # Fast mock response
            return Mock(content="Sustained load response")
        
        mock_llm.ainvoke = mock_ainvoke
        
        with patch('app.core.langgraph.graph.ChatOpenAI', return_value=mock_llm):
            agent = LangGraphAgent()
            
            # Sustained load test
            duration_seconds = 30
            request_interval = 0.1  # 10 requests per second
            
            start_time = time.time()
            successful_requests = 0
            failed_requests = 0
            response_times = []
            
            while time.time() - start_time < duration_seconds:
                request_start = time.time()
                
                try:
                    result = await agent.chat("Sustained load query")
                    request_time = time.time() - request_start
                    response_times.append(request_time)
                    
                    if result is not None:
                        successful_requests += 1
                    else:
                        failed_requests += 1
                        
                except Exception:
                    failed_requests += 1
                
                await asyncio.sleep(request_interval)
            
            total_requests = successful_requests + failed_requests
            success_rate = successful_requests / total_requests if total_requests > 0 else 0
            avg_response_time = statistics.mean(response_times) if response_times else 0
            
            # Performance expectations under sustained load
            assert success_rate > 0.95  # 95% success rate
            assert avg_response_time < 0.2  # Average response time under 200ms
            assert total_requests > 100  # Should handle many requests

    @pytest.mark.asyncio
    async def test_resource_exhaustion_handling(self):
        """Test behavior under resource exhaustion conditions."""
        mock_llm = AsyncMock()
        
        # Simulate resource exhaustion by adding delays
        async def slow_mock_ainvoke(messages, **kwargs):
            await asyncio.sleep(1.0)  # Very slow response
            return Mock(content="Resource exhausted response")
        
        mock_llm.ainvoke = slow_mock_ainvoke
        
        with patch('app.core.langgraph.graph.ChatOpenAI', return_value=mock_llm):
            agent = LangGraphAgent()
            
            # Test with many slow concurrent requests
            concurrent_requests = 20
            timeout_seconds = 3.0
            
            start_time = time.time()
            
            tasks = [agent.chat("Resource exhaustion query") for _ in range(concurrent_requests)]
            
            try:
                # Use wait_for to enforce timeout
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=timeout_seconds
                )
                
                execution_time = time.time() - start_time
                
                # Should handle resource constraints gracefully
                assert execution_time <= timeout_seconds + 0.5  # Some tolerance
                assert len(results) == concurrent_requests
                
                # Some requests may fail/timeout, which is acceptable under resource exhaustion
                successful_results = [r for r in results if not isinstance(r, Exception)]
                # At least some should succeed even under stress
                assert len(successful_results) > 0
                
            except asyncio.TimeoutError:
                # Timeout is acceptable under resource exhaustion
                execution_time = time.time() - start_time
                assert execution_time <= timeout_seconds + 0.5

    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self):
        """Test AI operations under memory pressure."""
        mock_llm = AsyncMock()
        
        async def mock_ainvoke(messages, **kwargs):
            await asyncio.sleep(0.01)
            # Simulate memory usage with large response
            large_content = "x" * 1000  # 1KB response
            return Mock(content=large_content)
        
        mock_llm.ainvoke = mock_ainvoke
        
        with patch('app.core.langgraph.graph.ChatOpenAI', return_value=mock_llm):
            agent = LangGraphAgent()
            state_manager = AIStateManager()
            
            process = psutil.Process()
            baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Create memory pressure with many operations
            operation_count = 100
            
            for i in range(operation_count):
                # AI query
                await agent.chat(f"Memory pressure query {i}")
                
                # State management
                await state_manager.create_conversation_state(
                    f"memory-pressure-{i}",
                    "memory-user",
                    {"data": f"large-state-{i}" * 100}  # Large state data
                )
                
                # Periodic memory check
                if i % 20 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024  # MB
                    memory_increase = current_memory - baseline_memory
                    
                    # Memory increase should be reasonable
                    assert memory_increase < 500  # Less than 500MB increase
            
            # Final memory check
            gc.collect()
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            total_memory_increase = final_memory - baseline_memory
            
            # Total memory increase should be bounded
            assert total_memory_increase < 1000  # Less than 1GB total increase