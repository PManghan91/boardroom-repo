"""Analytics and monitoring integrations for Google Analytics, Mixpanel, Sentry, DataDog, and Hotjar."""

from datetime import datetime
from typing import Dict, List, Optional, Any
import httpx
from pydantic import BaseModel

from app.core.logging import logger
from .base import IntegrationConfig


class AnalyticsEvent(BaseModel):
    """Analytics event model."""
    event_name: str
    user_id: Optional[str] = None
    properties: Dict[str, Any] = {}
    timestamp: datetime = datetime.utcnow()


class AnalyticsService:
    """Base analytics service."""
    
    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def track_event(self, event: AnalyticsEvent) -> bool:
        """Track an analytics event."""
        raise NotImplementedError
    
    async def identify_user(self, user_id: str, properties: Dict[str, Any]) -> bool:
        """Identify a user with properties."""
        raise NotImplementedError


class MixpanelService(AnalyticsService):
    """Mixpanel analytics service."""
    
    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.base_url = "https://api.mixpanel.com"
    
    async def track_event(self, event: AnalyticsEvent) -> bool:
        """Track event in Mixpanel."""
        try:
            data = {
                "event": event.event_name,
                "properties": {
                    **event.properties,
                    "token": self.config.credentials.api_key,
                    "time": int(event.timestamp.timestamp()),
                    "distinct_id": event.user_id or "anonymous"
                }
            }
            
            response = await self.client.post(f"{self.base_url}/track", json=[data])
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to track Mixpanel event: {e}")
            return False


class SentryService:
    """Sentry error tracking service."""
    
    def __init__(self, dsn: str):
        self.dsn = dsn
        # Initialize Sentry client
        import sentry_sdk
        sentry_sdk.init(dsn=dsn)
    
    def capture_exception(self, exception: Exception, extra_data: Dict[str, Any] = None):
        """Capture an exception in Sentry."""
        try:
            import sentry_sdk
            if extra_data:
                sentry_sdk.set_extra("boardroom_data", extra_data)
            sentry_sdk.capture_exception(exception)
        except Exception as e:
            logger.error(f"Failed to capture exception in Sentry: {e}")


# Global analytics manager
analytics_manager = type('AnalyticsManager', (), {
    'services': {},
    'register_service': lambda self, provider, service: setattr(self, provider, service)
})()