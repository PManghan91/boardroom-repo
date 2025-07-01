# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
- Install dependencies: `uv sync`
- Run development server: `make dev`
- Run staging server: `make staging`
- Run production server: `make prod`

### Code Quality
- Lint code: `make lint` (uses ruff)
- Format code: `make format` (uses ruff)

### Testing
- Run tests: `pytest` (see pyproject.toml for configuration)
- Available test files: `tests/test_api.py`, `tests/test_worker.py`

### Docker Operations
- Build Docker image: `make docker-build-env ENV=development`
- Run Docker container: `make docker-run-env ENV=development`
- Start full stack: `make docker-compose-up ENV=development`
- View logs: `make docker-logs ENV=development`
- Stop services: `make docker-stop ENV=development`

### Evaluation Framework
- Run interactive evaluation: `make eval ENV=development`
- Run quick evaluation: `make eval-quick ENV=development`
- Run evaluation without reports: `make eval-no-report ENV=development`

## Architecture Overview

### Core Components
- **FastAPI Application**: Main web framework with async endpoints
- **LangGraph Integration**: AI agent workflows in `app/core/langgraph/`
- **PostgreSQL**: Data persistence with connection pooling
- **Redis**: Caching and event bus for worker communication
- **Langfuse**: LLM observability and monitoring
- **Prometheus + Grafana**: Metrics collection and visualization

### Key Directory Structure
- `app/api/v1/`: API endpoints and routers
- `app/core/`: Core application components (config, logging, metrics, LangGraph)
- `app/models/`: Database models using SQLModel
- `app/schemas/`: Pydantic schemas for API validation
- `app/services/`: Business logic and external service integrations
- `app/workers/`: Background workers and async task processing
- `evals/`: Model evaluation framework with metrics

### Environment Configuration
- Uses environment-specific config files: `.env.development`, `.env.staging`, `.env.production`
- Environment is set via `APP_ENV` variable
- Configuration handled in `app/core/config.py` with `Settings` class

### LangGraph Agent Architecture
- **Main Agent**: `LangGraphAgent` class in `app/core/langgraph/graph.py`
- **State Management**: Uses PostgreSQL checkpointer for conversation persistence
- **Tools**: External tool integrations in `app/core/langgraph/tools/`
- **Prompts**: System prompts stored in `app/core/prompts/`

### Database Architecture
- **SQLModel/SQLAlchemy**: ORM for database operations
- **Connection Pooling**: Configured per environment with size limits
- **Migrations**: Managed via Alembic (see `migrations/` directory)
- **Tables**: Core models in `app/models/` (Thread, User, Session, etc.)

### Authentication & Security
- **JWT-based authentication**: Handled in `app/api/v1/auth.py`
- **Rate limiting**: Environment-specific limits via SlowAPI
- **Input sanitization**: Request validation and sanitization utilities
- **CORS**: Configurable origins per environment

### Monitoring & Observability
- **Structured Logging**: Uses structlog with environment-specific formatting
- **Metrics**: Prometheus metrics for API performance, LLM calls, rate limiting
- **Tracing**: Langfuse integration for LLM observability
- **Health Checks**: Available at `/health` endpoint

### Worker System
- **Stream Worker**: Handles async streaming responses in `app/workers/stream_worker.py`
- **Event Bus**: Redis-based communication between services
- **Background Tasks**: Async task processing with proper error handling

## Development Guidelines

### Environment-Specific Behavior
- Development: Debug logging, relaxed rate limits, console log format
- Staging: Balanced settings for testing
- Production: Warning-level logging, strict rate limits, JSON log format, fallback models

### Code Conventions
- Type hints throughout codebase
- Async/await for I/O operations
- Environment-specific configuration overrides
- Comprehensive error logging with structured context

### Testing Strategy
- Async test support via pytest-asyncio
- Fake Redis for testing with fakeredis
- HTTP client testing with httpx
- Test markers for slow tests

### Error Handling
- Graceful degradation in production (continues without checkpointer/connection pool if needed)
- Retry logic for LLM calls with fallback models
- Comprehensive logging of failures with context

### Rate Limiting
- Environment-specific rate limits
- Per-endpoint customization
- Configurable via environment variables with `RATE_LIMIT_` prefix

## Important Notes

- Always test with appropriate environment (development/staging) before production
- Database migrations should be handled via Alembic
- LLM API keys must be set for agent functionality
- Redis is required for worker communication
- PostgreSQL connection is required for conversation persistence