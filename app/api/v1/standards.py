"""API standards and documentation endpoints.

This module provides endpoints for API versioning, documentation,
and standards information.
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Request, Response, Depends
from fastapi.responses import JSONResponse

from app.core.api_standards import (
    APIResponseFormatter,
    add_standard_headers,
    get_api_version_from_request,
    validate_api_version
)
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.schemas.api import (
    APIVersionInfo,
    HealthResponse,
    StandardResponse
)

router = APIRouter()


@router.get("/version", response_model=StandardResponse[APIVersionInfo])
@limiter.limit("100 per minute")
async def get_api_version_info(request: Request, response: Response):
    """Get API version information and supported versions.
    
    Returns comprehensive information about the current API version,
    supported versions, deprecated versions, and documentation links.
    
    Returns:
        APIVersionInfo: Version information and metadata
    """
    logger.info("api_version_info_requested")
    
    version_info = APIVersionInfo(
        version=settings.VERSION,
        supported_versions=["1.0.0", "v1"],
        deprecated_versions={},  # No deprecated versions yet
        latest_version=settings.VERSION,
        documentation_url=f"{request.base_url}docs"
    )
    
    add_standard_headers(response, request)
    
    return APIResponseFormatter.format_success_response(
        data=version_info.model_dump(),
        message="API version information retrieved",
        request=request
    )


@router.get("/health/detailed", response_model=StandardResponse[HealthResponse])
@limiter.limit("50 per minute")
async def get_detailed_health(request: Request, response: Response):
    """Get detailed health information with component status.
    
    Provides comprehensive health information including individual
    component status, uptime, and system metrics.
    
    Returns:
        HealthResponse: Detailed health information
    """
    logger.info("detailed_health_check_requested")
    
    # Import here to avoid circular imports
    from app.services.database import database_service
    
    # Check database connectivity
    db_healthy = await database_service.health_check()
    
    # Calculate uptime (basic implementation)
    uptime_info = {
        "started_at": "2024-01-01T00:00:00Z",  # This should come from app startup
        "uptime_seconds": 3600,  # This should be calculated
        "status": "healthy"
    }
    
    health_info = HealthResponse(
        status="healthy" if db_healthy else "degraded",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT.value,
        components={
            "api": "healthy",
            "database": "healthy" if db_healthy else "unhealthy",
            "authentication": "healthy",
            "rate_limiter": "healthy",
            "monitoring": "healthy"
        },
        timestamp=datetime.now(),
        uptime=uptime_info
    )
    
    add_standard_headers(response, request)
    
    status_code = 200 if db_healthy else 503
    
    return JSONResponse(
        content=APIResponseFormatter.format_success_response(
            data=health_info.model_dump(),
            message="Detailed health information retrieved",
            request=request
        ),
        status_code=status_code
    )


@router.get("/standards", response_model=StandardResponse[Dict[str, Any]])
@limiter.limit("20 per minute")
async def get_api_standards(request: Request, response: Response):
    """Get API standards and conventions documentation.
    
    Returns information about API standards, response formats,
    error codes, and usage patterns.
    
    Returns:
        Dict containing API standards documentation
    """
    logger.info("api_standards_requested")
    
    standards_info = {
        "response_format": {
            "structure": "All responses follow StandardResponse format",
            "fields": {
                "success": "Boolean indicating request success",
                "data": "Response payload (varies by endpoint)",
                "message": "Human-readable result message",
                "metadata": "Request metadata (timestamp, request_id, etc.)",
                "pagination": "Pagination info for list endpoints",
                "errors": "Error details if applicable"
            }
        },
        "error_handling": {
            "format": "Errors follow StandardErrorResponse format",
            "codes": {
                "400": "Bad Request - Invalid request format",
                "401": "Unauthorized - Authentication required",
                "403": "Forbidden - Insufficient permissions",
                "404": "Not Found - Resource not found",
                "422": "Unprocessable Entity - Validation error",
                "429": "Too Many Requests - Rate limit exceeded",
                "500": "Internal Server Error - Server error"
            }
        },
        "versioning": {
            "strategy": "URL path versioning (/api/v1/)",
            "header_support": "X-API-Version header supported",
            "current_version": settings.VERSION,
            "supported_versions": ["1.0.0", "v1"]
        },
        "pagination": {
            "parameters": {
                "page": "Page number (1-based)",
                "size": "Items per page (1-100)",
                "sort": "Sort field",
                "order": "Sort order (asc/desc)"
            },
            "response": "Includes PaginationInfo in pagination field"
        },
        "rate_limiting": {
            "headers": {
                "X-RateLimit-Limit": "Request limit",
                "X-RateLimit-Remaining": "Remaining requests",
                "X-RateLimit-Reset": "Reset timestamp"
            },
            "default_limits": settings.RATE_LIMIT_DEFAULT
        },
        "authentication": {
            "type": "Bearer token (JWT)",
            "header": "Authorization: Bearer <token>",
            "endpoints": {
                "login": "POST /api/v1/auth/login",
                "register": "POST /api/v1/auth/register"
            }
        },
        "content_types": {
            "request": "application/json",
            "response": "application/json",
            "streaming": "text/event-stream (for SSE endpoints)"
        }
    }
    
    add_standard_headers(response, request)
    
    return APIResponseFormatter.format_success_response(
        data=standards_info,
        message="API standards information retrieved",
        request=request
    )


@router.get("/errors", response_model=StandardResponse[Dict[str, Any]])
@limiter.limit("20 per minute")
async def get_error_codes(request: Request, response: Response):
    """Get comprehensive error code documentation.
    
    Returns detailed information about all possible error codes,
    their meanings, and how to handle them.
    
    Returns:
        Dict containing error code documentation
    """
    logger.info("error_codes_requested")
    
    error_documentation = {
        "error_types": {
            "VALIDATION_ERROR": {
                "description": "Input validation failed",
                "status_code": 422,
                "examples": [
                    "Invalid email format",
                    "Password too weak",
                    "Required field missing"
                ]
            },
            "AUTHENTICATION_ERROR": {
                "description": "Authentication failed",
                "status_code": 401,
                "examples": [
                    "Invalid credentials",
                    "Token expired",
                    "Token malformed"
                ]
            },
            "AUTHORIZATION_ERROR": {
                "description": "Insufficient permissions",
                "status_code": 403,
                "examples": [
                    "Access denied to resource",
                    "Role permission insufficient"
                ]
            },
            "RESOURCE_NOT_FOUND": {
                "description": "Requested resource not found",
                "status_code": 404,
                "examples": [
                    "User not found",
                    "Session not found",
                    "Decision not found"
                ]
            },
            "CONFLICT_ERROR": {
                "description": "Resource conflict",
                "status_code": 409,
                "examples": [
                    "Email already exists",
                    "Duplicate vote attempt"
                ]
            },
            "RATE_LIMIT_ERROR": {
                "description": "Rate limit exceeded",
                "status_code": 429,
                "examples": [
                    "Too many requests per minute",
                    "Daily quota exceeded"
                ]
            },
            "DATABASE_ERROR": {
                "description": "Database operation failed",
                "status_code": 500,
                "examples": [
                    "Connection timeout",
                    "Query execution failed"
                ]
            },
            "EXTERNAL_SERVICE_ERROR": {
                "description": "External service error",
                "status_code": 502,
                "examples": [
                    "LLM service unavailable",
                    "Third-party API timeout"
                ]
            }
        },
        "error_response_format": {
            "success": False,
            "error": {
                "code": "HTTP status code",
                "message": "Human-readable error message",
                "type": "Error type identifier",
                "field": "Field that caused error (if applicable)",
                "details": "Additional error context"
            },
            "metadata": {
                "timestamp": "Error timestamp",
                "request_id": "Request identifier for tracing"
            }
        },
        "troubleshooting": {
            "401_errors": "Check Authorization header format and token validity",
            "422_errors": "Review request payload against schema requirements",
            "429_errors": "Implement exponential backoff and respect rate limits",
            "500_errors": "Check system status and contact support if persistent"
        }
    }
    
    add_standard_headers(response, request)
    
    return APIResponseFormatter.format_success_response(
        data=error_documentation,
        message="Error code documentation retrieved",
        request=request
    )


@router.get("/examples", response_model=StandardResponse[Dict[str, Any]])
@limiter.limit("20 per minute")
async def get_api_examples(request: Request, response: Response):
    """Get API usage examples and patterns.
    
    Returns practical examples of common API usage patterns,
    including authentication, pagination, and error handling.
    
    Returns:
        Dict containing API usage examples
    """
    logger.info("api_examples_requested")
    
    examples = {
        "authentication": {
            "login_request": {
                "method": "POST",
                "url": "/api/v1/auth/login",
                "headers": {
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                "body": "username=user@example.com&password=SecurePass123!"
            },
            "authenticated_request": {
                "method": "GET",
                "url": "/api/v1/chatbot/messages",
                "headers": {
                    "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "Content-Type": "application/json"
                }
            }
        },
        "pagination": {
            "request": {
                "method": "GET",
                "url": "/api/v1/boardroom/decisions?page=2&size=10&sort=created_at&order=desc"
            },
            "response": {
                "success": True,
                "data": ["...decision objects..."],
                "pagination": {
                    "page": 2,
                    "size": 10,
                    "total": 45,
                    "pages": 5,
                    "has_next": True,
                    "has_prev": True
                }
            }
        },
        "error_handling": {
            "validation_error": {
                "success": False,
                "error": {
                    "code": 422,
                    "message": "Password must contain at least one uppercase letter",
                    "type": "validation_error",
                    "field": "password"
                }
            },
            "authentication_error": {
                "success": False,
                "error": {
                    "code": 401,
                    "message": "Invalid authentication credentials",
                    "type": "authentication_error"
                }
            }
        },
        "streaming": {
            "server_sent_events": {
                "method": "GET",
                "url": "/api/v1/boardroom/events?decision_id=123e4567-e89b-12d3-a456-426614174000",
                "headers": {
                    "Accept": "text/event-stream",
                    "Authorization": "Bearer ..."
                },
                "response_format": "event: state_update\\ndata: {\"status\": \"voting_open\"}\\n\\n"
            },
            "chat_streaming": {
                "method": "POST",
                "url": "/api/v1/chatbot/chat/stream",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer ..."
                },
                "body": {
                    "messages": [
                        {"role": "user", "content": "Hello, how are you?"}
                    ]
                }
            }
        }
    }
    
    add_standard_headers(response, request)
    
    return APIResponseFormatter.format_success_response(
        data=examples,
        message="API usage examples retrieved",
        request=request
    )