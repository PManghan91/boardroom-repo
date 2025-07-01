"""Basic infrastructure tests that don't require database connectivity.

This module contains tests that verify the core testing setup is working
without requiring external dependencies like PostgreSQL.
"""

import pytest
from unittest.mock import Mock, patch


@pytest.mark.unit
def test_pytest_configuration():
    """Test that pytest is configured correctly."""
    import pytest
    assert pytest is not None
    assert hasattr(pytest, 'mark')
    assert hasattr(pytest, 'fixture')


@pytest.mark.unit
def test_faker_availability():
    """Test that Faker is available for test data generation."""
    from faker import Faker
    fake = Faker()
    assert fake is not None
    assert hasattr(fake, 'email')
    assert hasattr(fake, 'name')
    assert hasattr(fake, 'text')


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


@pytest.mark.unit
def test_testing_environment_variables():
    """Test that testing environment variables are set correctly."""
    import os
    # Test environment should be set
    env = os.getenv("APP_ENV")
    assert env == "test"


@pytest.mark.unit
def test_coverage_configuration():
    """Test that coverage configuration is working."""
    # This test just verifies that we can import the coverage module
    try:
        import coverage
        assert coverage is not None
    except ImportError:
        pytest.fail("Coverage module not available")


@pytest.mark.unit
async def test_async_test_support():
    """Test that async tests are supported."""
    # This is an async test to verify async support works
    assert True
    
    # Test asyncio functionality
    import asyncio
    await asyncio.sleep(0.001)  # Very short sleep to test async
    assert True


@pytest.mark.slow
def test_slow_marker():
    """Test that the slow marker is working."""
    # This test is marked as slow and should be skipped with -m "not slow"
    assert True


@pytest.mark.unit  
def test_mock_functionality():
    """Test that mocking functionality is available."""
    from unittest.mock import Mock, patch
    
    # Test Mock
    mock_obj = Mock()
    mock_obj.method.return_value = "mocked"
    assert mock_obj.method() == "mocked"
    
    # Test patch
    with patch('builtins.print') as mock_print:
        print("test")
        mock_print.assert_called_once_with("test")


@pytest.mark.unit
def test_httpx_availability():
    """Test that httpx is available for HTTP testing."""
    try:
        import httpx
        assert httpx is not None
        assert hasattr(httpx, 'AsyncClient')
    except ImportError:
        pytest.fail("httpx not available for testing")


@pytest.mark.unit
def test_test_settings_fixture(test_settings):
    """Test that test settings are configured correctly."""
    assert test_settings is not None
    assert test_settings.ENVIRONMENT == "test"
    assert test_settings.DEBUG is True
    assert test_settings.LOG_LEVEL == "ERROR"
    assert "test" in test_settings.database_url
    assert test_settings.JWT_SECRET_KEY == "test-secret-key-for-testing-only"