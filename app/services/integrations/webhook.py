"""Webhook manager for handling real-time updates from third-party services."""

import json
import hmac
import hashlib
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from fastapi import Request, HTTPException
from pydantic import BaseModel

from app.core.logging import logger
from .base import IntegrationError


class WebhookEvent(BaseModel):
    """Webhook event model."""
    id: str
    provider: str
    event_type: str
    data: Dict[str, Any]
    headers: Dict[str, str]
    timestamp: datetime
    processed: bool = False
    error: Optional[str] = None


class WebhookHandler:
    """Base webhook handler."""
    
    def __init__(self, provider: str, secret: str):
        """Initialize webhook handler."""
        self.provider = provider
        self.secret = secret
        self.events: List[WebhookEvent] = []
        self.handlers: Dict[str, Callable] = {}
    
    def register_handler(self, event_type: str, handler: Callable):
        """Register event handler."""
        self.handlers[event_type] = handler
        logger.info(f"Registered webhook handler for {self.provider}.{event_type}")
    
    async def validate_signature(self, payload: bytes, signature: str) -> bool:
        """Validate webhook signature."""
        if not self.secret:
            logger.warning(f"No webhook secret configured for {self.provider}")
            return True
        
        # Different providers use different signature formats
        if self.provider == "github":
            expected = f"sha256={hmac.new(self.secret.encode(), payload, hashlib.sha256).hexdigest()}"
        elif self.provider == "slack":
            expected = f"v0={hmac.new(self.secret.encode(), payload, hashlib.sha256).hexdigest()}"
        else:
            # Generic HMAC-SHA256
            expected = hmac.new(self.secret.encode(), payload, hashlib.sha256).hexdigest()
        
        return hmac.compare_digest(expected, signature)
    
    async def process_webhook(self, request: Request) -> WebhookEvent:
        """Process incoming webhook."""
        # Read request body
        payload = await request.body()
        headers = dict(request.headers)
        
        # Validate signature if required
        signature = headers.get("x-signature-256") or headers.get("x-hub-signature-256")
        if signature and not await self.validate_signature(payload, signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Parse payload
        try:
            data = json.loads(payload.decode())
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Determine event type
        event_type = self._extract_event_type(data, headers)
        
        # Create webhook event
        event = WebhookEvent(
            id=f"{self.provider}_{datetime.utcnow().isoformat()}",
            provider=self.provider,
            event_type=event_type,
            data=data,
            headers=headers,
            timestamp=datetime.utcnow()
        )
        
        # Store event
        self.events.append(event)
        
        # Process event
        await self._process_event(event)
        
        return event
    
    def _extract_event_type(self, data: Dict[str, Any], headers: Dict[str, str]) -> str:
        """Extract event type from payload or headers."""
        # Provider-specific event type extraction
        if self.provider == "google":
            return headers.get("x-goog-resource-state", "unknown")
        elif self.provider == "slack":
            return data.get("type", "unknown")
        elif self.provider == "github":
            return headers.get("x-github-event", "unknown")
        elif self.provider == "zoom":
            return data.get("event", "unknown")
        else:
            return data.get("event_type", "unknown")
    
    async def _process_event(self, event: WebhookEvent):
        """Process webhook event."""
        try:
            handler = self.handlers.get(event.event_type)
            if handler:
                await handler(event)
                event.processed = True
                logger.info(f"Processed webhook event: {event.provider}.{event.event_type}")
            else:
                logger.warning(f"No handler for webhook event: {event.provider}.{event.event_type}")
        except Exception as e:
            event.error = str(e)
            logger.error(f"Error processing webhook event {event.id}: {e}")
    
    def get_recent_events(self, limit: int = 100) -> List[WebhookEvent]:
        """Get recent webhook events."""
        return sorted(self.events, key=lambda e: e.timestamp, reverse=True)[:limit]
    
    def cleanup_old_events(self, days: int = 7):
        """Clean up old webhook events."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        before_count = len(self.events)
        self.events = [e for e in self.events if e.timestamp > cutoff]
        after_count = len(self.events)
        logger.info(f"Cleaned up {before_count - after_count} old webhook events for {self.provider}")


class WebhookManager:
    """Manager for all webhook handlers."""
    
    def __init__(self):
        """Initialize webhook manager."""
        self.handlers: Dict[str, WebhookHandler] = {}
    
    def register_handler(self, provider: str, secret: str) -> WebhookHandler:
        """Register webhook handler for a provider."""
        handler = WebhookHandler(provider, secret)
        self.handlers[provider] = handler
        logger.info(f"Registered webhook handler for {provider}")
        return handler
    
    def get_handler(self, provider: str) -> Optional[WebhookHandler]:
        """Get webhook handler for a provider."""
        return self.handlers.get(provider)
    
    async def process_webhook(self, provider: str, request: Request) -> WebhookEvent:
        """Process webhook for a provider."""
        handler = self.get_handler(provider)
        if not handler:
            raise HTTPException(status_code=404, detail=f"No webhook handler for {provider}")
        
        return await handler.process_webhook(request)
    
    def get_all_events(self, limit: int = 100) -> List[WebhookEvent]:
        """Get all recent webhook events."""
        all_events = []
        for handler in self.handlers.values():
            all_events.extend(handler.get_recent_events(limit))
        
        return sorted(all_events, key=lambda e: e.timestamp, reverse=True)[:limit]
    
    def cleanup_all_events(self, days: int = 7):
        """Clean up old events for all handlers."""
        for handler in self.handlers.values():
            handler.cleanup_old_events(days)
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check for webhook system."""
        status = {
            "total_handlers": len(self.handlers),
            "handlers": {},
            "recent_events": 0
        }
        
        for provider, handler in self.handlers.items():
            recent_events = handler.get_recent_events(10)
            status["handlers"][provider] = {
                "registered_event_types": list(handler.handlers.keys()),
                "recent_events": len(recent_events),
                "last_event": recent_events[0].timestamp.isoformat() if recent_events else None
            }
            status["recent_events"] += len(recent_events)
        
        return status


# Global webhook manager instance
webhook_manager = WebhookManager()


# Webhook handler decorators for different providers
class GoogleWebhookHandler(WebhookHandler):
    """Google-specific webhook handler."""
    
    def __init__(self, secret: str):
        super().__init__("google", secret)
    
    async def validate_signature(self, payload: bytes, signature: str) -> bool:
        """Google uses different signature validation."""
        # Google uses custom token validation
        return True  # Implement Google-specific validation


class SlackWebhookHandler(WebhookHandler):
    """Slack-specific webhook handler."""
    
    def __init__(self, secret: str):
        super().__init__("slack", secret)
    
    async def validate_signature(self, payload: bytes, signature: str) -> bool:
        """Slack signature validation."""
        if not signature.startswith("v0="):
            return False
        
        expected = f"v0={hmac.new(self.secret.encode(), payload, hashlib.sha256).hexdigest()}"
        return hmac.compare_digest(expected, signature)


class ZoomWebhookHandler(WebhookHandler):
    """Zoom-specific webhook handler."""
    
    def __init__(self, secret: str):
        super().__init__("zoom", secret)
    
    async def validate_signature(self, payload: bytes, signature: str) -> bool:
        """Zoom signature validation."""
        expected = hmac.new(self.secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


class GitHubWebhookHandler(WebhookHandler):
    """GitHub-specific webhook handler."""
    
    def __init__(self, secret: str):
        super().__init__("github", secret)
    
    async def validate_signature(self, payload: bytes, signature: str) -> bool:
        """GitHub signature validation."""
        if not signature.startswith("sha256="):
            return False
        
        expected = f"sha256={hmac.new(self.secret.encode(), payload, hashlib.sha256).hexdigest()}"
        return hmac.compare_digest(expected, signature)