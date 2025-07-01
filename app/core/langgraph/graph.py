"""This file contains the LangGraph Agent/workflow and interactions with the LLM."""

import time
import uuid
from datetime import datetime
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Literal,
    Optional,
)

from asgiref.sync import sync_to_async
from langchain_core.messages import (
    BaseMessage,
    ToolMessage,
    convert_to_openai_messages,
)
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import (
    END,
    StateGraph,
)
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StateSnapshot
from openai import OpenAIError
from psycopg_pool import AsyncConnectionPool

from app.core.config import (
    Environment,
    settings,
)
from app.core.langgraph.tools import tools
from app.core.logging import logger
from app.core.metrics import (
    llm_inference_duration_seconds,
    ai_operations_total,
    ai_operation_duration_seconds,
    ai_token_usage_total,
    ai_graph_node_executions_total,
    ai_conversation_turns_total,
)
from app.core.prompts import SYSTEM_PROMPT
from app.core.exceptions import (
    raise_llm_error,
    raise_graph_execution_error,
    raise_tool_execution_error,
    LLMException,
    GraphExecutionException,
    ToolExecutionException,
)
from app.core.error_monitoring import record_error
from app.schemas import (
    GraphState,
    Message,
)
from app.schemas.ai_operations import (
    AIOperationMetrics,
    AIOperationStatus,
    TokenUsage,
    ConversationContext,
)
from app.services.ai_state_manager import ai_state_manager
from app.utils import (
    dump_messages,
    prepare_messages,
)


class LangGraphAgent:
    """Enhanced LangGraph Agent with comprehensive AI operations monitoring and error handling.

    This class handles the creation and management of the LangGraph workflow,
    including LLM interactions, database connections, response processing,
    performance monitoring, and advanced error handling.
    """

    def __init__(self):
        """Initialize the LangGraph Agent with necessary components."""
        # Use environment-specific LLM model
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.DEFAULT_LLM_TEMPERATURE,
            api_key=settings.LLM_API_KEY,
            max_tokens=settings.MAX_TOKENS,
            **self._get_model_kwargs(),
        ).bind_tools(tools)
        self.tools_by_name = {tool.name: tool for tool in tools}
        self._connection_pool: Optional[AsyncConnectionPool] = None
        self._graph: Optional[CompiledStateGraph] = None
        self._active_operations: Dict[str, AIOperationMetrics] = {}

        logger.info("llm_initialized", model=settings.LLM_MODEL, environment=settings.ENVIRONMENT.value)

    def _get_model_kwargs(self) -> Dict[str, Any]:
        """Get environment-specific model kwargs.

        Returns:
            Dict[str, Any]: Additional model arguments based on environment
        """
        model_kwargs = {}

        # Development - we can use lower speeds for cost savings
        if settings.ENVIRONMENT == Environment.DEVELOPMENT:
            model_kwargs["top_p"] = 0.8

        # Production - use higher quality settings
        elif settings.ENVIRONMENT == Environment.PRODUCTION:
            model_kwargs["top_p"] = 0.95
            model_kwargs["presence_penalty"] = 0.1
            model_kwargs["frequency_penalty"] = 0.1

        return model_kwargs

    async def _get_connection_pool(self) -> AsyncConnectionPool:
        """Get a PostgreSQL connection pool using environment-specific settings.

        Returns:
            AsyncConnectionPool: A connection pool for PostgreSQL database.
        """
        if self._connection_pool is None:
            try:
                # Configure pool size based on environment
                max_size = settings.POSTGRES_POOL_SIZE

                self._connection_pool = AsyncConnectionPool(
                    settings.POSTGRES_URL,
                    open=False,
                    max_size=max_size,
                    kwargs={
                        "autocommit": True,
                        "connect_timeout": 5,
                        "prepare_threshold": None,
                    },
                )
                await self._connection_pool.open()
                logger.info("connection_pool_created", max_size=max_size, environment=settings.ENVIRONMENT.value)
            except Exception as e:
                logger.error("connection_pool_creation_failed", error=str(e), environment=settings.ENVIRONMENT.value)
                # In production, we might want to degrade gracefully
                if settings.ENVIRONMENT == Environment.PRODUCTION:
                    logger.warning("continuing_without_connection_pool", environment=settings.ENVIRONMENT.value)
                    return None
                raise e
        return self._connection_pool

    async def _chat(self, state: GraphState) -> dict:
        """Process the chat state and generate a response with enhanced monitoring.

        Args:
            state (GraphState): The current state of the conversation.

        Returns:
            dict: Updated state with new messages.
        """
        operation_id = str(uuid.uuid4())
        
        # Create operation metrics
        operation_metrics = AIOperationMetrics(
            operation_id=operation_id,
            operation_type="llm_inference",
            model=settings.LLM_MODEL,
            status=AIOperationStatus.IN_PROGRESS,
            start_time=datetime.now()
        )
        self._active_operations[operation_id] = operation_metrics

        try:
            ai_operations_total.labels(operation="llm_inference", model=settings.LLM_MODEL, status="started").inc()
            ai_graph_node_executions_total.labels(node_name="chat", status="started").inc()
            
            messages = prepare_messages(state.messages, self.llm, SYSTEM_PROMPT)
            llm_calls_num = 0
            max_retries = settings.MAX_LLM_CALL_RETRIES

            for attempt in range(max_retries):
                try:
                    start_time = time.time()
                    
                    with llm_inference_duration_seconds.labels(model=self.llm.model_name).time():
                        with ai_operation_duration_seconds.labels(operation="llm_inference", model=settings.LLM_MODEL).time():
                            response = await self.llm.ainvoke(dump_messages(messages))
                            generated_state = {"messages": [response]}
                    
                    # Record token usage if available
                    if hasattr(response, 'usage') and response.usage:
                        token_usage = TokenUsage(
                            prompt_tokens=getattr(response.usage, 'prompt_tokens', 0),
                            completion_tokens=getattr(response.usage, 'completion_tokens', 0)
                        )
                        token_usage.calculate_total()
                        operation_metrics.token_usage = token_usage
                        
                        # Update metrics
                        ai_token_usage_total.labels(model=settings.LLM_MODEL, operation="inference").inc(token_usage.total_tokens)
                    
                    # Complete operation successfully
                    operation_metrics.complete_operation(success=True)
                    ai_operations_total.labels(operation="llm_inference", model=settings.LLM_MODEL, status="success").inc()
                    ai_graph_node_executions_total.labels(node_name="chat", status="success").inc()
                    
                    logger.info(
                        "llm_response_generated",
                        session_id=state.session_id,
                        operation_id=operation_id,
                        llm_calls_num=llm_calls_num + 1,
                        model=settings.LLM_MODEL,
                        duration_seconds=operation_metrics.duration_seconds,
                        token_usage=operation_metrics.token_usage.total_tokens if operation_metrics.token_usage else None,
                        environment=settings.ENVIRONMENT.value,
                    )
                    
                    return generated_state
                    
                except OpenAIError as e:
                    llm_calls_num += 1
                    error_msg = f"LLM call failed (attempt {attempt + 1}/{max_retries}): {str(e)}"
                    
                    # Record error for monitoring
                    record_error(
                        error_type="llm_call_error",
                        path="/api/v1/chat",
                        status_code=503,
                        error_message=error_msg
                    )
                    
                    logger.error(
                        "llm_call_failed",
                        operation_id=operation_id,
                        llm_calls_num=llm_calls_num,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        error=str(e),
                        environment=settings.ENVIRONMENT.value,
                    )

                    # In production, try fallback model on second-to-last attempt
                    if settings.ENVIRONMENT == Environment.PRODUCTION and attempt == max_retries - 2:
                        fallback_model = "gpt-4o"
                        logger.warning(
                            "using_fallback_model",
                            operation_id=operation_id,
                            model=fallback_model,
                            environment=settings.ENVIRONMENT.value
                        )
                        self.llm.model_name = fallback_model

                    if attempt == max_retries - 1:
                        # Final attempt failed
                        operation_metrics.complete_operation(success=False, error_message=error_msg)
                        ai_operations_total.labels(operation="llm_inference", model=settings.LLM_MODEL, status="error").inc()
                        ai_graph_node_executions_total.labels(node_name="chat", status="error").inc()
                        raise_llm_error(f"Failed to get response from LLM after {max_retries} attempts: {str(e)}", settings.LLM_MODEL)

        except Exception as e:
            operation_metrics.complete_operation(success=False, error_message=str(e))
            ai_operations_total.labels(operation="llm_inference", model=settings.LLM_MODEL, status="error").inc()
            ai_graph_node_executions_total.labels(node_name="chat", status="error").inc()
            
            if not isinstance(e, LLMException):
                logger.error("chat_node_execution_failed", operation_id=operation_id, error=str(e), exc_info=True)
                raise_graph_execution_error(f"Chat node execution failed: {str(e)}", "chat", state.session_id)
            raise
        finally:
            # Clean up operation tracking
            if operation_id in self._active_operations:
                del self._active_operations[operation_id]

    async def _tool_call(self, state: GraphState) -> GraphState:
        """Process tool calls with enhanced monitoring and error handling.

        Args:
            state: The current agent state containing messages and tool calls.

        Returns:
            Dict with updated messages containing tool responses.
        """
        operation_id = str(uuid.uuid4())
        
        try:
            ai_graph_node_executions_total.labels(node_name="tool_call", status="started").inc()
            
            outputs = []
            last_message = state.messages[-1]
            
            if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
                logger.warning("tool_call_node_no_tools", session_id=state.session_id, operation_id=operation_id)
                return {"messages": []}
            
            for tool_call in last_message.tool_calls:
                tool_name = tool_call["name"]
                
                try:
                    if tool_name not in self.tools_by_name:
                        error_msg = f"Tool '{tool_name}' not found"
                        logger.error("tool_not_found", tool_name=tool_name, operation_id=operation_id)
                        raise_tool_execution_error(error_msg, tool_name)
                    
                    start_time = time.time()
                    
                    # Execute tool with monitoring
                    tool_result = await self.tools_by_name[tool_name].ainvoke(tool_call["args"])
                    
                    duration = time.time() - start_time
                    
                    # Create tool response message
                    tool_message = ToolMessage(
                        content=tool_result,
                        name=tool_name,
                        tool_call_id=tool_call["id"],
                    )
                    outputs.append(tool_message)
                    
                    logger.info("tool_executed_successfully",
                               tool_name=tool_name,
                               operation_id=operation_id,
                               duration_seconds=duration)
                    
                except Exception as e:
                    error_msg = f"Tool execution failed for '{tool_name}': {str(e)}"
                    
                    # Record error for monitoring
                    record_error(
                        error_type="tool_execution_error",
                        path=f"/tool/{tool_name}",
                        status_code=500,
                        error_message=error_msg
                    )
                    
                    logger.error("tool_execution_failed",
                                tool_name=tool_name,
                                operation_id=operation_id,
                                error=str(e),
                                exc_info=True)
                    
                    # Create error response message
                    error_message = ToolMessage(
                        content=f"Error executing tool {tool_name}: {str(e)}",
                        name=tool_name,
                        tool_call_id=tool_call["id"],
                    )
                    outputs.append(error_message)
            
            ai_graph_node_executions_total.labels(node_name="tool_call", status="success").inc()
            return {"messages": outputs}
            
        except Exception as e:
            ai_graph_node_executions_total.labels(node_name="tool_call", status="error").inc()
            logger.error("tool_call_node_failed", operation_id=operation_id, error=str(e), exc_info=True)
            raise_graph_execution_error(f"Tool call node execution failed: {str(e)}", "tool_call", state.session_id)

    def _should_continue(self, state: GraphState) -> Literal["end", "continue"]:
        """Determine if the agent should continue or end based on the last message.

        Args:
            state: The current agent state containing messages.

        Returns:
            Literal["end", "continue"]: "end" if there are no tool calls, "continue" otherwise.
        """
        messages = state.messages
        last_message = messages[-1]
        # If there is no function call, then we finish
        if not last_message.tool_calls:
            return "end"
        # Otherwise if there is, we continue
        else:
            return "continue"

    async def create_graph(self) -> Optional[CompiledStateGraph]:
        """Create and configure the LangGraph workflow.

        Returns:
            Optional[CompiledStateGraph]: The configured LangGraph instance or None if init fails
        """
        if self._graph is None:
            try:
                graph_builder = StateGraph(GraphState)
                graph_builder.add_node("chat", self._chat)
                graph_builder.add_node("tool_call", self._tool_call)
                graph_builder.add_conditional_edges(
                    "chat",
                    self._should_continue,
                    {"continue": "tool_call", "end": END},
                )
                graph_builder.add_edge("tool_call", "chat")
                graph_builder.set_entry_point("chat")
                graph_builder.set_finish_point("chat")

                # Get connection pool (may be None in production if DB unavailable)
                connection_pool = await self._get_connection_pool()
                if connection_pool:
                    checkpointer = AsyncPostgresSaver(connection_pool)
                    await checkpointer.setup()
                else:
                    # In production, proceed without checkpointer if needed
                    checkpointer = None
                    if settings.ENVIRONMENT != Environment.PRODUCTION:
                        raise Exception("Connection pool initialization failed")

                self._graph = graph_builder.compile(
                    checkpointer=checkpointer, name=f"{settings.PROJECT_NAME} Agent ({settings.ENVIRONMENT.value})"
                )

                logger.info(
                    "graph_created",
                    graph_name=f"{settings.PROJECT_NAME} Agent",
                    environment=settings.ENVIRONMENT.value,
                    has_checkpointer=checkpointer is not None,
                )
            except Exception as e:
                logger.error("graph_creation_failed", error=str(e), environment=settings.ENVIRONMENT.value)
                # In production, we don't want to crash the app
                if settings.ENVIRONMENT == Environment.PRODUCTION:
                    logger.warning("continuing_without_graph")
                    return None
                raise e

        return self._graph

    async def get_response(
        self,
        messages: list[Message],
        session_id: str,
        user_id: Optional[str] = None,
    ) -> list[dict]:
        """Get a response from the LLM.

        Args:
            messages (list[Message]): The messages to send to the LLM.
            session_id (str): The session ID for Langfuse tracking.
            user_id (Optional[str]): The user ID for Langfuse tracking.

        Returns:
            list[dict]: The response from the LLM.
        """
        if self._graph is None:
            self._graph = await self.create_graph()
        config = {
            "configurable": {"thread_id": session_id},
            "callbacks": [
                CallbackHandler(
                    environment=settings.ENVIRONMENT.value,
                    debug=False,
                    user_id=user_id,
                    session_id=session_id,
                )
            ],
        }
        try:
            response = await self._graph.ainvoke(
                {"messages": dump_messages(messages), "session_id": session_id}, config
            )
            return self.__process_messages(response["messages"])
        except Exception as e:
            logger.error(f"Error getting response: {str(e)}")
            raise e

    async def get_stream_response(
        self, messages: list[Message], session_id: str, user_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Get a stream response from the LLM.

        Args:
            messages (list[Message]): The messages to send to the LLM.
            session_id (str): The session ID for the conversation.
            user_id (Optional[str]): The user ID for the conversation.

        Yields:
            str: Tokens of the LLM response.
        """
        config = {
            "configurable": {"thread_id": session_id},
            "callbacks": [
                CallbackHandler(
                    environment=settings.ENVIRONMENT.value, debug=False, user_id=user_id, session_id=session_id
                )
            ],
        }
        if self._graph is None:
            self._graph = await self.create_graph()

        try:
            async for token, _ in self._graph.astream(
                {"messages": dump_messages(messages), "session_id": session_id}, config, stream_mode="messages"
            ):
                try:
                    yield token.content
                except Exception as token_error:
                    logger.error("Error processing token", error=str(token_error), session_id=session_id)
                    # Continue with next token even if current one fails
                    continue
        except Exception as stream_error:
            logger.error("Error in stream processing", error=str(stream_error), session_id=session_id)
            raise stream_error

    async def get_chat_history(self, session_id: str) -> list[Message]:
        """Get the chat history for a given thread ID.

        Args:
            session_id (str): The session ID for the conversation.

        Returns:
            list[Message]: The chat history.
        """
        if self._graph is None:
            self._graph = await self.create_graph()

        state: StateSnapshot = await sync_to_async(self._graph.get_state)(
            config={"configurable": {"thread_id": session_id}}
        )
        return self.__process_messages(state.values["messages"]) if state.values else []

    def __process_messages(self, messages: list[BaseMessage]) -> list[Message]:
        openai_style_messages = convert_to_openai_messages(messages)
        # keep just assistant and user messages
        return [
            Message(**message)
            for message in openai_style_messages
            if message["role"] in ["assistant", "user"] and message["content"]
        ]

    async def clear_chat_history(self, session_id: str) -> None:
        """Clear all chat history for a given thread ID.

        Args:
            session_id: The ID of the session to clear history for.

        Raises:
            Exception: If there's an error clearing the chat history.
        """
        try:
            # Make sure the pool is initialized in the current event loop
            conn_pool = await self._get_connection_pool()

            # Use a new connection for this specific operation
            async with conn_pool.connection() as conn:
                for table in settings.CHECKPOINT_TABLES:
                    try:
                        await conn.execute(f"DELETE FROM {table} WHERE thread_id = %s", (session_id,))
                        logger.info(f"Cleared {table} for session {session_id}")
                    except Exception as e:
                        logger.error(f"Error clearing {table}", error=str(e))
                        raise

        except Exception as e:
            logger.error("Failed to clear chat history", error=str(e))
            raise
