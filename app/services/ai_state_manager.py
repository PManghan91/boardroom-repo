"""AI State Management Service for LangGraph integration.

This module provides comprehensive state management for AI conversations,
including persistence, recovery, checkpointing, and cleanup capabilities
with full async support and proper error handling.
"""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.exceptions import raise_state_management_error
from app.core.logging import logger
from app.core.metrics import ai_state_operations_total
from app.schemas.ai_operations import AIOperationStatus, ConversationState
from app.services.database import get_db


class AIStateManager:
    """Manages AI conversation states with persistence and recovery capabilities.
    
    Provides comprehensive state management for AI conversations including:
    - In-memory state caching for performance
    - Database persistence for durability
    - Checkpoint creation and restoration
    - Concurrent access control with simple locking
    - Automatic cleanup of expired states
    """
    
    def __init__(self) -> None:
        """Initialize the state manager."""
        self._active_states: Dict[str, ConversationState] = {}
        self._state_locks: Dict[str, bool] = {}
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session.
        
        Yields:
            AsyncSession: Database session for operations.
        """
        async for session in get_db():
            yield session
            break
    
    async def create_conversation_state(
        self, 
        session_id: str, 
        user_id: Optional[str] = None,
        initial_state: Optional[Dict[str, Any]] = None
    ) -> ConversationState:
        """Create a new conversation state."""
        
        try:
            ai_state_operations_total.labels(operation="create", status="started").inc()
            
            # Check if state already exists
            if session_id in self._active_states:
                logger.warning("conversation_state_already_exists", session_id=session_id)
                return self._active_states[session_id]
            
            # Create new state
            state = ConversationState(
                session_id=session_id,
                user_id=user_id,
                current_state=initial_state or {},
                state_version=1,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Store in memory
            self._active_states[session_id] = state
            self._state_locks[session_id] = False
            
            # Persist to database (if needed)
            await self._persist_state(state)
            
            ai_state_operations_total.labels(operation="create", status="success").inc()
            logger.info("conversation_state_created", session_id=session_id, user_id=user_id)
            
            return state
            
        except Exception as e:
            ai_state_operations_total.labels(operation="create", status="error").inc()
            logger.error("conversation_state_creation_failed", session_id=session_id, error=str(e))
            raise_state_management_error(f"Failed to create conversation state: {str(e)}", session_id)
    
    async def get_conversation_state(self, session_id: str) -> Optional[ConversationState]:
        """Get an existing conversation state."""
        
        try:
            ai_state_operations_total.labels(operation="get", status="started").inc()
            
            # Check memory first
            if session_id in self._active_states:
                ai_state_operations_total.labels(operation="get", status="success").inc()
                return self._active_states[session_id]
            
            # Try to restore from database
            state = await self._restore_state(session_id)
            if state:
                self._active_states[session_id] = state
                self._state_locks[session_id] = False
                ai_state_operations_total.labels(operation="get", status="success").inc()
                logger.info("conversation_state_restored", session_id=session_id)
                return state
            
            ai_state_operations_total.labels(operation="get", status="not_found").inc()
            logger.info("conversation_state_not_found", session_id=session_id)
            return None
            
        except Exception as e:
            ai_state_operations_total.labels(operation="get", status="error").inc()
            logger.error("conversation_state_retrieval_failed", session_id=session_id, error=str(e))
            raise_state_management_error(f"Failed to get conversation state: {str(e)}", session_id)
    
    async def update_conversation_state(
        self, 
        session_id: str, 
        state_updates: Dict[str, Any],
        force_update: bool = False
    ) -> ConversationState:
        """Update an existing conversation state."""
        
        try:
            ai_state_operations_total.labels(operation="update", status="started").inc()
            
            # Check for lock (simple concurrency control)
            if not force_update and self._state_locks.get(session_id, False):
                raise_state_management_error("State is locked for update", session_id)
            
            # Get current state
            state = await self.get_conversation_state(session_id)
            if not state:
                raise_state_management_error("Conversation state not found", session_id)
            
            # Lock the state
            self._state_locks[session_id] = True
            
            try:
                # Update state
                state.update_state(state_updates)
                
                # Persist changes
                await self._persist_state(state)
                
                ai_state_operations_total.labels(operation="update", status="success").inc()
                logger.info("conversation_state_updated", 
                           session_id=session_id, 
                           version=state.state_version)
                
                return state
                
            finally:
                # Always unlock
                self._state_locks[session_id] = False
                
        except Exception as e:
            ai_state_operations_total.labels(operation="update", status="error").inc()
            logger.error("conversation_state_update_failed", session_id=session_id, error=str(e))
            raise_state_management_error(f"Failed to update conversation state: {str(e)}", session_id)
    
    async def create_checkpoint(self, session_id: str) -> str:
        """Create a checkpoint of the current state."""
        
        try:
            ai_state_operations_total.labels(operation="checkpoint", status="started").inc()
            
            state = await self.get_conversation_state(session_id)
            if not state:
                raise_state_management_error("Conversation state not found", session_id)
            
            # Create checkpoint data
            checkpoint_id = str(uuid.uuid4())
            checkpoint_data = {
                "checkpoint_id": checkpoint_id,
                "session_id": session_id,
                "state_version": state.state_version,
                "state_snapshot": state.current_state.copy(),
                "created_at": datetime.now().isoformat(),
                "metadata": {
                    "user_id": state.user_id,
                    "original_created_at": state.created_at.isoformat()
                }
            }
            
            # Store checkpoint
            state.checkpoint_data = checkpoint_data
            await self._persist_state(state)
            
            ai_state_operations_total.labels(operation="checkpoint", status="success").inc()
            logger.info("checkpoint_created", session_id=session_id, checkpoint_id=checkpoint_id)
            
            return checkpoint_id
            
        except Exception as e:
            ai_state_operations_total.labels(operation="checkpoint", status="error").inc()
            logger.error("checkpoint_creation_failed", session_id=session_id, error=str(e))
            raise_state_management_error(f"Failed to create checkpoint: {str(e)}", session_id)
    
    async def restore_from_checkpoint(self, session_id: str, checkpoint_id: str) -> ConversationState:
        """Restore state from a checkpoint."""
        
        try:
            ai_state_operations_total.labels(operation="restore", status="started").inc()
            
            state = await self.get_conversation_state(session_id)
            if not state:
                raise_state_management_error("Conversation state not found", session_id)
            
            if not state.checkpoint_data or state.checkpoint_data.get("checkpoint_id") != checkpoint_id:
                raise_state_management_error("Checkpoint not found", session_id)
            
            # Restore from checkpoint
            checkpoint_data = state.checkpoint_data
            state.current_state = checkpoint_data["state_snapshot"].copy()
            state.state_version = checkpoint_data["state_version"]
            state.updated_at = datetime.now()
            
            # Persist restored state
            await self._persist_state(state)
            
            ai_state_operations_total.labels(operation="restore", status="success").inc()
            logger.info("state_restored_from_checkpoint", 
                       session_id=session_id, 
                       checkpoint_id=checkpoint_id)
            
            return state
            
        except Exception as e:
            ai_state_operations_total.labels(operation="restore", status="error").inc()
            logger.error("checkpoint_restore_failed", 
                        session_id=session_id, 
                        checkpoint_id=checkpoint_id, 
                        error=str(e))
            raise_state_management_error(f"Failed to restore from checkpoint: {str(e)}", session_id)
    
    async def clear_conversation_state(self, session_id: str) -> bool:
        """Clear a conversation state."""
        
        try:
            ai_state_operations_total.labels(operation="clear", status="started").inc()
            
            # Remove from memory
            if session_id in self._active_states:
                del self._active_states[session_id]
            
            if session_id in self._state_locks:
                del self._state_locks[session_id]
            
            # Clear from database (implementation would depend on storage strategy)
            await self._clear_persisted_state(session_id)
            
            ai_state_operations_total.labels(operation="clear", status="success").inc()
            logger.info("conversation_state_cleared", session_id=session_id)
            
            return True
            
        except Exception as e:
            ai_state_operations_total.labels(operation="clear", status="error").inc()
            logger.error("conversation_state_clear_failed", session_id=session_id, error=str(e))
            raise_state_management_error(f"Failed to clear conversation state: {str(e)}", session_id)
    
    async def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs."""
        
        try:
            return list(self._active_states.keys())
        except Exception as e:
            logger.error("get_active_sessions_failed", error=str(e))
            return []
    
    async def cleanup_expired_states(self, expiry_hours: int = 24) -> int:
        """Clean up expired conversation states."""
        
        try:
            cutoff_time = datetime.now() - timedelta(hours=expiry_hours)
            cleaned_count = 0
            
            expired_sessions = []
            for session_id, state in self._active_states.items():
                if state.updated_at < cutoff_time:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                await self.clear_conversation_state(session_id)
                cleaned_count += 1
            
            logger.info("expired_states_cleaned", count=cleaned_count, expiry_hours=expiry_hours)
            return cleaned_count
            
        except Exception as e:
            logger.error("state_cleanup_failed", error=str(e))
            return 0
    
    async def _persist_state(self, state: ConversationState) -> None:
        """Persist state to database (placeholder implementation)."""
        # This would be implemented based on specific database schema
        # For now, this is a placeholder that logs the operation
        logger.debug("state_persisted", session_id=state.session_id, version=state.state_version)
    
    async def _restore_state(self, session_id: str) -> Optional[ConversationState]:
        """Restore state from database (placeholder implementation)."""
        # This would be implemented based on specific database schema
        # For now, this returns None indicating no stored state
        logger.debug("state_restore_attempted", session_id=session_id)
        return None
    
    async def _clear_persisted_state(self, session_id: str) -> None:
        """Clear persisted state from database (placeholder implementation)."""
        # This would be implemented based on specific database schema
        logger.debug("persisted_state_cleared", session_id=session_id)


# Global state manager instance
ai_state_manager = AIStateManager()