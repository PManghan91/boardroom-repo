"""Calendar integration services for Google Calendar, Outlook, and Apple Calendar."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
import httpx
from pydantic import BaseModel, Field

from app.core.logging import logger
from .base import IntegrationService, IntegrationConfig, OAuthToken, IntegrationError
from .oauth import OAuthManager


class CalendarEvent(BaseModel):
    """Calendar event model."""
    id: str
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    attendees: List[str] = Field(default_factory=list)
    meeting_url: Optional[str] = None
    timezone: str = "UTC"
    all_day: bool = False
    recurrence: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CalendarAvailability(BaseModel):
    """Calendar availability model."""
    start_time: datetime
    end_time: datetime
    status: str  # "free", "busy", "tentative", "out_of_office"
    title: Optional[str] = None


class CalendarIntegrationService(IntegrationService):
    """Base calendar integration service."""
    
    async def create_event(self, token: OAuthToken, event: CalendarEvent) -> str:
        """Create a calendar event."""
        raise NotImplementedError
    
    async def update_event(self, token: OAuthToken, event_id: str, event: CalendarEvent) -> bool:
        """Update a calendar event."""
        raise NotImplementedError
    
    async def delete_event(self, token: OAuthToken, event_id: str) -> bool:
        """Delete a calendar event."""
        raise NotImplementedError
    
    async def get_events(
        self,
        token: OAuthToken,
        start_date: datetime,
        end_date: datetime,
        max_results: int = 100
    ) -> List[CalendarEvent]:
        """Get calendar events in a date range."""
        raise NotImplementedError
    
    async def check_availability(
        self,
        token: OAuthToken,
        start_time: datetime,
        end_time: datetime
    ) -> List[CalendarAvailability]:
        """Check calendar availability."""
        raise NotImplementedError
    
    async def find_available_slots(
        self,
        token: OAuthToken,
        start_date: datetime,
        end_date: datetime,
        duration_minutes: int = 60,
        working_hours: tuple = (9, 17)
    ) -> List[Dict[str, datetime]]:
        """Find available meeting slots."""
        availability = await self.check_availability(token, start_date, end_date)
        
        # Generate all possible slots
        slots = []
        current = start_date.replace(hour=working_hours[0], minute=0, second=0, microsecond=0)
        
        while current < end_date:
            if current.hour >= working_hours[0] and current.hour < working_hours[1]:
                slot_end = current + timedelta(minutes=duration_minutes)
                
                # Check if slot is free
                is_free = True
                for busy_time in availability:
                    if busy_time.status == "busy" and (
                        (current >= busy_time.start_time and current < busy_time.end_time) or
                        (slot_end > busy_time.start_time and slot_end <= busy_time.end_time)
                    ):
                        is_free = False
                        break
                
                if is_free:
                    slots.append({
                        "start": current,
                        "end": slot_end
                    })
            
            current += timedelta(minutes=30)  # Check every 30 minutes
        
        return slots


class GoogleCalendarService(CalendarIntegrationService):
    """Google Calendar integration service."""
    
    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.oauth_manager = OAuthManager(config)
        self.base_url = "https://www.googleapis.com/calendar/v3"
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.revoke_url = "https://oauth2.googleapis.com/revoke"
    
    async def authorize_url(self, state: str) -> str:
        """Generate Google OAuth authorization URL."""
        return await self.oauth_manager.build_authorization_url(
            self.auth_url,
            state,
            self.config.scopes,
            {
                "access_type": "offline",
                "prompt": "consent"
            }
        )
    
    async def exchange_code(self, code: str, state: str) -> OAuthToken:
        """Exchange authorization code for access token."""
        return await self.oauth_manager.exchange_code_for_token(
            self.token_url,
            code
        )
    
    async def refresh_token(self, refresh_token: str) -> OAuthToken:
        """Refresh Google access token."""
        return await self.oauth_manager.refresh_access_token(
            self.token_url,
            refresh_token
        )
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke Google access token."""
        return await self.oauth_manager.revoke_token(
            self.revoke_url,
            token
        )
    
    async def test_connection(self, token: OAuthToken) -> bool:
        """Test Google Calendar connection."""
        try:
            await self._make_request(
                "GET",
                f"{self.base_url}/users/me/calendarList",
                token
            )
            return True
        except Exception as e:
            logger.error(f"Google Calendar connection test failed: {e}")
            return False
    
    async def create_event(self, token: OAuthToken, event: CalendarEvent) -> str:
        """Create Google Calendar event."""
        event_data = {
            "summary": event.title,
            "description": event.description,
            "start": {
                "dateTime": event.start_time.isoformat(),
                "timeZone": event.timezone
            },
            "end": {
                "dateTime": event.end_time.isoformat(),
                "timeZone": event.timezone
            },
            "location": event.location,
            "attendees": [{"email": email} for email in event.attendees],
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 15},
                    {"method": "popup", "minutes": 10}
                ]
            }
        }
        
        if event.meeting_url:
            event_data["conferenceData"] = {
                "createRequest": {
                    "requestId": f"boardroom-{event.id}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"}
                }
            }
        
        response = await self._make_request(
            "POST",
            f"{self.base_url}/calendars/primary/events",
            token,
            data=event_data,
            params={"conferenceDataVersion": 1} if event.meeting_url else None
        )
        
        return response["id"]
    
    async def update_event(self, token: OAuthToken, event_id: str, event: CalendarEvent) -> bool:
        """Update Google Calendar event."""
        event_data = {
            "summary": event.title,
            "description": event.description,
            "start": {
                "dateTime": event.start_time.isoformat(),
                "timeZone": event.timezone
            },
            "end": {
                "dateTime": event.end_time.isoformat(),
                "timeZone": event.timezone
            },
            "location": event.location,
            "attendees": [{"email": email} for email in event.attendees]
        }
        
        try:
            await self._make_request(
                "PUT",
                f"{self.base_url}/calendars/primary/events/{event_id}",
                token,
                data=event_data
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update Google Calendar event: {e}")
            return False
    
    async def delete_event(self, token: OAuthToken, event_id: str) -> bool:
        """Delete Google Calendar event."""
        try:
            await self._make_request(
                "DELETE",
                f"{self.base_url}/calendars/primary/events/{event_id}",
                token
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete Google Calendar event: {e}")
            return False
    
    async def get_events(
        self,
        token: OAuthToken,
        start_date: datetime,
        end_date: datetime,
        max_results: int = 100
    ) -> List[CalendarEvent]:
        """Get Google Calendar events."""
        params = {
            "timeMin": start_date.isoformat(),
            "timeMax": end_date.isoformat(),
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime"
        }
        
        response = await self._make_request(
            "GET",
            f"{self.base_url}/calendars/primary/events",
            token,
            params=params
        )
        
        events = []
        for item in response.get("items", []):
            start = item.get("start", {})
            end = item.get("end", {})
            
            # Handle date vs dateTime
            start_time = start.get("dateTime") or start.get("date")
            end_time = end.get("dateTime") or end.get("date")
            
            if start_time and end_time:
                event = CalendarEvent(
                    id=item["id"],
                    title=item.get("summary", ""),
                    description=item.get("description"),
                    start_time=datetime.fromisoformat(start_time.replace("Z", "+00:00")),
                    end_time=datetime.fromisoformat(end_time.replace("Z", "+00:00")),
                    location=item.get("location"),
                    attendees=[att.get("email", "") for att in item.get("attendees", [])],
                    meeting_url=item.get("conferenceData", {}).get("entryPoints", [{}])[0].get("uri"),
                    timezone=start.get("timeZone", "UTC"),
                    all_day=bool(start.get("date"))
                )
                events.append(event)
        
        return events
    
    async def check_availability(
        self,
        token: OAuthToken,
        start_time: datetime,
        end_time: datetime
    ) -> List[CalendarAvailability]:
        """Check Google Calendar availability."""
        request_data = {
            "timeMin": start_time.isoformat(),
            "timeMax": end_time.isoformat(),
            "items": [{"id": "primary"}]
        }
        
        response = await self._make_request(
            "POST",
            f"{self.base_url}/freeBusy",
            token,
            data=request_data
        )
        
        availability = []
        for busy_time in response.get("calendars", {}).get("primary", {}).get("busy", []):
            availability.append(CalendarAvailability(
                start_time=datetime.fromisoformat(busy_time["start"].replace("Z", "+00:00")),
                end_time=datetime.fromisoformat(busy_time["end"].replace("Z", "+00:00")),
                status="busy"
            ))
        
        return availability


class OutlookCalendarService(CalendarIntegrationService):
    """Microsoft Outlook Calendar integration service."""
    
    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.oauth_manager = OAuthManager(config)
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.auth_url = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        self.token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    
    async def authorize_url(self, state: str) -> str:
        """Generate Microsoft OAuth authorization URL."""
        return await self.oauth_manager.build_authorization_url(
            self.auth_url,
            state,
            self.config.scopes,
            {
                "response_mode": "query",
                "prompt": "consent"
            }
        )
    
    async def exchange_code(self, code: str, state: str) -> OAuthToken:
        """Exchange authorization code for access token."""
        return await self.oauth_manager.exchange_code_for_token(
            self.token_url,
            code
        )
    
    async def refresh_token(self, refresh_token: str) -> OAuthToken:
        """Refresh Microsoft access token."""
        return await self.oauth_manager.refresh_access_token(
            self.token_url,
            refresh_token
        )
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke Microsoft access token."""
        # Microsoft doesn't have a revoke endpoint, but we can sign out
        return True
    
    async def test_connection(self, token: OAuthToken) -> bool:
        """Test Microsoft Calendar connection."""
        try:
            await self._make_request(
                "GET",
                f"{self.base_url}/me/calendars",
                token
            )
            return True
        except Exception as e:
            logger.error(f"Microsoft Calendar connection test failed: {e}")
            return False
    
    async def create_event(self, token: OAuthToken, event: CalendarEvent) -> str:
        """Create Microsoft Calendar event."""
        event_data = {
            "subject": event.title,
            "body": {
                "contentType": "Text",
                "content": event.description or ""
            },
            "start": {
                "dateTime": event.start_time.isoformat(),
                "timeZone": event.timezone
            },
            "end": {
                "dateTime": event.end_time.isoformat(),
                "timeZone": event.timezone
            },
            "location": {
                "displayName": event.location or ""
            },
            "attendees": [
                {
                    "emailAddress": {"address": email, "name": email},
                    "type": "required"
                } for email in event.attendees
            ]
        }
        
        if event.meeting_url:
            event_data["isOnlineMeeting"] = True
            event_data["onlineMeetingProvider"] = "teamsForBusiness"
        
        response = await self._make_request(
            "POST",
            f"{self.base_url}/me/events",
            token,
            data=event_data
        )
        
        return response["id"]
    
    async def update_event(self, token: OAuthToken, event_id: str, event: CalendarEvent) -> bool:
        """Update Microsoft Calendar event."""
        event_data = {
            "subject": event.title,
            "body": {
                "contentType": "Text",
                "content": event.description or ""
            },
            "start": {
                "dateTime": event.start_time.isoformat(),
                "timeZone": event.timezone
            },
            "end": {
                "dateTime": event.end_time.isoformat(),
                "timeZone": event.timezone
            },
            "location": {
                "displayName": event.location or ""
            },
            "attendees": [
                {
                    "emailAddress": {"address": email, "name": email},
                    "type": "required"
                } for email in event.attendees
            ]
        }
        
        try:
            await self._make_request(
                "PATCH",
                f"{self.base_url}/me/events/{event_id}",
                token,
                data=event_data
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update Microsoft Calendar event: {e}")
            return False
    
    async def delete_event(self, token: OAuthToken, event_id: str) -> bool:
        """Delete Microsoft Calendar event."""
        try:
            await self._make_request(
                "DELETE",
                f"{self.base_url}/me/events/{event_id}",
                token
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete Microsoft Calendar event: {e}")
            return False
    
    async def get_events(
        self,
        token: OAuthToken,
        start_date: datetime,
        end_date: datetime,
        max_results: int = 100
    ) -> List[CalendarEvent]:
        """Get Microsoft Calendar events."""
        params = {
            "startDateTime": start_date.isoformat(),
            "endDateTime": end_date.isoformat(),
            "$top": max_results,
            "$orderby": "start/dateTime"
        }
        
        response = await self._make_request(
            "GET",
            f"{self.base_url}/me/calendarView",
            token,
            params=params
        )
        
        events = []
        for item in response.get("value", []):
            start = item.get("start", {})
            end = item.get("end", {})
            
            event = CalendarEvent(
                id=item["id"],
                title=item.get("subject", ""),
                description=item.get("body", {}).get("content", ""),
                start_time=datetime.fromisoformat(start.get("dateTime", "")),
                end_time=datetime.fromisoformat(end.get("dateTime", "")),
                location=item.get("location", {}).get("displayName", ""),
                attendees=[att.get("emailAddress", {}).get("address", "") for att in item.get("attendees", [])],
                meeting_url=item.get("onlineMeeting", {}).get("joinUrl"),
                timezone=start.get("timeZone", "UTC"),
                all_day=item.get("isAllDay", False)
            )
            events.append(event)
        
        return events
    
    async def check_availability(
        self,
        token: OAuthToken,
        start_time: datetime,
        end_time: datetime
    ) -> List[CalendarAvailability]:
        """Check Microsoft Calendar availability."""
        request_data = {
            "schedules": ["me"],
            "startTime": {
                "dateTime": start_time.isoformat(),
                "timeZone": "UTC"
            },
            "endTime": {
                "dateTime": end_time.isoformat(),
                "timeZone": "UTC"
            },
            "availabilityViewInterval": 30
        }
        
        response = await self._make_request(
            "POST",
            f"{self.base_url}/me/calendar/getSchedule",
            token,
            data=request_data
        )
        
        availability = []
        for schedule in response.get("value", []):
            for busy_time in schedule.get("busyViewItems", []):
                availability.append(CalendarAvailability(
                    start_time=datetime.fromisoformat(busy_time["start"].replace("Z", "+00:00")),
                    end_time=datetime.fromisoformat(busy_time["end"].replace("Z", "+00:00")),
                    status="busy",
                    title=busy_time.get("subject")
                ))
        
        return availability


class AppleCalendarService(CalendarIntegrationService):
    """Apple Calendar integration service (via CalDAV)."""
    
    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        # Apple Calendar uses CalDAV, not OAuth
        self.base_url = "https://caldav.icloud.com"
    
    async def authorize_url(self, state: str) -> str:
        """Apple Calendar doesn't use OAuth, returns configuration URL."""
        return f"/integrations/apple/configure?state={state}"
    
    async def exchange_code(self, code: str, state: str) -> OAuthToken:
        """Apple Calendar doesn't use OAuth, returns app-specific password."""
        # This would handle app-specific password configuration
        return OAuthToken(
            access_token=code,  # App-specific password
            token_type="Basic"
        )
    
    async def refresh_token(self, refresh_token: str) -> OAuthToken:
        """Apple Calendar doesn't need token refresh."""
        return OAuthToken(
            access_token=refresh_token,
            token_type="Basic"
        )
    
    async def revoke_token(self, token: str) -> bool:
        """Apple Calendar token revocation (remove app-specific password)."""
        return True
    
    async def test_connection(self, token: OAuthToken) -> bool:
        """Test Apple Calendar connection."""
        try:
            # Test CalDAV connection
            response = await self.client.request(
                "PROPFIND",
                f"{self.base_url}/calendars/",
                headers={
                    "Authorization": f"Basic {token.access_token}",
                    "Content-Type": "application/xml"
                }
            )
            return response.status_code == 207
        except Exception as e:
            logger.error(f"Apple Calendar connection test failed: {e}")
            return False
    
    async def create_event(self, token: OAuthToken, event: CalendarEvent) -> str:
        """Create Apple Calendar event via CalDAV."""
        # This would implement CalDAV event creation
        # For now, return a placeholder
        return f"apple-event-{event.id}"
    
    async def update_event(self, token: OAuthToken, event_id: str, event: CalendarEvent) -> bool:
        """Update Apple Calendar event via CalDAV."""
        # This would implement CalDAV event update
        return True
    
    async def delete_event(self, token: OAuthToken, event_id: str) -> bool:
        """Delete Apple Calendar event via CalDAV."""
        # This would implement CalDAV event deletion
        return True
    
    async def get_events(
        self,
        token: OAuthToken,
        start_date: datetime,
        end_date: datetime,
        max_results: int = 100
    ) -> List[CalendarEvent]:
        """Get Apple Calendar events via CalDAV."""
        # This would implement CalDAV event retrieval
        return []
    
    async def check_availability(
        self,
        token: OAuthToken,
        start_time: datetime,
        end_time: datetime
    ) -> List[CalendarAvailability]:
        """Check Apple Calendar availability via CalDAV."""
        # This would implement CalDAV availability check
        return []


class CalendarManager:
    """Manager for all calendar services."""
    
    def __init__(self):
        """Initialize calendar manager."""
        self.services: Dict[str, CalendarIntegrationService] = {}
    
    def register_service(self, provider: str, service: CalendarIntegrationService):
        """Register a calendar service."""
        self.services[provider] = service
        logger.info(f"Registered calendar service: {provider}")
    
    def get_service(self, provider: str) -> Optional[CalendarIntegrationService]:
        """Get calendar service by provider."""
        return self.services.get(provider)
    
    async def create_meeting(
        self,
        provider: str,
        token: OAuthToken,
        title: str,
        start_time: datetime,
        duration_minutes: int,
        attendees: List[str],
        description: Optional[str] = None,
        location: Optional[str] = None,
        include_video: bool = True
    ) -> Optional[str]:
        """Create a meeting across calendar providers."""
        service = self.get_service(provider)
        if not service:
            return None
        
        event = CalendarEvent(
            id=f"meeting-{datetime.utcnow().isoformat()}",
            title=title,
            description=description,
            start_time=start_time,
            end_time=start_time + timedelta(minutes=duration_minutes),
            location=location,
            attendees=attendees,
            meeting_url="generate" if include_video else None
        )
        
        try:
            return await service.create_event(token, event)
        except Exception as e:
            logger.error(f"Failed to create meeting in {provider}: {e}")
            return None
    
    async def find_optimal_meeting_time(
        self,
        tokens: Dict[str, OAuthToken],
        start_date: datetime,
        end_date: datetime,
        duration_minutes: int = 60,
        attendees: List[str] = None
    ) -> Optional[Dict[str, datetime]]:
        """Find optimal meeting time across all calendars."""
        all_availability = []
        
        # Get availability from all connected calendars
        for provider, token in tokens.items():
            service = self.get_service(provider)
            if service:
                try:
                    availability = await service.check_availability(token, start_date, end_date)
                    all_availability.extend(availability)
                except Exception as e:
                    logger.error(f"Failed to check availability for {provider}: {e}")
        
        # Find the first available slot
        for provider, token in tokens.items():
            service = self.get_service(provider)
            if service:
                try:
                    slots = await service.find_available_slots(
                        token, start_date, end_date, duration_minutes
                    )
                    if slots:
                        return slots[0]
                except Exception as e:
                    logger.error(f"Failed to find slots for {provider}: {e}")
        
        return None
    
    async def sync_events(
        self,
        tokens: Dict[str, OAuthToken],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, List[CalendarEvent]]:
        """Sync events from all connected calendars."""
        all_events = {}
        
        for provider, token in tokens.items():
            service = self.get_service(provider)
            if service:
                try:
                    events = await service.get_events(token, start_date, end_date)
                    all_events[provider] = events
                except Exception as e:
                    logger.error(f"Failed to sync events from {provider}: {e}")
                    all_events[provider] = []
        
        return all_events
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for all calendar services."""
        health_results = {}
        
        for provider, service in self.services.items():
            try:
                health_results[provider] = await service.health_check()
            except Exception as e:
                health_results[provider] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return {
            "services": health_results,
            "total_services": len(self.services)
        }


# Global calendar manager instance
calendar_manager = CalendarManager()