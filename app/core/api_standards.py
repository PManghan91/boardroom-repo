"""API standardization utilities and middleware.

This module provides utilities for implementing consistent API patterns,
response formatting, and standardization across all endpoints.
"""

import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union

from fastapi import Request, Response
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import logger
from app.schemas.api import (
    APIMetadata,
    PaginationInfo,
    RateLimitInfo,
    StandardErrorResponse,
    StandardResponse,
)


class APIStandardsMiddleware:
    """Middleware for applying API standards across all endpoints."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Add request timestamp
        request.state.start_time = time.time()
        
        # Log request
        logger.info(
            "api_request_started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown"
        )
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Add standard headers
                headers = dict(message.get("headers", []))
                headers.update({
                    b"x-request-id": request_id.encode(),
                    b"x-api-version": settings.VERSION.encode(),
                    b"x-response-time": str(int((time.time() - request.state.start_time) * 1000)).encode(),
                })
                message["headers"] = [(k.encode() if isinstance(k, str) else k, 
                                     v.encode() if isinstance(v, str) else v) 
                                    for k, v in headers.items()]
            
            await send(message)
        
        await self.app(scope, receive, send_wrapper)


def create_standard_response(
    data: Any = None,
    message: str = "Request processed successfully",
    success: bool = True,
    pagination: Optional[PaginationInfo] = None,
    request_id: Optional[str] = None,
    errors: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Create a standardized API response.
    
    Args:
        data: The response data
        message: Human-readable message
        success: Whether the request was successful
        pagination: Pagination information for list endpoints
        request_id: Request ID for tracing
        errors: List of errors if any
    
    Returns:
        Standardized response dictionary
    """
    metadata = APIMetadata(
        timestamp=datetime.now(),
        request_id=request_id or str(uuid.uuid4()),
        version=settings.VERSION,
        environment=settings.ENVIRONMENT.value
    )
    
    response = StandardResponse(
        success=success,
        data=data,
        message=message,
        metadata=metadata,
        pagination=pagination,
        errors=errors
    )
    
    return response.model_dump(exclude_none=True)


def create_error_response(
    code: str,
    message: str,
    field: Optional[str] = None,
    error_type: str = "error",
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a standardized error response.
    
    Args:
        code: Error code
        message: Error message
        field: Field that caused the error
        error_type: Type of error
        details: Additional error details
        request_id: Request ID for tracing
    
    Returns:
        Standardized error response dictionary
    """
    from app.schemas.api import ErrorDetail
    
    metadata = APIMetadata(
        timestamp=datetime.now(),
        request_id=request_id or str(uuid.uuid4()),
        version=settings.VERSION,
        environment=settings.ENVIRONMENT.value
    )
    
    error = ErrorDetail(
        code=code,
        message=message,
        field=field,
        type=error_type,
        details=details
    )
    
    response = StandardErrorResponse(
        error=error,
        metadata=metadata
    )
    
    return response.model_dump(exclude_none=True)


def create_pagination_info(
    page: int,
    size: int,
    total: int
) -> PaginationInfo:
    """Create pagination information.
    
    Args:
        page: Current page number
        size: Items per page
        total: Total number of items
    
    Returns:
        PaginationInfo object
    """
    pages = (total + size - 1) // size if total > 0 else 0
    
    return PaginationInfo(
        page=page,
        size=size,
        total=total,
        pages=pages,
        has_next=page < pages,
        has_prev=page > 1
    )


def create_rate_limit_info(
    limit: int,
    remaining: int,
    reset_timestamp: datetime,
    retry_after: Optional[int] = None
) -> RateLimitInfo:
    """Create rate limit information.
    
    Args:
        limit: Request limit
        remaining: Remaining requests
        reset_timestamp: When the limit resets
        retry_after: Seconds to wait before retrying
    
    Returns:
        RateLimitInfo object
    """
    return RateLimitInfo(
        limit=limit,
        remaining=remaining,
        reset=reset_timestamp,
        retry_after=retry_after
    )


def add_standard_headers(response: Response, request: Request) -> None:
    """Add standard headers to API responses.
    
    Args:
        response: FastAPI response object
        request: FastAPI request object
    """
    response.headers["X-API-Version"] = settings.VERSION
    response.headers["X-Environment"] = settings.ENVIRONMENT.value
    
    if hasattr(request.state, "request_id"):
        response.headers["X-Request-ID"] = request.state.request_id
    
    if hasattr(request.state, "start_time"):
        response_time = int((time.time() - request.state.start_time) * 1000)
        response.headers["X-Response-Time"] = str(response_time)


def validate_api_version(version: str) -> bool:
    """Validate if the requested API version is supported.
    
    Args:
        version: API version string
    
    Returns:
        True if version is supported, False otherwise
    """
    supported_versions = ["v1", "1.0", "1.0.0"]
    return version.lower() in supported_versions


def get_api_version_from_request(request: Request) -> str:
    """Extract API version from request.
    
    Args:
        request: FastAPI request object
    
    Returns:
        API version string
    """
    # Check Accept header first
    accept_header = request.headers.get("accept", "")
    if "application/vnd.boardroom.v" in accept_header:
        try:
            version = accept_header.split("application/vnd.boardroom.v")[1].split("+")[0]
            return version
        except IndexError:
            pass
    
    # Check custom header
    version_header = request.headers.get("X-API-Version")
    if version_header:
        return version_header
    
    # Default to current version
    return settings.VERSION


class APIResponseFormatter:
    """Formatter for consistent API responses."""
    
    @staticmethod
    def format_success_response(
        data: Any,
        message: str = "Success",
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        """Format a successful response."""
        request_id = getattr(request.state, "request_id", None) if request else None
        return create_standard_response(
            data=data,
            message=message,
            success=True,
            request_id=request_id
        )
    
    @staticmethod
    def format_list_response(
        items: List[Any],
        total: int,
        page: int,
        size: int,
        message: str = "List retrieved successfully",
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        """Format a paginated list response."""
        request_id = getattr(request.state, "request_id", None) if request else None
        pagination = create_pagination_info(page, size, total)
        
        return create_standard_response(
            data=items,
            message=message,
            success=True,
            pagination=pagination,
            request_id=request_id
        )
    
    @staticmethod
    def format_error_response(
        code: str,
        message: str,
        error_type: str = "error",
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        """Format an error response."""
        request_id = getattr(request.state, "request_id", None) if request else None
        return create_error_response(
            code=code,
            message=message,
            field=field,
            error_type=error_type,
            details=details,
            request_id=request_id
        )