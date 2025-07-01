"""Basic performance validation tests.

These tests establish baseline performance metrics and validate
response times for key operations without requiring external dependencies.
"""

import pytest
import asyncio
import time
from httpx import AsyncClient
from unittest.mock import patch, Mock, AsyncMock
from typing import List

from app.services.database import DatabaseService
from app.utils.auth import create_access_token, verify_token
from app.utils.sanitization import sanitize_string, sanitize_dict
from app.core.error_monitoring import ErrorMonitor


@pytest.mark.slow
@pytest.mark.integration
class TestAPIPerformance:
    """Test API endpoint performance characteristics."""
    
    @patch('app.services.database.database_service')
    async def test_health_endpoint_response_time(self, mock_db_service, client: AsyncClient):
        """Test health endpoint responds within acceptable time."""
        mock_db_service.health_check.return_value = {
            "status": "healthy",
            "database": "connected"
        }
        
        start_time = time.time()
        response = await client.get("/health")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 0.5  # Should respond within 500ms
        
        # Log performance metric
        print(f"Health endpoint response time: {response_time:.3f}s")
    
    @patch('app.services.database.database_service')
    @patch('app.utils.auth.verify_token')
    async def test_auth_endpoint_performance(self, mock_verify, mock_db_service, client: AsyncClient):
        """Test authentication endpoint performance."""
        # Mock user and auth
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.hashed_password = "$2b$12$hashedpassword"
        mock_user.is_active = True
        mock_user.role = "user"
        
        mock_db_service.get_user_by_email.return_value = mock_user
        
        with patch('app.api.v1.auth.verify_password') as mock_verify_pwd, \
             patch('app.api.v1.auth.create_access_token') as mock_create_token:
            
            mock_verify_pwd.return_value = True
            mock_token = Mock()
            mock_token.access_token = "test_token"
            mock_token.expires_at = "2023-12-31T23:59:59"
            mock_create_token.return_value = mock_token
            
            start_time = time.time()
            response = await client.post("/api/v1/auth/user-login", json={
                "email": "test@example.com",
                "password": "TestPassword123!"
            })
            end_time = time.time()
            
            response_time = end_time - start_time
            
            assert response.status_code == 200
            assert response_time < 1.0  # Should respond within 1 second
            
            print(f"Auth login response time: {response_time:.3f}s")
    
    @patch('app.services.database.database_service')
    @patch('app.utils.auth.verify_token')
    async def test_boardroom_creation_performance(self, mock_verify, mock_db_service, client: AsyncClient):
        """Test boardroom creation performance."""
        mock_verify.return_value = "user-thread-123"
        
        # Mock user
        mock_user = Mock()
        mock_user.id = 1
        mock_user.role = "admin"
        mock_db_service.get_user.return_value = mock_user
        
        # Mock boardroom creation
        mock_boardroom = Mock()
        mock_boardroom.id = "board-123"
        mock_boardroom.name = "Performance Test Boardroom"
        mock_db_service.create_boardroom.return_value = mock_boardroom
        
        headers = {"Authorization": "Bearer valid_token"}
        
        start_time = time.time()
        response = await client.post("/api/v1/boardroom/", json={
            "name": "Performance Test Boardroom",
            "description": "Testing performance",
            "settings": {"max_participants": 10}
        }, headers=headers)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 201
        assert response_time < 2.0  # Should respond within 2 seconds
        
        print(f"Boardroom creation response time: {response_time:.3f}s")
    
    @patch('app.services.database.database_service')
    async def test_concurrent_health_checks(self, mock_db_service, client: AsyncClient):
        """Test concurrent health check performance."""
        mock_db_service.health_check.return_value = {
            "status": "healthy",
            "database": "connected"
        }
        
        concurrent_requests = 10
        
        start_time = time.time()
        
        # Create concurrent requests
        tasks = []
        for _ in range(concurrent_requests):
            task = client.get("/health")
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
        
        # Average response time should be reasonable
        avg_response_time = total_time / concurrent_requests
        assert avg_response_time < 1.0
        
        print(f"Concurrent health checks ({concurrent_requests}): {total_time:.3f}s total, {avg_response_time:.3f}s avg")
    
    @pytest.mark.parametrize("request_count", [5, 10, 20])
    @patch('app.core.error_monitoring.get_error_summary')
    async def test_monitoring_endpoint_scalability(self, mock_get_summary, client: AsyncClient, request_count: int):
        """Test monitoring endpoint performance with different loads."""
        mock_get_summary.return_value = {}
        
        start_time = time.time()
        
        tasks = []
        for _ in range(request_count):
            task = client.get("/monitoring/errors")
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
        
        avg_response_time = total_time / request_count
        
        # Performance should scale reasonably
        assert avg_response_time < 2.0
        
        print(f"Monitoring endpoint scalability ({request_count} requests): {total_time:.3f}s total, {avg_response_time:.3f}s avg")


