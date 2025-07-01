"""Unit tests for AI State Manager service."""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from contextlib import asynccontextmanager

from app.services.ai_state_manager import AIStateManager, ai_state_manager
from app.schemas.ai_operations import ConversationState, AIOperationStatus
from app.core.exceptions import StateManagementException


@pytest.mark.unit
@pytest.mark.asyncio
class TestAIStateManager:
    """Test suite for AIStateManager class."""

    @pytest.fixture
    def state_manager(self):
        """Create a fresh AIStateManager instance for testing."""
        return AIStateManager()

    @pytest.fixture
    def sample_session_id(self):
        """Generate a sample session ID."""
        return "test-session-123"

    @pytest.fixture
    def sample_user_id(self):
        """Generate a sample user ID."""
        return "user-456"

    @pytest.fixture
    def sample_initial_state(self):
        """Create sample initial state data."""
        return {
            "conversation_context": "project discussion",
            "current_topic": "database design",
            "preferences": {
                "response_length": "detailed",
                "tone": "professional"
            }
        }

    def test_state_manager_initialization(self, state_manager):
        """Test state manager initialization."""
        assert state_manager._active_states == {}
        assert state_manager._state_locks == {}

    @pytest.mark.asyncio
    async def test_create_conversation_state_success(self, state_manager, sample_session_id, sample_user_id, sample_initial_state):
        """Test successful conversation state creation."""
        with patch.object(state_manager, '_persist_state') as mock_persist:
            mock_persist.return_value = None
            
            state = await state_manager.create_conversation_state(
                session_id=sample_session_id,
                user_id=sample_user_id,
                initial_state=sample_initial_state
            )
            
            assert state.session_id == sample_session_id
            assert state.user_id == sample_user_id
            assert state.current_state == sample_initial_state
            assert state.state_version == 1
            assert state.created_at is not None
            assert state.updated_at is not None
            
            # Verify state is stored in memory
            assert sample_session_id in state_manager._active_states
            assert state_manager._state_locks[sample_session_id] is False
            
            mock_persist.assert_called_once_with(state)

    @pytest.mark.asyncio
    async def test_create_conversation_state_already_exists(self, state_manager, sample_session_id):
        """Test creating state when it already exists."""
        # Create existing state
        existing_state = ConversationState(
            session_id=sample_session_id,
            user_id="existing-user",
            current_state={},
            state_version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        state_manager._active_states[sample_session_id] = existing_state
        
        state = await state_manager.create_conversation_state(
            session_id=sample_session_id,
            user_id="new-user"
        )
        
        # Should return existing state
        assert state == existing_state
        assert state.user_id == "existing-user"  # Not updated

    @pytest.mark.asyncio
    async def test_create_conversation_state_error(self, state_manager, sample_session_id):
        """Test error handling during state creation."""
        with patch.object(state_manager, '_persist_state') as mock_persist:
            mock_persist.side_effect = Exception("Database error")
            
            with pytest.raises(StateManagementException):
                await state_manager.create_conversation_state(
                    session_id=sample_session_id
                )

    @pytest.mark.asyncio
    async def test_get_conversation_state_from_memory(self, state_manager, sample_session_id):
        """Test getting state from memory."""
        # Create state in memory
        existing_state = ConversationState(
            session_id=sample_session_id,
            user_id="test-user",
            current_state={"key": "value"},
            state_version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        state_manager._active_states[sample_session_id] = existing_state
        
        state = await state_manager.get_conversation_state(sample_session_id)
        
        assert state == existing_state

    @pytest.mark.asyncio
    async def test_get_conversation_state_from_database(self, state_manager, sample_session_id):
        """Test getting state from database when not in memory."""
        restored_state = ConversationState(
            session_id=sample_session_id,
            user_id="restored-user",
            current_state={"restored": "data"},
            state_version=2,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        with patch.object(state_manager, '_restore_state') as mock_restore:
            mock_restore.return_value = restored_state
            
            state = await state_manager.get_conversation_state(sample_session_id)
            
            assert state == restored_state
            # Should be added to memory
            assert sample_session_id in state_manager._active_states
            assert state_manager._state_locks[sample_session_id] is False

    @pytest.mark.asyncio
    async def test_get_conversation_state_not_found(self, state_manager, sample_session_id):
        """Test getting non-existent state."""
        with patch.object(state_manager, '_restore_state') as mock_restore:
            mock_restore.return_value = None
            
            state = await state_manager.get_conversation_state(sample_session_id)
            
            assert state is None

    @pytest.mark.asyncio
    async def test_update_conversation_state_success(self, state_manager, sample_session_id):
        """Test successful state update."""
        # Create initial state
        initial_state = ConversationState(
            session_id=sample_session_id,
            user_id="test-user",
            current_state={"key1": "value1"},
            state_version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        state_manager._active_states[sample_session_id] = initial_state
        state_manager._state_locks[sample_session_id] = False
        
        update_data = {"key2": "value2", "key1": "updated_value1"}
        
        with patch.object(state_manager, '_persist_state') as mock_persist:
            mock_persist.return_value = None
            
            updated_state = await state_manager.update_conversation_state(
                session_id=sample_session_id,
                state_updates=update_data
            )
            
            assert updated_state.state_version == 2
            assert updated_state.current_state["key1"] == "updated_value1"
            assert updated_state.current_state["key2"] == "value2"
            
            mock_persist.assert_called_once_with(updated_state)

    @pytest.mark.asyncio
    async def test_update_conversation_state_locked(self, state_manager, sample_session_id):
        """Test update when state is locked."""
        # Create state and lock it
        state = ConversationState(
            session_id=sample_session_id,
            user_id="test-user",
            current_state={},
            state_version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        state_manager._active_states[sample_session_id] = state
        state_manager._state_locks[sample_session_id] = True
        
        with pytest.raises(StateManagementException):
            await state_manager.update_conversation_state(
                session_id=sample_session_id,
                state_updates={"key": "value"}
            )

    @pytest.mark.asyncio
    async def test_update_conversation_state_force_update(self, state_manager, sample_session_id):
        """Test force update bypasses lock."""
        # Create locked state
        state = ConversationState(
            session_id=sample_session_id,
            user_id="test-user",
            current_state={},
            state_version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        state_manager._active_states[sample_session_id] = state
        state_manager._state_locks[sample_session_id] = True
        
        with patch.object(state_manager, '_persist_state') as mock_persist:
            mock_persist.return_value = None
            
            updated_state = await state_manager.update_conversation_state(
                session_id=sample_session_id,
                state_updates={"key": "value"},
                force_update=True
            )
            
            assert updated_state.state_version == 2
            assert updated_state.current_state["key"] == "value"

    @pytest.mark.asyncio
    async def test_update_conversation_state_not_found(self, state_manager, sample_session_id):
        """Test update when state doesn't exist."""
        with patch.object(state_manager, 'get_conversation_state') as mock_get:
            mock_get.return_value = None
            
            with pytest.raises(StateManagementException):
                await state_manager.update_conversation_state(
                    session_id=sample_session_id,
                    state_updates={"key": "value"}
                )

    @pytest.mark.asyncio
    async def test_create_checkpoint_success(self, state_manager, sample_session_id):
        """Test successful checkpoint creation."""
        # Create state
        state = ConversationState(
            session_id=sample_session_id,
            user_id="test-user",
            current_state={"important": "data"},
            state_version=3,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        state_manager._active_states[sample_session_id] = state
        
        with patch.object(state_manager, '_persist_state') as mock_persist:
            mock_persist.return_value = None
            
            checkpoint_id = await state_manager.create_checkpoint(sample_session_id)
            
            assert checkpoint_id is not None
            assert isinstance(checkpoint_id, str)
            
            # Verify checkpoint data was added to state
            assert state.checkpoint_data is not None
            assert state.checkpoint_data["checkpoint_id"] == checkpoint_id
            assert state.checkpoint_data["session_id"] == sample_session_id
            assert state.checkpoint_data["state_version"] == 3

    @pytest.mark.asyncio
    async def test_restore_from_checkpoint_success(self, state_manager, sample_session_id):
        """Test successful checkpoint restoration."""
        checkpoint_id = str(uuid.uuid4())
        
        # Create state with checkpoint
        state = ConversationState(
            session_id=sample_session_id,
            user_id="test-user",
            current_state={"current": "data"},
            state_version=5,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        state.checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "session_id": sample_session_id,
            "state_version": 3,
            "state_snapshot": {"original": "data"},
            "created_at": datetime.now().isoformat(),
            "metadata": {"user_id": "test-user"}
        }
        state_manager._active_states[sample_session_id] = state
        
        with patch.object(state_manager, '_persist_state') as mock_persist:
            mock_persist.return_value = None
            
            restored_state = await state_manager.restore_from_checkpoint(
                session_id=sample_session_id,
                checkpoint_id=checkpoint_id
            )
            
            assert restored_state.current_state == {"original": "data"}
            assert restored_state.state_version == 3

    @pytest.mark.asyncio
    async def test_restore_from_checkpoint_not_found(self, state_manager, sample_session_id):
        """Test restoration when checkpoint doesn't exist."""
        # Create state without checkpoint
        state = ConversationState(
            session_id=sample_session_id,
            user_id="test-user",
            current_state={},
            state_version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        state_manager._active_states[sample_session_id] = state
        
        with pytest.raises(StateManagementException):
            await state_manager.restore_from_checkpoint(
                session_id=sample_session_id,
                checkpoint_id="nonexistent-checkpoint"
            )

    @pytest.mark.asyncio
    async def test_clear_conversation_state_success(self, state_manager, sample_session_id):
        """Test successful state clearing."""
        # Create state in memory
        state = ConversationState(
            session_id=sample_session_id,
            user_id="test-user",
            current_state={},
            state_version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        state_manager._active_states[sample_session_id] = state
        state_manager._state_locks[sample_session_id] = False
        
        with patch.object(state_manager, '_clear_persisted_state') as mock_clear:
            mock_clear.return_value = None
            
            result = await state_manager.clear_conversation_state(sample_session_id)
            
            assert result is True
            assert sample_session_id not in state_manager._active_states
            assert sample_session_id not in state_manager._state_locks
            
            mock_clear.assert_called_once_with(sample_session_id)

    @pytest.mark.asyncio
    async def test_get_active_sessions(self, state_manager):
        """Test getting active session list."""
        # Add some states
        session_ids = ["session-1", "session-2", "session-3"]
        for session_id in session_ids:
            state = ConversationState(
                session_id=session_id,
                user_id="test-user",
                current_state={},
                state_version=1,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            state_manager._active_states[session_id] = state
        
        active_sessions = await state_manager.get_active_sessions()
        
        assert len(active_sessions) == 3
        assert all(session_id in active_sessions for session_id in session_ids)

    @pytest.mark.asyncio
    async def test_cleanup_expired_states(self, state_manager):
        """Test cleanup of expired states."""
        now = datetime.now()
        
        # Create mix of expired and active states
        expired_state = ConversationState(
            session_id="expired-session",
            user_id="test-user",
            current_state={},
            state_version=1,
            created_at=now - timedelta(hours=25),
            updated_at=now - timedelta(hours=25)
        )
        
        active_state = ConversationState(
            session_id="active-session",
            user_id="test-user",
            current_state={},
            state_version=1,
            created_at=now - timedelta(hours=1),
            updated_at=now - timedelta(hours=1)
        )
        
        state_manager._active_states["expired-session"] = expired_state
        state_manager._active_states["active-session"] = active_state
        
        with patch.object(state_manager, 'clear_conversation_state') as mock_clear:
            mock_clear.return_value = True
            
            cleaned_count = await state_manager.cleanup_expired_states(expiry_hours=24)
            
            assert cleaned_count == 1
            mock_clear.assert_called_once_with("expired-session")

    @pytest.mark.asyncio
    async def test_persist_state_placeholder(self, state_manager):
        """Test _persist_state placeholder implementation."""
        state = ConversationState(
            session_id="test-session",
            user_id="test-user",
            current_state={},
            state_version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Should not raise an exception
        await state_manager._persist_state(state)

    @pytest.mark.asyncio
    async def test_restore_state_placeholder(self, state_manager):
        """Test _restore_state placeholder implementation."""
        result = await state_manager._restore_state("test-session")
        
        # Should return None (no stored state)
        assert result is None

    @pytest.mark.asyncio
    async def test_clear_persisted_state_placeholder(self, state_manager):
        """Test _clear_persisted_state placeholder implementation."""
        # Should not raise an exception
        await state_manager._clear_persisted_state("test-session")

    @pytest.mark.asyncio
    async def test_get_session_context_manager(self, state_manager):
        """Test get_session context manager."""
        mock_session = AsyncMock()
        
        async def mock_get_db():
            yield mock_session
        
        with patch('app.services.ai_state_manager.get_db', mock_get_db):
            async with state_manager.get_session() as session:
                assert session == mock_session


@pytest.mark.unit
class TestGlobalStateManager:
    """Test the global state manager instance."""

    def test_global_instance_exists(self):
        """Test that global state manager instance exists."""
        assert ai_state_manager is not None
        assert isinstance(ai_state_manager, AIStateManager)

    def test_global_instance_singleton(self):
        """Test that global instance behaves like singleton."""
        from app.services.ai_state_manager import ai_state_manager as another_import
        
        assert ai_state_manager is another_import


@pytest.mark.unit
@pytest.mark.asyncio
class TestStateManagerIntegration:
    """Integration tests for state manager functionality."""

    @pytest.fixture
    def state_manager(self):
        """Create a fresh state manager for integration testing."""
        return AIStateManager()

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, state_manager):
        """Test full state lifecycle: create, update, checkpoint, restore, clear."""
        session_id = "lifecycle-test-session"
        user_id = "lifecycle-user"
        
        with patch.object(state_manager, '_persist_state') as mock_persist:
            with patch.object(state_manager, '_clear_persisted_state') as mock_clear:
                mock_persist.return_value = None
                mock_clear.return_value = None
                
                # 1. Create state
                initial_state = {"step": "initial"}
                state = await state_manager.create_conversation_state(
                    session_id=session_id,
                    user_id=user_id,
                    initial_state=initial_state
                )
                assert state.current_state == initial_state
                assert state.state_version == 1
                
                # 2. Update state
                updated_state = await state_manager.update_conversation_state(
                    session_id=session_id,
                    state_updates={"step": "updated", "new_field": "value"}
                )
                assert updated_state.state_version == 2
                assert updated_state.current_state["step"] == "updated"
                assert updated_state.current_state["new_field"] == "value"
                
                # 3. Create checkpoint
                checkpoint_id = await state_manager.create_checkpoint(session_id)
                assert checkpoint_id is not None
                
                # 4. Make more updates
                await state_manager.update_conversation_state(
                    session_id=session_id,
                    state_updates={"step": "after_checkpoint"}
                )
                current_state = await state_manager.get_conversation_state(session_id)
                assert current_state.state_version == 3
                assert current_state.current_state["step"] == "after_checkpoint"
                
                # 5. Restore from checkpoint
                restored_state = await state_manager.restore_from_checkpoint(
                    session_id=session_id,
                    checkpoint_id=checkpoint_id
                )
                assert restored_state.state_version == 2
                assert restored_state.current_state["step"] == "updated"
                
                # 6. Clear state
                result = await state_manager.clear_conversation_state(session_id)
                assert result is True
                
                # 7. Verify state is gone
                final_state = await state_manager.get_conversation_state(session_id)
                assert final_state is None

    @pytest.mark.asyncio
    async def test_concurrent_access_simulation(self, state_manager):
        """Test simulated concurrent access to the same session."""
        session_id = "concurrent-test-session"
        
        with patch.object(state_manager, '_persist_state') as mock_persist:
            mock_persist.return_value = None
            
            # Create initial state
            await state_manager.create_conversation_state(
                session_id=session_id,
                initial_state={"counter": 0}
            )
            
            # Simulate concurrent updates (in real scenario, these would be async)
            # First update should succeed
            updated1 = await state_manager.update_conversation_state(
                session_id=session_id,
                state_updates={"counter": 1, "update": "first"}
            )
            assert updated1.current_state["counter"] == 1
            
            # Lock state manually to simulate concurrent access
            state_manager._state_locks[session_id] = True
            
            # Second update should fail due to lock
            with pytest.raises(StateManagementException):
                await state_manager.update_conversation_state(
                    session_id=session_id,
                    state_updates={"counter": 2, "update": "second"}
                )
            
            # Force update should succeed despite lock
            updated2 = await state_manager.update_conversation_state(
                session_id=session_id,
                state_updates={"counter": 2, "update": "forced"},
                force_update=True
            )
            assert updated2.current_state["counter"] == 2
            assert updated2.current_state["update"] == "forced"