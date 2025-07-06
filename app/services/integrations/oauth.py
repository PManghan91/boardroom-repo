"""OAuth 2.0 manager for handling authentication flows."""

import secrets
import hashlib
import base64
from typing import Dict, Optional
from urllib.parse import urlencode, urlparse, parse_qs
import httpx
from datetime import datetime, timedelta

from app.core.logging import logger
from .base import IntegrationError, OAuthToken, IntegrationConfig


class OAuthManager:
    """OAuth 2.0 manager for handling authentication flows."""

    def __init__(self, config: IntegrationConfig):
        """Initialize OAuth manager."""
        self.config = config
        self.client = httpx.AsyncClient(timeout=30.0)
        self._state_store: Dict[str, Dict] = {}

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()

    def generate_state(self, user_id: int) -> str:
        """Generate secure state parameter for OAuth flow."""
        state = secrets.token_urlsafe(32)
        self._state_store[state] = {
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "provider": self.config.provider
        }
        return state

    def validate_state(self, state: str, user_id: int) -> bool:
        """Validate state parameter."""
        if state not in self._state_store:
            return False
        
        stored_data = self._state_store[state]
        
        # Check if state has expired (10 minutes)
        if datetime.utcnow() - stored_data["created_at"] > timedelta(minutes=10):
            del self._state_store[state]
            return False
        
        # Check if user_id matches
        if stored_data["user_id"] != user_id:
            return False
        
        # Clean up used state
        del self._state_store[state]
        return True

    def generate_pkce_pair(self) -> tuple[str, str]:
        """Generate PKCE code verifier and challenge."""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')
        code_verifier = code_verifier.rstrip('=')
        
        code_challenge = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(code_challenge).decode('utf-8')
        code_challenge = code_challenge.rstrip('=')
        
        return code_verifier, code_challenge

    async def build_authorization_url(
        self,
        auth_url: str,
        state: str,
        scopes: Optional[list] = None,
        extra_params: Optional[dict] = None
    ) -> str:
        """Build OAuth authorization URL."""
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "state": state,
            "access_type": "offline",
        }
        
        if scopes or self.config.scopes:
            params["scope"] = " ".join(scopes or self.config.scopes)
        
        if extra_params:
            params.update(extra_params)
        
        return f"{auth_url}?{urlencode(params)}"

    async def exchange_code_for_token(
        self,
        token_url: str,
        code: str,
        code_verifier: Optional[str] = None,
        extra_params: Optional[dict] = None
    ) -> OAuthToken:
        """Exchange authorization code for access token."""
        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.config.redirect_uri,
        }
        
        if code_verifier:
            data["code_verifier"] = code_verifier
        
        if extra_params:
            data.update(extra_params)
        
        try:
            response = await self.client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            token_data = response.json()
            
            # Calculate expiration time
            expires_at = None
            if "expires_in" in token_data:
                expires_at = datetime.utcnow() + timedelta(seconds=int(token_data["expires_in"]))
            
            return OAuthToken(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_type=token_data.get("token_type", "Bearer"),
                expires_at=expires_at,
                scope=token_data.get("scope")
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to exchange code for token: {e.response.text}")
            raise IntegrationError(
                message="Failed to exchange authorization code",
                status_code=e.response.status_code,
                provider=self.config.provider
            )
        except Exception as e:
            logger.error(f"Token exchange error: {e}")
            raise IntegrationError(
                message=f"Token exchange error: {e}",
                status_code=500,
                provider=self.config.provider
            )

    async def refresh_access_token(
        self,
        token_url: str,
        refresh_token: str,
        extra_params: Optional[dict] = None
    ) -> OAuthToken:
        """Refresh access token using refresh token."""
        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        
        if extra_params:
            data.update(extra_params)
        
        try:
            response = await self.client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            token_data = response.json()
            
            # Calculate expiration time
            expires_at = None
            if "expires_in" in token_data:
                expires_at = datetime.utcnow() + timedelta(seconds=int(token_data["expires_in"]))
            
            return OAuthToken(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token", refresh_token),  # Keep old refresh token if not provided
                token_type=token_data.get("token_type", "Bearer"),
                expires_at=expires_at,
                scope=token_data.get("scope")
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to refresh token: {e.response.text}")
            raise IntegrationError(
                message="Failed to refresh access token",
                status_code=e.response.status_code,
                provider=self.config.provider
            )
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            raise IntegrationError(
                message=f"Token refresh error: {e}",
                status_code=500,
                provider=self.config.provider
            )

    async def revoke_token(
        self,
        revoke_url: str,
        token: str,
        token_type: str = "access_token"
    ) -> bool:
        """Revoke access or refresh token."""
        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "token": token,
            "token_type_hint": token_type,
        }
        
        try:
            response = await self.client.post(
                revoke_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to revoke token: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Token revoke error: {e}")
            return False

    def is_token_expired(self, token: OAuthToken) -> bool:
        """Check if token is expired."""
        if not token.expires_at:
            return False
        
        # Add 5 minute buffer
        return datetime.utcnow() + timedelta(minutes=5) >= token.expires_at

    async def introspect_token(
        self,
        introspect_url: str,
        token: str
    ) -> Dict:
        """Introspect token to get its status and metadata."""
        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "token": token,
        }
        
        try:
            response = await self.client.post(
                introspect_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to introspect token: {e.response.text}")
            raise IntegrationError(
                message="Failed to introspect token",
                status_code=e.response.status_code,
                provider=self.config.provider
            )
        except Exception as e:
            logger.error(f"Token introspection error: {e}")
            raise IntegrationError(
                message=f"Token introspection error: {e}",
                status_code=500,
                provider=self.config.provider
            )

    def cleanup_expired_states(self):
        """Clean up expired state parameters."""
        current_time = datetime.utcnow()
        expired_states = [
            state for state, data in self._state_store.items()
            if current_time - data["created_at"] > timedelta(minutes=10)
        ]
        
        for state in expired_states:
            del self._state_store[state]
        
        logger.info(f"Cleaned up {len(expired_states)} expired OAuth states")