@pytest.mark.slow
class TestUtilityPerformance:
    """Test performance of utility functions."""
    
    def test_token_creation_performance(self):
        """Test JWT token creation performance."""
        thread_ids = [f"thread-{i}" for i in range(100)]
        
        with patch('app.utils.auth.settings') as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test-secret"
            mock_settings.JWT_ALGORITHM = "HS256"
            mock_settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS = 1
            
            start_time = time.time()
            
            tokens = []
            for thread_id in thread_ids:
                token = create_access_token(thread_id)
                tokens.append(token)
            
            end_time = time.time()
            
            total_time = end_time - start_time
            avg_time = total_time / len(thread_ids)
            
            assert len(tokens) == 100
            assert avg_time < 0.01  # Should create token in less than 10ms
            
            print(f"Token creation (100 tokens): {total_time:.3f}s total, {avg_time:.3f}s avg")
    
    def test_token_verification_performance(self):
        """Test JWT token verification performance."""
        with patch('app.utils.auth.settings') as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test-secret"
            mock_settings.JWT_ALGORITHM = "HS256"
            mock_settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS = 1
            
            # Create test tokens
            tokens = []
            for i in range(100):
                token = create_access_token(f"thread-{i}")
                tokens.append(token.access_token)
            
            start_time = time.time()
            
            results = []
            for token in tokens:
                result = verify_token(token)
                results.append(result)
            
            end_time = time.time()
            
            total_time = end_time - start_time
            avg_time = total_time / len(tokens)
            
            assert len([r for r in results if r is not None]) == 100
            assert avg_time < 0.005  # Should verify token in less than 5ms
            
            print(f"Token verification (100 tokens): {total_time:.3f}s total, {avg_time:.3f}s avg")
    
    def test_string_sanitization_performance(self):
        """Test string sanitization performance."""
        test_strings = [
            "Normal string content",
            "<script>alert('xss')</script>",
            "String with null bytes\x00content",
            "<div onclick='malicious()'>HTML content</div>",
            "Very " + "long " * 1000 + "string"
        ]
        
        # Test with many strings
        large_dataset = test_strings * 200  # 1000 strings total
        
        start_time = time.time()
        
        sanitized = []
        for string in large_dataset:
            result = sanitize_string(string)
            sanitized.append(result)
        
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time = total_time / len(large_dataset)
        
        assert len(sanitized) == len(large_dataset)
        assert avg_time < 0.001  # Should sanitize string in less than 1ms
        
        print(f"String sanitization (1000 strings): {total_time:.3f}s total, {avg_time:.3f}s avg")
    
    def test_dict_sanitization_performance(self):
        """Test dictionary sanitization performance."""
        test_dict = {
            "user": {
                "name": "<script>alert('xss')</script>",
                "email": "test@example.com",
                "preferences": {
                    "theme": "dark",
                    "notifications": True,
                    "content": ["<div>item1</div>", "safe_item", {"nested": "<span>test</span>"}]
                }
            },
            "session": {
                "id": "session-123",
                "data": "Safe\x00Content",
                "metadata": {
                    "tags": ["<script>", "normal", "another<script>"],
                    "description": "Long " + "description " * 100
                }
            }
        }
        
        # Test with many dictionaries
        test_count = 100
        
        start_time = time.time()
        
        results = []
        for _ in range(test_count):
            result = sanitize_dict(test_dict)
            results.append(result)
        
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time = total_time / test_count
        
        assert len(results) == test_count
        assert avg_time < 0.01  # Should sanitize dict in less than 10ms
        
        print(f"Dictionary sanitization (100 dicts): {total_time:.3f}s total, {avg_time:.3f}s avg")


