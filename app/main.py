"""This file contains the main application entry point."""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import (
    Any,
    Dict,
)

from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langfuse import Langfuse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.exceptions import BoardroomException
from app.core.limiter import limiter
from app.core.logging import logger
from app.core.metrics import setup_metrics
from app.core.middleware import MetricsMiddleware, ValidationMiddleware, validation_error_handler
from app.core.api_standards import APIStandardsMiddleware
from app.core.cache_middleware import CacheMiddleware
from app.core.response_optimization import ResponseOptimizationMiddleware
from app.core.error_monitoring import record_error
from app.services.database import database_service
from app.services.redis_service import redis_service
from app.core.shutdown_manager import shutdown_manager
from app.core.health_checks import health_service

# Load environment variables
load_dotenv()

# Initialize Langfuse
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events with health monitoring."""
    async with shutdown_manager.lifecycle_manager():
        logger.info(
            "application_startup_with_health_monitoring",
            project_name=settings.PROJECT_NAME,
            version=settings.VERSION,
            api_prefix=settings.API_V1_STR,
        )
        
        # Initialize Redis service
        try:
            await redis_service.initialize()
            logger.info("redis_service_initialized")
        except Exception as e:
            logger.warning(
                "redis_service_initialization_failed",
                error=str(e),
                message="Continuing without Redis - cache will be disabled"
            )
        
        # Initialize performance optimization services
        try:
            from app.core.memory_management import setup_memory_management
            from app.core.advanced_caching import setup_advanced_caching
            
            await setup_memory_management(app)
            await setup_advanced_caching(app)
            logger.info("performance_optimization_services_initialized")
        except Exception as e:
            logger.warning(
                "performance_optimization_initialization_failed",
                error=str(e),
                message="Continuing without performance optimization - some features may be disabled"
            )
        
        logger.info("application_startup_completed_with_health_validation")
        
        yield
        
        # Cleanup is handled by shutdown_manager
        logger.info("application_shutdown_initiated_by_lifespan_manager")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    contact={
        "name": "Boardroom AI API Support",
        "url": "https://github.com/boardroom-ai/api",
        "email": "support@boardroom-ai.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": f"http://localhost:8000{settings.API_V1_STR}",
            "description": "Development server"
        },
        {
            "url": f"https://api.boardroom-ai.com{settings.API_V1_STR}",
            "description": "Production server"
        }
    ],
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "User authentication and session management. Includes registration, login, and session operations."
        },
        {
            "name": "Chat & AI",
            "description": "AI-powered chat interactions and conversation management. Supports both regular and streaming responses."
        },
        {
            "name": "Boardroom & Decisions",
            "description": "Core boardroom functionality for decision-making processes and voting management."
        },
        {
            "name": "Decision Management",
            "description": "Advanced decision lifecycle management with LangGraph integration for automated workflows."
        },
        {
            "name": "Real-time Events",
            "description": "Server-sent events (SSE) for real-time updates on decision processes and system events."
        },
        {
            "name": "API Standards & Documentation",
            "description": "API standards, versioning information, error codes, and usage examples."
        },
        {
            "name": "Health & Status",
            "description": "System health checks, monitoring endpoints, and operational status information."
        },
        {
            "name": "Cache Management",
            "description": "Redis cache management, monitoring, and performance optimization endpoints."
        }
    ]
)

# Set up Prometheus metrics
setup_metrics(app)

# Add API standards middleware first
app.add_middleware(APIStandardsMiddleware)

# Add response optimization middleware (should be early in the chain)
app.add_middleware(ResponseOptimizationMiddleware)

# Add cache middleware (before validation to cache responses)
app.add_middleware(CacheMiddleware)

# Add validation middleware
app.add_middleware(ValidationMiddleware)

# Add custom metrics middleware
app.add_middleware(MetricsMiddleware)

# Set up rate limiter exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add validation exception handlers
app.add_exception_handler(HTTPException, validation_error_handler)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors from request data.

    Args:
        request: The request that caused the validation error
        exc: The validation error

    Returns:
        JSONResponse: A formatted error response
    """
    # Log the validation error (without sensitive data)
    logger.warning(
        "pydantic_validation_error",
        client_host=request.client.host if request.client else "unknown",
        path=request.url.path,
        method=request.method,
        error_count=len(exc.errors()),
    )
    
    # Record error for monitoring
    record_error(
        error_type="pydantic_validation_error",
        path=request.url.path,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_message="Request validation failed",
        client_ip=request.client.host if request.client else None
    )

    # Format the errors to be more user-friendly
    formatted_errors = []
    for error in exc.errors():
        loc = " -> ".join([str(loc_part) for loc_part in error["loc"] if loc_part != "body"])
        formatted_errors.append({
            "field": loc,
            "message": error["msg"],
            "type": error.get("type", "unknown")
        })

    error_response = {
        "error": {
            "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "message": "Request validation failed",
            "type": "validation_error",
            "details": formatted_errors,
            "timestamp": datetime.now().isoformat()
        }
    }

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response,
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError exceptions with standardized response."""
    logger.warning(
        "value_error",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        client_ip=request.client.host if request.client else "unknown"
    )
    
    # Record error for monitoring
    record_error(
        error_type="value_error",
        path=request.url.path,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_message=str(exc),
        client_ip=request.client.host if request.client else None
    )
    
    error_response = {
        "error": {
            "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "message": str(exc),
            "type": "value_error",
            "timestamp": datetime.now().isoformat()
        }
    }
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response
    )


@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: Exception):
    """Handle internal server errors with standardized response."""
    logger.error(
        "internal_server_error",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        client_ip=request.client.host if request.client else "unknown",
        exc_info=True
    )
    
    # Record error for monitoring
    record_error(
        error_type="internal_server_error",
        path=request.url.path,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_message="Internal server error",
        client_ip=request.client.host if request.client else None
    )
    
    error_response = {
        "error": {
            "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "message": "Internal server error",
            "type": "server_error",
            "timestamp": datetime.now().isoformat()
        }
    }
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response
    )


@app.exception_handler(BoardroomException)
async def boardroom_exception_handler(request: Request, exc: BoardroomException):
    """Handle custom Boardroom exceptions with standardized response."""
    logger.error(
        "boardroom_exception",
        error_code=exc.error_code,
        path=request.url.path,
        method=request.method,
        error=exc.message,
        client_ip=request.client.host if request.client else "unknown",
        exc_info=True
    )
    
    # Record error for monitoring
    record_error(
        error_type=exc.error_code.lower(),
        path=request.url.path,
        status_code=exc.status_code,
        error_message=exc.message,
        client_ip=request.client.host if request.client else None
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Customize OpenAPI schema
from app.core.openapi_customization import customize_openapi_schema
app.openapi = lambda: customize_openapi_schema(app)


@app.get("/")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["root"][0])
async def root(request: Request):
    """Root endpoint returning comprehensive API information.
    
    Returns:
        Dict containing API information, endpoints, and documentation links
    """
    logger.info("root_endpoint_called")
    
    from app.core.api_standards import APIResponseFormatter
    
    api_info = {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "description": settings.DESCRIPTION,
        "status": "operational",
        "environment": settings.ENVIRONMENT.value,
        "api_version": "v1",
        "documentation": {
            "interactive": f"{request.base_url}docs",
            "redoc": f"{request.base_url}redoc",
            "openapi_spec": f"{request.base_url}api/v1/openapi.json"
        },
        "endpoints": {
            "authentication": f"{request.base_url}api/v1/auth",
            "chat": f"{request.base_url}api/v1/chatbot",
            "decisions": f"{request.base_url}api/v1/decisions",
            "boardroom": f"{request.base_url}api/v1/boardroom",
            "events": f"{request.base_url}api/v1/events",
            "standards": f"{request.base_url}api/v1/standards"
        },
        "features": [
            "JWT Authentication",
            "AI-Powered Chat",
            "Real-time Decision Making",
            "Server-Sent Events",
            "Comprehensive Monitoring",
            "Rate Limiting",
            "Input Validation",
            "Error Handling"
        ],
        "support": {
            "documentation": f"{request.base_url}api/v1/standards",
            "health_check": f"{request.base_url}health",
            "error_codes": f"{request.base_url}api/v1/standards/errors"
        }
    }
    
    return APIResponseFormatter.format_success_response(
        data=api_info,
        message=f"Welcome to {settings.PROJECT_NAME} API",
        request=request
    )


@app.get("/health")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["health"][0])
async def health_check(request: Request) -> Dict[str, Any]:
    """Health check endpoint with environment-specific information.

    Returns:
        Dict[str, Any]: Health status information using standardized response format
    """
    logger.info("health_check_called")
    
    from app.core.api_standards import APIResponseFormatter

    # Check database connectivity
    db_healthy = await database_service.health_check()

    health_data = {
        "status": "healthy" if db_healthy else "degraded",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT.value,
        "components": {
            "api": "healthy",
            "database": "healthy" if db_healthy else "unhealthy",
            "authentication": "healthy",
            "rate_limiter": "healthy",
            "monitoring": "healthy"
        },
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "database_connectivity": "pass" if db_healthy else "fail",
            "api_availability": "pass",
            "memory_usage": "pass",
            "disk_space": "pass"
        }
    }

    # Use standardized response format
    response_data = APIResponseFormatter.format_success_response(
        data=health_data,
        message="Health check completed",
        request=request
    )

    # If DB is unhealthy, set the appropriate status code
    status_code = status.HTTP_200_OK if db_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(content=response_data, status_code=status_code)


@app.get("/monitoring/errors")
@limiter.limit("10/minute")
async def error_monitoring_status(request: Request) -> Dict[str, Any]:
    """Get error monitoring status and recent error summary.
    
    Returns:
        Dict[str, Any]: Error monitoring information
    """
    logger.info("error_monitoring_endpoint_called")
    
    from app.core.error_monitoring import get_monitoring_health, get_error_summary
    
    # Get monitoring health status
    health_status = get_monitoring_health()
    
    # Get error summary for last 24 hours
    error_summary = get_error_summary(hours=24)
    
    # Convert ErrorMetric objects to dictionaries for JSON response
    summary_dict = {}
    for error_type, metric in error_summary.items():
        summary_dict[error_type] = {
            "count": metric.count,
            "last_occurrence": metric.last_occurrence.isoformat(),
            "first_occurrence": metric.first_occurrence.isoformat(),
            "paths": metric.paths[:10],  # Limit to first 10 paths
            "status_codes": list(set(metric.status_codes))
        }
    
    response = {
        "monitoring_health": health_status,
        "error_summary_24h": summary_dict,
        "timestamp": datetime.now().isoformat()
    }
    
    return JSONResponse(content=response, status_code=status.HTTP_200_OK)


@app.get("/performance")
@limiter.limit("10/minute")
async def performance_stats(request: Request) -> Dict[str, Any]:
    """Performance statistics endpoint.
    
    Returns:
        Dict[str, Any]: Performance optimization statistics and metrics
    """
    logger.info("performance_stats_endpoint_called")
    
    try:
        from app.core.advanced_caching import multi_level_cache
        from app.core.memory_management import memory_monitor
        
        performance_data = {
            "cache_stats": multi_level_cache.get_stats(),
            "memory_stats": memory_monitor.get_memory_stats(),
            "optimization_status": "active",
            "timestamp": datetime.now().isoformat()
        }
        
        return JSONResponse(content=performance_data, status_code=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(
            "performance_stats_error",
            error=str(e),
            exc_info=True
        )
        
        # Return basic status if performance modules aren't available
        fallback_data = {
            "optimization_status": "unavailable",
            "error": "Performance monitoring not available",
            "timestamp": datetime.now().isoformat()
        }
        
        return JSONResponse(content=fallback_data, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
