"""API v1 router configuration.

This module sets up the main API router and includes all sub-routers for different
endpoints like authentication and chatbot functionality.
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.chatbot import router as chatbot_router
from app.api.v1.standards import router as standards_router
# Temporarily disabled - missing models
# from app.api.v1.boardroom import router as boardroom_router
# from app.api.v1.endpoints.decisions import router as decisions_router  
# from app.api.v1.endpoints.events import router as events_router
from app.api.v1.ai_operations import router as ai_operations_router
from app.api.v1.ai_ml_operations import router as ai_ml_operations_router
from app.api.v1.cache import router as cache_router
from app.api.v1.health import router as health_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.monitoring import router as monitoring_router
from app.core.logging import logger

api_router = APIRouter()

# Include routers with proper tags and descriptions
api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"],
    responses={
        401: {"description": "Authentication failed"},
        422: {"description": "Validation error"}
    }
)

api_router.include_router(
    chatbot_router,
    prefix="/chatbot",
    tags=["Chat & AI"],
    responses={
        401: {"description": "Authentication required"},
        429: {"description": "Rate limit exceeded"}
    }
)

# Temporarily disabled - missing models
# api_router.include_router(
#     boardroom_router,
#     prefix="/boardroom", 
#     tags=["Boardroom & Decisions"],
#     responses={
#         404: {"description": "Resource not found"},
#         422: {"description": "Validation error"}
#     }
# )

# api_router.include_router(
#     decisions_router,
#     prefix="/decisions",
#     tags=["Decision Management"],
#     responses={
#         404: {"description": "Decision not found"},
#         422: {"description": "Validation error"}
#     }
# )

# api_router.include_router(
#     events_router,
#     prefix="/events",
#     tags=["Real-time Events"],
#     responses={
#         400: {"description": "Invalid event stream request"}
#     }
# )

api_router.include_router(
    standards_router,
    prefix="/standards",
    tags=["API Standards & Documentation"],
    responses={
        200: {"description": "Standards information retrieved"}
    }
)

api_router.include_router(
    ai_operations_router,
    prefix="/ai",
    tags=["AI Operations & Monitoring"],
    responses={
        401: {"description": "Authentication required"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "AI operation failed"}
    }
)

api_router.include_router(
    ai_ml_operations_router,
    prefix="/ai-ml",
    tags=["Advanced AI/ML Operations"],
    responses={
        401: {"description": "Authentication required"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "ML operation failed"},
        413: {"description": "Request entity too large"}
    }
)

api_router.include_router(
    cache_router,
    prefix="/cache",
    tags=["Cache Management"],
    responses={
        200: {"description": "Cache operation successful"},
        503: {"description": "Cache service unavailable"}
    }
)

api_router.include_router(
    health_router,
    prefix="/health",
    tags=["Health & Service Integration"],
    responses={
        200: {"description": "Service healthy"},
        503: {"description": "Service unavailable or degraded"}
    }
)

api_router.include_router(
    integrations_router,
    prefix="/integrations",
    tags=["Third-Party Integrations"],
    responses={
        401: {"description": "Authentication required"},
        400: {"description": "Integration not configured or connected"},
        500: {"description": "Integration service error"}
    }
)

api_router.include_router(
    monitoring_router,
    prefix="/monitoring",
    tags=["Production Monitoring & Alerting"],
    responses={
        200: {"description": "Monitoring data processed successfully"},
        422: {"description": "Invalid monitoring data"},
        500: {"description": "Monitoring service error"}
    }
)
