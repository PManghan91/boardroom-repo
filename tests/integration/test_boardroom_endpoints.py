"""Integration tests for boardroom endpoints.

Tests boardroom API endpoints with mocked database responses
to verify the complete request/response cycle without external dependencies.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, Mock, AsyncMock
from fastapi import status

from app.core.exceptions import ResourceNotFoundException, AuthorizationException


@pytest.mark.integration
class TestBoardroomEndpoints:
    """Test boardroom-related API endpoints."""
    
    @patch('app.services.database.database_service')
    @patch('app.utils.auth.verify_token')
    async def test_create_boardroom_success(self, mock_verify, mock_db_service, client: AsyncClient):
        """Test successful boardroom creation."""
        # Mock authentication
        mock_verify.return_value = "user-thread-123"
        
        # Mock user lookup
        mock_user = Mock()
        mock_user.id = 1
        mock_user.role = "admin"
        mock_db_service.get_user.return_value = mock_user
        
        # Mock boardroom creation
        mock_boardroom = Mock()
        mock_boardroom.id = "board-123"
        mock_boardroom.name = "Test Boardroom"
        mock_boardroom.description = "A test boardroom"
        mock_boardroom.owner_id = 1
        mock_boardroom.is_active = True
        mock_boardroom.settings = {"max_participants": 10}
        mock_db_service.create_boardroom.return_value = mock_boardroom
        
        headers = {"Authorization": "Bearer valid_token"}
        response = await client.post("/api/v1/boardroom/", json={
            "name": "Test Boardroom",
            "description": "A test boardroom",
            "settings": {"max_participants": 10}
        }, headers=headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Test Boardroom"
        assert data["description"] == "A test boardroom"
        assert data["owner_id"] == 1
        assert data["is_active"] is True
    
    @patch('app.utils.auth.verify_token')
    async def test_create_boardroom_unauthorized(self, mock_verify, client: AsyncClient):
        """Test boardroom creation without authentication."""
        mock_verify.return_value = None  # Invalid token
        
        headers = {"Authorization": "Bearer invalid_token"}
        response = await client.post("/api/v1/boardroom/", json={
            "name": "Test Boardroom",
            "description": "A test boardroom"
        }, headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    async def test_create_boardroom_missing_token(self, client: AsyncClient):
        """Test boardroom creation without token."""
        response = await client.post("/api/v1/boardroom/", json={
            "name": "Test Boardroom",
            "description": "A test boardroom"
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    async def test_create_boardroom_invalid_input(self, client: AsyncClient):
        """Test boardroom creation with invalid input."""
        with patch('app.utils.auth.verify_token') as mock_verify:
            mock_verify.return_value = "user-thread-123"
            
            headers = {"Authorization": "Bearer valid_token"}
            
            # Test missing name
            response = await client.post("/api/v1/boardroom/", json={
                "description": "A test boardroom"
            }, headers=headers)
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            
            # Test empty name
            response = await client.post("/api/v1/boardroom/", json={
                "name": "",
                "description": "A test boardroom"
            }, headers=headers)
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @patch('app.services.database.database_service')
    @patch('app.utils.auth.verify_token')
    async def test_get_boardroom_success(self, mock_verify, mock_db_service, client: AsyncClient):
        """Test successful boardroom retrieval."""
        mock_verify.return_value = "user-thread-123"
        
        # Mock boardroom data
        mock_boardroom = Mock()
        mock_boardroom.id = "board-123"
        mock_boardroom.name = "Test Boardroom"
        mock_boardroom.description = "A test boardroom"
        mock_boardroom.owner_id = 1
        mock_boardroom.is_active = True
        mock_boardroom.settings = {"max_participants": 10}
        mock_boardroom.created_at = "2023-01-01T00:00:00"
        
        mock_db_service.get_boardroom.return_value = mock_boardroom
        
        headers = {"Authorization": "Bearer valid_token"}
        response = await client.get("/api/v1/boardroom/board-123", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "board-123"
        assert data["name"] == "Test Boardroom"
        assert data["description"] == "A test boardroom"
    
    @patch('app.services.database.database_service')
    @patch('app.utils.auth.verify_token')
    async def test_get_boardroom_not_found(self, mock_verify, mock_db_service, client: AsyncClient):
        """Test boardroom retrieval when boardroom doesn't exist."""
        mock_verify.return_value = "user-thread-123"
        mock_db_service.get_boardroom.return_value = None
        
        headers = {"Authorization": "Bearer valid_token"}
        response = await client.get("/api/v1/boardroom/nonexistent", headers=headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert "not found" in data["error"]["message"].lower()
    
    @patch('app.services.database.database_service')
    @patch('app.utils.auth.verify_token')
    async def test_list_boardrooms_success(self, mock_verify, mock_db_service, client: AsyncClient):
        """Test successful boardroom listing."""
        mock_verify.return_value = "user-thread-123"
        
        # Mock user
        mock_user = Mock()
        mock_user.id = 1
        mock_db_service.get_user.return_value = mock_user
        
        # Mock boardrooms list
        mock_boardrooms = [
            Mock(id="board-1", name="Boardroom 1", owner_id=1, is_active=True),
            Mock(id="board-2", name="Boardroom 2", owner_id=1, is_active=True),
        ]
        mock_db_service.get_user_boardrooms.return_value = mock_boardrooms
        
        headers = {"Authorization": "Bearer valid_token"}
        response = await client.get("/api/v1/boardroom/", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "board-1"
        assert data[1]["id"] == "board-2"
    
    @patch('app.services.database.database_service')
    @patch('app.utils.auth.verify_token')
    async def test_update_boardroom_success(self, mock_verify, mock_db_service, client: AsyncClient):
        """Test successful boardroom update."""
        mock_verify.return_value = "user-thread-123"
        
        # Mock user
        mock_user = Mock()
        mock_user.id = 1
        mock_db_service.get_user.return_value = mock_user
        
        # Mock existing boardroom
        mock_boardroom = Mock()
        mock_boardroom.id = "board-123"
        mock_boardroom.name = "Old Name"
        mock_boardroom.description = "Old description"
        mock_boardroom.owner_id = 1
        mock_boardroom.is_active = True
        
        mock_db_service.get_boardroom.return_value = mock_boardroom
        mock_db_service.update_boardroom.return_value = mock_boardroom
        
        headers = {"Authorization": "Bearer valid_token"}
        response = await client.put("/api/v1/boardroom/board-123", json={
            "name": "Updated Name",
            "description": "Updated description"
        }, headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "board-123"
    
    @patch('app.services.database.database_service')
    @patch('app.utils.auth.verify_token')
    async def test_update_boardroom_not_owner(self, mock_verify, mock_db_service, client: AsyncClient):
        """Test boardroom update by non-owner."""
        mock_verify.return_value = "user-thread-123"
        
        # Mock user (not owner)
        mock_user = Mock()
        mock_user.id = 2
        mock_user.role = "user"
        mock_db_service.get_user.return_value = mock_user
        
        # Mock boardroom owned by different user
        mock_boardroom = Mock()
        mock_boardroom.id = "board-123"
        mock_boardroom.owner_id = 1  # Different owner
        mock_db_service.get_boardroom.return_value = mock_boardroom
        
        headers = {"Authorization": "Bearer valid_token"}
        response = await client.put("/api/v1/boardroom/board-123", json={
            "name": "Updated Name"
        }, headers=headers)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @patch('app.services.database.database_service')
    @patch('app.utils.auth.verify_token')
    async def test_delete_boardroom_success(self, mock_verify, mock_db_service, client: AsyncClient):
        """Test successful boardroom deletion."""
        mock_verify.return_value = "user-thread-123"
        
        # Mock user (owner)
        mock_user = Mock()
        mock_user.id = 1
        mock_db_service.get_user.return_value = mock_user
        
        # Mock boardroom
        mock_boardroom = Mock()
        mock_boardroom.id = "board-123"
        mock_boardroom.owner_id = 1
        mock_db_service.get_boardroom.return_value = mock_boardroom
        mock_db_service.delete_boardroom.return_value = True
        
        headers = {"Authorization": "Bearer valid_token"}
        response = await client.delete("/api/v1/boardroom/board-123", headers=headers)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
    
    @patch('app.services.database.database_service')
    @patch('app.utils.auth.verify_token')
    async def test_delete_boardroom_not_owner(self, mock_verify, mock_db_service, client: AsyncClient):
        """Test boardroom deletion by non-owner."""
        mock_verify.return_value = "user-thread-123"
        
        # Mock user (not owner)
        mock_user = Mock()
        mock_user.id = 2
        mock_user.role = "user"
        mock_db_service.get_user.return_value = mock_user
        
        # Mock boardroom owned by different user
        mock_boardroom = Mock()
        mock_boardroom.id = "board-123"
        mock_boardroom.owner_id = 1
        mock_db_service.get_boardroom.return_value = mock_boardroom
        
        headers = {"Authorization": "Bearer valid_token"}
        response = await client.delete("/api/v1/boardroom/board-123", headers=headers)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.integration
class TestBoardroomSessionEndpoints:
    """Test boardroom session-related endpoints."""
    
    @patch('app.services.database.database_service')
    @patch('app.utils.auth.verify_token')
    async def test_create_session_success(self, mock_verify, mock_db_service, client: AsyncClient):
        """Test successful session creation."""
        mock_verify.return_value = "user-thread-123"
        
        # Mock user
        mock_user = Mock()
        mock_user.id = 1
        mock_db_service.get_user.return_value = mock_user
        
        # Mock boardroom
        mock_boardroom = Mock()
        mock_boardroom.id = "board-123"
        mock_boardroom.owner_id = 1
        mock_boardroom.is_active = True
        mock_db_service.get_boardroom.return_value = mock_boardroom
        
        # Mock session creation
        mock_session = Mock()
        mock_session.id = "session-456"
        mock_session.boardroom_id = "board-123"
        mock_session.title = "Test Session"
        mock_session.status = "active"
        mock_db_service.create_session.return_value = mock_session
        
        headers = {"Authorization": "Bearer valid_token"}
        response = await client.post("/api/v1/boardroom/board-123/sessions", json={
            "title": "Test Session",
            "description": "A test session",
            "session_type": "discussion"
        }, headers=headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == "Test Session"
        assert data["boardroom_id"] == "board-123"
        assert data["status"] == "active"
    
    @patch('app.services.database.database_service')
    @patch('app.utils.auth.verify_token')
    async def test_get_session_success(self, mock_verify, mock_db_service, client: AsyncClient):
        """Test successful session retrieval."""
        mock_verify.return_value = "user-thread-123"
        
        # Mock session
        mock_session = Mock()
        mock_session.id = "session-456"
        mock_session.boardroom_id = "board-123"
        mock_session.title = "Test Session"
        mock_session.status = "active"
        mock_session.owner_id = 1
        mock_db_service.get_session.return_value = mock_session
        
        headers = {"Authorization": "Bearer valid_token"}
        response = await client.get("/api/v1/boardroom/board-123/sessions/session-456", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "session-456"
        assert data["title"] == "Test Session"
    
    @patch('app.services.database.database_service')
    @patch('app.utils.auth.verify_token')
    async def test_list_sessions_success(self, mock_verify, mock_db_service, client: AsyncClient):
        """Test successful session listing."""
        mock_verify.return_value = "user-thread-123"
        
        # Mock boardroom access check
        mock_boardroom = Mock()
        mock_boardroom.id = "board-123"
        mock_boardroom.is_active = True
        mock_db_service.get_boardroom.return_value = mock_boardroom
        
        # Mock sessions
        mock_sessions = [
            Mock(id="session-1", title="Session 1", boardroom_id="board-123"),
            Mock(id="session-2", title="Session 2", boardroom_id="board-123"),
        ]
        mock_db_service.get_boardroom_sessions.return_value = mock_sessions
        
        headers = {"Authorization": "Bearer valid_token"}
        response = await client.get("/api/v1/boardroom/board-123/sessions", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "session-1"
        assert data[1]["id"] == "session-2"
    
    @patch('app.services.database.database_service')
    @patch('app.utils.auth.verify_token')
    async def test_end_session_success(self, mock_verify, mock_db_service, client: AsyncClient):
        """Test successful session ending."""
        mock_verify.return_value = "user-thread-123"
        
        # Mock user
        mock_user = Mock()
        mock_user.id = 1
        mock_db_service.get_user.return_value = mock_user
        
        # Mock session
        mock_session = Mock()
        mock_session.id = "session-456"
        mock_session.owner_id = 1
        mock_session.status = "active"
        mock_db_service.get_session.return_value = mock_session
        mock_db_service.update_session_status.return_value = mock_session
        
        headers = {"Authorization": "Bearer valid_token"}
        response = await client.patch("/api/v1/boardroom/board-123/sessions/session-456/end", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
class TestBoardroomPermissions:
    """Test boardroom permission and access control."""
    
    @patch('app.services.database.database_service')
    @patch('app.utils.auth.verify_token')
    async def test_admin_can_access_any_boardroom(self, mock_verify, mock_db_service, client: AsyncClient):
        """Test that admin users can access any boardroom."""
        mock_verify.return_value = "admin-thread-123"
        
        # Mock admin user
        mock_user = Mock()
        mock_user.id = 999
        mock_user.role = "admin"
        mock_db_service.get_user.return_value = mock_user
        
        # Mock boardroom owned by different user
        mock_boardroom = Mock()
        mock_boardroom.id = "board-123"
        mock_boardroom.owner_id = 1  # Different owner
        mock_boardroom.name = "Test Boardroom"
        mock_db_service.get_boardroom.return_value = mock_boardroom
        
        headers = {"Authorization": "Bearer admin_token"}
        response = await client.get("/api/v1/boardroom/board-123", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
    
    @patch('app.services.database.database_service')
    @patch('app.utils.auth.verify_token')
    async def test_user_cannot_access_private_boardroom(self, mock_verify, mock_db_service, client: AsyncClient):
        """Test that regular users cannot access private boardrooms they don't own."""
        mock_verify.return_value = "user-thread-123"
        
        # Mock regular user
        mock_user = Mock()
        mock_user.id = 2
        mock_user.role = "user"
        mock_db_service.get_user.return_value = mock_user
        
        # Mock private boardroom owned by different user
        mock_boardroom = Mock()
        mock_boardroom.id = "board-123"
        mock_boardroom.owner_id = 1
        mock_boardroom.settings = {"public": False}
        mock_db_service.get_boardroom.return_value = mock_boardroom
        
        headers = {"Authorization": "Bearer user_token"}
        response = await client.get("/api/v1/boardroom/board-123", headers=headers)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @patch('app.services.database.database_service')
    @patch('app.utils.auth.verify_token')
    async def test_user_can_access_public_boardroom(self, mock_verify, mock_db_service, client: AsyncClient):
        """Test that users can access public boardrooms."""
        mock_verify.return_value = "user-thread-123"
        
        # Mock regular user
        mock_user = Mock()
        mock_user.id = 2
        mock_user.role = "user"
        mock_db_service.get_user.return_value = mock_user
        
        # Mock public boardroom owned by different user
        mock_boardroom = Mock()
        mock_boardroom.id = "board-123"
        mock_boardroom.owner_id = 1
        mock_boardroom.name = "Public Boardroom"
        mock_boardroom.settings = {"public": True}
        mock_db_service.get_boardroom.return_value = mock_boardroom
        
        headers = {"Authorization": "Bearer user_token"}
        response = await client.get("/api/v1/boardroom/board-123", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
class TestBoardroomValidation:
    """Test input validation for boardroom endpoints."""
    
    @patch('app.utils.auth.verify_token')
    async def test_boardroom_name_validation(self, mock_verify, client: AsyncClient):
        """Test boardroom name validation."""
        mock_verify.return_value = "user-thread-123"
        
        headers = {"Authorization": "Bearer valid_token"}
        
        # Test very long name
        long_name = "a" * 300
        response = await client.post("/api/v1/boardroom/", json={
            "name": long_name,
            "description": "Test description"
        }, headers=headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test special characters in name
        response = await client.post("/api/v1/boardroom/", json={
            "name": "<script>alert('xss')</script>",
            "description": "Test description"
        }, headers=headers)
        # Should either reject or sanitize
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_201_CREATED
        ]
    
    @patch('app.utils.auth.verify_token')
    async def test_boardroom_settings_validation(self, mock_verify, client: AsyncClient):
        """Test boardroom settings validation."""
        mock_verify.return_value = "user-thread-123"
        
        headers = {"Authorization": "Bearer valid_token"}
        
        # Test invalid max_participants
        response = await client.post("/api/v1/boardroom/", json={
            "name": "Test Boardroom",
            "description": "Test description",
            "settings": {
                "max_participants": -1  # Invalid
            }
        }, headers=headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test invalid settings type
        response = await client.post("/api/v1/boardroom/", json={
            "name": "Test Boardroom",
            "description": "Test description",
            "settings": "invalid_settings"  # Should be object
        }, headers=headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.integration  
class TestBoardroomErrorHandling:
    """Test error handling for boardroom endpoints."""
    
    @patch('app.services.database.database_service')
    @patch('app.utils.auth.verify_token')
    async def test_database_error_handling(self, mock_verify, mock_db_service, client: AsyncClient):
        """Test handling of database errors."""
        mock_verify.return_value = "user-thread-123"
        
        # Mock database error
        mock_db_service.create_boardroom.side_effect = Exception("Database connection failed")
        
        headers = {"Authorization": "Bearer valid_token"}
        response = await client.post("/api/v1/boardroom/", json={
            "name": "Test Boardroom",
            "description": "Test description"
        }, headers=headers)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "error" in data
    
    @patch('app.services.database.database_service')
    @patch('app.utils.auth.verify_token')
    async def test_concurrent_access_handling(self, mock_verify, mock_db_service, client: AsyncClient):
        """Test handling of concurrent access scenarios."""
        mock_verify.return_value = "user-thread-123"
        
        # Mock scenario where boardroom is deleted between check and access
        mock_db_service.get_boardroom.side_effect = [
            Mock(id="board-123", name="Test"),  # First call succeeds
            None  # Second call returns None (deleted)
        ]
        
        headers = {"Authorization": "Bearer valid_token"}
        
        # First request should work
        response1 = await client.get("/api/v1/boardroom/board-123", headers=headers)
        assert response1.status_code == status.HTTP_200_OK
        
        # Second request should handle missing boardroom
        response2 = await client.get("/api/v1/boardroom/board-123", headers=headers)
        assert response2.status_code == status.HTTP_404_NOT_FOUND