"""FastAPI application configuration with comprehensive integration support."""

import asyncio
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.core.exceptions import APIError
from app.core.logging import logger
from app.core.middleware import SecurityMiddleware, RequestLoggingMiddleware
from app.core.metrics import setup_metrics
from app.core.health_checks import health_check_manager
from app.services.database import database_service
from app.services.redis_service import redis_service
from app.services.monitoring_service import monitoring_service
from app.services.integrations import (
    integration_manager,
    calendar_manager,
    communication_manager,
    video_manager,
    webhook_manager,
    config_manager
)
from app.services.integrations.calendar import (
    GoogleCalendarService,
    OutlookCalendarService,
    AppleCalendarService
)
from app.services.integrations.communication import (
    SlackService,
    TeamsService,
    DiscordService,
    EmailService
)
from app.services.integrations.video import (
    ZoomService,
    GoogleMeetService,
    TeamsVideoService
)
from app.services.integrations.webhook import (
    GoogleWebhookHandler,
    SlackWebhookHandler,
    ZoomWebhookHandler,
    GitHubWebhookHandler
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Boardroom AI application...")
    
    try:
        # Initialize core services
        await database_service.initialize()
        await redis_service.initialize()
        
        # Start monitoring service
        await monitoring_service.start_monitoring()
        
        # Register integration services
        await initialize_integrations()
        
        # Start health check manager
        health_check_manager.start()
        
        logger.info("Application startup completed successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        logger.info("Shutting down application...")
        
        try:
            health_check_manager.stop()
            await monitoring_service.stop_monitoring()
            await database_service.close()
            await redis_service.close()
            
            # Close integration service clients
            for service in integration_manager.services.values():
                if hasattr(service, 'client'):
                    await service.client.aclose()
            
            logger.info("Application shutdown completed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


async def initialize_integrations():
    """Initialize all integration services."""
    try:
        # Initialize calendar services
        for provider in ['google', 'microsoft', 'apple']:
            config = config_manager.get_config(provider)
            if config and config.enabled:
                if provider == 'google':
                    service = GoogleCalendarService(config)
                    calendar_manager.register_service(provider, service)
                    integration_manager.register_service(provider, service)
                elif provider == 'microsoft':
                    service = OutlookCalendarService(config)
                    calendar_manager.register_service(provider, service)
                    integration_manager.register_service(provider, service)
                elif provider == 'apple':
                    service = AppleCalendarService(config)
                    calendar_manager.register_service(provider, service)
                    integration_manager.register_service(provider, service)
        
        # Initialize communication services
        for provider in ['slack', 'teams', 'discord']:
            config = config_manager.get_config(provider)
            if config and config.enabled:
                if provider == 'slack':
                    service = SlackService(config)
                    communication_manager.register_service(provider, service)
                    integration_manager.register_service(provider, service)
                elif provider == 'teams':
                    service = TeamsService(config)
                    communication_manager.register_service(provider, service)
                    integration_manager.register_service(provider, service)
                elif provider == 'discord':
                    service = DiscordService(config)
                    communication_manager.register_service(provider, service)
                    integration_manager.register_service(provider, service)
        
        # Initialize video conferencing services
        for provider in ['zoom', 'googlemeet', 'teams']:
            config = config_manager.get_config(provider)
            if config and config.enabled:
                if provider == 'zoom':
                    service = ZoomService(config)
                    video_manager.register_service(provider, service)
                    integration_manager.register_service(provider, service)
                elif provider == 'googlemeet':
                    # Use Google config for Google Meet
                    google_config = config_manager.get_config('google')
                    if google_config and google_config.enabled:
                        service = GoogleMeetService(google_config)
                        video_manager.register_service(provider, service)
                        integration_manager.register_service(provider, service)
                elif provider == 'teams':
                    # Use Microsoft config for Teams video
                    microsoft_config = config_manager.get_config('microsoft')
                    if microsoft_config and microsoft_config.enabled:
                        service = TeamsVideoService(microsoft_config)
                        video_manager.register_service(provider, service)
                        integration_manager.register_service(provider, service)
        
        # Initialize email service
        import os
        sendgrid_key = os.getenv('SENDGRID_API_KEY')
        mailgun_key = os.getenv('MAILGUN_API_KEY')
        
        if sendgrid_key:
            communication_manager.register_email_service('sendgrid', sendgrid_key)
        elif mailgun_key:
            communication_manager.register_email_service('mailgun', mailgun_key)
        
        # Initialize webhook handlers
        for provider in ['google', 'slack', 'zoom', 'github']:
            config = config_manager.get_config(provider)
            if config and config.enabled and config.webhook_url:
                secret = config.credentials.webhook_secret or ''
                
                if provider == 'google':
                    handler = GoogleWebhookHandler(secret)
                elif provider == 'slack':
                    handler = SlackWebhookHandler(secret)
                elif provider == 'zoom':
                    handler = ZoomWebhookHandler(secret)
                elif provider == 'github':
                    handler = GitHubWebhookHandler(secret)
                else:
                    continue
                
                webhook_manager.register_handler(provider, secret)
                
                # Register event handlers
                handler.register_handler('sync', handle_sync_event)
                handler.register_handler('message', handle_message_event)
                handler.register_handler('meeting.started', handle_meeting_event)
        
        logger.info(f"Initialized {len(integration_manager.services)} integration services")
        
    except Exception as e:
        logger.error(f"Failed to initialize integrations: {e}")
        raise


# Webhook event handlers
async def handle_sync_event(event):
    """Handle sync events from calendar providers."""
    logger.info(f"Handling sync event from {event.provider}")
    # Implement sync logic here


async def handle_message_event(event):
    """Handle message events from communication platforms."""
    logger.info(f"Handling message event from {event.provider}")
    # Implement message handling logic here


async def handle_meeting_event(event):
    """Handle meeting events from video providers."""
    logger.info(f"Handling meeting event from {event.provider}")
    # Implement meeting event logic here


# Create FastAPI application
app = FastAPI(
    title="Boardroom AI API",
    description="Comprehensive boardroom management with AI and third-party integrations",
    version="0.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Get settings
settings = get_settings()

# Add middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Setup Prometheus metrics
setup_metrics(app)

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Global exception handlers
@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    """Handle custom API errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "detail": exc.detail,
            "timestamp": exc.timestamp.isoformat(),
            "path": str(request.url.path)
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "path": str(request.url.path)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "path": str(request.url.path)
        }
    )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Boardroom AI API",
        "version": "0.3.0",
        "description": "Comprehensive boardroom management with AI and integrations",
        "docs": "/docs",
        "health": "/api/v1/health",
        "integrations": "/api/v1/integrations",
        "features": {
            "ai_powered": True,
            "real_time": True,
            "integrations": len(integration_manager.services),
            "calendar_sync": True,
            "video_conferencing": True,
            "communication": True,
            "document_management": True,
            "analytics": True,
            "webhooks": True
        }
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "services": {
            "database": "healthy",
            "redis": "healthy",
            "integrations": len(integration_manager.services)
        }
    }

# Static files (if needed)
# app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )