"""Configuration management for integrations."""

import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from cryptography.fernet import Fernet

from app.core.config import get_settings
from app.core.logging import logger


class IntegrationCredentials(BaseModel):
    """Encrypted integration credentials."""
    client_id: str
    client_secret: str
    webhook_secret: Optional[str] = None
    api_key: Optional[str] = None
    additional_config: Dict[str, Any] = Field(default_factory=dict)


class IntegrationConfig(BaseModel):
    """Integration configuration model."""
    provider: str
    enabled: bool = True
    credentials: IntegrationCredentials
    scopes: list[str] = Field(default_factory=list)
    redirect_uri: str
    webhook_url: Optional[str] = None
    rate_limit: int = 100
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    @validator('provider')
    def validate_provider(cls, v):
        """Validate provider name."""
        allowed_providers = [
            'google', 'microsoft', 'apple', 'slack', 'discord', 'zoom',
            'dropbox', 'github', 'notion', 'jira', 'trello', 'asana',
            'mixpanel', 'sentry', 'datadog', 'hotjar'
        ]
        if v.lower() not in allowed_providers:
            raise ValueError(f"Provider must be one of: {allowed_providers}")
        return v.lower()


class IntegrationConfigManager:
    """Manager for integration configurations."""
    
    def __init__(self):
        """Initialize configuration manager."""
        self.settings = get_settings()
        self._configs: Dict[str, IntegrationConfig] = {}
        self._cipher_suite = self._get_cipher_suite()
        self._load_configs()
    
    def _get_cipher_suite(self) -> Fernet:
        """Get cipher suite for encryption."""
        key = os.getenv('INTEGRATION_ENCRYPTION_KEY')
        if not key:
            # Generate a new key for development
            key = Fernet.generate_key()
            logger.warning("No encryption key found, generated new one. Set INTEGRATION_ENCRYPTION_KEY in production.")
        
        if isinstance(key, str):
            key = key.encode()
        
        return Fernet(key)
    
    def _encrypt_value(self, value: str) -> str:
        """Encrypt a configuration value."""
        return self._cipher_suite.encrypt(value.encode()).decode()
    
    def _decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a configuration value."""
        return self._cipher_suite.decrypt(encrypted_value.encode()).decode()
    
    def _load_configs(self):
        """Load integration configurations from environment."""
        # Google Calendar Configuration
        if os.getenv('GOOGLE_CLIENT_ID') and os.getenv('GOOGLE_CLIENT_SECRET'):
            self._configs['google'] = IntegrationConfig(
                provider='google',
                enabled=True,
                credentials=IntegrationCredentials(
                    client_id=os.getenv('GOOGLE_CLIENT_ID'),
                    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
                    webhook_secret=os.getenv('GOOGLE_WEBHOOK_SECRET')
                ),
                scopes=[
                    'https://www.googleapis.com/auth/calendar',
                    'https://www.googleapis.com/auth/calendar.events',
                    'https://www.googleapis.com/auth/drive.file',
                    'https://www.googleapis.com/auth/userinfo.email'
                ],
                redirect_uri=f"{self.settings.base_url}/api/v1/integrations/google/callback",
                webhook_url=f"{self.settings.base_url}/api/v1/integrations/google/webhook"
            )
        
        # Microsoft Configuration
        if os.getenv('MICROSOFT_CLIENT_ID') and os.getenv('MICROSOFT_CLIENT_SECRET'):
            self._configs['microsoft'] = IntegrationConfig(
                provider='microsoft',
                enabled=True,
                credentials=IntegrationCredentials(
                    client_id=os.getenv('MICROSOFT_CLIENT_ID'),
                    client_secret=os.getenv('MICROSOFT_CLIENT_SECRET'),
                    webhook_secret=os.getenv('MICROSOFT_WEBHOOK_SECRET')
                ),
                scopes=[
                    'https://graph.microsoft.com/calendars.readwrite',
                    'https://graph.microsoft.com/user.read',
                    'https://graph.microsoft.com/files.readwrite',
                    'https://graph.microsoft.com/sites.readwrite.all'
                ],
                redirect_uri=f"{self.settings.base_url}/api/v1/integrations/microsoft/callback",
                webhook_url=f"{self.settings.base_url}/api/v1/integrations/microsoft/webhook"
            )
        
        # Slack Configuration
        if os.getenv('SLACK_CLIENT_ID') and os.getenv('SLACK_CLIENT_SECRET'):
            self._configs['slack'] = IntegrationConfig(
                provider='slack',
                enabled=True,
                credentials=IntegrationCredentials(
                    client_id=os.getenv('SLACK_CLIENT_ID'),
                    client_secret=os.getenv('SLACK_CLIENT_SECRET'),
                    webhook_secret=os.getenv('SLACK_WEBHOOK_SECRET')
                ),
                scopes=[
                    'channels:read',
                    'chat:write',
                    'users:read',
                    'team:read'
                ],
                redirect_uri=f"{self.settings.base_url}/api/v1/integrations/slack/callback",
                webhook_url=f"{self.settings.base_url}/api/v1/integrations/slack/webhook"
            )
        
        # Zoom Configuration
        if os.getenv('ZOOM_CLIENT_ID') and os.getenv('ZOOM_CLIENT_SECRET'):
            self._configs['zoom'] = IntegrationConfig(
                provider='zoom',
                enabled=True,
                credentials=IntegrationCredentials(
                    client_id=os.getenv('ZOOM_CLIENT_ID'),
                    client_secret=os.getenv('ZOOM_CLIENT_SECRET'),
                    webhook_secret=os.getenv('ZOOM_WEBHOOK_SECRET')
                ),
                scopes=[
                    'meeting:write',
                    'user:read',
                    'webinar:write'
                ],
                redirect_uri=f"{self.settings.base_url}/api/v1/integrations/zoom/callback",
                webhook_url=f"{self.settings.base_url}/api/v1/integrations/zoom/webhook"
            )
        
        # Dropbox Configuration
        if os.getenv('DROPBOX_CLIENT_ID') and os.getenv('DROPBOX_CLIENT_SECRET'):
            self._configs['dropbox'] = IntegrationConfig(
                provider='dropbox',
                enabled=True,
                credentials=IntegrationCredentials(
                    client_id=os.getenv('DROPBOX_CLIENT_ID'),
                    client_secret=os.getenv('DROPBOX_CLIENT_SECRET')
                ),
                scopes=['files.content.write', 'files.content.read'],
                redirect_uri=f"{self.settings.base_url}/api/v1/integrations/dropbox/callback"
            )
        
        # GitHub Configuration
        if os.getenv('GITHUB_CLIENT_ID') and os.getenv('GITHUB_CLIENT_SECRET'):
            self._configs['github'] = IntegrationConfig(
                provider='github',
                enabled=True,
                credentials=IntegrationCredentials(
                    client_id=os.getenv('GITHUB_CLIENT_ID'),
                    client_secret=os.getenv('GITHUB_CLIENT_SECRET'),
                    webhook_secret=os.getenv('GITHUB_WEBHOOK_SECRET')
                ),
                scopes=['repo', 'user'],
                redirect_uri=f"{self.settings.base_url}/api/v1/integrations/github/callback",
                webhook_url=f"{self.settings.base_url}/api/v1/integrations/github/webhook"
            )
        
        # Notion Configuration
        if os.getenv('NOTION_CLIENT_ID') and os.getenv('NOTION_CLIENT_SECRET'):
            self._configs['notion'] = IntegrationConfig(
                provider='notion',
                enabled=True,
                credentials=IntegrationCredentials(
                    client_id=os.getenv('NOTION_CLIENT_ID'),
                    client_secret=os.getenv('NOTION_CLIENT_SECRET')
                ),
                scopes=[],  # Notion doesn't use scopes
                redirect_uri=f"{self.settings.base_url}/api/v1/integrations/notion/callback"
            )
        
        # Jira Configuration
        if os.getenv('JIRA_CLIENT_ID') and os.getenv('JIRA_CLIENT_SECRET'):
            self._configs['jira'] = IntegrationConfig(
                provider='jira',
                enabled=True,
                credentials=IntegrationCredentials(
                    client_id=os.getenv('JIRA_CLIENT_ID'),
                    client_secret=os.getenv('JIRA_CLIENT_SECRET'),
                    webhook_secret=os.getenv('JIRA_WEBHOOK_SECRET')
                ),
                scopes=['read:jira-work', 'write:jira-work'],
                redirect_uri=f"{self.settings.base_url}/api/v1/integrations/jira/callback",
                webhook_url=f"{self.settings.base_url}/api/v1/integrations/jira/webhook"
            )
        
        # Analytics Services (API Key based)
        if os.getenv('MIXPANEL_API_KEY'):
            self._configs['mixpanel'] = IntegrationConfig(
                provider='mixpanel',
                enabled=True,
                credentials=IntegrationCredentials(
                    client_id='',  # Not used
                    client_secret='',  # Not used
                    api_key=os.getenv('MIXPANEL_API_KEY')
                ),
                scopes=[],
                redirect_uri=''
            )
        
        if os.getenv('SENTRY_DSN'):
            self._configs['sentry'] = IntegrationConfig(
                provider='sentry',
                enabled=True,
                credentials=IntegrationCredentials(
                    client_id='',
                    client_secret='',
                    api_key=os.getenv('SENTRY_DSN')
                ),
                scopes=[],
                redirect_uri=''
            )
        
        if os.getenv('DATADOG_API_KEY'):
            self._configs['datadog'] = IntegrationConfig(
                provider='datadog',
                enabled=True,
                credentials=IntegrationCredentials(
                    client_id='',
                    client_secret='',
                    api_key=os.getenv('DATADOG_API_KEY')
                ),
                scopes=[],
                redirect_uri=''
            )
        
        logger.info(f"Loaded {len(self._configs)} integration configurations")
    
    def get_config(self, provider: str) -> Optional[IntegrationConfig]:
        """Get configuration for a provider."""
        return self._configs.get(provider.lower())
    
    def get_all_configs(self) -> Dict[str, IntegrationConfig]:
        """Get all integration configurations."""
        return self._configs.copy()
    
    def is_enabled(self, provider: str) -> bool:
        """Check if a provider is enabled."""
        config = self.get_config(provider)
        return config is not None and config.enabled
    
    def get_enabled_providers(self) -> list[str]:
        """Get list of enabled providers."""
        return [
            provider for provider, config in self._configs.items()
            if config.enabled
        ]
    
    def update_config(self, provider: str, config: IntegrationConfig):
        """Update configuration for a provider."""
        self._configs[provider.lower()] = config
        logger.info(f"Updated configuration for {provider}")
    
    def disable_provider(self, provider: str):
        """Disable a provider."""
        config = self.get_config(provider)
        if config:
            config.enabled = False
            logger.info(f"Disabled provider: {provider}")
    
    def enable_provider(self, provider: str):
        """Enable a provider."""
        config = self.get_config(provider)
        if config:
            config.enabled = True
            logger.info(f"Enabled provider: {provider}")
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check for configuration manager."""
        return {
            "total_configs": len(self._configs),
            "enabled_providers": self.get_enabled_providers(),
            "encryption_enabled": bool(self._cipher_suite),
            "configs": {
                provider: {
                    "enabled": config.enabled,
                    "has_credentials": bool(config.credentials.client_id or config.credentials.api_key),
                    "scopes": len(config.scopes),
                    "webhook_configured": bool(config.webhook_url)
                }
                for provider, config in self._configs.items()
            }
        }


# Global configuration manager instance
config_manager = IntegrationConfigManager()