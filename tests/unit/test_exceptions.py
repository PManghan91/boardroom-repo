"""Unit tests for custom exception classes.

Tests exception hierarchy, error categorization, and consistent error response patterns
without requiring external dependencies.
"""

import pytest
from datetime import datetime
from unittest.mock import patch
from fastapi import status

from app.core.exceptions import (
    BoardroomException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    ResourceNotFoundException,
    ConflictException,
    DatabaseException,
    ExternalServiceException,
    RateLimitException,
    BusinessLogicException,
    ConfigurationException,
    raise_not_found,
    raise_validation_error,
    raise_auth_error,
    raise_permission_error,
    raise_conflict_error,
    raise_database_error,
    raise_business_logic_error
)


@pytest.mark.unit
class TestBoardroomException:
    """Test base BoardroomException class."""
    
    def test_boardroom_exception_basic(self):
        """Test basic BoardroomException creation."""
        exception = BoardroomException("Test error message")
        
        assert str(exception) == "Test error message"
        assert exception.message == "Test error message"
        assert exception.error_code == "BOARDROOM_ERROR"
        assert exception.details == {}
        assert exception.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    def test_boardroom_exception_with_all_params(self):
        """Test BoardroomException with all parameters."""
        details = {"field": "test_field", "value": "test_value"}
        exception = BoardroomException(
            message="Custom error",
            error_code="CUSTOM_ERROR",
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST
        )
        
        assert exception.message == "Custom error"
        assert exception.error_code == "CUSTOM_ERROR"
        assert exception.details == details
        assert exception.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_boardroom_exception_to_dict(self):
        """Test exception to dictionary conversion."""
        details = {"context": "test"}
        exception = BoardroomException(
            message="Test message",
            error_code="TEST_ERROR",
            details=details,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        
        with patch('app.core.exceptions.datetime') as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            result = exception.to_dict()
        
        assert result["error"]["code"] == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert result["error"]["message"] == "Test message"
        assert result["error"]["type"] == "test_error"
        assert result["error"]["details"] == details
        assert result["error"]["timestamp"] == mock_now.isoformat()
    
    def test_boardroom_exception_details_default(self):
        """Test that details defaults to empty dict when None."""
        exception = BoardroomException("Test", details=None)
        assert exception.details == {}


@pytest.mark.unit
class TestValidationException:
    """Test ValidationException class."""
    
    def test_validation_exception_basic(self):
        """Test basic ValidationException creation."""
        exception = ValidationException("Validation failed")
        
        assert exception.message == "Validation failed"
        assert exception.error_code == "VALIDATION_ERROR"
        assert exception.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert exception.details == {}
    
    def test_validation_exception_with_field(self):
        """Test ValidationException with field specification."""
        exception = ValidationException("Email is required", field="email")
        
        assert exception.message == "Email is required"
        assert exception.details["field"] == "email"
    
    def test_validation_exception_with_details(self):
        """Test ValidationException with custom details."""
        details = {"min_length": 8, "max_length": 20}
        exception = ValidationException(
            "Password length invalid", 
            field="password", 
            details=details
        )
        
        assert exception.details["field"] == "password"
        assert exception.details["min_length"] == 8
        assert exception.details["max_length"] == 20


@pytest.mark.unit
class TestAuthenticationException:
    """Test AuthenticationException class."""
    
    def test_authentication_exception_default(self):
        """Test AuthenticationException with default message."""
        exception = AuthenticationException()
        
        assert exception.message == "Authentication failed"
        assert exception.error_code == "AUTHENTICATION_ERROR"
        assert exception.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_authentication_exception_custom_message(self):
        """Test AuthenticationException with custom message."""
        exception = AuthenticationException("Invalid token")
        
        assert exception.message == "Invalid token"
        assert exception.error_code == "AUTHENTICATION_ERROR"
        assert exception.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_authentication_exception_with_details(self):
        """Test AuthenticationException with details."""
        details = {"token_type": "Bearer", "expired": True}
        exception = AuthenticationException("Token expired", details=details)
        
        assert exception.message == "Token expired"
        assert exception.details == details


@pytest.mark.unit
class TestAuthorizationException:
    """Test AuthorizationException class."""
    
    def test_authorization_exception_default(self):
        """Test AuthorizationException with default message."""
        exception = AuthorizationException()
        
        assert exception.message == "Access denied"
        assert exception.error_code == "AUTHORIZATION_ERROR"
        assert exception.status_code == status.HTTP_403_FORBIDDEN
    
    def test_authorization_exception_custom_message(self):
        """Test AuthorizationException with custom message."""
        exception = AuthorizationException("Insufficient permissions")
        
        assert exception.message == "Insufficient permissions"
        assert exception.error_code == "AUTHORIZATION_ERROR"
        assert exception.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.unit
class TestResourceNotFoundException:
    """Test ResourceNotFoundException class."""
    
    def test_resource_not_found_basic(self):
        """Test basic ResourceNotFoundException."""
        exception = ResourceNotFoundException("User")
        
        assert exception.message == "User not found"
        assert exception.error_code == "RESOURCE_NOT_FOUND"
        assert exception.status_code == status.HTTP_404_NOT_FOUND
        assert exception.details["resource"] == "User"
    
    def test_resource_not_found_with_id(self):
        """Test ResourceNotFoundException with resource ID."""
        exception = ResourceNotFoundException("User", resource_id="123")
        
        assert exception.message == "User not found (ID: 123)"
        assert exception.details["resource"] == "User"
        assert exception.details["resource_id"] == "123"
    
    def test_resource_not_found_with_details(self):
        """Test ResourceNotFoundException with custom details."""
        details = {"search_criteria": "email=test@example.com"}
        exception = ResourceNotFoundException("User", details=details)
        
        assert exception.details["resource"] == "User"
        assert exception.details["search_criteria"] == "email=test@example.com"


@pytest.mark.unit
class TestConflictException:
    """Test ConflictException class."""
    
    def test_conflict_exception_basic(self):
        """Test basic ConflictException."""
        exception = ConflictException("Email already exists")
        
        assert exception.message == "Email already exists"
        assert exception.error_code == "CONFLICT_ERROR"
        assert exception.status_code == status.HTTP_409_CONFLICT
    
    def test_conflict_exception_with_resource(self):
        """Test ConflictException with resource specification."""
        exception = ConflictException("Already exists", resource="User")
        
        assert exception.message == "Already exists"
        assert exception.details["resource"] == "User"


@pytest.mark.unit
class TestDatabaseException:
    """Test DatabaseException class."""
    
    def test_database_exception_default(self):
        """Test DatabaseException with default message."""
        exception = DatabaseException()
        
        assert exception.message == "Database operation failed"
        assert exception.error_code == "DATABASE_ERROR"
        assert exception.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    def test_database_exception_custom_message(self):
        """Test DatabaseException with custom message."""
        exception = DatabaseException("Connection timeout")
        
        assert exception.message == "Connection timeout"
        assert exception.error_code == "DATABASE_ERROR"


@pytest.mark.unit
class TestExternalServiceException:
    """Test ExternalServiceException class."""
    
    def test_external_service_exception_basic(self):
        """Test basic ExternalServiceException."""
        exception = ExternalServiceException("OpenAI")
        
        assert exception.message == "OpenAI: External service error"
        assert exception.error_code == "EXTERNAL_SERVICE_ERROR"
        assert exception.status_code == status.HTTP_502_BAD_GATEWAY
        assert exception.details["service"] == "OpenAI"
    
    def test_external_service_exception_custom_message(self):
        """Test ExternalServiceException with custom message."""
        exception = ExternalServiceException("OpenAI", "API quota exceeded")
        
        assert exception.message == "OpenAI: API quota exceeded"
        assert exception.details["service"] == "OpenAI"
    
    def test_external_service_exception_with_details(self):
        """Test ExternalServiceException with custom details."""
        details = {"status_code": 429, "retry_after": 60}
        exception = ExternalServiceException("OpenAI", "Rate limited", details=details)
        
        assert exception.details["service"] == "OpenAI"
        assert exception.details["status_code"] == 429
        assert exception.details["retry_after"] == 60


@pytest.mark.unit
class TestRateLimitException:
    """Test RateLimitException class."""
    
    def test_rate_limit_exception_default(self):
        """Test RateLimitException with default message."""
        exception = RateLimitException()
        
        assert exception.message == "Rate limit exceeded"
        assert exception.error_code == "RATE_LIMIT_ERROR"
        assert exception.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    
    def test_rate_limit_exception_custom_message(self):
        """Test RateLimitException with custom message."""
        exception = RateLimitException("Too many requests per minute")
        
        assert exception.message == "Too many requests per minute"
        assert exception.error_code == "RATE_LIMIT_ERROR"


@pytest.mark.unit
class TestBusinessLogicException:
    """Test BusinessLogicException class."""
    
    def test_business_logic_exception_basic(self):
        """Test basic BusinessLogicException."""
        exception = BusinessLogicException("Invalid business rule")
        
        assert exception.message == "Invalid business rule"
        assert exception.error_code == "BUSINESS_LOGIC_ERROR"
        assert exception.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_business_logic_exception_with_rule(self):
        """Test BusinessLogicException with rule specification."""
        exception = BusinessLogicException("Cannot delete active user", rule="user_deletion")
        
        assert exception.message == "Cannot delete active user"
        assert exception.details["rule"] == "user_deletion"


@pytest.mark.unit
class TestConfigurationException:
    """Test ConfigurationException class."""
    
    def test_configuration_exception_basic(self):
        """Test basic ConfigurationException."""
        exception = ConfigurationException("Missing configuration")
        
        assert exception.message == "Missing configuration"
        assert exception.error_code == "CONFIGURATION_ERROR"
        assert exception.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    def test_configuration_exception_with_key(self):
        """Test ConfigurationException with config key."""
        exception = ConfigurationException("Key not found", config_key="DATABASE_URL")
        
        assert exception.message == "Key not found"
        assert exception.details["config_key"] == "DATABASE_URL"


@pytest.mark.unit
class TestUtilityFunctions:
    """Test utility functions for raising exceptions."""
    
    def test_raise_not_found_basic(self):
        """Test raise_not_found utility function."""
        with pytest.raises(ResourceNotFoundException) as exc_info:
            raise_not_found("User")
        
        exception = exc_info.value
        assert exception.message == "User not found"
        assert exception.details["resource"] == "User"
    
    def test_raise_not_found_with_id(self):
        """Test raise_not_found with resource ID."""
        with pytest.raises(ResourceNotFoundException) as exc_info:
            raise_not_found("User", "123")
        
        exception = exc_info.value
        assert exception.message == "User not found (ID: 123)"
        assert exception.details["resource_id"] == "123"
    
    def test_raise_validation_error_basic(self):
        """Test raise_validation_error utility function."""
        with pytest.raises(ValidationException) as exc_info:
            raise_validation_error("Invalid input")
        
        exception = exc_info.value
        assert exception.message == "Invalid input"
    
    def test_raise_validation_error_with_field(self):
        """Test raise_validation_error with field."""
        with pytest.raises(ValidationException) as exc_info:
            raise_validation_error("Email required", field="email")
        
        exception = exc_info.value
        assert exception.message == "Email required"
        assert exception.details["field"] == "email"
    
    def test_raise_auth_error_default(self):
        """Test raise_auth_error with default message."""
        with pytest.raises(AuthenticationException) as exc_info:
            raise_auth_error()
        
        exception = exc_info.value
        assert exception.message == "Authentication failed"
    
    def test_raise_auth_error_custom(self):
        """Test raise_auth_error with custom message."""
        with pytest.raises(AuthenticationException) as exc_info:
            raise_auth_error("Invalid credentials")
        
        exception = exc_info.value
        assert exception.message == "Invalid credentials"
    
    def test_raise_permission_error_default(self):
        """Test raise_permission_error with default message."""
        with pytest.raises(AuthorizationException) as exc_info:
            raise_permission_error()
        
        exception = exc_info.value
        assert exception.message == "Access denied"
    
    def test_raise_permission_error_custom(self):
        """Test raise_permission_error with custom message."""
        with pytest.raises(AuthorizationException) as exc_info:
            raise_permission_error("Insufficient privileges")
        
        exception = exc_info.value
        assert exception.message == "Insufficient privileges"
    
    def test_raise_conflict_error_basic(self):
        """Test raise_conflict_error utility function."""
        with pytest.raises(ConflictException) as exc_info:
            raise_conflict_error("Resource conflict")
        
        exception = exc_info.value
        assert exception.message == "Resource conflict"
    
    def test_raise_conflict_error_with_resource(self):
        """Test raise_conflict_error with resource."""
        with pytest.raises(ConflictException) as exc_info:
            raise_conflict_error("Already exists", resource="User")
        
        exception = exc_info.value
        assert exception.message == "Already exists"
        assert exception.details["resource"] == "User"
    
    def test_raise_database_error_default(self):
        """Test raise_database_error with default message."""
        with pytest.raises(DatabaseException) as exc_info:
            raise_database_error()
        
        exception = exc_info.value
        assert exception.message == "Database operation failed"
    
    def test_raise_database_error_custom(self):
        """Test raise_database_error with custom message."""
        with pytest.raises(DatabaseException) as exc_info:
            raise_database_error("Connection lost")
        
        exception = exc_info.value
        assert exception.message == "Connection lost"
    
    def test_raise_business_logic_error_basic(self):
        """Test raise_business_logic_error utility function."""
        with pytest.raises(BusinessLogicException) as exc_info:
            raise_business_logic_error("Business rule violated")
        
        exception = exc_info.value
        assert exception.message == "Business rule violated"
    
    def test_raise_business_logic_error_with_rule(self):
        """Test raise_business_logic_error with rule."""
        with pytest.raises(BusinessLogicException) as exc_info:
            raise_business_logic_error("Cannot proceed", rule="workflow_validation")
        
        exception = exc_info.value
        assert exception.message == "Cannot proceed"
        assert exception.details["rule"] == "workflow_validation"


@pytest.mark.unit
class TestExceptionInheritance:
    """Test exception inheritance and hierarchy."""
    
    def test_all_exceptions_inherit_from_boardroom_exception(self):
        """Test that all custom exceptions inherit from BoardroomException."""
        exception_classes = [
            ValidationException,
            AuthenticationException,
            AuthorizationException,
            ResourceNotFoundException,
            ConflictException,
            DatabaseException,
            ExternalServiceException,
            RateLimitException,
            BusinessLogicException,
            ConfigurationException
        ]
        
        for exc_class in exception_classes:
            assert issubclass(exc_class, BoardroomException)
            assert issubclass(exc_class, Exception)
    
    def test_all_exceptions_inherit_from_base_exception(self):
        """Test that all custom exceptions inherit from base Exception."""
        exception_classes = [
            BoardroomException,
            ValidationException,
            AuthenticationException,
            AuthorizationException,
            ResourceNotFoundException,
            ConflictException,
            DatabaseException,
            ExternalServiceException,
            RateLimitException,
            BusinessLogicException,
            ConfigurationException
        ]
        
        for exc_class in exception_classes:
            assert issubclass(exc_class, Exception)


@pytest.mark.unit
class TestExceptionSerialization:
    """Test exception serialization for API responses."""
    
    def test_exception_to_dict_structure(self):
        """Test that all exceptions produce consistent dict structure."""
        exceptions = [
            ValidationException("Test validation"),
            AuthenticationException("Test auth"),
            AuthorizationException("Test authz"),
            ResourceNotFoundException("Resource", "123"),
            ConflictException("Test conflict"),
            DatabaseException("Test db"),
            ExternalServiceException("Service", "Test external"),
            RateLimitException("Test rate limit"),
            BusinessLogicException("Test business"),
            ConfigurationException("Test config")
        ]
        
        with patch('app.core.exceptions.datetime') as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            for exception in exceptions:
                result = exception.to_dict()
                
                # Check structure
                assert "error" in result
                error = result["error"]
                
                assert "code" in error
                assert "message" in error
                assert "type" in error
                assert "details" in error
                assert "timestamp" in error
                
                # Check types
                assert isinstance(error["code"], int)
                assert isinstance(error["message"], str)
                assert isinstance(error["type"], str)
                assert isinstance(error["details"], dict)
                assert isinstance(error["timestamp"], str)
                
                # Check that type is lowercase version of error_code
                expected_type = exception.error_code.lower()
                assert error["type"] == expected_type
    
    def test_exception_json_serializable(self):
        """Test that exception dict is JSON serializable."""
        import json
        
        exception = ValidationException("Test", field="email", details={"min": 1})
        result = exception.to_dict()
        
        # Should not raise an exception
        json_str = json.dumps(result)
        assert isinstance(json_str, str)
        
        # Should be able to deserialize back
        deserialized = json.loads(json_str)
        assert deserialized == result