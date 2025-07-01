"""Custom middleware for tracking metrics and validation."""

import time
import json
from typing import Callable, Dict, Any

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    db_connections,
)
from app.core.logging import logger
from app.utils.sanitization import sanitize_string


class ValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for input validation and security checks."""

    SUSPICIOUS_PATTERNS = [
        # SQL injection patterns
        r"(?i)(union\s+select|select\s+.*from|insert\s+into|delete\s+from|drop\s+table)",
        # XSS patterns
        r"(?i)(<script|javascript:|vbscript:|onload=|onerror=)",
        # Command injection patterns
        r"(?i)(;|\||\&\&|`|\$\()",
        # Path traversal patterns
        r"(\.\./|\.\.\\|%2e%2e)",
    ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate request and track security events.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            Response: The response from the application
        """
        start_time = time.time()
        
        try:
            # Validate request headers
            await self._validate_headers(request)
            
            # Validate request size
            await self._validate_request_size(request)
            
            # Validate suspicious patterns in path and query
            await self._validate_request_patterns(request)
            
            response = await call_next(request)
            status_code = response.status_code
            
        except HTTPException:
            # Re-raise HTTP exceptions (validation failures)
            raise
        except Exception as e:
            status_code = 500
            logger.error("middleware_error", error=str(e), path=request.url.path, exc_info=True)
            raise
        finally:
            duration = time.time() - start_time

            # Record metrics
            http_requests_total.labels(method=request.method, endpoint=request.url.path, status=status_code).inc()
            http_request_duration_seconds.labels(method=request.method, endpoint=request.url.path).observe(duration)

        return response

    async def _validate_headers(self, request: Request):
        """Validate request headers for security issues."""
        # Check Content-Length header
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB limit
            logger.warning("request_too_large", content_length=content_length, path=request.url.path)
            raise HTTPException(status_code=413, detail="Request entity too large")

        # Validate User-Agent header
        user_agent = request.headers.get("user-agent", "")
        if len(user_agent) > 1000:  # Reasonable User-Agent length limit
            logger.warning("suspicious_user_agent", user_agent_length=len(user_agent), path=request.url.path)
            raise HTTPException(status_code=400, detail="Invalid User-Agent header")

    async def _validate_request_size(self, request: Request):
        """Validate request body size."""
        if hasattr(request, "_body"):
            body_size = len(request._body) if request._body else 0
            if body_size > 5 * 1024 * 1024:  # 5MB limit for request body
                logger.warning("request_body_too_large", body_size=body_size, path=request.url.path)
                raise HTTPException(status_code=413, detail="Request body too large")

    async def _validate_request_patterns(self, request: Request):
        """Validate request for suspicious patterns."""
        import re
        
        # Check URL path
        path = str(request.url.path)
        query = str(request.url.query) if request.url.query else ""
        
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, path) or re.search(pattern, query):
                logger.warning(
                    "suspicious_request_pattern",
                    pattern=pattern,
                    path=path,
                    query=query,
                    client_ip=request.client.host if request.client else "unknown"
                )
                raise HTTPException(status_code=400, detail="Malicious request pattern detected")


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for tracking HTTP request metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Track metrics for each request.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            Response: The response from the application
        """
        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.time() - start_time

            # Record metrics
            http_requests_total.labels(method=request.method, endpoint=request.url.path, status=status_code).inc()

            http_request_duration_seconds.labels(method=request.method, endpoint=request.url.path).observe(duration)

        return response


async def validation_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Custom error handler for validation errors."""
    
    # Standardized error response format
    error_response = {
        "error": {
            "code": exc.status_code,
            "message": exc.detail,
            "type": "validation_error",
            "timestamp": time.time()
        }
    }
    
    # Log validation error without sensitive data
    logger.warning(
        "validation_error",
        status_code=exc.status_code,
        path=request.url.path,
        method=request.method,
        client_ip=request.client.host if request.client else "unknown"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )
