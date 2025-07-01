"""Unit tests for authentication utilities.

Tests JWT token creation, validation, and auth helper functions
without requiring external dependencies.
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import patch, Mock
from jose import jwt, JWTError

from app.utils.auth import create_access_token, verify_token
from app.core.config import get_settings


@pytest.mark.unit
class TestCreateAccessToken:
    """Test JWT access token creation."""
    
    def test_create_access_token_with_default_expiry(self):
        """Test creating access token with default expiration."""
        thread_id = "test-thread-123"
        
        with patch('app.utils.auth.settings') as mock_settings:
            mock_settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS = 7
            mock_settings.JWT_SECRET_KEY = "test-secret"
            mock_settings.JWT_ALGORITHM = "HS256"
            
            token = create_access_token(thread_id)
            
            assert token.access_token is not None
            assert isinstance(token.access_token, str)
            assert token.expires_at > datetime.now(UTC)
            
            # Verify token can be decoded
            payload = jwt.decode(
                token.access_token, 
                mock_settings.JWT_SECRET_KEY, 
                algorithms=[mock_settings.JWT_ALGORITHM]
            )
            assert payload["sub"] == thread_id
            assert "exp" in payload
            assert "iat" in payload
            assert "jti" in payload

    def test_create_access_token_with_custom_expiry(self):
        """Test creating access token with custom expiration."""
        thread_id = "test-thread-456"
        custom_expiry = timedelta(hours=2)
        
        with patch('app.utils.auth.settings') as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test-secret"
            mock_settings.JWT_ALGORITHM = "HS256"
            
            token = create_access_token(thread_id, expires_delta=custom_expiry)
            
            expected_expiry = datetime.now(UTC) + custom_expiry
            assert abs((token.expires_at - expected_expiry).total_seconds()) < 10

    def test_create_access_token_includes_sanitized_jti(self):
        """Test that JTI is included and sanitized."""
        thread_id = "test-thread-<script>alert('xss')</script>"
        
        with patch('app.utils.auth.settings') as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test-secret"
            mock_settings.JWT_ALGORITHM = "HS256"
            mock_settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS = 1
            
            token = create_access_token(thread_id)
            
            payload = jwt.decode(
                token.access_token, 
                mock_settings.JWT_SECRET_KEY, 
                algorithms=[mock_settings.JWT_ALGORITHM]
            )
            
            # JTI should be sanitized
            assert "jti" in payload
            assert "<script>" not in payload["jti"]
            assert "&lt;script&gt;" in payload["jti"]


@pytest.mark.unit
class TestVerifyToken:
    """Test JWT token verification."""
    
    def test_verify_token_valid(self):
        """Test verifying a valid token."""
        thread_id = "test-thread-789"
        
        with patch('app.utils.auth.settings') as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test-secret"
            mock_settings.JWT_ALGORITHM = "HS256"
            
            # Create a token
            token = create_access_token(thread_id)
            
            # Verify the token
            result = verify_token(token.access_token)
            assert result == thread_id

    def test_verify_token_invalid_format(self):
        """Test verifying token with invalid format."""
        invalid_tokens = [
            "",
            None,
            "invalid",
            "not.enough.parts",
            "too.many.parts.here.invalid",
            "invalid-format-no-dots"
        ]
        
        for invalid_token in invalid_tokens:
            with pytest.raises(ValueError, match="Token must be a non-empty string|Token format is invalid"):
                verify_token(invalid_token)

    def test_verify_token_invalid_signature(self):
        """Test verifying token with invalid signature."""
        with patch('app.utils.auth.settings') as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test-secret"
            mock_settings.JWT_ALGORITHM = "HS256"
            
            # Create token with one secret
            token = create_access_token("test-thread")
            
            # Try to verify with different secret
            mock_settings.JWT_SECRET_KEY = "different-secret"
            
            result = verify_token(token.access_token)
            assert result is None

    def test_verify_token_expired(self):
        """Test verifying an expired token."""
        thread_id = "test-thread-expired"
        
        with patch('app.utils.auth.settings') as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test-secret"
            mock_settings.JWT_ALGORITHM = "HS256"
            
            # Create an expired token by mocking datetime
            past_time = datetime.now(UTC) - timedelta(hours=1)
            
            with patch('app.utils.auth.datetime') as mock_datetime:
                mock_datetime.now.return_value = past_time
                mock_datetime.UTC = UTC
                
                token = create_access_token(thread_id, expires_delta=timedelta(minutes=1))
            
            # Try to verify the expired token
            result = verify_token(token.access_token)
            assert result is None

    def test_verify_token_missing_subject(self):
        """Test verifying token without subject claim."""
        with patch('app.utils.auth.settings') as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test-secret"
            mock_settings.JWT_ALGORITHM = "HS256"
            
            # Create token without 'sub' claim
            payload = {
                "exp": datetime.now(UTC) + timedelta(hours=1),
                "iat": datetime.now(UTC)
            }
            
            token = jwt.encode(payload, mock_settings.JWT_SECRET_KEY, algorithm=mock_settings.JWT_ALGORITHM)
            
            result = verify_token(token)
            assert result is None

    def test_verify_token_malformed_jwt(self):
        """Test verifying malformed JWT token."""
        # Valid format but invalid JWT content
        malformed_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid.content"
        
        result = verify_token(malformed_token)
        assert result is None

    def test_verify_token_type_validation(self):
        """Test token type validation."""
        with pytest.raises(ValueError, match="Token must be a non-empty string"):
            verify_token(123)
        
        with pytest.raises(ValueError, match="Token must be a non-empty string"):
            verify_token([])
        
        with pytest.raises(ValueError, match="Token must be a non-empty string"):
            verify_token({})


@pytest.mark.unit
class TestAuthUtilsLogging:
    """Test auth utilities logging behavior."""
    
    @patch('app.utils.auth.logger')
    def test_create_access_token_logs_creation(self, mock_logger):
        """Test that token creation is logged."""
        thread_id = "test-thread-logging"
        
        with patch('app.utils.auth.settings') as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test-secret"
            mock_settings.JWT_ALGORITHM = "HS256"
            mock_settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS = 1
            
            create_access_token(thread_id)
            
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "token_created"
            assert call_args[1]["thread_id"] == thread_id

    @patch('app.utils.auth.logger')
    def test_verify_token_logs_verification(self, mock_logger):
        """Test that successful token verification is logged."""
        thread_id = "test-thread-verify-log"
        
        with patch('app.utils.auth.settings') as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test-secret"
            mock_settings.JWT_ALGORITHM = "HS256"
            
            token = create_access_token(thread_id)
            
            # Clear previous calls
            mock_logger.reset_mock()
            
            verify_token(token.access_token)
            
            # Should log verification
            mock_logger.info.assert_called_once_with("token_verified", thread_id=thread_id)

    @patch('app.utils.auth.logger')
    def test_verify_token_logs_invalid_format(self, mock_logger):
        """Test that invalid format is logged."""
        with pytest.raises(ValueError):
            verify_token("invalid-format")
        
        mock_logger.warning.assert_called_with("token_suspicious_format")

    @patch('app.utils.auth.logger')
    def test_verify_token_logs_jwt_error(self, mock_logger):
        """Test that JWT errors are logged."""
        with patch('app.utils.auth.settings') as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test-secret"
            mock_settings.JWT_ALGORITHM = "HS256"
            
            # Create a token then change the secret
            token = create_access_token("test")
            mock_settings.JWT_SECRET_KEY = "different-secret"
            
            # Clear previous calls
            mock_logger.reset_mock()
            
            result = verify_token(token.access_token)
            
            assert result is None
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert call_args[0][0] == "token_verification_failed"


@pytest.mark.unit
class TestAuthUtilsIntegration:
    """Integration tests for auth utilities."""
    
    def test_token_roundtrip(self):
        """Test creating and verifying token roundtrip."""
        thread_id = "test-roundtrip-12345"
        
        with patch('app.utils.auth.settings') as mock_settings:
            mock_settings.JWT_SECRET_KEY = "consistent-secret-key"
            mock_settings.JWT_ALGORITHM = "HS256"
            mock_settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS = 1
            
            # Create token
            token = create_access_token(thread_id)
            
            # Verify token
            result = verify_token(token.access_token)
            
            assert result == thread_id

    def test_different_thread_ids(self):
        """Test with various thread ID formats."""
        thread_ids = [
            "simple-thread-id",
            "thread_with_underscores",
            "thread-with-numbers-123",
            "UPPERCASE-THREAD-ID",
            "MixedCaseThreadId",
            "thread.with.dots",
            "very-long-thread-id-with-many-characters-and-segments"
        ]
        
        with patch('app.utils.auth.settings') as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test-secret"
            mock_settings.JWT_ALGORITHM = "HS256"
            mock_settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS = 1
            
            for thread_id in thread_ids:
                token = create_access_token(thread_id)
                result = verify_token(token.access_token)
                assert result == thread_id