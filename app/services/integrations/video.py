"""Video conferencing integrations for Zoom, Microsoft Teams, Google Meet, and WebRTC."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
import httpx
from pydantic import BaseModel, Field
import uuid

from app.core.logging import logger
from .base import IntegrationService, IntegrationConfig, OAuthToken, IntegrationError
from .oauth import OAuthManager


class VideoMeeting(BaseModel):
    """Video meeting model."""
    id: str
    title: str
    description: Optional[str] = None
    start_time: datetime
    duration_minutes: int
    timezone: str = "UTC"
    host_email: str
    join_url: str
    meeting_password: Optional[str] = None
    dial_in_numbers: List[Dict[str, str]] = Field(default_factory=list)
    participants: List[str] = Field(default_factory=list)
    recording_enabled: bool = False
    waiting_room: bool = True
    require_auth: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MeetingParticipant(BaseModel):
    """Meeting participant model."""
    id: str
    name: str
    email: Optional[str] = None
    is_host: bool = False
    is_co_host: bool = False
    join_time: Optional[datetime] = None
    leave_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    camera_enabled: bool = True
    microphone_enabled: bool = True


class MeetingRecording(BaseModel):
    """Meeting recording model."""
    id: str
    meeting_id: str
    title: str
    download_url: str
    file_size: int
    duration_seconds: int
    recording_type: str  # "cloud", "local"
    created_at: datetime
    expires_at: Optional[datetime] = None


class VideoConferencingService(IntegrationService):
    """Base video conferencing service."""
    
    async def create_meeting(self, token: OAuthToken, meeting: VideoMeeting) -> str:
        """Create a video meeting."""
        raise NotImplementedError
    
    async def update_meeting(self, token: OAuthToken, meeting_id: str, meeting: VideoMeeting) -> bool:
        """Update a video meeting."""
        raise NotImplementedError
    
    async def delete_meeting(self, token: OAuthToken, meeting_id: str) -> bool:
        """Delete a video meeting."""
        raise NotImplementedError
    
    async def get_meeting(self, token: OAuthToken, meeting_id: str) -> Optional[VideoMeeting]:
        """Get meeting details."""
        raise NotImplementedError
    
    async def list_meetings(self, token: OAuthToken, start_date: datetime, end_date: datetime) -> List[VideoMeeting]:
        """List meetings in date range."""
        raise NotImplementedError
    
    async def get_meeting_participants(self, token: OAuthToken, meeting_id: str) -> List[MeetingParticipant]:
        """Get meeting participants."""
        raise NotImplementedError
    
    async def get_meeting_recordings(self, token: OAuthToken, meeting_id: str) -> List[MeetingRecording]:
        """Get meeting recordings."""
        raise NotImplementedError


class ZoomService(VideoConferencingService):
    """Zoom integration service."""
    
    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.oauth_manager = OAuthManager(config)
        self.base_url = "https://api.zoom.us/v2"
        self.auth_url = "https://zoom.us/oauth/authorize"
        self.token_url = "https://zoom.us/oauth/token"
    
    async def authorize_url(self, state: str) -> str:
        """Generate Zoom OAuth authorization URL."""
        return await self.oauth_manager.build_authorization_url(
            self.auth_url,
            state,
            self.config.scopes
        )
    
    async def exchange_code(self, code: str, state: str) -> OAuthToken:
        """Exchange authorization code for access token."""
        return await self.oauth_manager.exchange_code_for_token(
            self.token_url,
            code
        )
    
    async def refresh_token(self, refresh_token: str) -> OAuthToken:
        """Refresh Zoom access token."""
        return await self.oauth_manager.refresh_access_token(
            self.token_url,
            refresh_token
        )
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke Zoom access token."""
        try:
            await self._make_request(
                "POST",
                f"{self.base_url}/oauth/revoke",
                OAuthToken(access_token=token, token_type="Bearer"),
                data={"token": token}
            )
            return True
        except Exception as e:
            logger.error(f"Failed to revoke Zoom token: {e}")
            return False
    
    async def test_connection(self, token: OAuthToken) -> bool:
        """Test Zoom connection."""
        try:
            await self._make_request(
                "GET",
                f"{self.base_url}/users/me",
                token
            )
            return True
        except Exception as e:
            logger.error(f"Zoom connection test failed: {e}")
            return False
    
    async def create_meeting(self, token: OAuthToken, meeting: VideoMeeting) -> str:
        """Create a Zoom meeting."""
        meeting_data = {
            "topic": meeting.title,
            "type": 2,  # Scheduled meeting
            "start_time": meeting.start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "duration": meeting.duration_minutes,
            "timezone": meeting.timezone,
            "agenda": meeting.description or "",
            "settings": {
                "host_video": True,
                "participant_video": True,
                "cn_meeting": False,
                "in_meeting": False,
                "join_before_host": False,
                "mute_upon_entry": True,
                "watermark": False,
                "use_pmi": False,
                "approval_type": 0,
                "registration_type": 1,
                "audio": "both",
                "auto_recording": "cloud" if meeting.recording_enabled else "none",
                "enforce_login": meeting.require_auth,
                "enforce_login_domains": "",
                "alternative_hosts": "",
                "waiting_room": meeting.waiting_room
            }
        }
        
        if meeting.meeting_password:
            meeting_data["password"] = meeting.meeting_password
        
        response = await self._make_request(
            "POST",
            f"{self.base_url}/users/me/meetings",
            token,
            data=meeting_data
        )
        
        # Update meeting with Zoom response data
        meeting.id = str(response["id"])
        meeting.join_url = response["join_url"]
        meeting.meeting_password = response.get("password")
        
        return meeting.id
    
    async def update_meeting(self, token: OAuthToken, meeting_id: str, meeting: VideoMeeting) -> bool:
        """Update a Zoom meeting."""
        meeting_data = {
            "topic": meeting.title,
            "start_time": meeting.start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "duration": meeting.duration_minutes,
            "timezone": meeting.timezone,
            "agenda": meeting.description or "",
            "settings": {
                "host_video": True,
                "participant_video": True,
                "mute_upon_entry": True,
                "auto_recording": "cloud" if meeting.recording_enabled else "none",
                "waiting_room": meeting.waiting_room
            }
        }
        
        try:
            await self._make_request(
                "PATCH",
                f"{self.base_url}/meetings/{meeting_id}",
                token,
                data=meeting_data
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update Zoom meeting: {e}")
            return False
    
    async def delete_meeting(self, token: OAuthToken, meeting_id: str) -> bool:
        """Delete a Zoom meeting."""
        try:
            await self._make_request(
                "DELETE",
                f"{self.base_url}/meetings/{meeting_id}",
                token
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete Zoom meeting: {e}")
            return False
    
    async def get_meeting(self, token: OAuthToken, meeting_id: str) -> Optional[VideoMeeting]:
        """Get Zoom meeting details."""
        try:
            response = await self._make_request(
                "GET",
                f"{self.base_url}/meetings/{meeting_id}",
                token
            )
            
            return VideoMeeting(
                id=str(response["id"]),
                title=response["topic"],
                description=response.get("agenda", ""),
                start_time=datetime.fromisoformat(response["start_time"].replace("Z", "+00:00")),
                duration_minutes=response["duration"],
                timezone=response["timezone"],
                host_email=response.get("host_email", ""),
                join_url=response["join_url"],
                meeting_password=response.get("password"),
                recording_enabled=response.get("settings", {}).get("auto_recording") == "cloud",
                waiting_room=response.get("settings", {}).get("waiting_room", False)
            )
        except Exception as e:
            logger.error(f"Failed to get Zoom meeting: {e}")
            return None
    
    async def list_meetings(self, token: OAuthToken, start_date: datetime, end_date: datetime) -> List[VideoMeeting]:
        """List Zoom meetings."""
        params = {
            "type": "scheduled",
            "page_size": 300,
            "from": start_date.strftime("%Y-%m-%d"),
            "to": end_date.strftime("%Y-%m-%d")
        }
        
        response = await self._make_request(
            "GET",
            f"{self.base_url}/users/me/meetings",
            token,
            params=params
        )
        
        meetings = []
        for meeting_data in response.get("meetings", []):
            meeting = VideoMeeting(
                id=str(meeting_data["id"]),
                title=meeting_data["topic"],
                start_time=datetime.fromisoformat(meeting_data["start_time"].replace("Z", "+00:00")),
                duration_minutes=meeting_data["duration"],
                timezone=meeting_data["timezone"],
                host_email=meeting_data.get("host_email", ""),
                join_url=meeting_data["join_url"]
            )
            meetings.append(meeting)
        
        return meetings
    
    async def get_meeting_participants(self, token: OAuthToken, meeting_id: str) -> List[MeetingParticipant]:
        """Get Zoom meeting participants."""
        try:
            response = await self._make_request(
                "GET",
                f"{self.base_url}/metrics/meetings/{meeting_id}/participants",
                token
            )
            
            participants = []
            for participant_data in response.get("participants", []):
                participant = MeetingParticipant(
                    id=participant_data["id"],
                    name=participant_data["name"],
                    email=participant_data.get("user_email"),
                    join_time=datetime.fromisoformat(participant_data["join_time"].replace("Z", "+00:00")) if participant_data.get("join_time") else None,
                    leave_time=datetime.fromisoformat(participant_data["leave_time"].replace("Z", "+00:00")) if participant_data.get("leave_time") else None,
                    duration_seconds=participant_data.get("duration")
                )
                participants.append(participant)
            
            return participants
        except Exception as e:
            logger.error(f"Failed to get Zoom meeting participants: {e}")
            return []
    
    async def get_meeting_recordings(self, token: OAuthToken, meeting_id: str) -> List[MeetingRecording]:
        """Get Zoom meeting recordings."""
        try:
            response = await self._make_request(
                "GET",
                f"{self.base_url}/meetings/{meeting_id}/recordings",
                token
            )
            
            recordings = []
            for recording_data in response.get("recording_files", []):
                recording = MeetingRecording(
                    id=recording_data["id"],
                    meeting_id=meeting_id,
                    title=recording_data["recording_type"],
                    download_url=recording_data["download_url"],
                    file_size=recording_data["file_size"],
                    duration_seconds=recording_data.get("recording_end", 0) - recording_data.get("recording_start", 0),
                    recording_type="cloud",
                    created_at=datetime.fromisoformat(recording_data["recording_start"].replace("Z", "+00:00"))
                )
                recordings.append(recording)
            
            return recordings
        except Exception as e:
            logger.error(f"Failed to get Zoom meeting recordings: {e}")
            return []


class GoogleMeetService(VideoConferencingService):
    """Google Meet integration service."""
    
    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.oauth_manager = OAuthManager(config)
        self.base_url = "https://www.googleapis.com/calendar/v3"
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
    
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
            "https://oauth2.googleapis.com/revoke",
            token
        )
    
    async def test_connection(self, token: OAuthToken) -> bool:
        """Test Google Meet connection."""
        try:
            await self._make_request(
                "GET",
                f"{self.base_url}/users/me/calendarList",
                token
            )
            return True
        except Exception as e:
            logger.error(f"Google Meet connection test failed: {e}")
            return False
    
    async def create_meeting(self, token: OAuthToken, meeting: VideoMeeting) -> str:
        """Create a Google Meet meeting (via Calendar event)."""
        event_data = {
            "summary": meeting.title,
            "description": meeting.description,
            "start": {
                "dateTime": meeting.start_time.isoformat(),
                "timeZone": meeting.timezone
            },
            "end": {
                "dateTime": (meeting.start_time + timedelta(minutes=meeting.duration_minutes)).isoformat(),
                "timeZone": meeting.timezone
            },
            "attendees": [{"email": email} for email in meeting.participants],
            "conferenceData": {
                "createRequest": {
                    "requestId": str(uuid.uuid4()),
                    "conferenceSolutionKey": {
                        "type": "hangoutsMeet"
                    }
                }
            }
        }
        
        response = await self._make_request(
            "POST",
            f"{self.base_url}/calendars/primary/events",
            token,
            data=event_data,
            params={"conferenceDataVersion": 1}
        )
        
        # Extract Google Meet link
        conference_data = response.get("conferenceData", {})
        entry_points = conference_data.get("entryPoints", [])
        meet_link = next((ep["uri"] for ep in entry_points if ep["entryPointType"] == "video"), "")
        
        # Update meeting with Google response data
        meeting.id = response["id"]
        meeting.join_url = meet_link
        
        return meeting.id
    
    async def update_meeting(self, token: OAuthToken, meeting_id: str, meeting: VideoMeeting) -> bool:
        """Update a Google Meet meeting."""
        event_data = {
            "summary": meeting.title,
            "description": meeting.description,
            "start": {
                "dateTime": meeting.start_time.isoformat(),
                "timeZone": meeting.timezone
            },
            "end": {
                "dateTime": (meeting.start_time + timedelta(minutes=meeting.duration_minutes)).isoformat(),
                "timeZone": meeting.timezone
            },
            "attendees": [{"email": email} for email in meeting.participants]
        }
        
        try:
            await self._make_request(
                "PUT",
                f"{self.base_url}/calendars/primary/events/{meeting_id}",
                token,
                data=event_data
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update Google Meet meeting: {e}")
            return False
    
    async def delete_meeting(self, token: OAuthToken, meeting_id: str) -> bool:
        """Delete a Google Meet meeting."""
        try:
            await self._make_request(
                "DELETE",
                f"{self.base_url}/calendars/primary/events/{meeting_id}",
                token
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete Google Meet meeting: {e}")
            return False
    
    async def get_meeting(self, token: OAuthToken, meeting_id: str) -> Optional[VideoMeeting]:
        """Get Google Meet meeting details."""
        try:
            response = await self._make_request(
                "GET",
                f"{self.base_url}/calendars/primary/events/{meeting_id}",
                token
            )
            
            start = response.get("start", {})
            end = response.get("end", {})
            start_time = datetime.fromisoformat(start.get("dateTime", "").replace("Z", "+00:00"))
            end_time = datetime.fromisoformat(end.get("dateTime", "").replace("Z", "+00:00"))
            
            # Extract Google Meet link
            conference_data = response.get("conferenceData", {})
            entry_points = conference_data.get("entryPoints", [])
            meet_link = next((ep["uri"] for ep in entry_points if ep["entryPointType"] == "video"), "")
            
            return VideoMeeting(
                id=response["id"],
                title=response.get("summary", ""),
                description=response.get("description", ""),
                start_time=start_time,
                duration_minutes=int((end_time - start_time).total_seconds() / 60),
                timezone=start.get("timeZone", "UTC"),
                host_email=response.get("creator", {}).get("email", ""),
                join_url=meet_link,
                participants=[att.get("email", "") for att in response.get("attendees", [])]
            )
        except Exception as e:
            logger.error(f"Failed to get Google Meet meeting: {e}")
            return None
    
    async def list_meetings(self, token: OAuthToken, start_date: datetime, end_date: datetime) -> List[VideoMeeting]:
        """List Google Meet meetings."""
        params = {
            "timeMin": start_date.isoformat(),
            "timeMax": end_date.isoformat(),
            "singleEvents": True,
            "orderBy": "startTime",
            "maxResults": 250
        }
        
        response = await self._make_request(
            "GET",
            f"{self.base_url}/calendars/primary/events",
            token,
            params=params
        )
        
        meetings = []
        for item in response.get("items", []):
            # Only include events with Google Meet links
            conference_data = item.get("conferenceData", {})
            if not conference_data:
                continue
            
            start = item.get("start", {})
            end = item.get("end", {})
            start_time = datetime.fromisoformat(start.get("dateTime", "").replace("Z", "+00:00"))
            end_time = datetime.fromisoformat(end.get("dateTime", "").replace("Z", "+00:00"))
            
            entry_points = conference_data.get("entryPoints", [])
            meet_link = next((ep["uri"] for ep in entry_points if ep["entryPointType"] == "video"), "")
            
            meeting = VideoMeeting(
                id=item["id"],
                title=item.get("summary", ""),
                start_time=start_time,
                duration_minutes=int((end_time - start_time).total_seconds() / 60),
                timezone=start.get("timeZone", "UTC"),
                host_email=item.get("creator", {}).get("email", ""),
                join_url=meet_link
            )
            meetings.append(meeting)
        
        return meetings
    
    async def get_meeting_participants(self, token: OAuthToken, meeting_id: str) -> List[MeetingParticipant]:
        """Get Google Meet participants (not available via API)."""
        # Google Meet doesn't provide participant data via API
        return []
    
    async def get_meeting_recordings(self, token: OAuthToken, meeting_id: str) -> List[MeetingRecording]:
        """Get Google Meet recordings (not available via API)."""
        # Google Meet recordings are managed separately via Google Drive
        return []


class TeamsVideoService(VideoConferencingService):
    """Microsoft Teams video conferencing service."""
    
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
        """Microsoft doesn't have a revoke endpoint."""
        return True
    
    async def test_connection(self, token: OAuthToken) -> bool:
        """Test Microsoft Teams connection."""
        try:
            await self._make_request(
                "GET",
                f"{self.base_url}/me",
                token
            )
            return True
        except Exception as e:
            logger.error(f"Microsoft Teams connection test failed: {e}")
            return False
    
    async def create_meeting(self, token: OAuthToken, meeting: VideoMeeting) -> str:
        """Create a Microsoft Teams meeting."""
        event_data = {
            "subject": meeting.title,
            "body": {
                "contentType": "Text",
                "content": meeting.description or ""
            },
            "start": {
                "dateTime": meeting.start_time.isoformat(),
                "timeZone": meeting.timezone
            },
            "end": {
                "dateTime": (meeting.start_time + timedelta(minutes=meeting.duration_minutes)).isoformat(),
                "timeZone": meeting.timezone
            },
            "attendees": [
                {
                    "emailAddress": {"address": email},
                    "type": "required"
                } for email in meeting.participants
            ],
            "isOnlineMeeting": True,
            "onlineMeetingProvider": "teamsForBusiness"
        }
        
        response = await self._make_request(
            "POST",
            f"{self.base_url}/me/events",
            token,
            data=event_data
        )
        
        # Update meeting with Teams response data
        meeting.id = response["id"]
        meeting.join_url = response.get("onlineMeeting", {}).get("joinUrl", "")
        
        return meeting.id
    
    async def update_meeting(self, token: OAuthToken, meeting_id: str, meeting: VideoMeeting) -> bool:
        """Update a Microsoft Teams meeting."""
        event_data = {
            "subject": meeting.title,
            "body": {
                "contentType": "Text",
                "content": meeting.description or ""
            },
            "start": {
                "dateTime": meeting.start_time.isoformat(),
                "timeZone": meeting.timezone
            },
            "end": {
                "dateTime": (meeting.start_time + timedelta(minutes=meeting.duration_minutes)).isoformat(),
                "timeZone": meeting.timezone
            },
            "attendees": [
                {
                    "emailAddress": {"address": email},
                    "type": "required"
                } for email in meeting.participants
            ]
        }
        
        try:
            await self._make_request(
                "PATCH",
                f"{self.base_url}/me/events/{meeting_id}",
                token,
                data=event_data
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update Teams meeting: {e}")
            return False
    
    async def delete_meeting(self, token: OAuthToken, meeting_id: str) -> bool:
        """Delete a Microsoft Teams meeting."""
        try:
            await self._make_request(
                "DELETE",
                f"{self.base_url}/me/events/{meeting_id}",
                token
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete Teams meeting: {e}")
            return False
    
    async def get_meeting(self, token: OAuthToken, meeting_id: str) -> Optional[VideoMeeting]:
        """Get Microsoft Teams meeting details."""
        try:
            response = await self._make_request(
                "GET",
                f"{self.base_url}/me/events/{meeting_id}",
                token
            )
            
            start = response.get("start", {})
            end = response.get("end", {})
            start_time = datetime.fromisoformat(start.get("dateTime", ""))
            end_time = datetime.fromisoformat(end.get("dateTime", ""))
            
            return VideoMeeting(
                id=response["id"],
                title=response.get("subject", ""),
                description=response.get("body", {}).get("content", ""),
                start_time=start_time,
                duration_minutes=int((end_time - start_time).total_seconds() / 60),
                timezone=start.get("timeZone", "UTC"),
                host_email=response.get("organizer", {}).get("emailAddress", {}).get("address", ""),
                join_url=response.get("onlineMeeting", {}).get("joinUrl", ""),
                participants=[att.get("emailAddress", {}).get("address", "") for att in response.get("attendees", [])]
            )
        except Exception as e:
            logger.error(f"Failed to get Teams meeting: {e}")
            return None
    
    async def list_meetings(self, token: OAuthToken, start_date: datetime, end_date: datetime) -> List[VideoMeeting]:
        """List Microsoft Teams meetings."""
        params = {
            "startDateTime": start_date.isoformat(),
            "endDateTime": end_date.isoformat(),
            "$filter": "isOnlineMeeting eq true",
            "$top": 250,
            "$orderby": "start/dateTime"
        }
        
        response = await self._make_request(
            "GET",
            f"{self.base_url}/me/calendarView",
            token,
            params=params
        )
        
        meetings = []
        for item in response.get("value", []):
            start = item.get("start", {})
            end = item.get("end", {})
            start_time = datetime.fromisoformat(start.get("dateTime", ""))
            end_time = datetime.fromisoformat(end.get("dateTime", ""))
            
            meeting = VideoMeeting(
                id=item["id"],
                title=item.get("subject", ""),
                start_time=start_time,
                duration_minutes=int((end_time - start_time).total_seconds() / 60),
                timezone=start.get("timeZone", "UTC"),
                host_email=item.get("organizer", {}).get("emailAddress", {}).get("address", ""),
                join_url=item.get("onlineMeeting", {}).get("joinUrl", "")
            )
            meetings.append(meeting)
        
        return meetings
    
    async def get_meeting_participants(self, token: OAuthToken, meeting_id: str) -> List[MeetingParticipant]:
        """Get Teams meeting participants (limited API access)."""
        # Teams participant data requires special permissions
        return []
    
    async def get_meeting_recordings(self, token: OAuthToken, meeting_id: str) -> List[MeetingRecording]:
        """Get Teams meeting recordings."""
        # Teams recordings are managed via SharePoint/Stream
        return []


class WebRTCService:
    """WebRTC service for built-in video calls."""
    
    def __init__(self):
        """Initialize WebRTC service."""
        self.active_rooms: Dict[str, Dict] = {}
    
    def create_room(self, room_id: str, title: str, host_id: str) -> Dict[str, Any]:
        """Create a WebRTC room."""
        room = {
            "id": room_id,
            "title": title,
            "host_id": host_id,
            "participants": [],
            "created_at": datetime.utcnow(),
            "is_recording": False,
            "settings": {
                "max_participants": 100,
                "require_auth": True,
                "waiting_room": False,
                "chat_enabled": True,
                "screen_share_enabled": True
            }
        }
        
        self.active_rooms[room_id] = room
        logger.info(f"Created WebRTC room: {room_id}")
        return room
    
    def join_room(self, room_id: str, user_id: str, user_name: str) -> Optional[Dict[str, Any]]:
        """Join a WebRTC room."""
        room = self.active_rooms.get(room_id)
        if not room:
            return None
        
        participant = {
            "user_id": user_id,
            "name": user_name,
            "joined_at": datetime.utcnow(),
            "is_host": user_id == room["host_id"],
            "camera_enabled": True,
            "microphone_enabled": True,
            "screen_sharing": False
        }
        
        room["participants"].append(participant)
        logger.info(f"User {user_id} joined WebRTC room {room_id}")
        return room
    
    def leave_room(self, room_id: str, user_id: str) -> bool:
        """Leave a WebRTC room."""
        room = self.active_rooms.get(room_id)
        if not room:
            return False
        
        room["participants"] = [p for p in room["participants"] if p["user_id"] != user_id]
        logger.info(f"User {user_id} left WebRTC room {room_id}")
        
        # Close room if empty
        if not room["participants"]:
            del self.active_rooms[room_id]
            logger.info(f"Closed empty WebRTC room: {room_id}")
        
        return True
    
    def get_room(self, room_id: str) -> Optional[Dict[str, Any]]:
        """Get WebRTC room details."""
        return self.active_rooms.get(room_id)
    
    def list_active_rooms(self) -> List[Dict[str, Any]]:
        """List all active WebRTC rooms."""
        return list(self.active_rooms.values())
    
    def update_participant_settings(
        self,
        room_id: str,
        user_id: str,
        camera_enabled: Optional[bool] = None,
        microphone_enabled: Optional[bool] = None,
        screen_sharing: Optional[bool] = None
    ) -> bool:
        """Update participant settings."""
        room = self.active_rooms.get(room_id)
        if not room:
            return False
        
        for participant in room["participants"]:
            if participant["user_id"] == user_id:
                if camera_enabled is not None:
                    participant["camera_enabled"] = camera_enabled
                if microphone_enabled is not None:
                    participant["microphone_enabled"] = microphone_enabled
                if screen_sharing is not None:
                    participant["screen_sharing"] = screen_sharing
                return True
        
        return False


class VideoConferencingManager:
    """Manager for all video conferencing services."""
    
    def __init__(self):
        """Initialize video conferencing manager."""
        self.services: Dict[str, VideoConferencingService] = {}
        self.webrtc_service = WebRTCService()
    
    def register_service(self, provider: str, service: VideoConferencingService):
        """Register a video conferencing service."""
        self.services[provider] = service
        logger.info(f"Registered video conferencing service: {provider}")
    
    def get_service(self, provider: str) -> Optional[VideoConferencingService]:
        """Get video conferencing service by provider."""
        return self.services.get(provider)
    
    async def create_instant_meeting(
        self,
        provider: str,
        token: OAuthToken,
        title: str,
        duration_minutes: int = 60,
        participants: List[str] = None
    ) -> Optional[VideoMeeting]:
        """Create an instant meeting."""
        service = self.get_service(provider)
        if not service:
            return None
        
        meeting = VideoMeeting(
            id=str(uuid.uuid4()),
            title=title,
            start_time=datetime.utcnow(),
            duration_minutes=duration_minutes,
            host_email="",
            join_url="",
            participants=participants or []
        )
        
        try:
            meeting_id = await service.create_meeting(token, meeting)
            return await service.get_meeting(token, meeting_id)
        except Exception as e:
            logger.error(f"Failed to create instant meeting: {e}")
            return None
    
    async def schedule_meeting(
        self,
        provider: str,
        token: OAuthToken,
        title: str,
        start_time: datetime,
        duration_minutes: int,
        participants: List[str],
        description: str = ""
    ) -> Optional[VideoMeeting]:
        """Schedule a future meeting."""
        service = self.get_service(provider)
        if not service:
            return None
        
        meeting = VideoMeeting(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            start_time=start_time,
            duration_minutes=duration_minutes,
            host_email="",
            join_url="",
            participants=participants
        )
        
        try:
            meeting_id = await service.create_meeting(token, meeting)
            return await service.get_meeting(token, meeting_id)
        except Exception as e:
            logger.error(f"Failed to schedule meeting: {e}")
            return None
    
    def create_webrtc_room(self, title: str, host_id: str) -> str:
        """Create a WebRTC room for built-in video calls."""
        room_id = str(uuid.uuid4())
        self.webrtc_service.create_room(room_id, title, host_id)
        return room_id
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for all video services."""
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
            "webrtc_active_rooms": len(self.webrtc_service.active_rooms),
            "total_services": len(self.services)
        }


# Global video conferencing manager instance
video_manager = VideoConferencingManager()