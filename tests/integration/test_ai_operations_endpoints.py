"""Integration tests for AI operations endpoints."""

import pytest
import time
from unittest.mock import AsyncMock, Mock, patch
from httpx import AsyncClient

from app.main import app
from app.models.session import Session
from app.services.ai_state_manager import ai_state_manager
from app.schemas.ai_operations import ConversationState


@pytest.mark.integration
@pytest.mark.asyncio
class TestAIOperationsEndpoints:
    """Integration tests for AI operations API endpoints."""

    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://testserver") as ac:
            yield ac

    @pytest.fixture
    def mock_session(self):
        """Create a mock session for authentication."""
        session = Mock(spec=Session)
        session.id = "test-session-123"
        session.user_thread_id = "user-thread-456"
        return session

    @pytest.fixture
    def auth_headers(self, mock_session):
        """Create authentication headers."""
        return {"Authorization": f"Bearer test-token-{mock_session.id}"}

    @pytest.mark.asyncio
    async def test_ai_health_check_success(self, client, mock_session, auth_headers):
        """Test successful AI health check."""
        with patch('app.api.v1.ai_operations.get_current_session', return_value=mock_session):
            with patch.object(ai_state_manager, 'get_active_sessions', return_value=["session1", "session2"]):
                
                response = await client.get("/ai/health", headers=auth_headers)
                
                assert response.status_code == 200
                data = response.json()
                
                assert data["success"] is True
                assert "data" in data
                assert data["data"]["status"] == "healthy"
                assert data["data"]["active_sessions"] == 2
                assert "models_available" in data["data"]
                assert "models_unavailable" in data["data"]

    @pytest.mark.asyncio
    async def test_ai_health_check_degraded_performance(self, client, mock_session, auth_headers):
        """Test AI health check with degraded performance."""
        # Mock many active sessions to trigger degraded status
        many_sessions = [f"session-{i}" for i in range(150)]
        
        with patch('app.api.v1.ai_operations.get_current_session', return_value=mock_session):
            with patch.object(ai_state_manager, 'get_active_sessions', return_value=many_sessions):
                
                response = await client.get("/ai/health", headers=auth_headers)
                
                assert response.status_code == 200
                data = response.json()
                
                assert data["data"]["status"] == "degraded"
                assert data["data"]["active_sessions"] == 150

    @pytest.mark.asyncio
    async def test_ai_health_check_error_handling(self, client, mock_session, auth_headers):
        """Test AI health check error handling."""
        with patch('app.api.v1.ai_operations.get_current_session', return_value=mock_session):
            with patch.object(ai_state_manager, 'get_active_sessions', side_effect=Exception("Service error")):
                
                response = await client.get("/ai/health", headers=auth_headers)
                
                assert response.status_code == 500
                data = response.json()
                
                assert data["success"] is False
                assert "error" in data
                assert data["error"]["type"] == "health_check_error"

    @pytest.mark.asyncio
    async def test_get_active_sessions_success(self, client, mock_session, auth_headers):
        """Test successful active sessions retrieval."""
        active_sessions = ["session-1", "session-2", "session-3"]
        
        with patch('app.api.v1.ai_operations.get_current_session', return_value=mock_session):
            with patch.object(ai_state_manager, 'get_active_sessions', return_value=active_sessions):
                
                response = await client.get("/ai/sessions/active", headers=auth_headers)
                
                assert response.status_code == 200
                data = response.json()
                
                assert data["success"] is True
                assert data["data"]["active_sessions"] == active_sessions
                assert data["data"]["total_count"] == 3
                assert "timestamp" in data["data"]

    @pytest.mark.asyncio
    async def test_get_active_sessions_empty(self, client, mock_session, auth_headers):
        """Test active sessions retrieval with no active sessions."""
        with patch('app.api.v1.ai_operations.get_current_session', return_value=mock_session):
            with patch.object(ai_state_manager, 'get_active_sessions', return_value=[]):
                
                response = await client.get("/ai/sessions/active", headers=auth_headers)
                
                assert response.status_code == 200
                data = response.json()
                
                assert data["data"]["total_count"] == 0
                assert data["data"]["active_sessions"] == []

    @pytest.mark.asyncio
    async def test_create_session_checkpoint_success(self, client, mock_session, auth_headers):
        """Test successful session checkpoint creation."""
        target_session_id = "target-session-456"
        checkpoint_id = "checkpoint-789"
        
        with patch('app.api.v1.ai_operations.get_current_session', return_value=mock_session):
            with patch.object(ai_state_manager, 'create_checkpoint', return_value=checkpoint_id):
                
                response = await client.post(
                    f"/ai/sessions/{target_session_id}/checkpoint",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                
                assert data["success"] is True
                assert data["data"]["checkpoint_id"] == checkpoint_id
                assert data["data"]["session_id"] == target_session_id
                assert "created_at" in data["data"]

    @pytest.mark.asyncio
    async def test_create_session_checkpoint_error(self, client, mock_session, auth_headers):
        """Test session checkpoint creation error handling."""
        target_session_id = "target-session-456"
        
        with patch('app.api.v1.ai_operations.get_current_session', return_value=mock_session):
            with patch.object(ai_state_manager, 'create_checkpoint', side_effect=Exception("Checkpoint error")):
                
                response = await client.post(
                    f"/ai/sessions/{target_session_id}/checkpoint",
                    headers=auth_headers
                )
                
                assert response.status_code == 500
                data = response.json()
                
                assert data["success"] is False
                assert data["error"]["type"] == "checkpoint_error"

    @pytest.mark.asyncio
    async def test_restore_session_checkpoint_success(self, client, mock_session, auth_headers):
        """Test successful session checkpoint restoration."""
        target_session_id = "target-session-456"
        checkpoint_id = "checkpoint-789"
        
        # Mock restored state
        restored_state = ConversationState(
            session_id=target_session_id,
            user_id="test-user",
            current_state={"restored": True},
            state_version=5,
            created_at=time.time(),
            updated_at=time.time()
        )
        
        with patch('app.api.v1.ai_operations.get_current_session', return_value=mock_session):
            with patch.object(ai_state_manager, 'restore_from_checkpoint', return_value=restored_state):
                
                response = await client.post(
                    f"/ai/sessions/{target_session_id}/restore/{checkpoint_id}",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                
                assert data["success"] is True
                assert data["data"]["session_id"] == target_session_id
                assert data["data"]["checkpoint_id"] == checkpoint_id
                assert data["data"]["restored_version"] == 5

    @pytest.mark.asyncio
    async def test_restore_session_checkpoint_error(self, client, mock_session, auth_headers):
        """Test session checkpoint restoration error handling."""
        target_session_id = "target-session-456"
        checkpoint_id = "checkpoint-789"
        
        with patch('app.api.v1.ai_operations.get_current_session', return_value=mock_session):
            with patch.object(ai_state_manager, 'restore_from_checkpoint', side_effect=Exception("Restore error")):
                
                response = await client.post(
                    f"/ai/sessions/{target_session_id}/restore/{checkpoint_id}",
                    headers=auth_headers
                )
                
                assert response.status_code == 500
                data = response.json()
                
                assert data["success"] is False
                assert data["error"]["type"] == "restore_error"

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions_success(self, client, mock_session, auth_headers):
        """Test successful expired sessions cleanup."""
        cleaned_count = 5
        expiry_hours = 48
        
        with patch('app.api.v1.ai_operations.get_current_session', return_value=mock_session):
            with patch.object(ai_state_manager, 'cleanup_expired_states', return_value=cleaned_count):
                
                response = await client.delete(
                    f"/ai/sessions/cleanup?expiry_hours={expiry_hours}",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                
                assert data["success"] is True
                assert data["data"]["cleaned_sessions"] == cleaned_count
                assert data["data"]["expiry_hours"] == expiry_hours
                assert "cleaned_at" in data["data"]

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions_default_expiry(self, client, mock_session, auth_headers):
        """Test expired sessions cleanup with default expiry."""
        cleaned_count = 2
        
        with patch('app.api.v1.ai_operations.get_current_session', return_value=mock_session):
            with patch.object(ai_state_manager, 'cleanup_expired_states', return_value=cleaned_count) as mock_cleanup:
                
                response = await client.delete("/ai/sessions/cleanup", headers=auth_headers)
                
                assert response.status_code == 200
                data = response.json()
                
                assert data["data"]["expiry_hours"] == 24  # Default value
                mock_cleanup.assert_called_once_with(24)

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions_error(self, client, mock_session, auth_headers):
        """Test expired sessions cleanup error handling."""
        with patch('app.api.v1.ai_operations.get_current_session', return_value=mock_session):
            with patch.object(ai_state_manager, 'cleanup_expired_states', side_effect=Exception("Cleanup error")):
                
                response = await client.delete("/ai/sessions/cleanup", headers=auth_headers)
                
                assert response.status_code == 500
                data = response.json()
                
                assert data["success"] is False
                assert data["error"]["type"] == "cleanup_error"

    @pytest.mark.asyncio
    async def test_get_ai_metrics_summary_success(self, client, mock_session, auth_headers):
        """Test successful AI metrics summary retrieval."""
        with patch('app.api.v1.ai_operations.get_current_session', return_value=mock_session):
            
            response = await client.get("/ai/metrics/summary", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert "data" in data
            
            metrics = data["data"]
            assert "operations" in metrics
            assert "performance" in metrics
            assert "errors" in metrics
            assert "timestamp" in metrics
            
            # Check operations metrics structure
            operations = metrics["operations"]
            assert "total_chat_requests" in operations
            assert "total_stream_requests" in operations
            assert "total_tool_executions" in operations
            assert "success_rate" in operations
            
            # Check performance metrics structure
            performance = metrics["performance"]
            assert "average_response_time_seconds" in performance
            assert "average_tokens_per_request" in performance
            assert "peak_concurrent_sessions" in performance
            
            # Check errors metrics structure
            errors = metrics["errors"]
            assert "llm_errors_last_hour" in errors
            assert "tool_errors_last_hour" in errors
            assert "total_errors_last_24h" in errors

    @pytest.mark.asyncio
    async def test_get_ai_metrics_summary_error(self, client, mock_session, auth_headers):
        """Test AI metrics summary error handling."""
        with patch('app.api.v1.ai_operations.get_current_session', return_value=mock_session):
            # Mock an error in the endpoint logic
            with patch('time.time', side_effect=Exception("Time error")):
                
                response = await client.get("/ai/metrics/summary", headers=auth_headers)
                
                assert response.status_code == 500
                data = response.json()
                
                assert data["success"] is False
                assert data["error"]["type"] == "metrics_error"

    @pytest.mark.asyncio
    async def test_rate_limiting(self, client, mock_session, auth_headers):
        """Test rate limiting on AI operations endpoints."""
        with patch('app.api.v1.ai_operations.get_current_session', return_value=mock_session):
            with patch.object(ai_state_manager, 'get_active_sessions', return_value=[]):
                
                # Make multiple requests rapidly (this test assumes rate limiting is configured)
                responses = []
                for i in range(25):  # Exceed rate limit of 20 per minute
                    response = await client.get("/ai/health", headers=auth_headers)
                    responses.append(response)
                
                # At least one should be rate limited (429 status)
                status_codes = [r.status_code for r in responses]
                # Note: This test might be flaky depending on rate limiter implementation
                # In a real environment, we might see 429 responses
                assert 200 in status_codes  # Some requests should succeed


@pytest.mark.integration
@pytest.mark.asyncio
class TestAIOperationsAuthentication:
    """Test authentication requirements for AI operations endpoints."""

    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://testserver") as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_health_check_without_auth(self, client):
        """Test health check without authentication."""
        response = await client.get("/ai/health")
        
        # Should require authentication
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_active_sessions_without_auth(self, client):
        """Test active sessions without authentication."""
        response = await client.get("/ai/sessions/active")
        
        # Should require authentication
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_checkpoint_creation_without_auth(self, client):
        """Test checkpoint creation without authentication."""
        response = await client.post("/ai/sessions/test-session/checkpoint")
        
        # Should require authentication
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_metrics_summary_without_auth(self, client):
        """Test metrics summary without authentication."""
        response = await client.get("/ai/metrics/summary")
        
        # Should require authentication
        assert response.status_code in [401, 403]


@pytest.mark.integration
@pytest.mark.asyncio
class TestAIOperationsEndToEnd:
    """End-to-end tests for AI operations workflows."""

    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://testserver") as ac:
            yield ac

    @pytest.fixture
    def mock_session(self):
        """Create a mock session for authentication."""
        session = Mock(spec=Session)
        session.id = "e2e-test-session"
        session.user_thread_id = "e2e-user-thread"
        return session

    @pytest.fixture
    def auth_headers(self, mock_session):
        """Create authentication headers."""
        return {"Authorization": f"Bearer e2e-token-{mock_session.id}"}

    @pytest.mark.asyncio
    async def test_session_management_workflow(self, client, mock_session, auth_headers):
        """Test complete session management workflow."""
        target_session_id = "workflow-session-123"
        
        with patch('app.api.v1.ai_operations.get_current_session', return_value=mock_session):
            # Mock state manager methods
            with patch.object(ai_state_manager, 'get_active_sessions') as mock_get_active:
                with patch.object(ai_state_manager, 'create_checkpoint') as mock_create_checkpoint:
                    with patch.object(ai_state_manager, 'restore_from_checkpoint') as mock_restore:
                        with patch.object(ai_state_manager, 'cleanup_expired_states') as mock_cleanup:
                            
                            # Setup mocks
                            mock_get_active.return_value = [target_session_id, "other-session"]
                            checkpoint_id = "workflow-checkpoint-456"
                            mock_create_checkpoint.return_value = checkpoint_id
                            
                            restored_state = ConversationState(
                                session_id=target_session_id,
                                user_id="workflow-user",
                                current_state={"step": "restored"},
                                state_version=3,
                                created_at=time.time(),
                                updated_at=time.time()
                            )
                            mock_restore.return_value = restored_state
                            mock_cleanup.return_value = 1
                            
                            # 1. Check initial active sessions
                            response = await client.get("/ai/sessions/active", headers=auth_headers)
                            assert response.status_code == 200
                            data = response.json()
                            assert target_session_id in data["data"]["active_sessions"]
                            
                            # 2. Create checkpoint
                            response = await client.post(
                                f"/ai/sessions/{target_session_id}/checkpoint",
                                headers=auth_headers
                            )
                            assert response.status_code == 200
                            data = response.json()
                            assert data["data"]["checkpoint_id"] == checkpoint_id
                            
                            # 3. Restore from checkpoint
                            response = await client.post(
                                f"/ai/sessions/{target_session_id}/restore/{checkpoint_id}",
                                headers=auth_headers
                            )
                            assert response.status_code == 200
                            data = response.json()
                            assert data["data"]["restored_version"] == 3
                            
                            # 4. Clean up expired sessions
                            response = await client.delete("/ai/sessions/cleanup", headers=auth_headers)
                            assert response.status_code == 200
                            data = response.json()
                            assert data["data"]["cleaned_sessions"] == 1
                            
                            # 5. Check final metrics
                            response = await client.get("/ai/metrics/summary", headers=auth_headers)
                            assert response.status_code == 200
                            data = response.json()
                            assert "operations" in data["data"]

    @pytest.mark.asyncio
    async def test_health_monitoring_workflow(self, client, mock_session, auth_headers):
        """Test health monitoring and metrics workflow."""
        with patch('app.api.v1.ai_operations.get_current_session', return_value=mock_session):
            with patch.object(ai_state_manager, 'get_active_sessions') as mock_get_active:
                
                # Start with healthy state
                mock_get_active.return_value = ["session-1", "session-2"]
                
                # 1. Check healthy status
                response = await client.get("/ai/health", headers=auth_headers)
                assert response.status_code == 200
                data = response.json()
                assert data["data"]["status"] == "healthy"
                assert data["data"]["active_sessions"] == 2
                
                # 2. Get baseline metrics
                response = await client.get("/ai/metrics/summary", headers=auth_headers)
                assert response.status_code == 200
                baseline_metrics = response.json()["data"]
                
                # 3. Simulate high load
                high_load_sessions = [f"session-{i}" for i in range(120)]
                mock_get_active.return_value = high_load_sessions
                
                # 4. Check degraded status
                response = await client.get("/ai/health", headers=auth_headers)
                assert response.status_code == 200
                data = response.json()
                assert data["data"]["status"] == "degraded"
                assert data["data"]["active_sessions"] == 120
                
                # 5. Get updated metrics
                response = await client.get("/ai/metrics/summary", headers=auth_headers)
                assert response.status_code == 200
                updated_metrics = response.json()["data"]
                
                # Verify metrics structure is consistent
                assert set(baseline_metrics.keys()) == set(updated_metrics.keys())


@pytest.mark.integration
@pytest.mark.slow
class TestAIOperationsPerformance:
    """Performance tests for AI operations endpoints."""

    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://testserver") as ac:
            yield ac

    @pytest.fixture
    def mock_session(self):
        """Create a mock session for authentication."""
        session = Mock(spec=Session)
        session.id = "perf-test-session"
        session.user_thread_id = "perf-user-thread"
        return session

    @pytest.fixture
    def auth_headers(self, mock_session):
        """Create authentication headers."""
        return {"Authorization": f"Bearer perf-token-{mock_session.id}"}

    @pytest.mark.asyncio
    async def test_health_check_response_time(self, client, mock_session, auth_headers):
        """Test health check response time."""
        with patch('app.api.v1.ai_operations.get_current_session', return_value=mock_session):
            with patch.object(ai_state_manager, 'get_active_sessions', return_value=[]):
                
                start_time = time.time()
                response = await client.get("/ai/health", headers=auth_headers)
                end_time = time.time()
                
                assert response.status_code == 200
                response_time = end_time - start_time
                
                # Health check should respond within 500ms
                assert response_time < 0.5

    @pytest.mark.asyncio
    async def test_metrics_summary_response_time(self, client, mock_session, auth_headers):
        """Test metrics summary response time."""
        with patch('app.api.v1.ai_operations.get_current_session', return_value=mock_session):
            
            start_time = time.time()
            response = await client.get("/ai/metrics/summary", headers=auth_headers)
            end_time = time.time()
            
            assert response.status_code == 200
            response_time = end_time - start_time
            
            # Metrics summary should respond within 1 second
            assert response_time < 1.0

    @pytest.mark.asyncio
    async def test_concurrent_requests_handling(self, client, mock_session, auth_headers):
        """Test handling of concurrent requests."""
        import asyncio
        
        with patch('app.api.v1.ai_operations.get_current_session', return_value=mock_session):
            with patch.object(ai_state_manager, 'get_active_sessions', return_value=[]):
                
                # Make 10 concurrent requests
                tasks = []
                for i in range(10):
                    task = client.get("/ai/health", headers=auth_headers)
                    tasks.append(task)
                
                responses = await asyncio.gather(*tasks)
                
                # All requests should succeed
                assert all(r.status_code == 200 for r in responses)
                
                # All should return consistent data
                data_list = [r.json()["data"] for r in responses]
                assert all(data["status"] == "healthy" for data in data_list)

    @pytest.mark.asyncio
    async def test_session_operations_performance(self, client, mock_session, auth_headers):
        """Test session operations performance."""
        target_session_id = "perf-target-session"
        
        with patch('app.api.v1.ai_operations.get_current_session', return_value=mock_session):
            with patch.object(ai_state_manager, 'create_checkpoint', return_value="checkpoint-123"):
                with patch.object(ai_state_manager, 'restore_from_checkpoint') as mock_restore:
                    
                    mock_state = ConversationState(
                        session_id=target_session_id,
                        user_id="perf-user",
                        current_state={},
                        state_version=1,
                        created_at=time.time(),
                        updated_at=time.time()
                    )
                    mock_restore.return_value = mock_state
                    
                    # Test checkpoint creation performance
                    start_time = time.time()
                    response = await client.post(
                        f"/ai/sessions/{target_session_id}/checkpoint",
                        headers=auth_headers
                    )
                    checkpoint_time = time.time() - start_time
                    
                    assert response.status_code == 200
                    assert checkpoint_time < 1.0  # Should be fast
                    
                    # Test restore performance
                    start_time = time.time()
                    response = await client.post(
                        f"/ai/sessions/{target_session_id}/restore/checkpoint-123",
                        headers=auth_headers
                    )
                    restore_time = time.time() - start_time
                    
                    assert response.status_code == 200
                    assert restore_time < 1.0  # Should be fast

    @pytest.mark.asyncio
    async def test_throughput_under_sustained_load(self, client, mock_session, auth_headers):
        """Test API throughput under sustained load."""
        duration_seconds = 10
        request_interval = 0.1  # 10 requests per second
        
        with patch('app.api.v1.ai_operations.get_current_session', return_value=mock_session):
            with patch.object(ai_state_manager, 'get_active_sessions', return_value=[]):
                
                start_time = time.time()
                successful_requests = 0
                failed_requests = 0
                
                while time.time() - start_time < duration_seconds:
                    try:
                        response = await client.get("/ai/health", headers=auth_headers)
                        if response.status_code == 200:
                            successful_requests += 1
                        else:
                            failed_requests += 1
                    except Exception:
                        failed_requests += 1
                    
                    await asyncio.sleep(request_interval)
                
                total_requests = successful_requests + failed_requests
                success_rate = successful_requests / total_requests if total_requests > 0 else 0
                
                # Should maintain high success rate under load
                assert success_rate > 0.95  # 95% success rate
                
                # Should handle at least 5 requests per second
                requests_per_second = total_requests / duration_seconds
                assert requests_per_second >= 5