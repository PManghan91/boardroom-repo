"""
Integration tests for health check system.
Tests service health monitoring, circuit breakers, and production readiness.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.core.health_checks import (
    health_service,
    HealthStatus,
    CircuitBreaker,
    RetryManager,
    HealthCheckResult,
    ServiceType
)


class TestHealthCheckService:
    """Test health check service functionality."""
    
    @pytest.mark.asyncio
    async def test_database_health_check(self):
        """Test database health check."""
        result = await health_service.check_database_health()
        
        assert isinstance(result, HealthCheckResult)
        assert result.service_name == "postgresql"
        assert result.service_type == ServiceType.DATABASE
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
        assert result.response_time_ms >= 0
        assert isinstance(result.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_redis_health_check(self):
        """Test Redis health check."""
        result = await health_service.check_redis_health()
        
        assert isinstance(result, HealthCheckResult)
        assert result.service_name == "redis"
        assert result.service_type == ServiceType.REDIS
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
        assert result.response_time_ms >= 0
        assert isinstance(result.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_system_resources_health_check(self):
        """Test system resources health check."""
        result = await health_service.check_system_resources()
        
        assert isinstance(result, HealthCheckResult)
        assert result.service_name == "system_resources"
        assert result.service_type == ServiceType.INTERNAL_SERVICE
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY, HealthStatus.UNKNOWN]
        assert result.response_time_ms >= 0
        assert isinstance(result.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_comprehensive_health_check(self):
        """Test comprehensive health check."""
        health_data = await health_service.get_comprehensive_health()
        
        assert "status" in health_data
        assert "timestamp" in health_data
        assert "services" in health_data
        assert "circuit_breakers" in health_data
        assert "summary" in health_data
        assert "uptime_seconds" in health_data
        
        # Check summary structure
        summary = health_data["summary"]
        assert "total_services" in summary
        assert "healthy_services" in summary
        assert "degraded_services" in summary
        assert "unhealthy_services" in summary
    
    @pytest.mark.asyncio
    async def test_is_ready(self):
        """Test readiness check."""
        is_ready = await health_service.is_ready()
        assert isinstance(is_ready, bool)
    
    @pytest.mark.asyncio
    async def test_is_alive(self):
        """Test liveness check."""
        is_alive = await health_service.is_alive()
        assert isinstance(is_alive, bool)
        # Service should be alive if running
        assert is_alive is True
    
    def test_dependencies_status(self):
        """Test dependencies status."""
        dependencies = health_service.get_dependencies_status()
        
        assert isinstance(dependencies, dict)
        assert "database" in dependencies
        assert "redis" in dependencies
        assert "external_apis" in dependencies
        
        for dep_name, dep_info in dependencies.items():
            assert "required" in dep_info
            assert "description" in dep_info


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        
        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 30
        assert cb.state.is_open is False
        assert cb.state.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_success(self):
        """Test circuit breaker with successful calls."""
        cb = CircuitBreaker(failure_threshold=3)
        
        async with cb.call():
            # Simulate successful operation
            pass
        
        assert cb.state.is_open is False
        assert cb.state.failure_count == 0
        assert cb.state.total_requests == 1
        assert cb.state.total_failures == 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_threshold(self):
        """Test circuit breaker opening after failure threshold."""
        cb = CircuitBreaker(failure_threshold=2)
        
        # Simulate failures
        for i in range(3):
            try:
                async with cb.call():
                    raise Exception("Test failure")
            except Exception:
                pass
        
        # Circuit should be open after 2 failures
        assert cb.state.is_open is True
        assert cb.state.failure_count >= 2
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_when_open(self):
        """Test circuit breaker blocks calls when open."""
        cb = CircuitBreaker(failure_threshold=1)
        
        # Cause failure to open circuit
        try:
            async with cb.call():
                raise Exception("Test failure")
        except Exception:
            pass
        
        assert cb.state.is_open is True
        
        # Next call should be blocked
        with pytest.raises(Exception, match="Circuit breaker is open"):
            async with cb.call():
                pass


class TestRetryManager:
    """Test retry manager functionality."""
    
    @pytest.mark.asyncio
    async def test_retry_success_on_first_attempt(self):
        """Test retry manager with successful first attempt."""
        retry_manager = RetryManager(max_retries=3)
        call_count = 0
        
        async def mock_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await retry_manager.execute(mock_function)
        
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_with_failures(self):
        """Test retry manager with initial failures."""
        retry_manager = RetryManager(max_retries=2, base_delay=0.01)
        call_count = 0
        
        async def mock_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Test failure")
            return "success"
        
        result = await retry_manager.execute(mock_function, exceptions=(Exception,))
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_max_attempts_exceeded(self):
        """Test retry manager when max attempts exceeded."""
        retry_manager = RetryManager(max_retries=2, base_delay=0.01)
        
        async def mock_function():
            raise Exception("Persistent failure")
        
        with pytest.raises(Exception, match="Persistent failure"):
            await retry_manager.execute(mock_function, exceptions=(Exception,))


class TestHealthEndpoints:
    """Test health check API endpoints."""
    
    @pytest.mark.asyncio
    async def test_basic_health_endpoint(self):
        """Test basic health endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/health/")
        
        assert response.status_code in [200, 503]
        data = response.json()
        
        assert "status" in data
        assert "timestamp" in data
        assert "message" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
    
    @pytest.mark.asyncio
    async def test_readiness_endpoint(self):
        """Test readiness probe endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/health/ready")
        
        assert response.status_code in [200, 503]
        data = response.json()
        
        assert "status" in data
        assert "timestamp" in data
        assert "details" in data
        assert "ready" in data["details"]
    
    @pytest.mark.asyncio
    async def test_liveness_endpoint(self):
        """Test liveness probe endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/health/live")
        
        assert response.status_code in [200, 503]
        data = response.json()
        
        assert "status" in data
        assert "timestamp" in data
        assert "details" in data
        assert "alive" in data["details"]
    
    @pytest.mark.asyncio
    async def test_detailed_health_endpoint(self):
        """Test detailed health endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/health/detailed")
        
        assert response.status_code in [200, 503]
        data = response.json()
        
        assert "status" in data
        assert "timestamp" in data
        assert "services" in data
        assert "circuit_breakers" in data
        assert "summary" in data
        assert "uptime_seconds" in data
    
    @pytest.mark.asyncio
    async def test_dependencies_endpoint(self):
        """Test dependencies endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/health/dependencies")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "dependencies" in data
        assert "timestamp" in data
        assert isinstance(data["dependencies"], dict)
    
    @pytest.mark.asyncio
    async def test_circuit_breakers_endpoint(self):
        """Test circuit breakers endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/health/circuit-breakers")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "circuit_breakers" in data
        assert "timestamp" in data
        assert "summary" in data
        assert isinstance(data["circuit_breakers"], dict)
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint(self):
        """Test health metrics endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/health/metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "metrics" in data
        assert "timestamp" in data
        assert "format" in data
        assert data["format"] == "prometheus_compatible"


