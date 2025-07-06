"""Integration management API endpoints."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.services.database import get_db
from app.services.integrations import (
    integration_manager,
    calendar_manager,
    communication_manager,
    video_manager,
    webhook_manager,
    config_manager
)
from app.services.integrations.config import IntegrationConfig
from app.services.integrations.base import IntegrationConnection, IntegrationStatus, OAuthToken
from app.services.integrations.calendar import CalendarEvent
from app.services.integrations.communication import Notification
from app.services.integrations.video import VideoMeeting


router = APIRouter()


# Request/Response Models
class ConnectIntegrationRequest(BaseModel):
    """Request to connect an integration."""
    provider: str
    redirect_url: Optional[str] = None


class IntegrationStatusResponse(BaseModel):
    """Integration status response."""
    provider: str
    status: IntegrationStatus
    connected_at: Optional[datetime] = None
    last_sync: Optional[datetime] = None
    error_message: Optional[str] = None


class CreateMeetingRequest(BaseModel):
    """Request to create a meeting."""
    provider: str
    title: str
    start_time: datetime
    duration_minutes: int = 60
    attendees: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    location: Optional[str] = None
    include_video: bool = True


class SendNotificationRequest(BaseModel):
    """Request to send a notification."""
    providers: List[str]
    title: str
    message: str
    channel: str
    urgency: str = "normal"
    recipients: List[str] = Field(default_factory=list)


class WebhookEventResponse(BaseModel):
    """Webhook event response."""
    id: str
    provider: str
    event_type: str
    timestamp: datetime
    processed: bool


# Helper Functions
async def get_current_user_id() -> int:
    """Get current user ID (placeholder - integrate with auth system)."""
    # TODO: Integrate with actual authentication system
    return 1


async def require_integration(provider: str, user_id: int) -> IntegrationConnection:
    """Require an active integration connection."""
    connection = await integration_manager.get_connection(user_id, provider)
    if not connection or connection.status != IntegrationStatus.CONNECTED:
        raise HTTPException(
            status_code=400,
            detail=f"No active {provider} integration found. Please connect first."
        )
    return connection


# OAuth Flow Endpoints
@router.get("/auth/{provider}")
async def start_oauth_flow(
    provider: str,
    redirect_url: Optional[str] = None,
    user_id: int = Depends(get_current_user_id)
):
    """Start OAuth flow for an integration provider."""
    if not config_manager.is_enabled(provider):
        raise HTTPException(status_code=400, detail=f"Provider {provider} is not enabled")
    
    service = integration_manager.get_service(provider)
    if not service:
        raise HTTPException(status_code=400, detail=f"Provider {provider} not supported")
    
    try:
        state = service.oauth_manager.generate_state(user_id)
        auth_url = await service.authorize_url(state)
        
        # Store redirect URL in state if provided
        if redirect_url:
            # TODO: Store redirect URL securely
            pass
        
        return {"auth_url": auth_url, "state": state}
    except Exception as e:
        logger.error(f"Failed to start OAuth flow for {provider}: {e}")
        raise HTTPException(status_code=500, detail="Failed to start authorization flow")


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    error: Optional[str] = None,
    user_id: int = Depends(get_current_user_id)
):
    """Handle OAuth callback from integration provider."""
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    
    service = integration_manager.get_service(provider)
    if not service:
        raise HTTPException(status_code=400, detail=f"Provider {provider} not supported")
    
    try:
        # Validate state
        if not service.oauth_manager.validate_state(state, user_id):
            raise HTTPException(status_code=400, detail="Invalid or expired state parameter")
        
        # Exchange code for token
        token = await service.exchange_code(code, state)
        
        # Get user info from provider
        user_info = await service.get_user_info(token)
        
        # Create connection
        connection = await integration_manager.create_connection(
            user_id=user_id,
            provider=provider,
            token=token,
            metadata=user_info
        )
        
        logger.info(f"Successfully connected {provider} integration for user {user_id}")
        
        # Return success page or redirect
        return RedirectResponse(
            url=f"/integrations?connected={provider}&status={connection.status.value}",
            status_code=302
        )
        
    except Exception as e:
        logger.error(f"OAuth callback failed for {provider}: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete authorization")


# Integration Management Endpoints
@router.get("/", response_model=List[IntegrationStatusResponse])
async def list_integrations(user_id: int = Depends(get_current_user_id)):
    """List all integration statuses for the current user."""
    statuses = []
    
    for provider in config_manager.get_enabled_providers():
        connection = await integration_manager.get_connection(user_id, provider)
        
        if connection:
            status = IntegrationStatusResponse(
                provider=provider,
                status=connection.status,
                connected_at=connection.created_at,
                last_sync=connection.last_sync,
                error_message=connection.error_message
            )
        else:
            status = IntegrationStatusResponse(
                provider=provider,
                status=IntegrationStatus.DISCONNECTED
            )
        
        statuses.append(status)
    
    return statuses


@router.get("/{provider}/status", response_model=IntegrationStatusResponse)
async def get_integration_status(
    provider: str,
    user_id: int = Depends(get_current_user_id)
):
    """Get status of a specific integration."""
    connection = await integration_manager.get_connection(user_id, provider)
    
    if connection:
        return IntegrationStatusResponse(
            provider=provider,
            status=connection.status,
            connected_at=connection.created_at,
            last_sync=connection.last_sync,
            error_message=connection.error_message
        )
    else:
        return IntegrationStatusResponse(
            provider=provider,
            status=IntegrationStatus.DISCONNECTED
        )


@router.post("/{provider}/disconnect")
async def disconnect_integration(
    provider: str,
    user_id: int = Depends(get_current_user_id)
):
    """Disconnect an integration."""
    success = await integration_manager.revoke_connection(user_id, provider)
    
    if success:
        return {"message": f"Successfully disconnected {provider} integration"}
    else:
        raise HTTPException(status_code=404, detail="Integration not found")


@router.post("/{provider}/refresh")
async def refresh_integration(
    provider: str,
    user_id: int = Depends(get_current_user_id)
):
    """Refresh an integration connection."""
    connection = await integration_manager.refresh_connection(user_id, provider)
    
    if not connection:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    return IntegrationStatusResponse(
        provider=provider,
        status=connection.status,
        connected_at=connection.created_at,
        last_sync=connection.last_sync,
        error_message=connection.error_message
    )


@router.post("/sync")
async def sync_all_integrations(
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id)
):
    """Sync data from all connected integrations."""
    background_tasks.add_task(integration_manager.sync_all_connections, user_id)
    return {"message": "Sync initiated for all integrations"}


# Calendar Integration Endpoints
@router.post("/calendar/meeting", response_model=Dict[str, Any])
async def create_calendar_meeting(
    request: CreateMeetingRequest,
    user_id: int = Depends(get_current_user_id)
):
    """Create a calendar meeting."""
    connection = await require_integration(request.provider, user_id)
    
    service = calendar_manager.get_service(request.provider)
    if not service:
        raise HTTPException(status_code=400, detail=f"Calendar provider {request.provider} not supported")
    
    try:
        event = CalendarEvent(
            id=f"meeting-{datetime.utcnow().isoformat()}",
            title=request.title,
            description=request.description,
            start_time=request.start_time,
            end_time=request.start_time + timedelta(minutes=request.duration_minutes),
            location=request.location,
            attendees=request.attendees,
            meeting_url="generate" if request.include_video else None
        )
        
        event_id = await service.create_event(connection.token, event)
        
        return {
            "event_id": event_id,
            "provider": request.provider,
            "title": request.title,
            "start_time": request.start_time.isoformat(),
            "join_url": event.meeting_url
        }
    except Exception as e:
        logger.error(f"Failed to create calendar meeting: {e}")
        raise HTTPException(status_code=500, detail="Failed to create meeting")


@router.get("/calendar/events")
async def get_calendar_events(
    provider: str,
    start_date: datetime,
    end_date: datetime,
    user_id: int = Depends(get_current_user_id)
):
    """Get calendar events from a provider."""
    connection = await require_integration(provider, user_id)
    
    service = calendar_manager.get_service(provider)
    if not service:
        raise HTTPException(status_code=400, detail=f"Calendar provider {provider} not supported")
    
    try:
        events = await service.get_events(connection.token, start_date, end_date)
        return [
            {
                "id": event.id,
                "title": event.title,
                "start_time": event.start_time.isoformat(),
                "end_time": event.end_time.isoformat(),
                "location": event.location,
                "attendees": event.attendees,
                "meeting_url": event.meeting_url
            }
            for event in events
        ]
    except Exception as e:
        logger.error(f"Failed to get calendar events: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve events")


@router.get("/calendar/availability")
async def check_calendar_availability(
    provider: str,
    start_time: datetime,
    end_time: datetime,
    user_id: int = Depends(get_current_user_id)
):
    """Check calendar availability."""
    connection = await require_integration(provider, user_id)
    
    service = calendar_manager.get_service(provider)
    if not service:
        raise HTTPException(status_code=400, detail=f"Calendar provider {provider} not supported")
    
    try:
        availability = await service.check_availability(connection.token, start_time, end_time)
        return [
            {
                "start_time": slot.start_time.isoformat(),
                "end_time": slot.end_time.isoformat(),
                "status": slot.status,
                "title": slot.title
            }
            for slot in availability
        ]
    except Exception as e:
        logger.error(f"Failed to check availability: {e}")
        raise HTTPException(status_code=500, detail="Failed to check availability")


# Communication Integration Endpoints
@router.post("/communication/notify")
async def send_notification(
    request: SendNotificationRequest,
    user_id: int = Depends(get_current_user_id)
):
    """Send notification to communication platforms."""
    tokens = {}
    
    # Get tokens for requested providers
    for provider in request.providers:
        connection = await integration_manager.get_connection(user_id, provider)
        if connection and connection.status == IntegrationStatus.CONNECTED:
            tokens[provider] = connection.token
    
    if not tokens:
        raise HTTPException(status_code=400, detail="No connected communication platforms found")
    
    notification = Notification(
        title=request.title,
        message=request.message,
        channel=request.channel,
        urgency=request.urgency,
        recipients=request.recipients
    )
    
    try:
        results = await communication_manager.broadcast_notification(tokens, notification)
        return {
            "message": "Notification sent",
            "results": results,
            "successful_providers": [p for p, success in results.items() if success]
        }
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to send notification")


@router.get("/communication/{provider}/channels")
async def get_communication_channels(
    provider: str,
    user_id: int = Depends(get_current_user_id)
):
    """Get available channels for a communication provider."""
    connection = await require_integration(provider, user_id)
    
    service = communication_manager.get_service(provider)
    if not service:
        raise HTTPException(status_code=400, detail=f"Communication provider {provider} not supported")
    
    try:
        channels = await service.get_channels(connection.token)
        return [
            {
                "id": channel.id,
                "name": channel.name,
                "description": channel.description,
                "is_private": channel.is_private,
                "member_count": channel.member_count
            }
            for channel in channels
        ]
    except Exception as e:
        logger.error(f"Failed to get channels: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve channels")


# Video Conferencing Endpoints
@router.post("/video/meeting", response_model=Dict[str, Any])
async def create_video_meeting(
    request: CreateMeetingRequest,
    user_id: int = Depends(get_current_user_id)
):
    """Create a video meeting."""
    connection = await require_integration(request.provider, user_id)
    
    service = video_manager.get_service(request.provider)
    if not service:
        raise HTTPException(status_code=400, detail=f"Video provider {request.provider} not supported")
    
    try:
        meeting = VideoMeeting(
            id=f"meeting-{datetime.utcnow().isoformat()}",
            title=request.title,
            description=request.description,
            start_time=request.start_time,
            duration_minutes=request.duration_minutes,
            host_email="",
            join_url="",
            participants=request.attendees
        )
        
        meeting_id = await service.create_meeting(connection.token, meeting)
        meeting_details = await service.get_meeting(connection.token, meeting_id)
        
        return {
            "meeting_id": meeting_id,
            "provider": request.provider,
            "title": meeting_details.title,
            "start_time": meeting_details.start_time.isoformat(),
            "join_url": meeting_details.join_url,
            "meeting_password": meeting_details.meeting_password
        }
    except Exception as e:
        logger.error(f"Failed to create video meeting: {e}")
        raise HTTPException(status_code=500, detail="Failed to create video meeting")


@router.post("/video/webrtc/room")
async def create_webrtc_room(
    title: str,
    user_id: int = Depends(get_current_user_id)
):
    """Create a WebRTC room for built-in video calls."""
    try:
        room_id = video_manager.create_webrtc_room(title, str(user_id))
        room = video_manager.webrtc_service.get_room(room_id)
        
        return {
            "room_id": room_id,
            "title": title,
            "host_id": str(user_id),
            "join_url": f"/video/room/{room_id}",
            "created_at": room["created_at"].isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to create WebRTC room: {e}")
        raise HTTPException(status_code=500, detail="Failed to create video room")


# Webhook Endpoints
@router.post("/webhook/{provider}")
async def handle_webhook(
    provider: str,
    request: Request,
    background_tasks: BackgroundTasks
):
    """Handle webhook from integration provider."""
    try:
        event = await webhook_manager.process_webhook(provider, request)
        
        # Process webhook in background
        background_tasks.add_task(process_webhook_event, event)
        
        return {"status": "received", "event_id": event.id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.get("/webhook/events", response_model=List[WebhookEventResponse])
async def get_webhook_events(
    provider: Optional[str] = None,
    limit: int = 50
):
    """Get recent webhook events."""
    try:
        if provider:
            handler = webhook_manager.get_handler(provider)
            if not handler:
                raise HTTPException(status_code=404, detail=f"No webhook handler for {provider}")
            events = handler.get_recent_events(limit)
        else:
            events = webhook_manager.get_all_events(limit)
        
        return [
            WebhookEventResponse(
                id=event.id,
                provider=event.provider,
                event_type=event.event_type,
                timestamp=event.timestamp,
                processed=event.processed
            )
            for event in events
        ]
    except Exception as e:
        logger.error(f"Failed to get webhook events: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve webhook events")


# Admin/Health Endpoints
@router.get("/health")
async def integration_health_check():
    """Perform health check for all integration services."""
    try:
        health_data = {
            "integration_manager": await integration_manager.health_check(),
            "calendar_manager": await calendar_manager.health_check(),
            "communication_manager": await communication_manager.health_check(),
            "video_manager": await video_manager.health_check(),
            "webhook_manager": webhook_manager.health_check(),
            "config_manager": config_manager.health_check(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return health_data
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@router.get("/config")
async def get_integration_config():
    """Get integration configuration (admin only)."""
    # TODO: Add admin authentication
    try:
        configs = config_manager.get_all_configs()
        return {
            provider: {
                "enabled": config.enabled,
                "scopes": config.scopes,
                "has_credentials": bool(config.credentials.client_id or config.credentials.api_key),
                "webhook_configured": bool(config.webhook_url)
            }
            for provider, config in configs.items()
        }
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve configuration")


# Background Tasks
async def process_webhook_event(event):
    """Process webhook event in background."""
    try:
        # Handle different event types
        if event.provider == "google" and event.event_type == "sync":
            # Handle Google Calendar sync
            pass
        elif event.provider == "slack" and event.event_type == "message":
            # Handle Slack message
            pass
        elif event.provider == "zoom" and event.event_type == "meeting.started":
            # Handle Zoom meeting started
            pass
        
        logger.info(f"Processed webhook event: {event.id}")
    except Exception as e:
        logger.error(f"Failed to process webhook event {event.id}: {e}")