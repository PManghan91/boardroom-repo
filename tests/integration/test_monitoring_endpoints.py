"""Integration tests for monitoring endpoints.

Tests monitoring and health check API endpoints with mocked dependencies
to verify system monitoring capabilities without external dependencies.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, Mock, AsyncMock
from fastapi import status

from app.core.error_monitoring import ErrorMetric
from datetime import datetime, timedelta


@pytest.mark.integration
class TestHealthEndpoints:
    """Test health check and status endpoints."""
    
    @patch('app.services.database.database_service')
    async def test_health_check_healthy(self, mock_db_service, client: AsyncClient):
        """Test health check when all systems are healthy."""
        # Mock healthy database
        mock_db_service.health_check.return_value = {
            "status": "healthy",
            "database": "connected",
            "pool_status": {"size": 5, "checked_in": 3, "checked_out": 2}
        }
        
        response = await client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["environment"] == "test"
        assert "version" in data
        assert "components" in data
        assert data["components"]["database"]["status"] == "healthy"
    
    @patch('app.services.database.database_service')
    async def test_health_check_unhealthy_database(self, mock_db_service, client: AsyncClient):
        """Test health check when database is unhealthy."""
        # Mock unhealthy database
        mock_db_service.health_check.return_value = {
            "status": "unhealthy",
            "database": "disconnected",
            "error": "Connection timeout"
        }
        
        response = await client.get("/health")
        
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["components"]["database"]["status"] == "unhealthy"
        assert "Connection timeout" in data["components"]["database"]["error"]
    
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint returns basic info."""
        response = await client.get("/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Boardroom AI"
        assert data["status"] == "healthy"
        assert "version" in data
    
    @patch('app.services.database.database_service')
    async def test_health_check_with_migration_status(self, mock_db_service, client: AsyncClient):
        """Test health check includes migration status."""
        # Mock healthy database with migration info
        mock_db_service.health_check.return_value = {
            "status": "healthy",
            "database": "connected"
        }
        mock_db_service.execute_migration_check.return_value = "abc123def456"
        
        response = await client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "migration_version" in data["components"]["database"]


@pytest.mark.integration
class TestErrorMonitoringEndpoints:
    """Test error monitoring and alerting endpoints."""
    
    @patch('app.core.error_monitoring.get_error_summary')
    async def test_get_error_summary_success(self, mock_get_summary, client: AsyncClient):
        """Test successful error summary retrieval."""
        # Mock error summary data
        mock_error_metric = ErrorMetric(
            error_type="validation_error",
            count=5,
            last_occurrence=datetime.now(),
            first_occurrence=datetime.now() - timedelta(hours=1),
            paths=["/api/v1/auth/login", "/api/v1/boardroom/"],
            status_codes=[400, 422]
        )
        
        mock_get_summary.return_value = {
            "validation_error": mock_error_metric,
            "auth_error": ErrorMetric(
                error_type="auth_error", 
                count=3,
                last_occurrence=datetime.now(),
                first_occurrence=datetime.now() - timedelta(minutes=30),
                paths=["/api/v1/auth/login"],
                status_codes=[401]
            )
        }
        
        response = await client.get("/monitoring/errors")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["errors"]) == 2
        assert "validation_error" in data["errors"]
        assert "auth_error" in data["errors"]
        assert data["errors"]["validation_error"]["count"] == 5
        assert data["errors"]["auth_error"]["count"] == 3
    
    @patch('app.core.error_monitoring.get_error_summary')
    async def test_get_error_summary_empty(self, mock_get_summary, client: AsyncClient):
        """Test error summary when no errors exist."""
        mock_get_summary.return_value = {}
        
        response = await client.get("/monitoring/errors")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["errors"] == {}
        assert data["total_error_types"] == 0
    
    @patch('app.core.error_monitoring.get_error_summary')
    async def test_get_error_summary_with_timeframe(self, mock_get_summary, client: AsyncClient):
        """Test error summary with custom timeframe."""
        mock_get_summary.return_value = {}
        
        # Test with 12 hour timeframe
        response = await client.get("/monitoring/errors?hours=12")
        
        assert response.status_code == status.HTTP_200_OK
        mock_get_summary.assert_called_with(hours=12)
        
        # Test with 24 hour timeframe (default)
        response = await client.get("/monitoring/errors")
        mock_get_summary.assert_called_with(hours=24)
    
    async def test_get_error_summary_invalid_timeframe(self, client: AsyncClient):
        """Test error summary with invalid timeframe parameter."""
        # Test with negative hours
        response = await client.get("/monitoring/errors?hours=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test with non-numeric hours
        response = await client.get("/monitoring/errors?hours=invalid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test with excessively large hours
        response = await client.get("/monitoring/errors?hours=999999")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @patch('app.core.error_monitoring.get_monitoring_health')
    async def test_get_monitoring_health_success(self, mock_get_health, client: AsyncClient):
        """Test monitoring health status retrieval."""
        mock_get_health.return_value = {
            "status": "healthy",
            "recent_errors_5min": 2,
            "total_error_types": 3,
            "monitoring_window_minutes": 60,
            "alert_threshold": 10,
            "timestamp": "2023-01-01T12:00:00"
        }
        
        response = await client.get("/monitoring/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["recent_errors_5min"] == 2
        assert data["total_error_types"] == 3
        assert data["monitoring_window_minutes"] == 60
        assert data["alert_threshold"] == 10
    
    @patch('app.core.error_monitoring.get_monitoring_health')
    async def test_get_monitoring_health_degraded(self, mock_get_health, client: AsyncClient):
        """Test monitoring health status when degraded."""
        mock_get_health.return_value = {
            "status": "degraded",
            "recent_errors_5min": 8,
            "total_error_types": 4,
            "monitoring_window_minutes": 60,
            "alert_threshold": 10,
            "timestamp": "2023-01-01T12:00:00"
        }
        
        response = await client.get("/monitoring/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "degraded"
        assert data["recent_errors_5min"] == 8
    
    @patch('app.core.error_monitoring.record_error')
    async def test_record_error_endpoint(self, mock_record_error, client: AsyncClient):
        """Test manual error recording endpoint."""
        error_data = {
            "error_type": "manual_test_error",
            "path": "/api/test",
            "status_code": 500,
            "error_message": "Test error message",
            "client_ip": "192.168.1.100"
        }
        
        response = await client.post("/monitoring/errors", json=error_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        mock_record_error.assert_called_once_with(
            error_type="manual_test_error",
            path="/api/test",
            status_code=500,
            error_message="Test error message",
            client_ip="192.168.1.100"
        )
    
    async def test_record_error_endpoint_invalid_data(self, client: AsyncClient):
        """Test error recording with invalid data."""
        # Missing required fields
        incomplete_data = {
            "error_type": "test_error"
            # Missing path and status_code
        }
        
        response = await client.post("/monitoring/errors", json=incomplete_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Invalid status code
        invalid_data = {
            "error_type": "test_error",
            "path": "/api/test",
            "status_code": 999  # Invalid HTTP status code
        }
        
        response = await client.post("/monitoring/errors", json=invalid_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.integration
class TestMetricsEndpoints:
    """Test metrics and observability endpoints."""
    
    @patch('app.core.metrics.get_system_metrics')
    async def test_get_system_metrics_success(self, mock_get_metrics, client: AsyncClient):
        """Test system metrics retrieval."""
        mock_get_metrics.return_value = {
            "cpu_usage": 45.2,
            "memory_usage": 67.8,
            "disk_usage": 23.1,
            "active_connections": 12,
            "requests_per_minute": 150,
            "timestamp": "2023-01-01T12:00:00"
        }
        
        response = await client.get("/monitoring/metrics")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["cpu_usage"] == 45.2
        assert data["memory_usage"] == 67.8
        assert data["active_connections"] == 12
        assert data["requests_per_minute"] == 150
    
    @patch('app.core.metrics.get_application_metrics')
    async def test_get_application_metrics_success(self, mock_get_app_metrics, client: AsyncClient):
        """Test application-specific metrics retrieval."""
        mock_get_app_metrics.return_value = {
            "total_users": 1250,
            "active_boardrooms": 85,
            "active_sessions": 12,
            "total_decisions": 3400,
            "avg_response_time_ms": 245,
            "cache_hit_rate": 0.87,
            "timestamp": "2023-01-01T12:00:00"
        }
        
        response = await client.get("/monitoring/metrics/application")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_users"] == 1250
        assert data["active_boardrooms"] == 85
        assert data["active_sessions"] == 12
        assert data["avg_response_time_ms"] == 245
        assert data["cache_hit_rate"] == 0.87
    
    async def test_prometheus_metrics_endpoint(self, client: AsyncClient):
        """Test Prometheus metrics endpoint."""
        response = await client.get("/metrics")
        
        # Prometheus metrics should be in text format
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
        
        # Should contain some basic metrics
        content = response.text
        assert "# HELP" in content
        assert "# TYPE" in content


@pytest.mark.integration
class TestMonitoringAuthentication:
    """Test authentication requirements for monitoring endpoints."""
    
    @patch('app.utils.auth.verify_token')
    async def test_monitoring_endpoints_require_admin(self, mock_verify, client: AsyncClient):
        """Test that monitoring endpoints require admin access."""
        # Mock non-admin user
        mock_verify.return_value = "user-thread-123"
        
        with patch('app.services.database.database_service') as mock_db:
            mock_user = Mock()
            mock_user.role = "user"  # Not admin
            mock_db.get_user.return_value = mock_user
            
            headers = {"Authorization": "Bearer user_token"}
            
            # Test various monitoring endpoints
            endpoints = [
                "/monitoring/errors",
                "/monitoring/health", 
                "/monitoring/metrics",
                "/monitoring/metrics/application"
            ]
            
            for endpoint in endpoints:
                response = await client.get(endpoint, headers=headers)
                assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @patch('app.utils.auth.verify_token')
    async def test_monitoring_endpoints_allow_admin(self, mock_verify, client: AsyncClient):
        """Test that monitoring endpoints allow admin access."""
        # Mock admin user
        mock_verify.return_value = "admin-thread-123"
        
        with patch('app.services.database.database_service') as mock_db:
            mock_user = Mock()
            mock_user.role = "admin"
            mock_db.get_user.return_value = mock_user
            
            with patch('app.core.error_monitoring.get_error_summary') as mock_summary:
                mock_summary.return_value = {}
                
                headers = {"Authorization": "Bearer admin_token"}
                response = await client.get("/monitoring/errors", headers=headers)
                
                assert response.status_code == status.HTTP_200_OK
    
    async def test_health_endpoint_public_access(self, client: AsyncClient):
        """Test that health endpoint allows public access."""
        with patch('app.services.database.database_service') as mock_db:
            mock_db.health_check.return_value = {
                "status": "healthy",
                "database": "connected"
            }
            
            # No authorization header
            response = await client.get("/health")
            assert response.status_code == status.HTTP_200_OK
    
    async def test_prometheus_metrics_public_access(self, client: AsyncClient):
        """Test that Prometheus metrics endpoint allows public access."""
        # Prometheus metrics should be publicly accessible for scraping
        response = await client.get("/metrics")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
class TestMonitoringErrorScenarios:
    """Test error scenarios in monitoring endpoints."""
    
    @patch('app.core.error_monitoring.get_error_summary')
    async def test_error_summary_service_failure(self, mock_get_summary, client: AsyncClient):
        """Test error summary when monitoring service fails."""
        mock_get_summary.side_effect = Exception("Monitoring service unavailable")
        
        response = await client.get("/monitoring/errors")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "error" in data
    
    @patch('app.core.metrics.get_system_metrics')
    async def test_metrics_collection_failure(self, mock_get_metrics, client: AsyncClient):
        """Test metrics endpoint when collection fails."""
        mock_get_metrics.side_effect = Exception("Metrics collection failed")
        
        response = await client.get("/monitoring/metrics")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "error" in data
    
    @patch('app.services.database.database_service')
    async def test_health_check_partial_failure(self, mock_db_service, client: AsyncClient):
        """Test health check with partial service failures."""
        # Mock database partially failing
        mock_db_service.health_check.return_value = {
            "status": "degraded",
            "database": "connected",
            "pool_status": None,  # Pool info unavailable
            "warning": "High connection usage"
        }
        
        response = await client.get("/health")
        
        # Should still return 200 but indicate degraded status
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "degraded"
        assert "warning" in str(data)


@pytest.mark.integration
class TestMonitoringPerformance:
    """Test performance characteristics of monitoring endpoints."""
    
    @pytest.mark.slow
    async def test_monitoring_endpoints_response_time(self, client: AsyncClient):
        """Test that monitoring endpoints respond quickly."""
        import time
        
        with patch('app.services.database.database_service') as mock_db:
            mock_db.health_check.return_value = {"status": "healthy", "database": "connected"}
            
            start_time = time.time()
            response = await client.get("/health")
            end_time = time.time()
            
            assert response.status_code == status.HTTP_200_OK
            # Health check should respond within 1 second
            assert (end_time - start_time) < 1.0
    
    @pytest.mark.slow
    async def test_concurrent_monitoring_requests(self, client: AsyncClient):
        """Test handling of concurrent monitoring requests."""
        import asyncio
        
        with patch('app.core.error_monitoring.get_error_summary') as mock_summary:
            mock_summary.return_value = {}
            
            # Make 5 concurrent requests
            tasks = []
            for _ in range(5):
                task = client.get("/monitoring/errors")
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks)
            
            # All requests should succeed
            for response in responses:
                assert response.status_code == status.HTTP_200_OK
    
    @patch('app.core.error_monitoring.get_error_summary')
    async def test_large_error_summary_handling(self, mock_get_summary, client: AsyncClient):
        """Test handling of large error summaries."""
        # Create a large number of error types
        large_summary = {}
        for i in range(100):
            large_summary[f"error_type_{i}"] = ErrorMetric(
                error_type=f"error_type_{i}",
                count=i + 1,
                last_occurrence=datetime.now(),
                first_occurrence=datetime.now() - timedelta(hours=1),
                paths=[f"/api/endpoint_{i}"],
                status_codes=[400 + (i % 100)]
            )
        
        mock_get_summary.return_value = large_summary
        
        response = await client.get("/monitoring/errors")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["errors"]) == 100
        assert data["total_error_types"] == 100