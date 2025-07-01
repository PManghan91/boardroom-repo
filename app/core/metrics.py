"""Prometheus metrics configuration for the application.

This module sets up and configures Prometheus metrics for monitoring the application.
"""

from prometheus_client import Counter, Histogram, Gauge
from starlette_prometheus import metrics, PrometheusMiddleware

# Request metrics
http_requests_total = Counter("http_requests_total", "Total number of HTTP requests", ["method", "endpoint", "status"])

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds", "HTTP request duration in seconds", ["method", "endpoint"]
)

# Database metrics
db_connections = Gauge("db_connections", "Number of active database connections")

# Custom business metrics
orders_processed = Counter("orders_processed_total", "Total number of orders processed")

llm_inference_duration_seconds = Histogram(
    "llm_inference_duration_seconds",
    "Time spent processing LLM inference",
    ["model"],
    buckets=[0.1, 0.3, 0.5, 1.0, 2.0, 5.0]
)



llm_stream_duration_seconds = Histogram(
    "llm_stream_duration_seconds",
    "Time spent processing LLM stream inference",
    ["model"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# AI Operation metrics
ai_operations_total = Counter(
    "ai_operations_total",
    "Total number of AI operations",
    ["operation", "model", "status"]
)

ai_operation_duration_seconds = Histogram(
    "ai_operation_duration_seconds",
    "Time spent on AI operations",
    ["operation", "model"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

ai_token_usage_total = Counter(
    "ai_token_usage_total",
    "Total tokens used in AI operations",
    ["model", "operation"]
)

ai_tool_executions_total = Counter(
    "ai_tool_executions_total",
    "Total number of tool executions",
    ["tool_name", "status"]
)

ai_tool_duration_seconds = Histogram(
    "ai_tool_duration_seconds",
    "Time spent executing tools",
    ["tool_name"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

ai_graph_node_executions_total = Counter(
    "ai_graph_node_executions_total",
    "Total number of graph node executions",
    ["node_name", "status"]
)

ai_conversation_turns_total = Counter(
    "ai_conversation_turns_total",
    "Total number of conversation turns",
    ["session_type"]
)

ai_state_operations_total = Counter(
    "ai_state_operations_total",
    "Total number of state operations",
    ["operation", "status"]
)

# Cache metrics
cache_operations_total = Counter(
    "cache_operations_total",
    "Total number of cache operations",
    ["operation", "status"]
)

cache_hit_ratio = Gauge(
    "cache_hit_ratio",
    "Cache hit ratio percentage"
)

cache_size_bytes = Gauge(
    "cache_size_bytes",
    "Current cache size in bytes"
)

cache_keys_total = Gauge(
    "cache_keys_total",
    "Total number of keys in cache"
)

cache_operation_duration_seconds = Histogram(
    "cache_operation_duration_seconds",
    "Time spent on cache operations",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
)

cache_connections_active = Gauge(
    "cache_connections_active",
    "Number of active cache connections"
)

cache_memory_usage_bytes = Gauge(
    "cache_memory_usage_bytes",
    "Memory usage of cache in bytes"
)


def setup_metrics(app):
    """Set up Prometheus metrics middleware and endpoints.

    Args:
        app: FastAPI application instance
    """
    # Add Prometheus middleware
    app.add_middleware(PrometheusMiddleware)

    # Add metrics endpoint
    app.add_route("/metrics", metrics)
