"""AI Operations monitoring and management endpoints."""

import time
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.api.v1.auth import get_current_session
from app.core.limiter import limiter
from app.core.logging import logger
from app.core.config import settings
from app.core.api_standards import create_standard_response, create_error_response
from app.core.metrics import (
    ai_operations_total,
    ai_token_usage_total,
    ai_tool_executions_total,
)
from app.models.session import Session
from app.schemas.ai_operations import (
    AIHealthCheck,
    ConversationContext,
    ToolExecutionRequest,
    ToolExecutionResponse,
    AIOperationStatus,
)
from app.services.ai_state_manager import ai_state_manager
from app.core.langgraph.graph import LangGraphAgent

router = APIRouter()
agent = LangGraphAgent()


@router.get("/health")
@limiter.limit("20 per minute")
async def get_ai_health(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get AI operations health status.
    
    Returns comprehensive health information for AI operations including
    model availability, performance metrics, and system status.
    """
    try:
        # Get active sessions
        active_sessions = await ai_state_manager.get_active_sessions()
        
        # Calculate basic metrics (in production, these would come from actual metrics store)
        health_check = AIHealthCheck(
            status="healthy",
            models_available=[settings.LLM_MODEL],
            models_unavailable=[],
            active_sessions=len(active_sessions),
            total_token_usage_last_hour=0,  # Would be calculated from metrics
            recent_errors=[],
        )
        
        # Determine overall status based on recent performance
        if len(active_sessions) > 100:  # Example threshold
            health_check.status = "degraded"
        
        logger.info("ai_health_check_requested", 
                   session_id=session.id,
                   active_sessions=len(active_sessions))
        
        return create_standard_response(
            data=health_check.model_dump(),
            message="AI operations health status retrieved successfully"
        )
        
    except Exception as e:
        logger.error("ai_health_check_failed", session_id=session.id, error=str(e), exc_info=True)
        return create_error_response(
            message="Failed to retrieve AI health status",
            error_type="health_check_error",
            details={"session_id": session.id},
            status_code=500
        )


@router.get("/sessions/active")
@limiter.limit("10 per minute")
async def get_active_sessions(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get list of active AI conversation sessions.
    
    Returns information about currently active conversation sessions
    for monitoring and management purposes.
    """
    try:
        active_sessions = await ai_state_manager.get_active_sessions()
        
        logger.info("active_sessions_requested", 
                   session_id=session.id,
                   active_count=len(active_sessions))
        
        return create_standard_response(
            data={
                "active_sessions": active_sessions,
                "total_count": len(active_sessions),
                "timestamp": time.time()
            },
            message="Active sessions retrieved successfully"
        )
        
    except Exception as e:
        logger.error("active_sessions_retrieval_failed", session_id=session.id, error=str(e), exc_info=True)
        return create_error_response(
            message="Failed to retrieve active sessions",
            error_type="session_retrieval_error",
            details={"session_id": session.id},
            status_code=500
        )


@router.post("/sessions/{target_session_id}/checkpoint")
@limiter.limit("5 per minute")
async def create_session_checkpoint(
    target_session_id: str,
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Create a checkpoint for a conversation session.
    
    Creates a checkpoint of the current conversation state that can be
    restored later if needed.
    """
    try:
        # Verify the requesting user can access this session
        # In a full implementation, you'd check permissions here
        
        checkpoint_id = await ai_state_manager.create_checkpoint(target_session_id)
        
        logger.info("session_checkpoint_created", 
                   session_id=session.id,
                   target_session=target_session_id,
                   checkpoint_id=checkpoint_id)
        
        return create_standard_response(
            data={
                "checkpoint_id": checkpoint_id,
                "session_id": target_session_id,
                "created_at": time.time()
            },
            message="Session checkpoint created successfully"
        )
        
    except Exception as e:
        logger.error("session_checkpoint_failed", 
                    session_id=session.id,
                    target_session=target_session_id,
                    error=str(e), 
                    exc_info=True)
        return create_error_response(
            message="Failed to create session checkpoint",
            error_type="checkpoint_error",
            details={"session_id": session.id, "target_session": target_session_id},
            status_code=500
        )


@router.post("/sessions/{target_session_id}/restore/{checkpoint_id}")
@limiter.limit("3 per minute")
async def restore_session_checkpoint(
    target_session_id: str,
    checkpoint_id: str,
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Restore a conversation session from a checkpoint.
    
    Restores the conversation state from a previously created checkpoint.
    """
    try:
        # Verify the requesting user can access this session
        # In a full implementation, you'd check permissions here
        
        restored_state = await ai_state_manager.restore_from_checkpoint(
            target_session_id, 
            checkpoint_id
        )
        
        logger.info("session_checkpoint_restored", 
                   session_id=session.id,
                   target_session=target_session_id,
                   checkpoint_id=checkpoint_id,
                   restored_version=restored_state.state_version)
        
        return create_standard_response(
            data={
                "session_id": target_session_id,
                "checkpoint_id": checkpoint_id,
                "restored_version": restored_state.state_version,
                "restored_at": time.time()
            },
            message="Session restored from checkpoint successfully"
        )
        
    except Exception as e:
        logger.error("session_restore_failed", 
                    session_id=session.id,
                    target_session=target_session_id,
                    checkpoint_id=checkpoint_id,
                    error=str(e), 
                    exc_info=True)
        return create_error_response(
            message="Failed to restore session from checkpoint",
            error_type="restore_error",
            details={
                "session_id": session.id, 
                "target_session": target_session_id,
                "checkpoint_id": checkpoint_id
            },
            status_code=500
        )


@router.delete("/sessions/cleanup")
@limiter.limit("2 per hour")
async def cleanup_expired_sessions(
    request: Request,
    session: Session = Depends(get_current_session),
    expiry_hours: int = 24,
):
    """Clean up expired conversation sessions.
    
    Removes conversation sessions that haven't been active for the
    specified number of hours.
    """
    try:
        cleaned_count = await ai_state_manager.cleanup_expired_states(expiry_hours)
        
        logger.info("expired_sessions_cleaned", 
                   session_id=session.id,
                   cleaned_count=cleaned_count,
                   expiry_hours=expiry_hours)
        
        return create_standard_response(
            data={
                "cleaned_sessions": cleaned_count,
                "expiry_hours": expiry_hours,
                "cleaned_at": time.time()
            },
            message=f"Cleaned up {cleaned_count} expired sessions"
        )
        
    except Exception as e:
        logger.error("session_cleanup_failed", 
                    session_id=session.id,
                    error=str(e), 
                    exc_info=True)
        return create_error_response(
            message="Failed to clean up expired sessions",
            error_type="cleanup_error",
            details={"session_id": session.id},
            status_code=500
        )


@router.get("/metrics/summary")
@limiter.limit("10 per minute")
async def get_ai_metrics_summary(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get AI operations metrics summary.
    
    Returns a summary of AI operations metrics including operation counts,
    performance data, and error rates.
    """
    try:
        # In a production environment, these would be retrieved from the metrics store
        # For now, we return a basic summary structure
        metrics_summary = {
            "operations": {
                "total_chat_requests": 0,  # Would come from metrics
                "total_stream_requests": 0,
                "total_tool_executions": 0,
                "success_rate": 0.95,  # Would be calculated
            },
            "performance": {
                "average_response_time_seconds": 2.5,  # Would come from metrics
                "average_tokens_per_request": 150,
                "peak_concurrent_sessions": 10,
            },
            "errors": {
                "llm_errors_last_hour": 0,
                "tool_errors_last_hour": 0,
                "total_errors_last_24h": 0,
            },
            "timestamp": time.time()
        }
        
        logger.info("ai_metrics_summary_requested", session_id=session.id)
        
        return create_standard_response(
            data=metrics_summary,
            message="AI metrics summary retrieved successfully"
        )
        
    except Exception as e:
        logger.error("ai_metrics_summary_failed", session_id=session.id, error=str(e), exc_info=True)
        return create_error_response(
            message="Failed to retrieve AI metrics summary",
            error_type="metrics_error",
            details={"session_id": session.id},
            status_code=500
        )