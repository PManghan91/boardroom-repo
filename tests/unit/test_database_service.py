"""Unit tests for database service.

Tests database operations with proper mocking to avoid PostgreSQL dependencies
while maintaining comprehensive coverage of business logic.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from contextlib import asynccontextmanager

from app.services.database import DatabaseService, database_service
from app.core.exceptions import DatabaseException


@pytest.mark.unit
class TestDatabaseServiceInitialization:
    """Test DatabaseService initialization and configuration."""
    
    def test_database_service_init(self):
        """Test DatabaseService initialization."""
        with patch('app.services.database.get_settings') as mock_settings:
            mock_settings.return_value = Mock()
            
            service = DatabaseService()
            
            assert service._engine is None
            assert service._session_factory is None
            assert service._initialized is False
            assert service._connection_retries == 3
            assert service._retry_delay == 1.0
    
    @patch('app.services.database.create_async_engine')
    @patch('app.services.database.async_sessionmaker')
    async def test_initialize_success(self, mock_sessionmaker, mock_create_engine):
        """Test successful database initialization."""
        # Setup mocks
        mock_engine = AsyncMock()
        mock_create_engine.return_value = mock_engine
        mock_session_factory = Mock()
        mock_sessionmaker.return_value = mock_session_factory
        
        # Mock test connection
        mock_conn = AsyncMock()
        mock_engine.begin.return_value.__aenter__.return_value = mock_conn
        
        with patch('app.services.database.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                DEBUG=False,
                ENVIRONMENT=Mock(value="development"),
                database_url="postgresql+asyncpg://test:test@localhost:5432/test"
            )
            
            service = DatabaseService()
            await service.initialize()
            
            assert service._initialized is True
            assert service._engine == mock_engine
            assert service._session_factory == mock_session_factory
            
            # Verify engine creation
            mock_create_engine.assert_called_once()
            
            # Verify session factory creation
            mock_sessionmaker.assert_called_once()
    
    @patch('app.services.database.create_async_engine')
    async def test_initialize_test_environment(self, mock_create_engine):
        """Test initialization in test environment."""
        mock_engine = AsyncMock()
        mock_create_engine.return_value = mock_engine
        
        # Mock test connection
        mock_conn = AsyncMock()
        mock_engine.begin.return_value.__aenter__.return_value = mock_conn
        
        with patch('app.services.database.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                DEBUG=True,
                ENVIRONMENT=Mock(value="test"),
                database_url="postgresql+asyncpg://test:test@localhost:5432/test"
            )
            
            service = DatabaseService()
            await service.initialize()
            
            # Check that NullPool is used for test environment
            call_args = mock_create_engine.call_args
            assert "poolclass" in call_args[1]
    
    @patch('app.services.database.create_async_engine')
    @patch('app.services.database.asyncio.sleep')
    async def test_initialize_with_retries(self, mock_sleep, mock_create_engine):
        """Test initialization with connection retries."""
        # First two attempts fail, third succeeds
        mock_engine = AsyncMock()
        mock_create_engine.side_effect = [
            Exception("Connection failed"),
            Exception("Connection failed"),
            mock_engine
        ]
        
        # Mock test connection for successful attempt
        mock_conn = AsyncMock()
        mock_engine.begin.return_value.__aenter__.return_value = mock_conn
        
        with patch('app.services.database.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                DEBUG=False,
                ENVIRONMENT=Mock(value="development"),
                database_url="postgresql+asyncpg://test:test@localhost:5432/test"
            )
            
            service = DatabaseService()
            await service.initialize()
            
            assert service._initialized is True
            assert mock_create_engine.call_count == 3
            assert mock_sleep.call_count == 2
    
    @patch('app.services.database.create_async_engine')
    async def test_initialize_max_retries_exceeded(self, mock_create_engine):
        """Test initialization when max retries are exceeded."""
        mock_create_engine.side_effect = Exception("Persistent connection failure")
        
        with patch('app.services.database.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                DEBUG=False,
                ENVIRONMENT=Mock(value="development"),
                database_url="postgresql+asyncpg://test:test@localhost:5432/test"
            )
            
            service = DatabaseService()
            
            with pytest.raises(Exception, match="Persistent connection failure"):
                await service.initialize()
            
            assert service._initialized is False
            assert mock_create_engine.call_count == 3
    
    async def test_initialize_idempotent(self):
        """Test that initialize is idempotent."""
        with patch('app.services.database.get_settings') as mock_settings:
            mock_settings.return_value = Mock()
            
            service = DatabaseService()
            service._initialized = True
            
            # Should return early without doing anything
            await service.initialize()
            
            # State should remain the same
            assert service._initialized is True


@pytest.mark.unit
class TestDatabaseServiceSessionManagement:
    """Test database session management."""
    
    @patch('app.services.database.get_settings')
    async def test_get_session_context_manager(self, mock_settings):
        """Test get_session context manager."""
        mock_settings.return_value = Mock()
        
        service = DatabaseService()
        service._initialized = True
        
        # Mock session factory and session
        mock_session = AsyncMock()
        mock_session_factory = Mock(return_value=mock_session)
        service._session_factory = mock_session_factory
        
        async with service.get_session() as session:
            assert session == mock_session
        
        # Verify session was closed
        mock_session.close.assert_called_once()
    
    @patch('app.services.database.get_settings')
    async def test_get_session_initializes_if_needed(self, mock_settings):
        """Test that get_session initializes service if needed."""
        mock_settings.return_value = Mock(
            DEBUG=False,
            ENVIRONMENT=Mock(value="test"),
            database_url="test://url"
        )
        
        service = DatabaseService()
        
        with patch.object(service, 'initialize') as mock_init:
            mock_session = AsyncMock()
            service._session_factory = Mock(return_value=mock_session)
            service._initialized = True  # Set after init mock setup
            
            async with service.get_session() as session:
                assert session == mock_session
            
            mock_init.assert_called_once()
    
    @patch('app.services.database.get_settings')
    async def test_get_session_operational_error_handling(self, mock_settings):
        """Test handling of operational errors."""
        mock_settings.return_value = Mock()
        
        service = DatabaseService()
        service._initialized = True
        
        # Mock session that raises OperationalError
        mock_session = AsyncMock()
        mock_session_factory = Mock(return_value=mock_session)
        service._session_factory = mock_session_factory
        
        # Mock the close and initialize methods
        with patch.object(service, 'close') as mock_close, \
             patch.object(service, 'initialize') as mock_init:
            
            # Simulate OperationalError during session use
            async with pytest.raises(OperationalError):
                async with service.get_session() as session:
                    raise OperationalError("Connection lost", None, None)
            
            # Verify rollback, close, and re-initialize were called
            mock_session.rollback.assert_called_once()
            mock_close.assert_called_once()
            mock_init.assert_called_once()
    
    @patch('app.services.database.get_settings')
    async def test_get_session_sqlalchemy_error_handling(self, mock_settings):
        """Test handling of SQLAlchemy errors."""
        mock_settings.return_value = Mock()
        
        service = DatabaseService()
        service._initialized = True
        
        mock_session = AsyncMock()
        mock_session_factory = Mock(return_value=mock_session)
        service._session_factory = mock_session_factory
        
        # Simulate SQLAlchemyError during session use
        async with pytest.raises(SQLAlchemyError):
            async with service.get_session() as session:
                raise SQLAlchemyError("Database error")
        
        # Verify rollback was called
        mock_session.rollback.assert_called_once()
    
    @patch('app.services.database.get_settings')
    async def test_get_session_generic_error_handling(self, mock_settings):
        """Test handling of generic errors."""
        mock_settings.return_value = Mock()
        
        service = DatabaseService()
        service._initialized = True
        
        mock_session = AsyncMock()
        mock_session_factory = Mock(return_value=mock_session)
        service._session_factory = mock_session_factory
        
        # Simulate generic error during session use
        async with pytest.raises(Exception, match="Generic error"):
            async with service.get_session() as session:
                raise Exception("Generic error")
        
        # Verify rollback was called
        mock_session.rollback.assert_called_once()


@pytest.mark.unit
class TestDatabaseServiceHealthCheck:
    """Test database health check functionality."""
    
    @patch('app.services.database.get_settings')
    async def test_health_check_healthy(self, mock_settings):
        """Test health check when database is healthy."""
        mock_settings.return_value = Mock()
        
        service = DatabaseService()
        service._initialized = True
        
        # Mock session and query result
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result
        
        # Mock get_session context manager
        @asynccontextmanager
        async def mock_get_session():
            yield mock_session
        
        with patch.object(service, 'get_session', mock_get_session):
            health = await service.health_check()
        
        assert health["status"] == "healthy"
        assert health["database"] == "connected"
        assert health["error"] is None
    
    @patch('app.services.database.get_settings')
    async def test_health_check_with_pool_status(self, mock_settings):
        """Test health check with pool status information."""
        mock_settings.return_value = Mock()
        
        service = DatabaseService()
        service._initialized = True
        
        # Mock engine with pool
        mock_pool = Mock()
        mock_pool.size.return_value = 5
        mock_pool.checkedin.return_value = 3
        mock_pool.checkedout.return_value = 2
        mock_pool.invalidated.return_value = 0
        
        service._engine = Mock()
        service._engine.pool = mock_pool
        
        # Mock session and query result
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result
        
        @asynccontextmanager
        async def mock_get_session():
            yield mock_session
        
        with patch.object(service, 'get_session', mock_get_session):
            health = await service.health_check()
        
        assert health["status"] == "healthy"
        assert health["pool_status"] is not None
        assert health["pool_status"]["size"] == 5
        assert health["pool_status"]["checked_in"] == 3
        assert health["pool_status"]["checked_out"] == 2
        assert health["pool_status"]["invalidated"] == 0
    
    @patch('app.services.database.get_settings')
    async def test_health_check_unhealthy(self, mock_settings):
        """Test health check when database is unhealthy."""
        mock_settings.return_value = Mock()
        
        service = DatabaseService()
        service._initialized = True
        
        # Mock get_session to raise an exception
        @asynccontextmanager
        async def mock_get_session():
            raise Exception("Database connection failed")
            yield  # This won't be reached
        
        with patch.object(service, 'get_session', mock_get_session):
            health = await service.health_check()
        
        assert health["status"] == "unhealthy"
        assert health["database"] == "disconnected"
        assert "Database connection failed" in health["error"]
    
    @patch('app.services.database.get_settings')
    async def test_health_check_initializes_if_needed(self, mock_settings):
        """Test that health check initializes service if needed."""
        mock_settings.return_value = Mock(
            DEBUG=False,
            ENVIRONMENT=Mock(value="test"),
            database_url="test://url"
        )
        
        service = DatabaseService()
        
        with patch.object(service, 'initialize') as mock_init:
            # Mock successful health check after initialization
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_result.scalar.return_value = 1
            mock_session.execute.return_value = mock_result
            
            @asynccontextmanager
            async def mock_get_session():
                yield mock_session
            
            with patch.object(service, 'get_session', mock_get_session):
                service._initialized = True  # Set after init
                health = await service.health_check()
            
            mock_init.assert_called_once()
            assert health["status"] == "healthy"


@pytest.mark.unit
class TestDatabaseServiceMigrationCheck:
    """Test migration status checking."""
    
    @patch('app.services.database.get_settings')
    async def test_execute_migration_check_success(self, mock_settings):
        """Test successful migration check."""
        mock_settings.return_value = Mock()
        
        service = DatabaseService()
        
        # Mock session and query result
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar.return_value = "abc123def456"
        mock_session.execute.return_value = mock_result
        
        @asynccontextmanager
        async def mock_get_session():
            yield mock_session
        
        with patch.object(service, 'get_session', mock_get_session):
            version = await service.execute_migration_check()
        
        assert version == "abc123def456"
        mock_session.execute.assert_called_once()
    
    @patch('app.services.database.get_settings')
    async def test_execute_migration_check_failure(self, mock_settings):
        """Test migration check when it fails."""
        mock_settings.return_value = Mock()
        
        service = DatabaseService()
        
        @asynccontextmanager
        async def mock_get_session():
            raise Exception("Table does not exist")
            yield  # Won't be reached
        
        with patch.object(service, 'get_session', mock_get_session):
            version = await service.execute_migration_check()
        
        assert version is None


@pytest.mark.unit
class TestDatabaseServiceUserOperations:
    """Test user-related database operations."""
    
    @patch('app.services.database.get_settings')
    async def test_create_user_success(self, mock_settings):
        """Test successful user creation."""
        mock_settings.return_value = Mock()
        
        service = DatabaseService()
        
        # Mock session
        mock_session = AsyncMock()
        mock_user = Mock()
        
        @asynccontextmanager
        async def mock_get_session():
            yield mock_session
        
        with patch.object(service, 'get_session', mock_get_session), \
             patch('app.services.database.User') as mock_user_class:
            
            mock_user_class.return_value = mock_user
            
            result = await service.create_user("test@example.com", "hashed_password")
        
        assert result == mock_user
        mock_session.add.assert_called_once_with(mock_user)
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(mock_user)


@pytest.mark.unit
class TestDatabaseServiceCleanup:
    """Test database cleanup and disposal."""
    
    @patch('app.services.database.get_settings')
    async def test_close_disposes_engine(self, mock_settings):
        """Test that close properly disposes of the engine."""
        mock_settings.return_value = Mock()
        
        service = DatabaseService()
        mock_engine = AsyncMock()
        service._engine = mock_engine
        service._initialized = True
        
        await service.close()
        
        mock_engine.dispose.assert_called_once()
        assert service._initialized is False
    
    @patch('app.services.database.get_settings')
    async def test_close_when_no_engine(self, mock_settings):
        """Test close when no engine exists."""
        mock_settings.return_value = Mock()
        
        service = DatabaseService()
        service._engine = None
        
        # Should not raise an exception
        await service.close()
        
        assert service._initialized is False


@pytest.mark.unit
class TestDatabaseServiceSingleton:
    """Test the global database service instance."""
    
    def test_database_service_singleton_exists(self):
        """Test that the global database service instance exists."""
        assert database_service is not None
        assert isinstance(database_service, DatabaseService)
    
    @patch('app.services.database.get_settings')
    def test_database_service_singleton_configuration(self, mock_settings):
        """Test that the singleton is properly configured."""
        mock_settings.return_value = Mock()
        
        # The singleton should have default values
        assert database_service._connection_retries == 3
        assert database_service._retry_delay == 1.0
        assert database_service._initialized is False


@pytest.mark.unit
class TestDatabaseServiceErrorHandling:
    """Test comprehensive error handling scenarios."""
    
    @patch('app.services.database.get_settings')
    async def test_session_error_during_operation(self, mock_settings):
        """Test error handling during database operations."""
        mock_settings.return_value = Mock()
        
        service = DatabaseService()
        service._initialized = True
        
        # Mock session that fails during operation
        mock_session = AsyncMock()
        mock_session.execute.side_effect = SQLAlchemyError("Query failed")
        
        @asynccontextmanager
        async def mock_get_session():
            yield mock_session
        
        with patch.object(service, 'get_session', mock_get_session):
            with pytest.raises(SQLAlchemyError, match="Query failed"):
                async with service.get_session() as session:
                    await session.execute("SELECT 1")
        
        # Session should be rolled back
        mock_session.rollback.assert_called_once()
    
    @patch('app.services.database.get_settings')
    async def test_connection_recovery_after_operational_error(self, mock_settings):
        """Test connection recovery after operational error."""
        mock_settings.return_value = Mock()
        
        service = DatabaseService()
        service._initialized = True
        
        # Mock session that raises OperationalError
        mock_session = AsyncMock()
        
        @asynccontextmanager
        async def mock_get_session():
            yield mock_session
        
        with patch.object(service, 'get_session', mock_get_session), \
             patch.object(service, 'close') as mock_close, \
             patch.object(service, 'initialize') as mock_init:
            
            with pytest.raises(OperationalError):
                async with service.get_session() as session:
                    raise OperationalError("Connection lost", None, None)
        
        # Verify recovery process
        mock_session.rollback.assert_called_once()
        mock_close.assert_called_once()
        mock_init.assert_called_once()


@pytest.mark.unit
class TestDatabaseServiceAsyncOperations:
    """Test async operation patterns."""
    
    @patch('app.services.database.get_settings')
    async def test_concurrent_session_usage(self, mock_settings):
        """Test concurrent session usage."""
        mock_settings.return_value = Mock()
        
        service = DatabaseService()
        service._initialized = True
        
        # Mock multiple sessions
        sessions = [AsyncMock() for _ in range(3)]
        session_iter = iter(sessions)
        
        def mock_session_factory():
            return next(session_iter)
        
        service._session_factory = mock_session_factory
        
        # Create multiple concurrent tasks
        async def use_session(session_id):
            async with service.get_session() as session:
                # Simulate some work
                await asyncio.sleep(0.001)
                return session_id
        
        # Run concurrent tasks
        tasks = [use_session(i) for i in range(3)]
        results = await asyncio.gather(*tasks)
        
        assert results == [0, 1, 2]
        
        # All sessions should be closed
        for session in sessions:
            session.close.assert_called_once()
    
    @patch('app.services.database.get_settings')
    async def test_async_context_manager_cleanup(self, mock_settings):
        """Test that async context manager properly cleans up on exceptions."""
        mock_settings.return_value = Mock()
        
        service = DatabaseService()
        service._initialized = True
        
        mock_session = AsyncMock()
        service._session_factory = Mock(return_value=mock_session)
        
        # Test that session is cleaned up even when exception occurs
        with pytest.raises(ValueError, match="Test exception"):
            async with service.get_session() as session:
                assert session == mock_session
                raise ValueError("Test exception")
        
        # Session should still be closed and rolled back
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


@pytest.mark.unit
class TestDatabaseServiceConfigurationVariants:
    """Test different configuration scenarios."""
    
    async def test_debug_mode_configuration(self):
        """Test configuration in debug mode."""
        with patch('app.services.database.get_settings') as mock_settings, \
             patch('app.services.database.create_async_engine') as mock_create_engine:
            
            mock_settings.return_value = Mock(
                DEBUG=True,
                ENVIRONMENT=Mock(value="development"),
                database_url="postgresql+asyncpg://test:test@localhost:5432/test"
            )
            
            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine
            
            # Mock test connection
            mock_conn = AsyncMock()
            mock_engine.begin.return_value.__aenter__.return_value = mock_conn
            
            service = DatabaseService()
            await service.initialize()
            
            # Verify debug mode affects engine creation
            call_args = mock_create_engine.call_args
            assert call_args[1]["echo"] is True
    
    async def test_production_mode_configuration(self):
        """Test configuration in production mode."""
        with patch('app.services.database.get_settings') as mock_settings, \
             patch('app.services.database.create_async_engine') as mock_create_engine:
            
            mock_settings.return_value = Mock(
                DEBUG=False,
                ENVIRONMENT=Mock(value="production"),
                database_url="postgresql+asyncpg://test:test@localhost:5432/test"
            )
            
            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine
            
            # Mock test connection
            mock_conn = AsyncMock()
            mock_engine.begin.return_value.__aenter__.return_value = mock_conn
            
            service = DatabaseService()
            await service.initialize()
            
            # Verify production mode configuration
            call_args = mock_create_engine.call_args
            assert call_args[1]["echo"] is False
            assert "pool_size" in call_args[1]
            assert "max_overflow" in call_args[1]