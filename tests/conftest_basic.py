"""Basic pytest configuration for testing without database dependencies.

This module provides core testing infrastructure that doesn't require
external dependencies like PostgreSQL, suitable for unit tests and
basic infrastructure verification.
"""

import asyncio
import os
import pytest
from typing import Generator
from unittest.mock import Mock, patch
from faker import Faker

# Initialize Faker for test data generation
fake = Faker()


class TestSettings:
    """Test-specific settings that don't require database connectivity."""
    
    def __init__(self):
        self.ENVIRONMENT = "test"
        self.DEBUG = True
        self.LOG_LEVEL = "ERROR"
        
        # Test database configuration (mock values)
        self.database_url = "postgresql+asyncpg://test_user:test_password@localhost:5432/test_boardroom_db"
        self.database_url_sync = "postgresql://test_user:test_password@localhost:5432/test_boardroom_db"
        
        # Disable external services for testing
        self.LANGFUSE_PUBLIC_KEY = "test-key"
        self.LANGFUSE_SECRET_KEY = "test-secret"
        self.LLM_API_KEY = "test-llm-key"
        
        # Test-friendly rate limits
        self.RATE_LIMIT_DEFAULT = ["1000 per day", "1000 per hour"]
        
        # JWT settings for testing
        self.JWT_SECRET_KEY = "test-secret-key-for-testing-only"
        self.JWT_ACCESS_TOKEN_EXPIRE_DAYS = 1


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> TestSettings:
    """Provide test-specific settings."""
    return TestSettings()


@pytest.fixture(scope="session", autouse=True)
def set_test_environment():
    """Set test environment variables."""
    os.environ["APP_ENV"] = "test"
    os.environ["LOG_LEVEL"] = "ERROR"
    os.environ["RATE_LIMIT_DEFAULT"] = "1000 per day,1000 per hour"
    yield
    # Cleanup if needed


# Test data fixtures
@pytest.fixture
def sample_user_data():
    """Generate sample user data for testing."""
    return {
        "email": fake.email(),
        "username": fake.user_name(),
        "full_name": fake.name(),
        "password": "TestPassword123!",
        "role": "user"
    }


@pytest.fixture
def sample_boardroom_data():
    """Generate sample boardroom data for testing."""
    return {
        "name": fake.company(),
        "description": fake.text(max_nb_chars=200),
        "is_active": True,
        "settings": {
            "max_participants": fake.random_int(min=2, max=20),
            "voting_enabled": fake.boolean(),
            "public": fake.boolean()
        }
    }


@pytest.fixture
def sample_session_data():
    """Generate sample session data for testing."""
    return {
        "title": fake.sentence(nb_words=4),
        "description": fake.text(max_nb_chars=300),
        "status": "active",
        "session_type": "discussion",
        "metadata": {
            "duration_minutes": fake.random_int(min=30, max=180),
            "participant_limit": fake.random_int(min=2, max=15)
        }
    }


@pytest.fixture
def sample_thread_data():
    """Generate sample thread data for testing."""
    return {
        "title": fake.sentence(nb_words=6),
        "content": fake.text(max_nb_chars=500),
        "thread_type": "discussion",
        "is_private": fake.boolean(),
        "metadata": {
            "tags": [fake.word() for _ in range(fake.random_int(min=1, max=5))],
            "priority": fake.random_element(elements=["low", "medium", "high"])
        }
    }


# Import and use data fixtures
from tests.fixtures.data_fixtures import *


# Performance testing fixtures
@pytest.fixture
def performance_user_count():
    """Number of users for performance tests."""
    return int(os.getenv("PERFORMANCE_USER_COUNT", "10"))


@pytest.fixture
def load_test_duration():
    """Duration for load tests in seconds."""
    return int(os.getenv("LOAD_TEST_DURATION", "30"))


# Pytest configuration hooks
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "asyncio: marks tests as async tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add async marker to async tests
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)