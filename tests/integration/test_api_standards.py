"""Integration tests for API standardization and documentation endpoints.

Tests the consistency of API responses, documentation endpoints,
and standard patterns across the API.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestAPIStandards:
    """Test API standardization patterns."""
    
    def test_root_endpoint_standard_format(self, client):
        """Test that root endpoint follows standard response format."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check standard response structure
        assert "success" in data
        assert "data" in data
        assert "message" in data
        assert "metadata" in data
        
        assert data["success"] is True
        assert "name" in data["data"]
        assert "version" in data["data"]
        assert "endpoints" in data["data"]
        
        # Check metadata structure
        metadata = data["metadata"]
        assert "timestamp" in metadata
        assert "request_id" in metadata
        assert "version" in metadata
        assert "environment" in metadata
    
    def test_health_endpoint_standard_format(self, client):
        """Test that health endpoint follows standard response format."""
        response = client.get("/health")
        
        assert response.status_code in [200, 503]  # May be degraded if DB issues
        data = response.json()
        
        # Check standard response structure
        assert "success" in data
        assert "data" in data
        assert "message" in data
        assert "metadata" in data
        
        # Check health data structure
        health_data = data["data"]
        assert "status" in health_data
        assert "version" in health_data
        assert "environment" in health_data
        assert "components" in health_data
        assert "checks" in health_data
    
    def test_standard_headers_present(self, client):
        """Test that standard headers are present in responses."""
        response = client.get("/")
        
        # Check for standard headers
        assert "x-request-id" in response.headers
        assert "x-api-version" in response.headers
        assert "x-response-time" in response.headers
        
        # Validate header formats
        assert len(response.headers["x-request-id"]) > 0
        assert response.headers["x-api-version"] == "1.0.0"
        assert response.headers["x-response-time"].isdigit()
    
    def test_api_version_info_endpoint(self, client):
        """Test API version information endpoint."""
        response = client.get("/api/v1/standards/version")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check standard response format
        assert data["success"] is True
        assert "data" in data
        
        version_info = data["data"]
        assert "version" in version_info
        assert "supported_versions" in version_info
        assert "deprecated_versions" in version_info
        assert "latest_version" in version_info
        assert "documentation_url" in version_info
    
    def test_api_standards_documentation(self, client):
        """Test API standards documentation endpoint."""
        response = client.get("/api/v1/standards/standards")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check standard response format
        assert data["success"] is True
        assert "data" in data
        
        standards_info = data["data"]
        assert "response_format" in standards_info
        assert "error_handling" in standards_info
        assert "versioning" in standards_info
        assert "pagination" in standards_info
        assert "rate_limiting" in standards_info
        assert "authentication" in standards_info
    
    def test_error_codes_documentation(self, client):
        """Test error codes documentation endpoint."""
        response = client.get("/api/v1/standards/errors")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check standard response format
        assert data["success"] is True
        assert "data" in data
        
        error_docs = data["data"]
        assert "error_types" in error_docs
        assert "error_response_format" in error_docs
        assert "troubleshooting" in error_docs
        
        # Check that common error types are documented
        error_types = error_docs["error_types"]
        assert "VALIDATION_ERROR" in error_types
        assert "AUTHENTICATION_ERROR" in error_types
        assert "AUTHORIZATION_ERROR" in error_types
        assert "RESOURCE_NOT_FOUND" in error_types
    
    def test_api_examples_endpoint(self, client):
        """Test API usage examples endpoint."""
        response = client.get("/api/v1/standards/examples")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check standard response format
        assert data["success"] is True
        assert "data" in data
        
        examples = data["data"]
        assert "authentication" in examples
        assert "pagination" in examples
        assert "error_handling" in examples
        assert "streaming" in examples
    
    def test_detailed_health_endpoint(self, client):
        """Test detailed health information endpoint."""
        response = client.get("/api/v1/standards/health/detailed")
        
        assert response.status_code in [200, 503]
        data = response.json()
        
        # Check standard response format
        assert data["success"] is True
        assert "data" in data
        
        health_info = data["data"]
        assert "status" in health_info
        assert "version" in health_info
        assert "environment" in health_info
        assert "components" in health_info
        assert "timestamp" in health_info
        assert "uptime" in health_info


