# LangGraph Implementation Notes

**Document Version**: 1.0  
**Last Updated**: January 2025  
**Author**: Founder + Claude Code  
**Audience**: AI/Backend Developers  
**Next Review**: With LangGraph updates  

## Overview

Boardroom AI uses LangGraph to orchestrate complex AI workflows with stateful conversation management. This document details our implementation patterns, state management approach, and integration points with FastAPI.

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   FastAPI       │────▶│   LangGraph     │────▶│    LLM API      │
│   Endpoints     │     │   Agent         │     │   (OpenAI)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                        
         │                       ▼                        
         │              ┌─────────────────┐              
         │              │   PostgreSQL    │              
         └─────────────▶│  Checkpoints    │              
                        └─────────────────┘              
```

## Core Components

### 1. LangGraph Agent

Location: `app/core/langgraph/agent.py`

The main orchestrator for AI workflows:

```python
class LangGraphAgent:
    """Main agent for orchestrating LangGraph workflows."""
    
    def __init__(self):
        self.llm = self._create_llm()
        self.tools = self._setup_tools()
        self.checkpointer = self._setup_checkpointer()
        self.graph = self._create_graph()
    
    def _create_graph(self) -> StateGraph:
        """Create the workflow graph."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("agent", self.call_model)
        workflow.add_node("tools", self.execute_tools)
        
        # Add edges
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges(
            "agent",
            self.should_continue,
            {
                "continue": "tools",
                "end": END,
            }
        )
        workflow.add_edge("tools", "agent")
        
        return workflow.compile(checkpointer=self.checkpointer)
```

### 2. State Management

The conversation state is managed through:

```python
class AgentState(TypedDict):
    """State schema for the agent."""
    messages: Annotated[list[BaseMessage], add_messages]
    thread_id: str
    user_id: Optional[str]
    session_id: Optional[str]
    context: Optional[Dict[str, Any]]
```

### 3. Checkpoint Storage

PostgreSQL-based persistence:

```python
async def _setup_checkpointer(self) -> AsyncPostgresSaver:
    """Set up PostgreSQL checkpointer for conversation persistence."""
    return AsyncPostgresSaver.from_conn_string(
        settings.POSTGRES_URL,
        checkpoint_tables=["checkpoints", "checkpoint_writes", "checkpoint_blobs"]
    )
```

## Workflow Patterns

### Basic Conversation Flow

```python
# 1. User sends message
# 2. Agent processes message
# 3. Agent decides: respond or use tools?
# 4. If tools needed, execute and return to agent
# 5. Agent generates final response

async def process_message(
    self,
    message: str,
    thread_id: str,
    user_id: Optional[str] = None
) -> str:
    """Process a user message through the graph."""
    
    # Create initial state
    state = {
        "messages": [HumanMessage(content=message)],
        "thread_id": thread_id,
        "user_id": user_id
    }
    
    # Run the graph
    config = {"configurable": {"thread_id": thread_id}}
    result = await self.graph.ainvoke(state, config)
    
    # Extract response
    return result["messages"][-1].content
```

### Tool Integration

Tools extend the agent's capabilities:

```python
class MeetingManagementTool(BaseTool):
    """Tool for managing meetings and boardrooms."""
    
    name = "meeting_management"
    description = "Manage meetings, boardrooms, and participants"
    
    async def _arun(
        self,
        action: str,
        params: Dict[str, Any]
    ) -> str:
        """Execute meeting management actions."""
        if action == "create_meeting":
            return await self._create_meeting(params)
        elif action == "add_participant":
            return await self._add_participant(params)
        # ... more actions
```

### Conditional Routing

Decision logic for workflow branching:

```python
def should_continue(self, state: AgentState) -> str:
    """Determine if we should continue or end."""
    messages = state["messages"]
    last_message = messages[-1]
    
    # If LLM decides to use a tool
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "continue"
    
    # If conversation should end
    if self._is_conversation_complete(state):
        return "end"
    
    return "continue"
```

## State Persistence

### Checkpoint Creation

Checkpoints are created automatically after each step:

```python
# Checkpoint structure in PostgreSQL
{
    "thread_id": "session_123",
    "thread_ts": "2025-01-07T10:30:00Z",
    "checkpoint": {
        "messages": [...],
        "context": {...},
        "tool_calls": [...],
        "metadata": {...}
    }
}
```

### State Recovery

Restore conversation from checkpoint:

```python
async def resume_conversation(
    self,
    thread_id: str
) -> Optional[AgentState]:
    """Resume a conversation from checkpoint."""
    config = {"configurable": {"thread_id": thread_id}}
    
    # Get latest checkpoint
    checkpoint = await self.checkpointer.aget(config)
    
    if checkpoint:
        return checkpoint["data"]
    return None
```

## Integration with FastAPI

### Endpoint Integration

```python
@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    agent: LangGraphAgent = Depends(get_agent)
):
    """Process chat message through LangGraph."""
    
    # Get or create thread
    thread_id = request.session_id or str(uuid.uuid4())
    
    # Process message
    response = await agent.process_message(
        message=request.message,
        thread_id=thread_id,
        user_id=str(current_user.id)
    )
    
    return ChatResponse(
        response=response,
        session_id=thread_id,
        message_id=str(uuid.uuid4())
    )
```

### Streaming Responses

For real-time responses:

```python
@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """Stream chat responses using SSE."""
    
    async def event_generator():
        async for chunk in agent.astream_events(
            {"messages": [HumanMessage(content=request.message)]},
            {"configurable": {"thread_id": request.session_id}}
        ):
            if chunk["event"] == "on_llm_stream":
                yield f"data: {json.dumps({'text': chunk['data']['chunk']})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

## Error Handling

### Retry Logic

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(RateLimitError)
)
async def call_model(self, state: AgentState) -> AgentState:
    """Call the LLM with retry logic."""
    try:
        response = await self.llm.ainvoke(state["messages"])
        return {"messages": [response]}
    except Exception as e:
        logger.error("llm_call_failed", error=str(e))
        # Fallback response
        return {
            "messages": [
                AIMessage(content="I encountered an error. Please try again.")
            ]
        }
```

### Graceful Degradation

```python
async def _setup_checkpointer(self) -> Optional[AsyncPostgresSaver]:
    """Set up checkpointer with fallback."""
    try:
        return AsyncPostgresSaver.from_conn_string(
            settings.POSTGRES_URL,
            checkpoint_tables=self.checkpoint_tables
        )
    except Exception as e:
        logger.warning(
            "checkpoint_setup_failed",
            error=str(e),
            message="Running without persistence"
        )
        return None
```

## Performance Optimization

### 1. Connection Pooling

```python
# Shared connection pool
async_engine = create_async_engine(
    settings.POSTGRES_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True
)

# Use with checkpointer
checkpointer = AsyncPostgresSaver(async_engine)
```

### 2. Caching Strategies

```python
class CachedLangGraphAgent(LangGraphAgent):
    """Agent with response caching."""
    
    async def process_message(self, message: str, thread_id: str) -> str:
        # Check cache first
        cache_key = f"chat:{thread_id}:{hash(message)}"
        cached = await redis_service.get(cache_key)
        
        if cached:
            return cached
        
        # Process normally
        response = await super().process_message(message, thread_id)
        
        # Cache response
        await redis_service.set(cache_key, response, ttl=1800)
        
        return response
```

### 3. Token Optimization

```python
def _create_llm(self) -> ChatOpenAI:
    """Create LLM with token limits."""
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=0.7,
        max_tokens=500,  # Limit response length
        model_kwargs={
            "top_p": 0.9,
            "frequency_penalty": 0.5
        }
    )
```

## Monitoring and Observability

### Langfuse Integration

```python
from langfuse.decorators import observe

@observe()
async def process_message(self, message: str, thread_id: str) -> str:
    """Process message with observability."""
    # Langfuse automatically tracks:
    # - Execution time
    # - Token usage
    # - Error rates
    # - LLM calls
```

### Custom Metrics

```python
# Track LangGraph performance
langgraph_latency = Histogram(
    "langgraph_processing_seconds",
    "Time spent processing in LangGraph"
)

langgraph_tokens = Counter(
    "langgraph_tokens_total",
    "Total tokens used by LangGraph",
    ["model", "operation"]
)
```

## Common Patterns

### 1. Multi-Turn Conversations

```python
# Maintain context across turns
state = {
    "messages": existing_messages + [new_message],
    "context": {
        "boardroom_id": "room_123",
        "meeting_type": "strategic_planning",
        "participants": ["user1", "user2"]
    }
}
```

### 2. Tool Chaining

```python
# Define tool sequence
workflow.add_node("search", SearchTool())
workflow.add_node("summarize", SummarizeTool())
workflow.add_node("format", FormatTool())

# Chain tools
workflow.add_edge("search", "summarize")
workflow.add_edge("summarize", "format")
```

### 3. Parallel Tool Execution

```python
# Execute tools in parallel
workflow.add_node("parallel_tools", parallel_tool_executor)

async def parallel_tool_executor(state):
    tasks = [
        tool1.arun(state),
        tool2.arun(state),
        tool3.arun(state)
    ]
    results = await asyncio.gather(*tasks)
    return combine_results(results)
```

## Troubleshooting

### Common Issues

1. **Checkpoint Not Found**
   - Check thread_id format
   - Verify PostgreSQL connection
   - Check table permissions

2. **Tool Execution Failures**
   - Validate tool parameters
   - Check tool permissions
   - Review error logs

3. **Memory Issues**
   - Limit message history
   - Implement message pruning
   - Use streaming for long responses

### Debug Mode

```python
# Enable debug logging
import langchain
langchain.debug = True

# Or use callbacks
from langchain.callbacks import StdOutCallbackHandler

llm = ChatOpenAI(callbacks=[StdOutCallbackHandler()])
```

## Best Practices

1. **State Design**
   - Keep state minimal
   - Use structured data
   - Implement state validation

2. **Tool Design**
   - Single responsibility
   - Clear descriptions
   - Comprehensive error handling

3. **Performance**
   - Cache when possible
   - Limit token usage
   - Use streaming for UX

4. **Reliability**
   - Implement retries
   - Graceful degradation
   - Comprehensive logging

## Future Enhancements

1. **Advanced Workflows**
   - Sub-graphs for complex flows
   - Dynamic tool loading
   - Custom routing logic

2. **Optimization**
   - Response caching
   - Parallel processing
   - Token optimization

3. **Features**
   - Multi-agent collaboration
   - Long-term memory
   - Custom checkpointers

## Related Documentation

- [System Architecture](./system_overview.md)
- [AI Service Documentation](../services/ai_service.md)
- [API Integration](../api/ai_endpoints.md)
- [Performance Guide](../operations/performance.md)

---

**LangGraph Resources**: 
- [Official Documentation](https://python.langchain.com/docs/langgraph)
- [Checkpoint Guide](https://python.langchain.com/docs/langgraph/how-tos/persistence)