class TestHealthCaching:
    """Test health check caching functionality."""
    
    @pytest.mark.asyncio
    async def test_health_check_caching(self):
        """Test that health checks are cached appropriately."""
        # Clear cache
        health_service._check_cache.clear()
        
        # First call
        start_time = datetime.utcnow()
        result1 = await health_service.check_database_health()
        
        # Second call (should be cached)
        result2 = await health_service.check_database_health()
        
        # Results should be identical (cached)
        assert result1.timestamp == result2.timestamp
        
        # Wait for cache to expire
        await asyncio.sleep(health_service._cache_ttl + 1)
        
        # Third call (cache expired)
        result3 = await health_service.check_database_health()
        
        # Should be different timestamp (not cached)
        assert result3.timestamp > result1.timestamp


class TestExternalAPIHealthCheck:
    """Test external API health check functionality."""
    
    @pytest.mark.asyncio
    async def test_external_api_health_check_success(self):
        """Test successful external API health check."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"Content-Type": "application/json"}
            mock_response.raise_for_status = Mock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await health_service.check_external_api_health("test_api", "https://api.example.com/health")
            
            assert result.service_name == "test_api"
            assert result.service_type == ServiceType.EXTERNAL_API
            assert result.status == HealthStatus.HEALTHY
            assert result.response_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_external_api_health_check_failure(self):
        """Test failed external API health check."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=Exception("Connection failed"))
            
            result = await health_service.check_external_api_health("test_api", "https://api.example.com/health")
            
            assert result.service_name == "test_api"
            assert result.service_type == ServiceType.EXTERNAL_API
            assert result.status == HealthStatus.UNHEALTHY
            assert result.error is not None
            assert "Connection failed" in result.error