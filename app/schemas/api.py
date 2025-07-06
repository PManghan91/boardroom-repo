"""Standardized API schemas for consistent request/response patterns.

This module provides base schemas for standardized API responses, pagination,
error handling, and metadata across all endpoints.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, Field

# Generic type for data payloads
T = TypeVar('T')


class APIMetadata(BaseModel):
    """Standard metadata included in all API responses.
    
    Attributes:
        timestamp: ISO timestamp of when the response was generated
        request_id: Unique identifier for this request (for tracing)
        version: API version that handled this request
        environment: Environment where this response was generated
    """
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique request identifier")
    version: str = Field(default="1.0.0", description="API version")
    environment: str = Field(default="development", description="Environment identifier")


class PaginationInfo(BaseModel):
    """Pagination information for list endpoints.
    
    Attributes:
        page: Current page number (1-based)
        size: Number of items per page
        total: Total number of items available
        pages: Total number of pages available
        has_next: Whether there is a next page
        has_prev: Whether there is a previous page
    """
    page: int = Field(..., ge=1, description="Current page number")
    size: int = Field(..., ge=1, le=100, description="Items per page")
    total: int = Field(..., ge=0, description="Total number of items")
    pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class StandardResponse(BaseModel, Generic[T]):
    """Standard response wrapper for all API endpoints.
    
    Provides consistent structure across all endpoints with success/error handling,
    metadata, and optional pagination.
    
    Attributes:
        success: Whether the request was successful
        data: The actual response data (type varies by endpoint)
        message: Human-readable message describing the result
        metadata: Standard metadata about the response
        pagination: Pagination information (for list endpoints)
        errors: List of errors (if any occurred)
    """
    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[T] = Field(None, description="Response data")
    message: str = Field(default="Request processed successfully", description="Result message")
    metadata: APIMetadata = Field(default_factory=APIMetadata, description="Response metadata")
    pagination: Optional[PaginationInfo] = Field(None, description="Pagination information")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="List of errors if any")


class ErrorDetail(BaseModel):
    """Detailed error information.
    
    Attributes:
        code: Error code for programmatic handling
        message: Human-readable error message
        field: Field that caused the error (if applicable)
        type: Type of error (validation, authentication, etc.)
        details: Additional error context
    """
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    field: Optional[str] = Field(None, description="Field that caused the error")
    type: str = Field(..., description="Error type")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error context")


class StandardErrorResponse(BaseModel):
    """Standard error response structure.
    
    Attributes:
        success: Always False for error responses
        error: Detailed error information
        metadata: Standard metadata about the response
    """
    success: bool = Field(default=False, description="Always False for errors")
    error: ErrorDetail = Field(..., description="Error details")
    metadata: APIMetadata = Field(default_factory=APIMetadata, description="Response metadata")


class HealthResponse(BaseModel):
    """Health check response schema.
    
    Attributes:
        status: Overall system status
        version: Application version
        environment: Environment identifier
        components: Status of individual components
        timestamp: When the health check was performed
        uptime: System uptime information
    """
    status: str = Field(..., description="Overall system status")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment identifier")
    components: Dict[str, str] = Field(default_factory=dict, description="Component statuses")
    timestamp: datetime = Field(default_factory=datetime.now, description="Health check timestamp")
    uptime: Optional[Dict[str, Any]] = Field(None, description="System uptime information")


class APIVersionInfo(BaseModel):
    """API version information.
    
    Attributes:
        version: Current API version
        supported_versions: List of supported API versions
        deprecated_versions: List of deprecated versions with sunset dates
        latest_version: Latest available API version
        documentation_url: URL to API documentation
    """
    version: str = Field(..., description="Current API version")
    supported_versions: List[str] = Field(default_factory=list, description="Supported versions")
    deprecated_versions: Dict[str, str] = Field(default_factory=dict, description="Deprecated versions with dates")
    latest_version: str = Field(..., description="Latest API version")
    documentation_url: str = Field(..., description="API documentation URL")


class APIListRequest(BaseModel):
    """Standard request schema for list endpoints.
    
    Attributes:
        page: Page number to retrieve (1-based)
        size: Number of items per page
        sort: Sort field
        order: Sort order (asc/desc)
        search: Search query string
        filters: Additional filters as key-value pairs
    """
    page: int = Field(default=1, ge=1, le=1000, description="Page number")
    size: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort: Optional[str] = Field(None, description="Sort field")
    order: str = Field(default="asc", pattern="^(asc|desc)$", description="Sort order")
    search: Optional[str] = Field(None, max_length=100, description="Search query")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters")


class RateLimitInfo(BaseModel):
    """Rate limiting information.
    
    Attributes:
        limit: Maximum requests allowed in the time window
        remaining: Remaining requests in current window
        reset: When the rate limit window resets (timestamp)
        retry_after: Seconds to wait before retrying (if rate limited)
    """
    limit: int = Field(..., description="Request limit")
    remaining: int = Field(..., description="Remaining requests")
    reset: datetime = Field(..., description="Reset timestamp")
    retry_after: Optional[int] = Field(None, description="Retry after seconds")


# Common response types
SuccessResponse = StandardResponse[Dict[str, Any]]
ListResponse = StandardResponse[List[Dict[str, Any]]]
MessageResponse = StandardResponse[str]