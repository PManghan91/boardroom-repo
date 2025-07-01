"""Pytest configuration and shared fixtures for the Boardroom AI test suite.

This module provides the core testing infrastructure including:
- Test database configuration and lifecycle management
- Async test client setup for FastAPI testing
- Mock configurations for external services
- Shared test data fixtures
"""

import asyncio
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, patch
from httpx import AsyncClient, ASGITransport
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

# Import application components
from app.main import app
from app.core.config import Settings, get_settings
from app.models.database import get_session
from app.services.database import database_service

# Initialize Faker for test data generation
fake = Faker()


class TestSettings(Settings):
    """Test-specific settings that override the base settings."""
    
    def __init__(self):
        super().__init__()
        # Override with test-specific configurations
        self.ENVIRONMENT = "test"
        self.DEBUG = True
        self.LOG_LEVEL = "ERROR"  # Reduce log noise during tests
        
        # Test database configuration
        self.database_url = os.getenv(
            "TEST_DATABASE_URL", 
            "postgresql+asyncpg://test_user:test_password@localhost:5432/test_boardroom_db"
        )
        self.database_url_sync = self.database_url.replace("postgresql+asyncpg://", "postgresql://")
        
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
def override_get_settings(test_settings: TestSettings):
    """Override the get_settings dependency with test settings."""
    with patch("app.core.config.get_settings", return_value=test_settings):
        with patch("app.core.config.settings", test_settings):
            yield test_settings


@pytest_asyncio.fixture(scope="session")
async def test_engine(test_settings: TestSettings):
    """Create a test database engine."""
    engine = create_async_engine(
        test_settings.database_url,
        echo=False,  # Set to True for SQL debugging
        pool_pre_ping=True,
        pool_recycle=300,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def create_test_database(test_engine):
    """Create all database tables for testing."""
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(test_engine, create_test_database) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for testing with automatic rollback."""
    async_session_maker = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client for testing API endpoints."""
    
    # Override the database dependency
    async def override_get_session():
        yield db_session
    
    app.dependency_overrides[get_session] = override_get_session
    
    # Create the test client
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver"
    ) as ac:
        yield ac
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def mock_langfuse():
    """Mock Langfuse for testing."""
    with patch("app.main.langfuse") as mock_lf:
        mock_lf.trace.return_value.update.return_value = None
        mock_lf.generation.return_value.end.return_value = None
        yield mock_lf


@pytest.fixture
def mock_llm_service():
    """Mock LLM service calls for testing."""
    with patch("app.services.llm.LLMService") as mock_service:
        mock_instance = Mock()
        mock_instance.generate_response.return_value = "Mocked LLM response"
        mock_service.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_database_service():
    """Mock database service for unit tests."""
    with patch("app.services.database.database_service") as mock_service:
        mock_service.health_check.return_value = True
        yield mock_service


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


# Authentication fixtures
@pytest.fixture
def auth_headers(sample_user_data):
    """Generate authentication headers for testing."""
    # This is a simplified version - in practice, you'd create a real JWT token
    return {
        "Authorization": f"Bearer test-token-{sample_user_data['email']}"
    }


@pytest.fixture
def admin_user_data():
    """Generate admin user data for testing."""
    return {
        "email": "admin@test.com",
        "username": "testadmin",
        "full_name": "Test Administrator",
        "password": "AdminPassword123!",
        "role": "admin"
    }


@pytest.fixture
def admin_auth_headers(admin_user_data):
    """Generate admin authentication headers for testing."""
    return {
        "Authorization": f"Bearer admin-token-{admin_user_data['email']}"
    }


# Async context managers for testing
@pytest_asyncio.fixture
async def logged_in_user(client: AsyncClient, sample_user_data, db_session: AsyncSession):
    """Create and authenticate a test user."""
    # Create user
    response = await client.post("/api/v1/auth/register", json=sample_user_data)
    assert response.status_code == 201
    user_data = response.json()
    
    # Login to get token
    login_data = {
        "email": sample_user_data["email"],
        "password": sample_user_data["password"]
    }
    response = await client.post("/api/v1/auth/user-login", json=login_data)
    assert response.status_code == 200
    token_data = response.json()
    
    return {
        "user": user_data,
        "token": token_data["access_token"],
        "headers": {"Authorization": f"Bearer {token_data['access_token']}"}
    }


# Performance and load testing fixtures
@pytest.fixture
def performance_user_count():
    """Number of users for performance tests."""
    return int(os.getenv("PERFORMANCE_USER_COUNT", "10"))


@pytest.fixture
def load_test_duration():
    """Duration for load tests in seconds."""
    return int(os.getenv("LOAD_TEST_DURATION", "30"))


# Cleanup fixtures
@pytest.fixture(autouse=True)
async def cleanup_test_data(db_session: AsyncSession):
    """Automatically clean up test data after each test."""
    yield
    # Cleanup is handled by the session rollback in db_session fixture


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