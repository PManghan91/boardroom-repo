"""Communication platform integrations for Slack, Microsoft Teams, Discord, and email automation."""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
import httpx
from pydantic import BaseModel, Field

from app.core.logging import logger
from .base import IntegrationService, IntegrationConfig, OAuthToken, IntegrationError
from .oauth import OAuthManager


class Message(BaseModel):
    """Message model for communication platforms."""
    id: Optional[str] = None
    text: str
    channel: str
    user: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    thread_id: Optional[str] = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    mentions: List[str] = Field(default_factory=list)
    reactions: Dict[str, int] = Field(default_factory=dict)


class Channel(BaseModel):
    """Channel model for communication platforms."""
    id: str
    name: str
    description: Optional[str] = None
    is_private: bool = False
    member_count: Optional[int] = None
    created_at: Optional[datetime] = None


class User(BaseModel):
    """User model for communication platforms."""
    id: str
    name: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    status: Optional[str] = None
    is_online: bool = False


class Notification(BaseModel):
    """Notification model."""
    title: str
    message: str
    channel: str
    urgency: str = "normal"  # "low", "normal", "high", "urgent"
    recipients: List[str] = Field(default_factory=list)
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    scheduled_at: Optional[datetime] = None


class CommunicationIntegrationService(IntegrationService):
    """Base communication integration service."""
    
    async def send_message(self, token: OAuthToken, message: Message) -> str:
        """Send a message to a channel."""
        raise NotImplementedError
    
    async def send_notification(self, token: OAuthToken, notification: Notification) -> bool:
        """Send a notification."""
        raise NotImplementedError
    
    async def get_channels(self, token: OAuthToken) -> List[Channel]:
        """Get list of channels."""
        raise NotImplementedError
    
    async def get_users(self, token: OAuthToken) -> List[User]:
        """Get list of users."""
        raise NotImplementedError
    
    async def create_channel(self, token: OAuthToken, name: str, description: str = "", private: bool = False) -> str:
        """Create a new channel."""
        raise NotImplementedError
    
    async def invite_users(self, token: OAuthToken, channel_id: str, user_ids: List[str]) -> bool:
        """Invite users to a channel."""
        raise NotImplementedError