@pytest.mark.slow
class TestDatabaseServicePerformance:
    """Test database service performance characteristics."""
    
    @patch('app.services.database.create_async_engine')
    @patch('app.services.database.async_sessionmaker')
    async def test_database_initialization_performance(self, mock_sessionmaker, mock_create_engine):
        """Test database service initialization performance."""
        mock_engine = AsyncMock()
        mock_create_engine.return_value = mock_engine
        mock_sessionmaker.return_value = Mock()
        
        # Mock test connection
        mock_conn = AsyncMock()
        mock_engine.begin.return_value.__aenter__.return_value = mock_conn
        
        with patch('app.services.database.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                DEBUG=False,
                ENVIRONMENT=Mock(value="test"),
                database_url="postgresql+asyncpg://test:test@localhost:5432/test"
            )
            
            service = DatabaseService()
            
            start_time = time.time()
            await service.initialize()
            end_time = time.time()
            
            init_time = end_time - start_time
            
            assert service._initialized is True
            assert init_time < 1.0  # Should initialize within 1 second
            
            print(f"Database initialization time: {init_time:.3f}s")
    
    @patch('app.services.database.get_settings')
    async def test_session_context_manager_performance(self, mock_settings):
        """Test database session context manager performance."""
        mock_settings.return_value = Mock()
        
        service = DatabaseService()
        service._initialized = True
        
        # Mock session factory
        mock_sessions = [AsyncMock() for _ in range(10)]
        session_iter = iter(mock_sessions)
        
        def mock_session_factory():
            return next(session_iter)
        
        service._session_factory = mock_session_factory
        
        start_time = time.time()
        
        # Test multiple session acquisitions
        for i in range(10):
            async with service.get_session() as session:
                # Simulate brief work
                await asyncio.sleep(0.001)
        
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time = total_time / 10
        
        assert avg_time < 0.1  # Each session should be fast
        
        # All sessions should be closed
        for session in mock_sessions:
            session.close.assert_called_once()
        
        print(f"Database session operations (10 sessions): {total_time:.3f}s total, {avg_time:.3f}s avg")


@pytest.mark.slow
class TestErrorMonitoringPerformance:
    """Test error monitoring system performance."""
    
    def test_error_recording_performance(self):
        """Test error recording performance."""
        monitor = ErrorMonitor(window_minutes=60, alert_threshold=100)
        
        error_count = 1000
        
        start_time = time.time()
        
        for i in range(error_count):
            monitor.record_error(
                error_type=f"error_type_{i % 10}",
                path=f"/api/endpoint_{i % 20}",
                status_code=400 + (i % 100),
                error_message=f"Error message {i}",
                client_ip=f"192.168.1.{i % 255}"
            )
        
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time = total_time / error_count
        
        assert len(monitor.error_details) == 10  # 10 different error types
        assert avg_time < 0.001  # Should record error in less than 1ms
        
        print(f"Error recording (1000 errors): {total_time:.3f}s total, {avg_time:.3f}s avg")
    
    def test_error_summary_performance(self):
        """Test error summary generation performance."""
        monitor = ErrorMonitor(window_minutes=60, alert_threshold=100)
        
        # Pre-populate with errors
        for i in range(500):
            monitor.record_error(
                error_type=f"error_type_{i % 20}",
                path=f"/api/endpoint_{i % 50}",
                status_code=400 + (i % 100)
            )
        
        start_time = time.time()
        
        # Generate summaries multiple times
        summaries = []
        for _ in range(100):
            summary = monitor.get_error_summary(hours=24)
            summaries.append(summary)
        
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time = total_time / 100
        
        assert len(summaries) == 100
        assert avg_time < 0.01  # Should generate summary in less than 10ms
        
        print(f"Error summary generation (100 summaries): {total_time:.3f}s total, {avg_time:.3f}s avg")
    
    def test_health_status_performance(self):
        """Test health status check performance."""
        monitor = ErrorMonitor(window_minutes=60, alert_threshold=100)
        
        # Pre-populate with recent errors
        for i in range(100):
            monitor.record_error(
                error_type=f"error_type_{i % 5}",
                path=f"/api/endpoint_{i % 10}",
                status_code=500
            )
        
        start_time = time.time()
        
        # Check health status multiple times
        health_checks = []
        for _ in range(200):
            health = monitor.get_health_status()
            health_checks.append(health)
        
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time = total_time / 200
        
        assert len(health_checks) == 200
        assert avg_time < 0.005  # Should check health in less than 5ms
        
        print(f"Health status checks (200 checks): {total_time:.3f}s total, {avg_time:.3f}s avg")