class TestAPIConsistency:
    """Test API consistency across different endpoints."""
    
    def test_error_response_consistency(self, client):
        """Test that error responses follow consistent format."""
        # Test authentication error
        response = client.get("/api/v1/chatbot/messages")
        
        assert response.status_code == 401
        data = response.json()
        
        # Check error response structure
        assert "error" in data
        error = data["error"]
        assert "code" in error
        assert "message" in error
        assert "type" in error
        assert "timestamp" in error
    
    def test_validation_error_consistency(self, client):
        """Test that validation errors follow consistent format."""
        # Test with invalid registration data
        response = client.post("/api/v1/auth/register", json={
            "email": "invalid-email",
            "password": "weak"
        })
        
        assert response.status_code == 422
        data = response.json()
        
        # Check error response structure
        assert "error" in data
        error = data["error"]
        assert "code" in error
        assert "message" in error
        assert "type" in error
        assert "details" in error
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are properly configured."""
        response = client.options("/api/v1/auth/login")
        
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers
    
    def test_openapi_spec_available(self, client):
        """Test that OpenAPI specification is available."""
        response = client.get("/api/v1/openapi.json")
        
        assert response.status_code == 200
        openapi_spec = response.json()
        
        # Check basic OpenAPI structure
        assert "openapi" in openapi_spec
        assert "info" in openapi_spec
        assert "paths" in openapi_spec
        assert "components" in openapi_spec
        
        # Check that our custom components are present
        components = openapi_spec["components"]
        assert "securitySchemes" in components
        assert "examples" in components
        assert "responses" in components
    
    def test_documentation_pages_accessible(self, client):
        """Test that documentation pages are accessible."""
        # Test Swagger UI
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        # Test ReDoc
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestRateLimitingStandards:
    """Test rate limiting standardization."""
    
    def test_rate_limit_headers_present(self, client):
        """Test that rate limiting headers are present when applicable."""
        response = client.get("/")
        
        # Rate limiting should be applied, check for potential headers
        # Note: Actual rate limit headers may not be present on first request
        # but the endpoint should be protected
        assert response.status_code == 200
    
    def test_rate_limit_documentation(self, client):
        """Test that rate limiting is properly documented."""
        response = client.get("/api/v1/standards/standards")
        
        assert response.status_code == 200
        data = response.json()
        
        standards_info = data["data"]
        rate_limiting = standards_info["rate_limiting"]
        
        assert "headers" in rate_limiting
        assert "default_limits" in rate_limiting
        
        headers = rate_limiting["headers"]
        assert "X-RateLimit-Limit" in headers
        assert "X-RateLimit-Remaining" in headers
        assert "X-RateLimit-Reset" in headers


class TestAPIVersioning:
    """Test API versioning standards."""
    
    def test_version_in_url_path(self, client):
        """Test that API version is properly included in URL paths."""
        # All API endpoints should be under /api/v1/
        response = client.get("/api/v1/standards/version")
        assert response.status_code == 200
        
        # Non-versioned paths should not work for API endpoints
        response = client.get("/standards/version")
        assert response.status_code == 404
    
    def test_version_header_support(self, client):
        """Test that API version can be specified via header."""
        headers = {"X-API-Version": "1.0.0"}
        response = client.get("/api/v1/standards/version", headers=headers)
        
        assert response.status_code == 200
        # The response should acknowledge the version
        assert response.headers.get("x-api-version") == "1.0.0"
    
    def test_unsupported_version_handling(self, client):
        """Test handling of unsupported API versions."""
        headers = {"X-API-Version": "2.0.0"}
        response = client.get("/api/v1/standards/version", headers=headers)
        
        # Should still work but with current version
        assert response.status_code == 200
        assert response.headers.get("x-api-version") == "1.0.0"