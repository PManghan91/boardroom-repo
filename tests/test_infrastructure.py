"""Test the testing infrastructure itself to ensure everything is working correctly.

This module contains tests that verify the testing setup is working properly,
including database connections, fixtures, and async testing capabilities.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.unit
async def test_database_session_fixture(db_session: AsyncSession):
    """Test that the database session fixture is working correctly."""
    assert db_session is not None
    assert hasattr(db_session, 'execute')
    assert hasattr(db_session, 'commit')
    assert hasattr(db_session, 'rollback')


@pytest.mark.unit
async def test_async_client_fixture(client: AsyncClient):
    """Test that the async client fixture is working correctly."""
    assert client is not None
    assert hasattr(client, 'get')
    assert hasattr(client, 'post')
    assert hasattr(client, 'put')
    assert hasattr(client, 'delete')


@pytest.mark.integration
async def test_health_check_endpoint(client: AsyncClient):
    """Test the health check endpoint to verify API connectivity."""
    response = await client.get("/health")
    assert response.status_code in [200, 503]  # 503 if DB connection fails
    
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "environment" in data
    assert "components" in data
    assert data["environment"] == "test"


@pytest.mark.integration
async def test_root_endpoint(client: AsyncClient):
    """Test the root endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "status" in data
    assert data["status"] == "healthy"


@pytest.mark.unit
def test_sample_user_data_fixture(sample_user_data):
    """Test that the sample user data fixture generates valid data."""
    assert "email" in sample_user_data
    assert "username" in sample_user_data
    assert "full_name" in sample_user_data
    assert "password" in sample_user_data
    assert "role" in sample_user_data
    
    assert "@" in sample_user_data["email"]
    assert len(sample_user_data["password"]) >= 8
    assert sample_user_data["role"] in ["user", "admin"]


@pytest.mark.unit
def test_sample_boardroom_data_fixture(sample_boardroom_data):
    """Test that the sample boardroom data fixture generates valid data."""
    assert "name" in sample_boardroom_data
    assert "description" in sample_boardroom_data
    assert "is_active" in sample_boardroom_data
    assert "settings" in sample_boardroom_data
    
    settings = sample_boardroom_data["settings"]
    assert "max_participants" in settings
    assert "voting_enabled" in settings
    assert "public" in settings
    assert isinstance(settings["max_participants"], int)
    assert isinstance(settings["voting_enabled"], bool)


@pytest.mark.unit
def test_user_factory_fixture(user_factory):
    """Test that the user factory fixture creates valid user data."""
    user1 = user_factory()
    user2 = user_factory(email="custom@test.com", role="admin")
    
    # Test default user
    assert "id" in user1
    assert "email" in user1
    assert "role" in user1
    assert user1["role"] == "user"
    
    # Test custom user
    assert user2["email"] == "custom@test.com"
    assert user2["role"] == "admin"
    
    # Ensure different users have different IDs
    assert user1["id"] != user2["id"]


@pytest.mark.unit
def test_boardroom_factory_fixture(boardroom_factory):
    """Test that the boardroom factory fixture creates valid boardroom data."""
    boardroom1 = boardroom_factory()
    boardroom2 = boardroom_factory(name="Custom Boardroom", is_active=False)
    
    # Test default boardroom
    assert "id" in boardroom1
    assert "name" in boardroom1
    assert "settings" in boardroom1
    assert boardroom1["is_active"] is True
    
    # Test custom boardroom
    assert boardroom2["name"] == "Custom Boardroom"
    assert boardroom2["is_active"] is False
    
    # Ensure different boardrooms have different IDs
    assert boardroom1["id"] != boardroom2["id"]


@pytest.mark.unit
async def test_mock_langfuse_fixture(mock_langfuse):
    """Test that the Langfuse mock is working correctly."""
    assert mock_langfuse is not None
    assert hasattr(mock_langfuse, 'trace')
    assert hasattr(mock_langfuse, 'generation')


@pytest.mark.unit
async def test_mock_llm_service_fixture(mock_llm_service):
    """Test that the LLM service mock is working correctly."""
    assert mock_llm_service is not None
    assert hasattr(mock_llm_service, 'generate_response')
    
    response = mock_llm_service.generate_response("test prompt")
    assert response == "Mocked LLM response"


@pytest.mark.unit
def test_realistic_test_scenario_fixture(realistic_test_scenario):
    """Test that the realistic test scenario fixture creates valid data."""
    scenario = realistic_test_scenario(num_users=3, num_boardrooms=2, num_sessions=2)
    
    assert "users" in scenario
    assert "boardrooms" in scenario
    assert "sessions" in scenario
    assert "threads" in scenario
    
    assert len(scenario["users"]) == 3
    assert len(scenario["boardrooms"]) == 2
    assert len(scenario["sessions"]) == 2
    
    # Verify relationships
    first_boardroom = scenario["boardrooms"][0]
    first_user = scenario["users"][0]
    assert first_boardroom["owner_id"] == first_user["id"]


@pytest.mark.slow
async def test_performance_fixture_availability(performance_user_count, load_test_duration):
    """Test that performance testing fixtures are available."""
    assert isinstance(performance_user_count, int)
    assert performance_user_count > 0
    assert isinstance(load_test_duration, int)
    assert load_test_duration > 0


@pytest.mark.unit
def test_error_response_factory(error_response_factory):
    """Test that the error response factory creates valid error responses."""
    error = error_response_factory()
    
    assert "error" in error
    error_data = error["error"]
    
    assert "code" in error_data
    assert "message" in error_data
    assert "type" in error_data
    assert "timestamp" in error_data
    
    # Test custom error
    custom_error = error_response_factory(
        error_code="CUSTOM_ERROR",
        message="Custom error message",
        status_code=404
    )
    
    assert custom_error["error"]["code"] == 404
    assert custom_error["error"]["message"] == "Custom error message"
    assert custom_error["error"]["type"] == "custom_error"