@pytest.mark.slow
class TestMemoryUsage:
    """Test memory usage characteristics of key components."""
    
    def test_token_creation_memory_usage(self):
        """Test memory usage during token creation."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        with patch('app.utils.auth.settings') as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test-secret"
            mock_settings.JWT_ALGORITHM = "HS256"
            mock_settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS = 1
            
            # Create many tokens
            tokens = []
            for i in range(1000):
                token = create_access_token(f"thread-{i}")
                tokens.append(token)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        memory_per_token = memory_increase / 1000
        
        # Memory increase should be reasonable (less than 1KB per token)
        assert memory_per_token < 1024
        
        print(f"Memory usage for 1000 tokens: {memory_increase} bytes total, {memory_per_token:.1f} bytes per token")
    
    def test_error_monitoring_memory_usage(self):
        """Test memory usage of error monitoring system."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        monitor = ErrorMonitor(window_minutes=60, alert_threshold=100)
        
        # Record many errors
        for i in range(5000):
            monitor.record_error(
                error_type=f"error_type_{i % 50}",
                path=f"/api/endpoint_{i % 100}",
                status_code=400 + (i % 200),
                error_message=f"Error message {i}"
            )
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        memory_per_error = memory_increase / 5000
        
        # Memory per error should be reasonable
        assert memory_per_error < 512  # Less than 512 bytes per error
        
        print(f"Memory usage for 5000 errors: {memory_increase} bytes total, {memory_per_error:.1f} bytes per error")


@pytest.mark.slow
class TestLoadTesting:
    """Basic load testing patterns."""
    
    @patch('app.services.database.database_service')
    async def test_sustained_health_check_load(self, mock_db_service, client: AsyncClient):
        """Test sustained load on health check endpoint."""
        mock_db_service.health_check.return_value = {
            "status": "healthy",
            "database": "connected"
        }
        
        duration_seconds = 5
        request_interval = 0.1  # Request every 100ms
        
        start_time = time.time()
        responses = []
        
        while time.time() - start_time < duration_seconds:
            response = await client.get("/health")
            responses.append(response)
            await asyncio.sleep(request_interval)
        
        end_time = time.time()
        actual_duration = end_time - start_time
        
        # Calculate metrics
        total_requests = len(responses)
        requests_per_second = total_requests / actual_duration
        success_rate = len([r for r in responses if r.status_code == 200]) / total_requests
        
        assert success_rate > 0.95  # At least 95% success rate
        assert requests_per_second > 5  # At least 5 requests per second
        
        print(f"Sustained load test: {total_requests} requests in {actual_duration:.1f}s")
        print(f"Rate: {requests_per_second:.1f} req/s, Success: {success_rate:.1%}")
    
    @pytest.mark.parametrize("batch_size", [5, 10, 20])
    async def test_batch_request_performance(self, client: AsyncClient, batch_size: int):
        """Test performance with different batch sizes."""
        with patch('app.services.database.database_service') as mock_db:
            mock_db.health_check.return_value = {"status": "healthy", "database": "connected"}
            
            start_time = time.time()
            
            # Send batch of concurrent requests
            tasks = [client.get("/health") for _ in range(batch_size)]
            responses = await asyncio.gather(*tasks)
            
            end_time = time.time()
            batch_time = end_time - start_time
            
            # All requests should succeed
            success_count = len([r for r in responses if r.status_code == 200])
            success_rate = success_count / batch_size
            
            assert success_rate >= 1.0  # 100% success rate expected
            assert batch_time < 5.0  # Batch should complete within 5 seconds
            
            throughput = batch_size / batch_time
            
            print(f"Batch performance (size {batch_size}): {batch_time:.3f}s, {throughput:.1f} req/s")


# Performance baseline constants for CI/CD
PERFORMANCE_BASELINES = {
    "health_endpoint_max_response_time": 0.5,
    "auth_endpoint_max_response_time": 1.0,
    "token_creation_max_time": 0.01,
    "token_verification_max_time": 0.005,
    "string_sanitization_max_time": 0.001,
    "dict_sanitization_max_time": 0.01,
    "error_recording_max_time": 0.001,
    "min_requests_per_second": 5,
    "min_success_rate": 0.95
}


def test_performance_baselines_defined():
    """Ensure performance baselines are defined for monitoring."""
    assert PERFORMANCE_BASELINES is not None
    assert len(PERFORMANCE_BASELINES) > 0
    assert all(isinstance(v, (int, float)) for v in PERFORMANCE_BASELINES.values())
    
    print("Performance baselines:")
    for metric, baseline in PERFORMANCE_BASELINES.items():
        print(f"  {metric}: {baseline}")