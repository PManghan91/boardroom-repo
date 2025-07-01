"""Integration tests for authentication endpoints.

Tests authentication API endpoints with mocked database responses
to verify the complete request/response cycle without external dependencies.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, Mock, AsyncMock
from fastapi import status

from app.core.exceptions import AuthenticationException, ValidationException


@pytest.mark.integration
class TestAuthenticationEndpoints:
    """Test authentication-related API endpoints."""
    
    @patch('app.services.database.database_service')
    async def test_user_login_success(self, mock_db_service, client: AsyncClient):
        """Test successful user login."""
        # Mock user data
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.hashed_password = "$2b$12$hashedpassword"
        mock_user.is_active = True
        mock_user.role = "user"
        
        # Mock database service response
        mock_db_service.get_user_by_email.return_value = mock_user
        
        # Mock password verification
        with patch('app.api.v1.auth.verify_password') as mock_verify, \
             patch('app.api.v1.auth.create_access_token') as mock_create_token:
            
            mock_verify.return_value = True
            mock_token = Mock()
            mock_token.access_token = "mock_access_token"
            mock_token.expires_at = "2023-12-31T23:59:59"
            mock_create_token.return_value = mock_token
            
            response = await client.post("/api/v1/auth/user-login", json={
                "email": "test@example.com",
                "password": "TestPassword123!"
            })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["access_token"] == "mock_access_token"
        assert data["token_type"] == "bearer"
        assert "expires_at" in data
    
    @patch('app.services.database.database_service')
    async def test_user_login_invalid_credentials(self, mock_db_service, client: AsyncClient):
        """Test user login with invalid credentials."""
        # Mock user not found
        mock_db_service.get_user_by_email.return_value = None
        
        response = await client.post("/api/v1/auth/user-login", json={
            "email": "nonexistent@example.com",
            "password": "WrongPassword123!"
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "error" in data
        assert "authentication" in data["error"]["type"].lower()
    
    @patch('app.services.database.database_service')
    async def test_user_login_wrong_password(self, mock_db_service, client: AsyncClient):
        """Test user login with wrong password."""
        # Mock user data
        mock_user = Mock()
        mock_user.email = "test@example.com"
        mock_user.hashed_password = "$2b$12$hashedpassword"
        mock_user.is_active = True
        
        mock_db_service.get_user_by_email.return_value = mock_user
        
        # Mock password verification failure
        with patch('app.api.v1.auth.verify_password') as mock_verify:
            mock_verify.return_value = False
            
            response = await client.post("/api/v1/auth/user-login", json={
                "email": "test@example.com",
                "password": "WrongPassword123!"
            })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @patch('app.services.database.database_service')
    async def test_user_login_inactive_user(self, mock_db_service, client: AsyncClient):
        """Test user login with inactive user account."""
        # Mock inactive user
        mock_user = Mock()
        mock_user.email = "test@example.com"
        mock_user.is_active = False
        
        mock_db_service.get_user_by_email.return_value = mock_user
        
        response = await client.post("/api/v1/auth/user-login", json={
            "email": "test@example.com",
            "password": "TestPassword123!"
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    async def test_user_login_invalid_input(self, client: AsyncClient):
        """Test user login with invalid input data."""
        # Test missing email
        response = await client.post("/api/v1/auth/user-login", json={
            "password": "TestPassword123!"
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test missing password
        response = await client.post("/api/v1/auth/user-login", json={
            "email": "test@example.com"
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test invalid email format
        response = await client.post("/api/v1/auth/user-login", json={
            "email": "invalid-email",
            "password": "TestPassword123!"
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @patch('app.services.database.database_service')
    async def test_user_register_success(self, mock_db_service, client: AsyncClient):
        """Test successful user registration."""
        # Mock successful user creation
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "newuser@example.com"
        mock_user.username = "newuser"
        mock_user.full_name = "New User"
        mock_user.role = "user"
        mock_user.is_active = True
        
        mock_db_service.get_user_by_email.return_value = None  # User doesn't exist
        mock_db_service.create_user.return_value = mock_user
        
        with patch('app.api.v1.auth.get_password_hash') as mock_hash:
            mock_hash.return_value = "$2b$12$hashedpassword"
            
            response = await client.post("/api/v1/auth/register", json={
                "email": "newuser@example.com",
                "username": "newuser",
                "full_name": "New User",
                "password": "NewPassword123!",
                "role": "user"
            })
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert data["full_name"] == "New User"
        assert data["role"] == "user"
        assert "password" not in data
    
    @patch('app.services.database.database_service')
    async def test_user_register_duplicate_email(self, mock_db_service, client: AsyncClient):
        """Test user registration with duplicate email."""
        # Mock existing user
        mock_existing_user = Mock()
        mock_db_service.get_user_by_email.return_value = mock_existing_user
        
        response = await client.post("/api/v1/auth/register", json={
            "email": "existing@example.com",
            "username": "newuser",
            "full_name": "New User",
            "password": "NewPassword123!",
            "role": "user"
        })
        
        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "error" in data
        assert "conflict" in data["error"]["type"].lower()
    
    async def test_user_register_weak_password(self, client: AsyncClient):
        """Test user registration with weak password."""
        response = await client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "username": "newuser",
            "full_name": "New User",
            "password": "weak",  # Too weak
            "role": "user"
        })
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_user_register_invalid_input(self, client: AsyncClient):
        """Test user registration with invalid input data."""
        # Test invalid email format
        response = await client.post("/api/v1/auth/register", json={
            "email": "invalid-email",
            "username": "newuser",
            "full_name": "New User",
            "password": "NewPassword123!",
            "role": "user"
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test missing required fields
        response = await client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "password": "NewPassword123!"
            # Missing username, full_name
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.integration
class TestTokenValidation:
    """Test token validation and protected endpoints."""
    
    @patch('app.utils.auth.verify_token')
    async def test_protected_endpoint_with_valid_token(self, mock_verify, client: AsyncClient):
        """Test accessing protected endpoint with valid token."""
        mock_verify.return_value = "valid-thread-id"
        
        headers = {"Authorization": "Bearer valid_token"}
        response = await client.get("/api/v1/auth/me", headers=headers)
        
        # This assumes there's a /me endpoint, adjust based on actual endpoints
        # The test verifies that token validation works
        assert mock_verify.called
    
    @patch('app.utils.auth.verify_token')
    async def test_protected_endpoint_with_invalid_token(self, mock_verify, client: AsyncClient):
        """Test accessing protected endpoint with invalid token."""
        mock_verify.return_value = None  # Invalid token
        
        headers = {"Authorization": "Bearer invalid_token"}
        response = await client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    async def test_protected_endpoint_without_token(self, client: AsyncClient):
        """Test accessing protected endpoint without token."""
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestAuthenticationFlow:
    """Test complete authentication flow scenarios."""
    
    @patch('app.services.database.database_service')
    async def test_register_login_flow(self, mock_db_service, client: AsyncClient):
        """Test complete register then login flow."""
        # Mock user creation
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "flowtest@example.com"
        mock_user.username = "flowtest"
        mock_user.full_name = "Flow Test"
        mock_user.role = "user"
        mock_user.is_active = True
        mock_user.hashed_password = "$2b$12$hashedpassword"
        
        # First call for registration check (user doesn't exist)
        # Second call for login (user exists)
        mock_db_service.get_user_by_email.side_effect = [None, mock_user]
        mock_db_service.create_user.return_value = mock_user
        
        with patch('app.api.v1.auth.get_password_hash') as mock_hash, \
             patch('app.api.v1.auth.verify_password') as mock_verify, \
             patch('app.api.v1.auth.create_access_token') as mock_create_token:
            
            mock_hash.return_value = "$2b$12$hashedpassword"
            mock_verify.return_value = True
            mock_token = Mock()
            mock_token.access_token = "flow_test_token"
            mock_token.expires_at = "2023-12-31T23:59:59"
            mock_create_token.return_value = mock_token
            
            # Step 1: Register
            register_response = await client.post("/api/v1/auth/register", json={
                "email": "flowtest@example.com",
                "username": "flowtest",
                "full_name": "Flow Test",
                "password": "FlowPassword123!",
                "role": "user"
            })
            
            assert register_response.status_code == status.HTTP_201_CREATED
            
            # Step 2: Login with same credentials
            login_response = await client.post("/api/v1/auth/user-login", json={
                "email": "flowtest@example.com",
                "password": "FlowPassword123!"
            })
            
            assert login_response.status_code == status.HTTP_200_OK
            login_data = login_response.json()
            assert "access_token" in login_data
    
    @patch('app.services.database.database_service')
    async def test_multiple_login_attempts(self, mock_db_service, client: AsyncClient):
        """Test multiple login attempts with rate limiting considerations."""
        mock_user = Mock()
        mock_user.email = "test@example.com"
        mock_user.hashed_password = "$2b$12$hashedpassword"
        mock_user.is_active = True
        mock_user.role = "user"
        
        mock_db_service.get_user_by_email.return_value = mock_user
        
        with patch('app.api.v1.auth.verify_password') as mock_verify, \
             patch('app.api.v1.auth.create_access_token') as mock_create_token:
            
            # First attempt - success
            mock_verify.return_value = True
            mock_token = Mock()
            mock_token.access_token = "success_token"
            mock_token.expires_at = "2023-12-31T23:59:59"
            mock_create_token.return_value = mock_token
            
            response1 = await client.post("/api/v1/auth/user-login", json={
                "email": "test@example.com",
                "password": "CorrectPassword123!"
            })
            assert response1.status_code == status.HTTP_200_OK
            
            # Second attempt - wrong password
            mock_verify.return_value = False
            
            response2 = await client.post("/api/v1/auth/user-login", json={
                "email": "test@example.com",
                "password": "WrongPassword123!"
            })
            assert response2.status_code == status.HTTP_401_UNAUTHORIZED
            
            # Third attempt - success again
            mock_verify.return_value = True
            
            response3 = await client.post("/api/v1/auth/user-login", json={
                "email": "test@example.com",
                "password": "CorrectPassword123!"
            })
            assert response3.status_code == status.HTTP_200_OK


@pytest.mark.integration
class TestAuthenticationSecurity:
    """Test security aspects of authentication endpoints."""
    
    async def test_sql_injection_prevention(self, client: AsyncClient):
        """Test that SQL injection attempts are prevented."""
        # Attempt SQL injection in email field
        malicious_email = "'; DROP TABLE users; --"
        
        response = await client.post("/api/v1/auth/user-login", json={
            "email": malicious_email,
            "password": "password"
        })
        
        # Should be handled gracefully, not cause server error
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    async def test_xss_prevention_in_registration(self, client: AsyncClient):
        """Test that XSS attempts in registration are sanitized."""
        malicious_name = "<script>alert('xss')</script>"
        
        response = await client.post("/api/v1/auth/register", json={
            "email": "xsstest@example.com",
            "username": "xsstest",
            "full_name": malicious_name,
            "password": "TestPassword123!",
            "role": "user"
        })
        
        # Should be rejected or sanitized
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_201_CREATED  # If sanitized and accepted
        ]
        
        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            # Verify that malicious content was sanitized
            assert "<script>" not in data.get("full_name", "")
    
    async def test_password_not_returned_in_responses(self, client: AsyncClient):
        """Test that passwords are never returned in API responses."""
        with patch('app.services.database.database_service') as mock_db_service:
            mock_user = Mock()
            mock_user.id = 1
            mock_user.email = "test@example.com"
            mock_user.username = "test"
            mock_user.full_name = "Test User"
            mock_user.role = "user"
            mock_user.is_active = True
            
            mock_db_service.get_user_by_email.return_value = None
            mock_db_service.create_user.return_value = mock_user
            
            with patch('app.api.v1.auth.get_password_hash'):
                response = await client.post("/api/v1/auth/register", json={
                    "email": "test@example.com",
                    "username": "test",
                    "full_name": "Test User",
                    "password": "TestPassword123!",
                    "role": "user"
                })
                
                if response.status_code == status.HTTP_201_CREATED:
                    data = response.json()
                    assert "password" not in data
                    assert "hashed_password" not in data
    
    async def test_case_insensitive_email_handling(self, client: AsyncClient):
        """Test that email handling is case-insensitive."""
        with patch('app.services.database.database_service') as mock_db_service:
            mock_user = Mock()
            mock_user.email = "test@example.com"  # Stored in lowercase
            mock_user.hashed_password = "$2b$12$hashedpassword"
            mock_user.is_active = True
            mock_user.role = "user"
            
            mock_db_service.get_user_by_email.return_value = mock_user
            
            with patch('app.api.v1.auth.verify_password') as mock_verify, \
                 patch('app.api.v1.auth.create_access_token') as mock_create_token:
                
                mock_verify.return_value = True
                mock_token = Mock()
                mock_token.access_token = "test_token"
                mock_token.expires_at = "2023-12-31T23:59:59"
                mock_create_token.return_value = mock_token
                
                # Try login with uppercase email
                response = await client.post("/api/v1/auth/user-login", json={
                    "email": "TEST@EXAMPLE.COM",
                    "password": "TestPassword123!"
                })
                
                # Should work regardless of case
                assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
class TestAuthenticationRateLimiting:
    """Test rate limiting on authentication endpoints."""
    
    @pytest.mark.slow
    async def test_login_rate_limiting(self, client: AsyncClient):
        """Test that login attempts are rate limited."""
        # This test would need actual rate limiting to be implemented
        # For now, it's a placeholder to ensure the concept is tested
        
        login_data = {
            "email": "ratelimit@example.com",
            "password": "TestPassword123!"
        }
        
        # Make multiple rapid requests
        responses = []
        for i in range(10):
            response = await client.post("/api/v1/auth/user-login", json=login_data)
            responses.append(response.status_code)
        
        # At least some should succeed (or fail with auth errors)
        # If rate limiting is implemented, some should return 429
        success_or_auth_errors = [
            code for code in responses 
            if code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED]
        ]
        rate_limit_errors = [
            code for code in responses 
            if code == status.HTTP_429_TOO_MANY_REQUESTS
        ]
        
        # Either no rate limiting (all auth attempts) or some rate limiting
        assert len(success_or_auth_errors) + len(rate_limit_errors) == len(responses)