"""OpenAPI schema customization for enhanced API documentation.

This module provides utilities for customizing the OpenAPI schema
with enhanced documentation, examples, and standardized response patterns.
"""

from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.core.config import settings


def add_response_examples() -> Dict[str, Any]:
    """Add comprehensive response examples to OpenAPI schema."""
    return {
        "SuccessResponse": {
            "value": {
                "success": True,
                "data": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "Example Resource",
                    "created_at": "2024-01-01T12:00:00Z"
                },
                "message": "Resource retrieved successfully",
                "metadata": {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "request_id": "req_123456789",
                    "version": "1.0.0",
                    "environment": "development"
                }
            }
        },
        "ListResponse": {
            "value": {
                "success": True,
                "data": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "Example Resource 1"
                    },
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174001",
                        "name": "Example Resource 2"
                    }
                ],
                "message": "Resources retrieved successfully",
                "pagination": {
                    "page": 1,
                    "size": 10,
                    "total": 25,
                    "pages": 3,
                    "has_next": True,
                    "has_prev": False
                },
                "metadata": {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "request_id": "req_123456789",
                    "version": "1.0.0",
                    "environment": "development"
                }
            }
        },
        "ErrorResponse": {
            "value": {
                "success": False,
                "error": {
                    "code": "422",
                    "message": "Validation error",
                    "type": "validation_error",
                    "field": "email",
                    "details": {
                        "validation_errors": [
                            {
                                "field": "email",
                                "message": "Invalid email format",
                                "type": "value_error.email"
                            }
                        ]
                    }
                },
                "metadata": {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "request_id": "req_123456789",
                    "version": "1.0.0",
                    "environment": "development"
                }
            }
        },
        "AuthenticationError": {
            "value": {
                "success": False,
                "error": {
                    "code": "401",
                    "message": "Invalid authentication credentials",
                    "type": "authentication_error"
                },
                "metadata": {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "request_id": "req_123456789",
                    "version": "1.0.0",
                    "environment": "development"
                }
            }
        },
        "RateLimitError": {
            "value": {
                "success": False,
                "error": {
                    "code": "429",
                    "message": "Rate limit exceeded",
                    "type": "rate_limit_error",
                    "details": {
                        "limit": 100,
                        "remaining": 0,
                        "reset": "2024-01-01T13:00:00Z"
                    }
                },
                "metadata": {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "request_id": "req_123456789",
                    "version": "1.0.0",
                    "environment": "development"
                }
            }
        }
    }


def add_security_schemes() -> Dict[str, Any]:
    """Add security schemes to OpenAPI schema."""
    return {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token for authenticating requests. Obtain from /auth/login endpoint."
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for external service integrations."
        }
    }


def customize_openapi_schema(app: FastAPI) -> Dict[str, Any]:
    """Customize the OpenAPI schema with enhanced documentation.
    
    Args:
        app: FastAPI application instance
    
    Returns:
        Customized OpenAPI schema
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = add_security_schemes()

    # Add response examples
    response_examples = add_response_examples()
    if "examples" not in openapi_schema["components"]:
        openapi_schema["components"]["examples"] = {}
    openapi_schema["components"]["examples"].update(response_examples)

    # Add common response schemas
    common_responses = {
        "ValidationError": {
            "description": "Validation Error",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/StandardErrorResponse"},
                    "examples": {
                        "validation_error": {"$ref": "#/components/examples/ErrorResponse"}
                    }
                }
            }
        },
        "AuthenticationError": {
            "description": "Authentication Error",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/StandardErrorResponse"},
                    "examples": {
                        "auth_error": {"$ref": "#/components/examples/AuthenticationError"}
                    }
                }
            }
        },
        "RateLimitError": {
            "description": "Rate Limit Exceeded",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/StandardErrorResponse"},
                    "examples": {
                        "rate_limit": {"$ref": "#/components/examples/RateLimitError"}
                    }
                }
            },
            "headers": {
                "X-RateLimit-Limit": {
                    "description": "Request limit per time window",
                    "schema": {"type": "integer"}
                },
                "X-RateLimit-Remaining": {
                    "description": "Remaining requests in current window",
                    "schema": {"type": "integer"}
                },
                "X-RateLimit-Reset": {
                    "description": "Time when rate limit resets",
                    "schema": {"type": "string", "format": "date-time"}
                }
            }
        }
    }

    if "responses" not in openapi_schema["components"]:
        openapi_schema["components"]["responses"] = {}
    openapi_schema["components"]["responses"].update(common_responses)

    # Add API information
    openapi_schema["info"]["x-api-id"] = "boardroom-ai-api"
    openapi_schema["info"]["x-audience"] = "public"
    openapi_schema["info"]["x-api-version"] = settings.VERSION
    
    # Add external documentation
    openapi_schema["externalDocs"] = {
        "description": "Find more info here",
        "url": "https://github.com/boardroom-ai/api"
    }

    # Add custom extensions
    openapi_schema["x-tagGroups"] = [
        {
            "name": "Core API",
            "tags": ["Authentication", "Chat & AI", "Health & Status"]
        },
        {
            "name": "Boardroom Features",
            "tags": ["Boardroom & Decisions", "Decision Management", "Real-time Events"]
        },
        {
            "name": "Documentation",
            "tags": ["API Standards & Documentation"]
        }
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def add_standard_headers_to_schema(openapi_schema: Dict[str, Any]) -> None:
    """Add standard headers to all responses in the OpenAPI schema.
    
    Args:
        openapi_schema: OpenAPI schema to modify
    """
    standard_headers = {
        "X-Request-ID": {
            "description": "Unique request identifier for tracing",
            "schema": {"type": "string", "format": "uuid"}
        },
        "X-API-Version": {
            "description": "API version that handled this request",
            "schema": {"type": "string"}
        },
        "X-Response-Time": {
            "description": "Response time in milliseconds",
            "schema": {"type": "integer"}
        },
        "X-Environment": {
            "description": "Environment that generated this response",
            "schema": {"type": "string"}
        }
    }

    # Add headers to all successful responses
    for path_data in openapi_schema.get("paths", {}).values():
        for method_data in path_data.values():
            if "responses" in method_data:
                for status_code, response_data in method_data["responses"].items():
                    if status_code.startswith("2"):  # Success responses
                        if "headers" not in response_data:
                            response_data["headers"] = {}
                        response_data["headers"].update(standard_headers)