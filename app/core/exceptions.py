"""Custom exception classes for the Boardroom AI application.

This module defines standardized exception classes with proper error categorization
and consistent error response patterns for effective troubleshooting in solo development.
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class BoardroomException(Exception):
    """Base exception class for all Boardroom AI specific exceptions.
    
    Provides consistent error handling patterns and categorization.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "BOARDROOM_ERROR",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        """Initialize the exception.
        
        Args:
            message: Human-readable error message
            error_code: Specific error code for categorization
            details: Additional error details (sanitized)
            status_code: HTTP status code for API responses
        """
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        from datetime import datetime
        
        return {
            "error": {
                "code": self.status_code,
                "message": self.message,
                "type": self.error_code.lower(),
                "details": self.details,
                "timestamp": datetime.now().isoformat()
            }
        }


class ValidationException(BoardroomException):
    """Exception for input validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if field:
            error_details["field"] = field
            
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=error_details,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class AuthenticationException(BoardroomException):
    """Exception for authentication-related errors."""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            details=details,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class AuthorizationException(BoardroomException):
    """Exception for authorization-related errors."""
    
    def __init__(self, message: str = "Access denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            details=details,
            status_code=status.HTTP_403_FORBIDDEN
        )


class ResourceNotFoundException(BoardroomException):
    """Exception for resource not found errors."""
    
    def __init__(self, resource: str, resource_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        message = f"{resource} not found"
        if resource_id:
            message += f" (ID: {resource_id})"
            
        error_details = details or {}
        error_details.update({"resource": resource})
        if resource_id:
            error_details["resource_id"] = resource_id
            
        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            details=error_details,
            status_code=status.HTTP_404_NOT_FOUND
        )


class ConflictException(BoardroomException):
    """Exception for resource conflict errors."""
    
    def __init__(self, message: str, resource: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if resource:
            error_details["resource"] = resource
            
        super().__init__(
            message=message,
            error_code="CONFLICT_ERROR",
            details=error_details,
            status_code=status.HTTP_409_CONFLICT
        )


class DatabaseException(BoardroomException):
    """Exception for database-related errors."""
    
    def __init__(self, message: str = "Database operation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class ExternalServiceException(BoardroomException):
    """Exception for external service integration errors."""
    
    def __init__(
        self, 
        service_name: str, 
        message: str = "External service error", 
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        error_details["service"] = service_name
        
        super().__init__(
            message=f"{service_name}: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            details=error_details,
            status_code=status.HTTP_502_BAD_GATEWAY
        )


class RateLimitException(BoardroomException):
    """Exception for rate limiting errors."""
    
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            details=details,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )


class BusinessLogicException(BoardroomException):
    """Exception for business logic violations."""
    
    def __init__(self, message: str, rule: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if rule:
            error_details["rule"] = rule
            
        super().__init__(
            message=message,
            error_code="BUSINESS_LOGIC_ERROR",
            details=error_details,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class ConfigurationException(BoardroomException):
    """Exception for configuration-related errors."""
    
    def __init__(self, message: str, config_key: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if config_key:
            error_details["config_key"] = config_key
            
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details=error_details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Utility functions for common error scenarios

def raise_not_found(resource: str, resource_id: Optional[str] = None) -> None:
    """Utility function to raise a not found exception."""
    raise ResourceNotFoundException(resource=resource, resource_id=resource_id)


def raise_validation_error(message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None:
    """Utility function to raise a validation exception."""
    raise ValidationException(message=message, field=field, details=details)


def raise_auth_error(message: str = "Authentication failed") -> None:
    """Utility function to raise an authentication exception."""
    raise AuthenticationException(message=message)


def raise_permission_error(message: str = "Access denied") -> None:
    """Utility function to raise an authorization exception."""
    raise AuthorizationException(message=message)


def raise_conflict_error(message: str, resource: Optional[str] = None) -> None:
    """Utility function to raise a conflict exception."""
    raise ConflictException(message=message, resource=resource)


def raise_database_error(message: str = "Database operation failed") -> None:
    """Utility function to raise a database exception."""
    raise DatabaseException(message=message)


def raise_business_logic_error(message: str, rule: Optional[str] = None) -> None:
    """Utility function to raise a business logic exception."""
    raise BusinessLogicException(message=message, rule=rule)