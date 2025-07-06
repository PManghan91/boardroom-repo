"""Document management integrations for Google Drive, Dropbox, SharePoint, and OneDrive."""

from datetime import datetime
from typing import Dict, List, Optional, Any
import httpx
from pydantic import BaseModel, Field

from app.core.logging import logger
from .base import IntegrationService, IntegrationConfig, OAuthToken, IntegrationError
from .oauth import OAuthManager


class Document(BaseModel):
    """Document model."""
    id: str
    name: str
    path: str
    size: int
    mime_type: str
    created_at: datetime
    modified_at: datetime
    owner: Optional[str] = None
    shared: bool = False
    download_url: Optional[str] = None
    edit_url: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)


class DocumentManagementService(IntegrationService):
    """Base document management service."""
    
    async def upload_file(self, token: OAuthToken, file_path: str, content: bytes, folder_id: Optional[str] = None) -> str:
        """Upload a file."""
        raise NotImplementedError
    
    async def download_file(self, token: OAuthToken, file_id: str) -> bytes:
        """Download a file."""
        raise NotImplementedError
    
    async def list_files(self, token: OAuthToken, folder_id: Optional[str] = None, limit: int = 100) -> List[Document]:
        """List files in a folder."""
        raise NotImplementedError
    
    async def create_folder(self, token: OAuthToken, name: str, parent_id: Optional[str] = None) -> str:
        """Create a folder."""
        raise NotImplementedError
    
    async def share_file(self, token: OAuthToken, file_id: str, emails: List[str], permission: str = "read") -> bool:
        """Share a file with users."""
        raise NotImplementedError


class GoogleDriveService(DocumentManagementService):
    """Google Drive integration service."""
    
    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.oauth_manager = OAuthManager(config)
        self.base_url = "https://www.googleapis.com/drive/v3"
        self.upload_url = "https://www.googleapis.com/upload/drive/v3"
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
    
    async def authorize_url(self, state: str) -> str:
        """Generate Google OAuth authorization URL."""
        return await self.oauth_manager.build_authorization_url(
            self.auth_url,
            state,
            self.config.scopes,
            {"access_type": "offline", "prompt": "consent"}
        )
    
    async def exchange_code(self, code: str, state: str) -> OAuthToken:
        """Exchange authorization code for access token."""
        return await self.oauth_manager.exchange_code_for_token(self.token_url, code)
    
    async def refresh_token(self, refresh_token: str) -> OAuthToken:
        """Refresh Google access token."""
        return await self.oauth_manager.refresh_access_token(self.token_url, refresh_token)
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke Google access token."""
        return await self.oauth_manager.revoke_token("https://oauth2.googleapis.com/revoke", token)
    
    async def test_connection(self, token: OAuthToken) -> bool:
        """Test Google Drive connection."""
        try:
            await self._make_request("GET", f"{self.base_url}/about", token, params={"fields": "user"})
            return True
        except Exception as e:
            logger.error(f"Google Drive connection test failed: {e}")
            return False


class DropboxService(DocumentManagementService):
    """Dropbox integration service."""
    
    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.oauth_manager = OAuthManager(config)
        self.base_url = "https://api.dropboxapi.com/2"
        self.content_url = "https://content.dropboxapi.com/2"
        self.auth_url = "https://www.dropbox.com/oauth2/authorize"
        self.token_url = "https://api.dropboxapi.com/oauth2/token"


class OneDriveService(DocumentManagementService):
    """Microsoft OneDrive integration service."""
    
    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.oauth_manager = OAuthManager(config)
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.auth_url = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        self.token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"


# Global document manager instance
document_manager = type('DocumentManager', (), {
    'services': {},
    'register_service': lambda self, provider, service: setattr(self, provider, service),
    'get_service': lambda self, provider: getattr(self, provider, None)
})()