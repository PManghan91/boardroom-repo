"""AI Operations schemas for enhanced LangGraph integration."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class AIOperationStatus(str, Enum):
    """Status of an AI operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class TokenUsage(BaseModel):
    """Token usage information for AI operations."""
    
    prompt_tokens: int = Field(default=0, description="Number of tokens in the prompt")
    completion_tokens: int = Field(default=0, description="Number of tokens in the completion")
    total_tokens: int = Field(default=0, description="Total number of tokens used")
    
    def calculate_total(self) -> None:
        """Calculate and set the total tokens."""
        self.total_tokens = self.prompt_tokens + self.completion_tokens


class AIOperationMetrics(BaseModel):
    """Metrics for AI operations."""
    
    operation_id: str = Field(description="Unique operation identifier")
    operation_type: str = Field(description="Type of operation (llm_inference, tool_execution, etc.)")
    model: Optional[str] = Field(default=None, description="AI model used")
    status: AIOperationStatus = Field(description="Operation status")
    
    start_time: datetime = Field(description="Operation start time")
    end_time: Optional[datetime] = Field(default=None, description="Operation end time")
    duration_seconds: Optional[float] = Field(default=None, description="Operation duration in seconds")
    
    token_usage: Optional[TokenUsage] = Field(default=None, description="Token usage information")
    
    # Error information
    error_type: Optional[str] = Field(default=None, description="Error type if operation failed")
    error_message: Optional[str] = Field(default=None, description="Error message if operation failed")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional operation metadata")

    def complete_operation(self, success: bool = True, error_message: Optional[str] = None) -> None:
        """Mark operation as complete."""
        self.end_time = datetime.now()
        if self.start_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        
        if success:
            self.status = AIOperationStatus.COMPLETED
        else:
            self.status = AIOperationStatus.FAILED
            self.error_message = error_message


class ConversationContext(BaseModel):
    """Context information for conversations."""
    
    session_id: str = Field(description="Session identifier")
    user_id: Optional[str] = Field(default=None, description="User identifier")
    conversation_type: str = Field(default="chat", description="Type of conversation")
    
    # State management
    turn_count: int = Field(default=0, description="Number of turns in conversation")
    last_activity: datetime = Field(default_factory=datetime.now, description="Last activity timestamp")
    
    # Context metadata
    context_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context metadata")


class StreamingResponse(BaseModel):
    """Enhanced streaming response with metadata."""
    
    content: str = Field(default="", description="Content chunk")
    done: bool = Field(default=False, description="Whether streaming is complete")
    
    # Additional streaming metadata
    chunk_index: int = Field(default=0, description="Index of the current chunk")
    total_chunks: Optional[int] = Field(default=None, description="Total expected chunks")
    
    # Token information for the chunk
    tokens_in_chunk: Optional[int] = Field(default=None, description="Number of tokens in this chunk")
    cumulative_tokens: Optional[int] = Field(default=None, description="Cumulative tokens so far")
    
    # Performance metadata
    generation_time_ms: Optional[float] = Field(default=None, description="Time to generate this chunk in milliseconds")


class ToolExecutionRequest(BaseModel):
    """Request for tool execution."""
    
    tool_name: str = Field(description="Name of the tool to execute")
    arguments: Dict[str, Any] = Field(description="Arguments for the tool")
    session_id: str = Field(description="Session identifier")
    
    # Execution options
    timeout_seconds: int = Field(default=30, description="Timeout for tool execution")
    retry_count: int = Field(default=3, description="Number of retries on failure")


class ToolExecutionResponse(BaseModel):
    """Response from tool execution."""
    
    tool_name: str = Field(description="Name of the executed tool")
    result: Any = Field(description="Tool execution result")
    status: AIOperationStatus = Field(description="Execution status")
    
    # Performance information
    execution_time_seconds: float = Field(description="Tool execution time")
    
    # Error information if applicable
    error_message: Optional[str] = Field(default=None, description="Error message if execution failed")
    error_type: Optional[str] = Field(default=None, description="Error type if execution failed")


class GraphNodeExecution(BaseModel):
    """Information about graph node execution."""
    
    node_name: str = Field(description="Name of the executed node")
    execution_id: str = Field(description="Unique execution identifier")
    session_id: str = Field(description="Session identifier")
    
    # Execution status
    status: AIOperationStatus = Field(description="Node execution status")
    start_time: datetime = Field(description="Node execution start time")
    end_time: Optional[datetime] = Field(default=None, description="Node execution end time")
    
    # Input/Output information
    input_data: Optional[Dict[str, Any]] = Field(default=None, description="Node input data")
    output_data: Optional[Dict[str, Any]] = Field(default=None, description="Node output data")
    
    # Error information
    error_message: Optional[str] = Field(default=None, description="Error message if node failed")


class ConversationState(BaseModel):
    """Enhanced conversation state for persistence."""
    
    session_id: str = Field(description="Session identifier")
    user_id: Optional[str] = Field(default=None, description="User identifier")
    
    # State information
    current_state: Dict[str, Any] = Field(default_factory=dict, description="Current conversation state")
    state_version: int = Field(default=1, description="State version for conflict resolution")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now, description="State creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last state update time")
    
    # Recovery information
    checkpoint_data: Optional[Dict[str, Any]] = Field(default=None, description="Checkpoint data for recovery")
    
    def update_state(self, new_state: Dict[str, Any]) -> None:
        """Update the conversation state."""
        self.current_state.update(new_state)
        self.state_version += 1
        self.updated_at = datetime.now()


class AIHealthCheck(BaseModel):
    """Health check information for AI operations."""
    
    model_config = ConfigDict(extra="allow")
    
    # Overall status
    status: str = Field(description="Overall AI operations status")
    
    # Model availability
    models_available: List[str] = Field(default_factory=list, description="Available models")
    models_unavailable: List[str] = Field(default_factory=list, description="Unavailable models")
    
    # Performance metrics
    average_response_time_seconds: Optional[float] = Field(default=None, description="Average response time")
    successful_operations_rate: Optional[float] = Field(default=None, description="Success rate of operations")
    
    # Resource usage
    active_sessions: int = Field(default=0, description="Number of active sessions")
    total_token_usage_last_hour: int = Field(default=0, description="Token usage in the last hour")
    
    # Error information
    recent_errors: List[str] = Field(default_factory=list, description="Recent error types")
    
    # Timestamp
    checked_at: datetime = Field(default_factory=datetime.now, description="Health check timestamp")