class SlackService(CommunicationIntegrationService):
    """Slack integration service."""
    
    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.oauth_manager = OAuthManager(config)
        self.base_url = "https://slack.com/api"
        self.auth_url = "https://slack.com/oauth/v2/authorize"
        self.token_url = "https://slack.com/api/oauth.v2.access"
    
    async def authorize_url(self, state: str) -> str:
        """Generate Slack OAuth authorization URL."""
        return await self.oauth_manager.build_authorization_url(
            self.auth_url,
            state,
            self.config.scopes,
            {
                "user_scope": "identity.basic"
            }
        )
    
    async def exchange_code(self, code: str, state: str) -> OAuthToken:
        """Exchange authorization code for access token."""
        return await self.oauth_manager.exchange_code_for_token(
            self.token_url,
            code
        )
    
    async def refresh_token(self, refresh_token: str) -> OAuthToken:
        """Slack tokens don't expire, return the same token."""
        return OAuthToken(
            access_token=refresh_token,
            token_type="Bearer"
        )
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke Slack access token."""
        try:
            await self._make_request(
                "POST",
                f"{self.base_url}/auth.revoke",
                OAuthToken(access_token=token, token_type="Bearer")
            )
            return True
        except Exception as e:
            logger.error(f"Failed to revoke Slack token: {e}")
            return False
    
    async def test_connection(self, token: OAuthToken) -> bool:
        """Test Slack connection."""
        try:
            response = await self._make_request(
                "POST",
                f"{self.base_url}/auth.test",
                token
            )
            return response.get("ok", False)
        except Exception as e:
            logger.error(f"Slack connection test failed: {e}")
            return False
    
    async def send_message(self, token: OAuthToken, message: Message) -> str:
        """Send a message to a Slack channel."""
        data = {
            "channel": message.channel,
            "text": message.text,
            "thread_ts": message.thread_id,
            "attachments": message.attachments
        }
        
        response = await self._make_request(
            "POST",
            f"{self.base_url}/chat.postMessage",
            token,
            data=data
        )
        
        if response.get("ok"):
            return response.get("ts", "")
        else:
            raise IntegrationError(
                message=f"Failed to send Slack message: {response.get('error')}",
                status_code=400,
                provider="slack"
            )
    
    async def send_notification(self, token: OAuthToken, notification: Notification) -> bool:
        """Send a notification to Slack."""
        # Determine urgency formatting
        urgency_colors = {
            "low": "#36a64f",
            "normal": "#3AA3E3", 
            "high": "#ff9500",
            "urgent": "#ff0000"
        }
        
        attachment = {
            "color": urgency_colors.get(notification.urgency, "#3AA3E3"),
            "title": notification.title,
            "text": notification.message,
            "footer": "Boardroom AI",
            "ts": int(datetime.utcnow().timestamp())
        }
        
        if notification.attachments:
            attachment.update(notification.attachments[0])
        
        message = Message(
            text=f"*{notification.title}*",
            channel=notification.channel,
            attachments=[attachment]
        )
        
        try:
            await self.send_message(token, message)
            return True
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False
    
    async def get_channels(self, token: OAuthToken) -> List[Channel]:
        """Get list of Slack channels."""
        response = await self._make_request(
            "POST",
            f"{self.base_url}/conversations.list",
            token,
            data={"types": "public_channel,private_channel"}
        )
        
        channels = []
        for channel_data in response.get("channels", []):
            channel = Channel(
                id=channel_data["id"],
                name=channel_data["name"],
                is_private=channel_data.get("is_private", False),
                member_count=channel_data.get("num_members"),
                created_at=datetime.fromtimestamp(channel_data.get("created", 0)) if channel_data.get("created") else None
            )
            channels.append(channel)
        
        return channels
    
    async def get_users(self, token: OAuthToken) -> List[User]:
        """Get list of Slack users."""
        response = await self._make_request(
            "POST",
            f"{self.base_url}/users.list",
            token
        )
        
        users = []
        for user_data in response.get("members", []):
            if not user_data.get("deleted") and not user_data.get("is_bot"):
                user = User(
                    id=user_data["id"],
                    name=user_data.get("real_name", user_data.get("name", "")),
                    email=user_data.get("profile", {}).get("email"),
                    avatar_url=user_data.get("profile", {}).get("image_72"),
                    status=user_data.get("profile", {}).get("status_text"),
                    is_online=user_data.get("presence") == "active"
                )
                users.append(user)
        
        return users
    
    async def create_channel(self, token: OAuthToken, name: str, description: str = "", private: bool = False) -> str:
        """Create a new Slack channel."""
        data = {
            "name": name,
            "is_private": private
        }
        
        response = await self._make_request(
            "POST",
            f"{self.base_url}/conversations.create",
            token,
            data=data
        )
        
        if response.get("ok"):
            channel_id = response["channel"]["id"]
            
            # Set description if provided
            if description:
                await self._make_request(
                    "POST",
                    f"{self.base_url}/conversations.setPurpose",
                    token,
                    data={"channel": channel_id, "purpose": description}
                )
            
            return channel_id
        else:
            raise IntegrationError(
                message=f"Failed to create Slack channel: {response.get('error')}",
                status_code=400,
                provider="slack"
            )
    
    async def invite_users(self, token: OAuthToken, channel_id: str, user_ids: List[str]) -> bool:
        """Invite users to a Slack channel."""
        try:
            await self._make_request(
                "POST",
                f"{self.base_url}/conversations.invite",
                token,
                data={"channel": channel_id, "users": ",".join(user_ids)}
            )
            return True
        except Exception as e:
            logger.error(f"Failed to invite users to Slack channel: {e}")
            return False


class TeamsService(CommunicationIntegrationService):
    """Microsoft Teams integration service."""
    
    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.oauth_manager = OAuthManager(config)
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.auth_url = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        self.token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    
    async def authorize_url(self, state: str) -> str:
        """Generate Microsoft Teams OAuth authorization URL."""
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
        """Refresh Microsoft Teams access token."""
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
                f"{self.base_url}/me/joinedTeams",
                token
            )
            return True
        except Exception as e:
            logger.error(f"Microsoft Teams connection test failed: {e}")
            return False
    
    async def send_message(self, token: OAuthToken, message: Message) -> str:
        """Send a message to a Teams channel."""
        # Parse channel format: team_id:channel_id
        team_id, channel_id = message.channel.split(":", 1)
        
        data = {
            "body": {
                "content": message.text,
                "contentType": "text"
            }
        }
        
        if message.attachments:
            data["attachments"] = message.attachments
        
        response = await self._make_request(
            "POST",
            f"{self.base_url}/teams/{team_id}/channels/{channel_id}/messages",
            token,
            data=data
        )
        
        return response.get("id", "")
    
    async def send_notification(self, token: OAuthToken, notification: Notification) -> bool:
        """Send a notification to Teams."""
        message = Message(
            text=f"**{notification.title}**\n\n{notification.message}",
            channel=notification.channel,
            attachments=notification.attachments
        )
        
        try:
            await self.send_message(token, message)
            return True
        except Exception as e:
            logger.error(f"Failed to send Teams notification: {e}")
            return False
    
    async def get_channels(self, token: OAuthToken) -> List[Channel]:
        """Get list of Teams channels."""
        # First get teams
        teams_response = await self._make_request(
            "GET",
            f"{self.base_url}/me/joinedTeams",
            token
        )
        
        channels = []
        for team in teams_response.get("value", []):
            team_id = team["id"]
            
            # Get channels for each team
            channels_response = await self._make_request(
                "GET",
                f"{self.base_url}/teams/{team_id}/channels",
                token
            )
            
            for channel_data in channels_response.get("value", []):
                channel = Channel(
                    id=f"{team_id}:{channel_data['id']}",
                    name=f"{team['displayName']} / {channel_data['displayName']}",
                    description=channel_data.get("description"),
                    is_private=channel_data.get("membershipType") == "private"
                )
                channels.append(channel)
        
        return channels
    
    async def get_users(self, token: OAuthToken) -> List[User]:
        """Get list of Teams users."""
        response = await self._make_request(
            "GET",
            f"{self.base_url}/users",
            token
        )
        
        users = []
        for user_data in response.get("value", []):
            user = User(
                id=user_data["id"],
                name=user_data.get("displayName", ""),
                email=user_data.get("mail") or user_data.get("userPrincipalName"),
                is_online=False  # Teams doesn't provide presence in this endpoint
            )
            users.append(user)
        
        return users
    
    async def create_channel(self, token: OAuthToken, name: str, description: str = "", private: bool = False) -> str:
        """Create a new Teams channel."""
        # This requires a team ID - would need to be passed as parameter
        # For now, return a placeholder
        return f"teams-channel-{name}"
    
    async def invite_users(self, token: OAuthToken, channel_id: str, user_ids: List[str]) -> bool:
        """Invite users to a Teams channel."""
        # Teams channel membership is managed differently
        return True


class DiscordService(CommunicationIntegrationService):
    """Discord integration service."""
    
    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.oauth_manager = OAuthManager(config)
        self.base_url = "https://discord.com/api/v10"
        self.auth_url = "https://discord.com/api/oauth2/authorize"
        self.token_url = "https://discord.com/api/oauth2/token"
    
    async def authorize_url(self, state: str) -> str:
        """Generate Discord OAuth authorization URL."""
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
        """Refresh Discord access token."""
        return await self.oauth_manager.refresh_access_token(
            self.token_url,
            refresh_token
        )
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke Discord access token."""
        try:
            await self._make_request(
                "POST",
                f"{self.base_url}/oauth2/token/revoke",
                OAuthToken(access_token=token, token_type="Bearer"),
                data={"token": token}
            )
            return True
        except Exception as e:
            logger.error(f"Failed to revoke Discord token: {e}")
            return False
    
    async def test_connection(self, token: OAuthToken) -> bool:
        """Test Discord connection."""
        try:
            await self._make_request(
                "GET",
                f"{self.base_url}/users/@me",
                token
            )
            return True
        except Exception as e:
            logger.error(f"Discord connection test failed: {e}")
            return False
    
    async def send_message(self, token: OAuthToken, message: Message) -> str:
        """Send a message to a Discord channel."""
        data = {
            "content": message.text
        }
        
        if message.attachments:
            data["embeds"] = message.attachments
        
        response = await self._make_request(
            "POST",
            f"{self.base_url}/channels/{message.channel}/messages",
            token,
            data=data
        )
        
        return response.get("id", "")
    
    async def send_notification(self, token: OAuthToken, notification: Notification) -> bool:
        """Send a notification to Discord."""
        # Create rich embed for notification
        embed = {
            "title": notification.title,
            "description": notification.message,
            "color": {
                "low": 0x36a64f,
                "normal": 0x3AA3E3,
                "high": 0xff9500,
                "urgent": 0xff0000
            }.get(notification.urgency, 0x3AA3E3),
            "footer": {
                "text": "Boardroom AI"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        message = Message(
            text="📢 **Boardroom Notification**",
            channel=notification.channel,
            attachments=[embed]
        )
        
        try:
            await self.send_message(token, message)
            return True
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False
    
    async def get_channels(self, token: OAuthToken) -> List[Channel]:
        """Get list of Discord channels."""
        # First get guilds (servers)
        guilds_response = await self._make_request(
            "GET",
            f"{self.base_url}/users/@me/guilds",
            token
        )
        
        channels = []
        for guild in guilds_response:
            guild_id = guild["id"]
            
            # Get channels for each guild
            channels_response = await self._make_request(
                "GET",
                f"{self.base_url}/guilds/{guild_id}/channels",
                token
            )
            
            for channel_data in channels_response:
                if channel_data.get("type") == 0:  # Text channel
                    channel = Channel(
                        id=channel_data["id"],
                        name=f"{guild['name']} / #{channel_data['name']}",
                        is_private=False
                    )
                    channels.append(channel)
        
        return channels
    
    async def get_users(self, token: OAuthToken) -> List[User]:
        """Get list of Discord users."""
        # Discord API doesn't provide a general user list
        # Would need to get members from specific guilds
        return []
    
    async def create_channel(self, token: OAuthToken, name: str, description: str = "", private: bool = False) -> str:
        """Create a new Discord channel."""
        # This requires a guild ID - would need to be passed as parameter
        return f"discord-channel-{name}"
    
    async def invite_users(self, token: OAuthToken, channel_id: str, user_ids: List[str]) -> bool:
        """Invite users to a Discord channel."""
        # Discord uses invite links rather than direct invitations
        return True


class EmailService:
    """Email automation service using SendGrid/Mailgun."""
    
    def __init__(self, provider: str, api_key: str):
        """Initialize email service."""
        self.provider = provider
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)
        
        if provider == "sendgrid":
            self.base_url = "https://api.sendgrid.com/v3"
        elif provider == "mailgun":
            self.base_url = "https://api.mailgun.net/v3"
        else:
            raise ValueError(f"Unsupported email provider: {provider}")
    
    async def send_email(
        self,
        to_emails: List[str],
        subject: str,
        content: str,
        from_email: str = "noreply@boardroom.ai",
        from_name: str = "Boardroom AI"
    ) -> bool:
        """Send email notification."""
        try:
            if self.provider == "sendgrid":
                return await self._send_sendgrid_email(to_emails, subject, content, from_email, from_name)
            elif self.provider == "mailgun":
                return await self._send_mailgun_email(to_emails, subject, content, from_email, from_name)
        except Exception as e:
            logger.error(f"Failed to send email via {self.provider}: {e}")
            return False
    
    async def _send_sendgrid_email(
        self,
        to_emails: List[str],
        subject: str,
        content: str,
        from_email: str,
        from_name: str
    ) -> bool:
        """Send email via SendGrid."""
        data = {
            "personalizations": [{
                "to": [{"email": email} for email in to_emails]
            }],
            "from": {"email": from_email, "name": from_name},
            "subject": subject,
            "content": [{
                "type": "text/html",
                "value": content
            }]
        }
        
        response = await self.client.post(
            f"{self.base_url}/mail/send",
            json=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        
        return response.status_code == 202
    
    async def _send_mailgun_email(
        self,
        to_emails: List[str],
        subject: str,
        content: str,
        from_email: str,
        from_name: str
    ) -> bool:
        """Send email via Mailgun."""
        domain = from_email.split("@")[1]
        
        data = {
            "from": f"{from_name} <{from_email}>",
            "to": to_emails,
            "subject": subject,
            "html": content
        }
        
        response = await self.client.post(
            f"{self.base_url}/{domain}/messages",
            data=data,
            auth=("api", self.api_key)
        )
        
        return response.status_code == 200


class CommunicationManager:
    """Manager for all communication services."""
    
    def __init__(self):
        """Initialize communication manager."""
        self.services: Dict[str, CommunicationIntegrationService] = {}
        self.email_service: Optional[EmailService] = None
    
    def register_service(self, provider: str, service: CommunicationIntegrationService):
        """Register a communication service."""
        self.services[provider] = service
        logger.info(f"Registered communication service: {provider}")
    
    def register_email_service(self, provider: str, api_key: str):
        """Register email service."""
        self.email_service = EmailService(provider, api_key)
        logger.info(f"Registered email service: {provider}")
    
    def get_service(self, provider: str) -> Optional[CommunicationIntegrationService]:
        """Get communication service by provider."""
        return self.services.get(provider)
    
    async def broadcast_notification(
        self,
        tokens: Dict[str, OAuthToken],
        notification: Notification
    ) -> Dict[str, bool]:
        """Broadcast notification to all connected platforms."""
        results = {}
        
        for provider, token in tokens.items():
            service = self.get_service(provider)
            if service:
                try:
                    success = await service.send_notification(token, notification)
                    results[provider] = success
                except Exception as e:
                    logger.error(f"Failed to send notification via {provider}: {e}")
                    results[provider] = False
        
        return results
    
    async def send_email_notification(
        self,
        to_emails: List[str],
        title: str,
        message: str
    ) -> bool:
        """Send email notification."""
        if not self.email_service:
            logger.warning("No email service configured")
            return False
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                    <h2 style="color: #333; margin-bottom: 20px;">{title}</h2>
                    <div style="background-color: white; padding: 20px; border-radius: 8px; border-left: 4px solid #007bff;">
                        <p style="color: #555; line-height: 1.6; margin: 0;">{message}</p>
                    </div>
                    <div style="margin-top: 20px; text-align: center;">
                        <p style="color: #888; font-size: 12px;">
                            This notification was sent by Boardroom AI<br>
                            © 2024 Boardroom AI. All rights reserved.
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        return await self.email_service.send_email(
            to_emails=to_emails,
            subject=title,
            content=html_content
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for all communication services."""
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
            "email_service": self.email_service.provider if self.email_service else None,
            "total_services": len(self.services)
        }


# Global communication manager instance
communication_manager = CommunicationManager()