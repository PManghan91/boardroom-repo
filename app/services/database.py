"""Enhanced database service for the application with async support and improved error handling."""

import asyncio
from contextlib import asynccontextmanager
from typing import (
    AsyncGenerator,
    List,
    Optional,
)

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlmodel import SQLModel

from app.core.config import get_settings
from app.core.logging import logger
from app.models.session import Session as ChatSession
from app.models.user import User


class DatabaseService:
    """Enhanced database service for managing async connections and sessions.

    This class handles all database operations with async support, connection pooling,
    retry logic, and comprehensive error handling.
    """

    def __init__(self):
        """Initialize database service with async connection pool."""
        self.settings = get_settings()
        self._engine = None
        self._session_factory = None
        self._initialized = False
        self._connection_retries = 3
        self._retry_delay = 1.0

    async def initialize(self):
        """Initialize database engine and session factory with retry logic."""
        if self._initialized:
            return

        for attempt in range(self._connection_retries):
            try:
                # Create async engine with enhanced connection pooling
                engine_kwargs = {
                    "echo": self.settings.DEBUG,
                    "pool_pre_ping": True,
                    "pool_recycle": 3600,
                    "connect_args": {
                        "server_settings": {
                            "application_name": "boardroom_ai",
                        }
                    }
                }

                # Configure pooling based on environment
                if self.settings.ENVIRONMENT.value == "test":
                    engine_kwargs["poolclass"] = NullPool
                else:
                    engine_kwargs["poolclass"] = QueuePool
                    engine_kwargs["pool_size"] = 5
                    engine_kwargs["max_overflow"] = 10
                    engine_kwargs["pool_timeout"] = 30

                self._engine = create_async_engine(
                    self.settings.database_url,
                    **engine_kwargs
                )

                # Create session factory
                self._session_factory = async_sessionmaker(
                    bind=self._engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                    autoflush=True,
                    autocommit=False
                )

                # Test the connection
                await self._test_connection()

                self._initialized = True
                logger.info("Database service initialized successfully")
                break

            except Exception as e:
                logger.warning(f"Database initialization attempt {attempt + 1} failed: {e}")
                if attempt < self._connection_retries - 1:
                    await asyncio.sleep(self._retry_delay * (2 ** attempt))
                else:
                    logger.error(f"Failed to initialize database service after {self._connection_retries} attempts")
                    raise

    async def _test_connection(self):
        """Test database connection."""
        async with self._engine.begin() as conn:
            await conn.execute(text("SELECT 1"))

    async def close(self):
        """Close database connections."""
        if self._engine:
            await self._engine.dispose()
            self._initialized = False
            logger.info("Database connections closed")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session with automatic cleanup and error handling."""
        if not self._initialized:
            await self.initialize()

        session = None
        try:
            session = self._session_factory()
            yield session

        except OperationalError as e:
            if session:
                await session.rollback()
            logger.error(f"Database operational error: {e}")
            # Re-initialize connection pool on operational errors
            await self.close()
            await self.initialize()
            raise

        except SQLAlchemyError as e:
            if session:
                await session.rollback()
            logger.error(f"Database SQLAlchemy error: {e}")
            raise

        except Exception as e:
            if session:
                await session.rollback()
            logger.error(f"Database session error: {e}")
            raise

        finally:
            if session:
                await session.close()

    async def health_check(self) -> dict:
        """Enhanced health check with detailed information."""
        health_info = {
            "status": "unknown",
            "database": "disconnected",
            "pool_status": None,
            "error": None
        }

        try:
            if not self._initialized:
                await self.initialize()

            async with self.get_session() as session:
                # Test basic connectivity
                result = await session.execute(text("SELECT 1 as test"))
                test_value = result.scalar()

                if test_value == 1:
                    health_info["status"] = "healthy"
                    health_info["database"] = "connected"

                # Get pool status if available
                if hasattr(self._engine.pool, 'size'):
                    health_info["pool_status"] = {
                        "size": self._engine.pool.size(),
                        "checked_in": self._engine.pool.checkedin(),
                        "checked_out": self._engine.pool.checkedout(),
                        "invalidated": self._engine.pool.invalidated()
                    }

        except Exception as e:
            health_info["status"] = "unhealthy"
            health_info["error"] = str(e)
            logger.error(f"Database health check failed: {e}")

        return health_info

    async def execute_migration_check(self) -> Optional[str]:
        """Check current migration status."""
        try:
            async with self.get_session() as session:
                result = await session.execute(text("""
                    SELECT version_num
                    FROM alembic_version
                    ORDER BY version_num DESC
                    LIMIT 1
                """))
                version = result.scalar()
                return version
        except Exception as e:
            logger.warning(f"Could not check migration status: {e}")
            return None

    async def create_user(self, email: str, password: str) -> User:
        """Create a new user.

        Args:
            email: User's email address
            password: Hashed password

        Returns:
            User: The created user
        """
        with Session(self.engine) as session:
            user = User(email=email, hashed_password=password)
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info("user_created", email=email)
            return user

    async def get_user(self, user_id: int) -> Optional[User]:
        """Get a user by ID.

        Args:
            user_id: The ID of the user to retrieve

        Returns:
            Optional[User]: The user if found, None otherwise
        """
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email.

        Args:
            email: The email of the user to retrieve

        Returns:
            Optional[User]: The user if found, None otherwise
        """
        with Session(self.engine) as session:
            statement = select(User).where(User.email == email)
            user = session.exec(statement).first()
            return user

    async def delete_user_by_email(self, email: str) -> bool:
        """Delete a user by email.

        Args:
            email: The email of the user to delete

        Returns:
            bool: True if deletion was successful, False if user not found
        """
        with Session(self.engine) as session:
            user = session.exec(select(User).where(User.email == email)).first()
            if not user:
                return False

            session.delete(user)
            session.commit()
            logger.info("user_deleted", email=email)
            return True

    async def create_session(self, session_id: str, user_id: int, name: str = "") -> ChatSession:
        """Create a new chat session.

        Args:
            session_id: The ID for the new session
            user_id: The ID of the user who owns the session
            name: Optional name for the session (defaults to empty string)

        Returns:
            ChatSession: The created session
        """
        with Session(self.engine) as session:
            chat_session = ChatSession(id=session_id, user_id=user_id, name=name)
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            logger.info("session_created", session_id=session_id, user_id=user_id, name=name)
            return chat_session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID.

        Args:
            session_id: The ID of the session to delete

        Returns:
            bool: True if deletion was successful, False if session not found
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session:
                return False

            session.delete(chat_session)
            session.commit()
            logger.info("session_deleted", session_id=session_id)
            return True

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID.

        Args:
            session_id: The ID of the session to retrieve

        Returns:
            Optional[ChatSession]: The session if found, None otherwise
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            return chat_session

    async def get_user_sessions(self, user_id: int) -> List[ChatSession]:
        """Get all sessions for a user.

        Args:
            user_id: The ID of the user

        Returns:
            List[ChatSession]: List of user's sessions
        """
        with Session(self.engine) as session:
            statement = select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.created_at)
            sessions = session.exec(statement).all()
            return sessions

    async def update_session_name(self, session_id: str, name: str) -> ChatSession:
        """Update a session's name.

        Args:
            session_id: The ID of the session to update
            name: The new name for the session

        Returns:
            ChatSession: The updated session

        Raises:
            HTTPException: If session is not found
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session:
                raise HTTPException(status_code=404, detail="Session not found")

            chat_session.name = name
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            logger.info("session_name_updated", session_id=session_id, name=name)
            return chat_session

    def get_session_maker(self):
        """Get a session maker for creating database sessions.

        Returns:
            Session: A SQLModel session maker
        """
        return Session(self.engine)

    async def health_check(self) -> bool:
        """Check database connection health.

        Returns:
            bool: True if database is healthy, False otherwise
        """
        try:
            with Session(self.engine) as session:
                # Execute a simple query to check connection
                session.exec(select(1)).first()
                return True
        except Exception as e:
            logger.error("database_health_check_failed", error=str(e))
            return False


# Create a singleton instance
database_service = DatabaseService()
