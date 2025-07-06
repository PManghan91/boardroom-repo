"""Third-party integrations service module.

This module provides comprehensive third-party integration services for the boardroom application,
including calendar providers, communication platforms, video conferencing, document management,
analytics, and productivity tools.
"""

from .base import IntegrationService, IntegrationError, IntegrationStatus
from .calendar import CalendarIntegrationService
from .communication import CommunicationIntegrationService
from .video import VideoConferencingService
from .documents import DocumentManagementService
from .analytics import AnalyticsService
from .productivity import ProductivityService
from .oauth import OAuthManager
from .webhook import WebhookManager
from .config import IntegrationConfig

__all__ = [
    "IntegrationService",
    "IntegrationError", 
    "IntegrationStatus",
    "CalendarIntegrationService",
    "CommunicationIntegrationService",
    "VideoConferencingService",
    "DocumentManagementService",
    "AnalyticsService",
    "ProductivityService",
    "OAuthManager",
    "WebhookManager",
    "IntegrationConfig",
]