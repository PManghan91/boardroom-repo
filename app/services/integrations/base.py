"""Base integration service with OAuth 2.0 support and error handling."""

import asyncio
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import json
import httpx
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import logger
from app.core.exceptions import APIError


class IntegrationStatus(str, Enum):
    """Integration connection status."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    PENDING = "pending"
    EXPIRED = "expired"


class IntegrationError(APIError):
    """Base exception for integration errors."""
    pass


class IntegrationConfig(BaseModel):
    """Configuration for integration services."""
    provider: str
    client_id: str
    client_secret: str
    scopes: List[str] = Field(default_factory=list)
    redirect_uri: str
    webhook_url: Optional[str] = None
    rate_limit: int = 100
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    enabled: bool = True


class OAuthToken(BaseModel):
    """OAuth token model."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None
    scope: Optional[str] = None


class IntegrationConnection(BaseModel):
    """Integration connection model."""
    id: str
    user_id: int
    provider: str
    status: IntegrationStatus
    token: Optional[OAuthToken] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_sync: Optional[datetime] = None
    error_message: Optional[str] = None


class IntegrationService(ABC):
    """Base class for all integration services."""

    def __init__(self, config: IntegrationConfig):
        """Initialize integration service."""
        self.config = config
        self.settings = get_settings()
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.timeout),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
        self._rate_limiter = {}
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()

    @abstractmethod
    async def authorize_url(self, state: str) -> str:
        """Generate OAuth authorization URL."""
        pass

    @abstractmethod
    async def exchange_code(self, code: str, state: str) -> OAuthToken:
        """Exchange authorization code for access token."""
        pass

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> OAuthToken:
        """Refresh an expired access token."""
        pass

    @abstractmethod
    async def revoke_token(self, token: str) -> bool:
        """Revoke an access token."""
        pass

    @abstractmethod
    async def test_connection(self, token: OAuthToken) -> bool:
        """Test if the connection is valid."""
        pass

    async def _make_request(
        self,
        method: str,
        url: str,
        token: OAuthToken,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make authenticated HTTP request with rate limiting and retries."""
        await self._check_rate_limit()
        
        # Prepare headers
        request_headers = {
            "Authorization": f"{token.token_type} {token.access_token}",
            "Content-Type": "application/json",
            "User-Agent": "Boardroom-AI/1.0"
        }
        if headers:
            request_headers.update(headers)

        # Retry logic
        for attempt in range(self.config.retry_attempts):
            try:
                response = await self.client.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=request_headers
                )
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited by {self.config.provider}, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue
                
                # Handle token expiration
                if response.status_code == 401:
                    logger.warning(f"Token expired for {self.config.provider}")
                    raise IntegrationError(
                        message="Token expired",
                        status_code=401,
                        provider=self.config.provider
                    )
                
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                if attempt == self.config.retry_attempts - 1:
                    logger.error(f"Request failed after {self.config.retry_attempts} attempts: {e}")
                    raise IntegrationError(
                        message=f"Request failed: {e}",
                        status_code=e.response.status_code,
                        provider=self.config.provider
                    )
                await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                
            except Exception as e:
                logger.error(f"Request error: {e}")
                raise IntegrationError(
                    message=f"Request error: {e}",
                    status_code=500,
                    provider=self.config.provider
                )

    async def _check_rate_limit(self):
        """Check rate limit for the provider."""
        now = datetime.utcnow()
        provider_limits = self._rate_limiter.get(self.config.provider, [])
        
        # Clean old entries
        cutoff = now - timedelta(minutes=1)
        provider_limits = [ts for ts in provider_limits if ts > cutoff]
        
        # Check if we're within limits
        if len(provider_limits) >= self.config.rate_limit:
            sleep_time = 60 - (now - min(provider_limits)).total_seconds()
            if sleep_time > 0:
                logger.warning(f"Rate limit reached for {self.config.provider}, sleeping {sleep_time}s")
                await asyncio.sleep(sleep_time)
        
        # Add current request
        provider_limits.append(now)
        self._rate_limiter[self.config.provider] = provider_limits

    async def get_user_info(self, token: OAuthToken) -> Dict[str, Any]:
        """Get user information from the provider."""
        # This should be implemented by each provider
        return {}

    async def sync_data(self, token: OAuthToken, last_sync: Optional[datetime] = None) -> Dict[str, Any]:
        """Sync data from the provider."""
        # This should be implemented by each provider
        return {}

    async def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> bool:
        """Handle webhook payload from the provider."""
        # This should be implemented by each provider
        return True

    def _validate_webhook_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """Validate webhook signature."""
        import hmac
        import hashlib
        
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected_signature}", signature)

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for the integration."""
        return {
            "provider": self.config.provider,
            "status": "healthy" if self.config.enabled else "disabled",
            "rate_limit": self.config.rate_limit,
            "last_request": self._rate_limiter.get(self.config.provider, [])[-1:],
        }


class IntegrationManager:
    """Manager for all integration services."""

    def __init__(self):
        """Initialize integration manager."""
        self.services: Dict[str, IntegrationService] = {}
        self.connections: Dict[str, IntegrationConnection] = {}

    def register_service(self, provider: str, service: IntegrationService):
        """Register an integration service."""
        self.services[provider] = service
        logger.info(f"Registered integration service: {provider}")

    def get_service(self, provider: str) -> Optional[IntegrationService]:
        """Get integration service by provider."""
        return self.services.get(provider)

    async def create_connection(
        self,
        user_id: int,
        provider: str,
        token: OAuthToken,
        metadata: Dict[str, Any] = None
    ) -> IntegrationConnection:
        """Create a new integration connection."""
        connection = IntegrationConnection(
            id=f"{user_id}_{provider}",
            user_id=user_id,
            provider=provider,
            status=IntegrationStatus.CONNECTED,
            token=token,
            metadata=metadata or {}
        )
        
        # Test the connection
        service = self.get_service(provider)
        if service:
            try:
                is_valid = await service.test_connection(token)
                if not is_valid:
                    connection.status = IntegrationStatus.ERROR
                    connection.error_message = "Connection test failed"
            except Exception as e:
                connection.status = IntegrationStatus.ERROR
                connection.error_message = str(e)
        
        self.connections[connection.id] = connection
        logger.info(f"Created integration connection: {connection.id}")
        return connection

    async def get_connection(self, user_id: int, provider: str) -> Optional[IntegrationConnection]:
        """Get integration connection."""
        connection_id = f"{user_id}_{provider}"
        return self.connections.get(connection_id)

    async def refresh_connection(self, user_id: int, provider: str) -> Optional[IntegrationConnection]:
        """Refresh an integration connection."""
        connection = await self.get_connection(user_id, provider)
        if not connection or not connection.token or not connection.token.refresh_token:
            return None
        
        service = self.get_service(provider)
        if not service:
            return None
        
        try:
            new_token = await service.refresh_token(connection.token.refresh_token)
            connection.token = new_token
            connection.status = IntegrationStatus.CONNECTED
            connection.updated_at = datetime.utcnow()
            connection.error_message = None
            logger.info(f"Refreshed integration connection: {connection.id}")
            return connection
        except Exception as e:
            connection.status = IntegrationStatus.ERROR
            connection.error_message = str(e)
            logger.error(f"Failed to refresh connection {connection.id}: {e}")
            return connection

    async def revoke_connection(self, user_id: int, provider: str) -> bool:
        """Revoke an integration connection."""
        connection = await self.get_connection(user_id, provider)
        if not connection:
            return False
        
        service = self.get_service(provider)
        if service and connection.token:
            try:
                await service.revoke_token(connection.token.access_token)
            except Exception as e:
                logger.warning(f"Failed to revoke token for {connection.id}: {e}")
        
        del self.connections[connection.id]
        logger.info(f"Revoked integration connection: {connection.id}")
        return True

    async def sync_all_connections(self, user_id: int) -> Dict[str, Any]:
        """Sync data for all user connections."""
        results = {}
        
        for connection_id, connection in self.connections.items():
            if connection.user_id != user_id:
                continue
                
            service = self.get_service(connection.provider)
            if not service or connection.status != IntegrationStatus.CONNECTED:
                continue
                
            try:
                sync_result = await service.sync_data(connection.token, connection.last_sync)
                connection.last_sync = datetime.utcnow()
                results[connection.provider] = sync_result
            except Exception as e:
                logger.error(f"Failed to sync {connection.provider} for user {user_id}: {e}")
                results[connection.provider] = {"error": str(e)}
        
        return results

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for all integration services."""
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
            "connections": len(self.connections),
            "active_connections": len([
                c for c in self.connections.values()
                if c.status == IntegrationStatus.CONNECTED
            ])
        }


# Global integration manager instance
integration_manager = IntegrationManager()