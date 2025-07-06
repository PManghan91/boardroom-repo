"""Productivity tool integrations for Notion, Confluence, Jira, Trello, and Asana."""

from datetime import datetime
from typing import Dict, List, Optional, Any
import httpx
from pydantic import BaseModel

from app.core.logging import logger
from .base import IntegrationService, IntegrationConfig, OAuthToken
from .oauth import OAuthManager


class Task(BaseModel):
    """Task model for productivity tools."""
    id: str
    title: str
    description: Optional[str] = None
    status: str
    assignee: Optional[str] = None
    due_date: Optional[datetime] = None
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()
    labels: List[str] = []
    project_id: Optional[str] = None


class Project(BaseModel):
    """Project model for productivity tools."""
    id: str
    name: str
    description: Optional[str] = None
    status: str = "active"
    created_at: datetime = datetime.utcnow()
    members: List[str] = []


class ProductivityService(IntegrationService):
    """Base productivity service."""
    
    async def create_task(self, token: OAuthToken, task: Task) -> str:
        """Create a task."""
        raise NotImplementedError
    
    async def update_task(self, token: OAuthToken, task_id: str, updates: Dict[str, Any]) -> bool:
        """Update a task."""
        raise NotImplementedError
    
    async def list_tasks(self, token: OAuthToken, project_id: Optional[str] = None) -> List[Task]:
        """List tasks."""
        raise NotImplementedError
    
    async def create_project(self, token: OAuthToken, project: Project) -> str:
        """Create a project."""
        raise NotImplementedError


class NotionService(ProductivityService):
    """Notion integration service."""
    
    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.oauth_manager = OAuthManager(config)
        self.base_url = "https://api.notion.com/v1"
        self.auth_url = "https://api.notion.com/v1/oauth/authorize"
        self.token_url = "https://api.notion.com/v1/oauth/token"
    
    async def authorize_url(self, state: str) -> str:
        """Generate Notion OAuth authorization URL."""
        return await self.oauth_manager.build_authorization_url(self.auth_url, state, self.config.scopes)
    
    async def exchange_code(self, code: str, state: str) -> OAuthToken:
        """Exchange authorization code for access token."""
        return await self.oauth_manager.exchange_code_for_token(self.token_url, code)
    
    async def refresh_token(self, refresh_token: str) -> OAuthToken:
        """Notion doesn't support token refresh."""
        return OAuthToken(access_token=refresh_token, token_type="Bearer")
    
    async def revoke_token(self, token: str) -> bool:
        """Notion doesn't have token revocation."""
        return True
    
    async def test_connection(self, token: OAuthToken) -> bool:
        """Test Notion connection."""
        try:
            await self._make_request("GET", f"{self.base_url}/users/me", token)
            return True
        except Exception as e:
            logger.error(f"Notion connection test failed: {e}")
            return False


class JiraService(ProductivityService):
    """Jira integration service."""
    
    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.oauth_manager = OAuthManager(config)
        self.base_url = "https://api.atlassian.com/ex/jira"
        self.auth_url = "https://auth.atlassian.com/authorize"
        self.token_url = "https://auth.atlassian.com/oauth/token"


# Global productivity manager
productivity_manager = type('ProductivityManager', (), {
    'services': {},
    'register_service': lambda self, provider, service: setattr(self, provider, service)
})()