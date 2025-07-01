# Developer Reference Document

A comprehensive quick reference for developers working on the FastAPI LangGraph Agent Template project.

## Table of Contents

1. [Quick Start Commands](#quick-start-commands)
2. [API Reference](#api-reference)
3. [Database Schema Quick Reference](#database-schema-quick-reference)
4. [Environment & Configuration](#environment--configuration)
5. [Development Workflow](#development-workflow)
6. [Key Dependencies & Integrations](#key-dependencies--integrations)
7. [Troubleshooting Quick Reference](#troubleshooting-quick-reference)
8. [Project Structure Overview](#project-structure-overview)

---

## Quick Start Commands

### Development Server Startup

```bash
# Install dependencies
uv sync

# Development environment (with reload)
make dev

# Staging environment
make staging

# Production environment
make prod

# Set specific environment
make set-env ENV=development
source scripts/set_env.sh development
```

### Database Setup/Migration Commands

```bash
# Database connection is automatic via SQLModel
# Manual schema creation (if needed):
psql -h [HOST] -U [USER] -d [DATABASE] -f schema.sql

# Environment-specific database URLs:
# Development: Set in .env.development
# Staging: Set in .env.staging  
# Production: Set in .env.production
```

### Testing Commands

```bash
# Run tests (when test suite is implemented)
pytest

# Run with coverage
pytest --cov=app

# Run specific test files
pytest tests/test_*.py

# Run evaluation metrics
make eval                    # Interactive mode
make eval-quick             # Default settings
make eval-no-report         # No report generation
```

### Docker Commands

```bash
# Build Docker image
make docker-build
make docker-build-env ENV=development

# Run Docker container
make docker-run
make docker-run-env ENV=development

# Docker Compose (full stack)
make docker-compose-up ENV=development
make docker-compose-down ENV=development
make docker-compose-logs ENV=development

# View logs
make docker-logs ENV=development

# Stop containers
make docker-stop ENV=development
```

### Code Quality & Formatting

```bash
# Format code
make format
ruff format .

# Lint code
make lint
ruff check .

# Clean up
make clean
```

---

## API Reference

### Base URL
- **Development**: `http://localhost:8000`
- **API Prefix**: `/api/v1`
- **Documentation**: `http://localhost:8000/docs` (Swagger UI)

### Authentication Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/api/v1/auth/register` | POST | Register new user | 10 per hour |
| `/api/v1/auth/login` | POST | User login | 20 per minute |
| `/api/v1/auth/session` | POST | Create chat session | N/A |
| `/api/v1/auth/session/{session_id}/name` | PATCH | Update session name | N/A |
| `/api/v1/auth/session/{session_id}` | DELETE | Delete session | N/A |
| `/api/v1/auth/sessions` | GET | Get user sessions | N/A |

#### Authentication Requirements
- **Bearer Token**: Required for all protected endpoints
- **Format**: `Authorization: Bearer <jwt_token>`
- **Token Type**: JWT with HS256 algorithm
- **Expiry**: 30 days (configurable via `JWT_ACCESS_TOKEN_EXPIRE_DAYS`)

#### Request/Response Formats

**Register Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Login Request (Form Data):**
```
username=user@example.com
password=SecurePassword123!
grant_type=password
```

**Token Response:**
```json
{
  "access_token": "jwt_token_here",
  "token_type": "bearer",
  "expires_at": "2024-01-01T00:00:00Z"
}
```

### Chatbot Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/api/v1/chatbot/chat` | POST | Send chat message | 30 per minute |
| `/api/v1/chatbot/chat/stream` | POST | Stream chat response | 20 per minute |
| `/api/v1/chatbot/messages` | GET | Get chat history | 50 per minute |
| `/api/v1/chatbot/messages` | DELETE | Clear chat history | 50 per minute |

**Chat Request:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Hello, how can you help me?"
    }
  ]
}
```

**Chat Response:**
```json
{
  "messages": [
    {
      "role": "user", 
      "content": "Hello, how can you help me?"
    },
    {
      "role": "assistant",
      "content": "I can help you with various tasks..."
    }
  ]
}
```

### Decision/Boardroom Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/decisions/` | POST | Create decision |
| `/api/v1/decisions/{decision_id}` | GET | Get decision |
| `/api/v1/decisions/{decision_id}/rounds` | POST | Create decision round |
| `/api/v1/decisions/rounds/{round_id}/votes` | POST | Cast vote |
| `/api/v1/decisions/events` | GET | SSE event stream |

### Health & System Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/` | GET | Root endpoint | 10 per minute |
| `/health` | GET | Health check | 20 per minute |
| `/api/v1/health` | GET | API health check | 20 per minute |

### Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Invalid/missing token |
| 403 | Forbidden - Access denied |
| 404 | Not Found - Resource not found |
| 422 | Unprocessable Entity - Validation error |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |
| 503 | Service Unavailable - Database unavailable |

---

## Database Schema Quick Reference

### Tables

#### `user`
```sql
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

#### `session`
```sql
CREATE TABLE session (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);
```

#### `thread`
```sql
CREATE TABLE thread (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

#### LangGraph Checkpoint Tables
- `checkpoints` - LangGraph state checkpoints
- `checkpoint_writes` - LangGraph write operations
- `checkpoint_blobs` - LangGraph binary data

### Key Relationships
- `session.user_id` → `user.id` (CASCADE DELETE)
- Sessions are isolated per user
- Threads are independent conversation contexts

### Indexes
```sql
CREATE INDEX idx_user_email ON user(email);
CREATE INDEX idx_session_user_id ON session(user_id);
```

### Connection Strings
```bash
# Format
postgresql://[user]:[password]@[host]:[port]/[database]

# Example
postgresql://user:pass@localhost:5432/mydb
```

---

## Environment & Configuration

### Required Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `APP_ENV` | Environment (development/staging/production) | development | No |
| `POSTGRES_URL` | PostgreSQL connection string | - | Yes |
| `LLM_API_KEY` | OpenAI API key | - | Yes |
| `JWT_SECRET_KEY` | JWT signing secret | - | Yes |

### Optional Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PROJECT_NAME` | Application name | "FastAPI LangGraph Template" |
| `VERSION` | Application version | "1.0.0" |
| `API_V1_STR` | API prefix | "/api/v1" |
| `DEBUG` | Debug mode | false |
| `LOG_LEVEL` | Logging level | INFO |
| `LOG_FORMAT` | Log format (json/console) | json |
| `LLM_MODEL` | LLM model name | gpt-4o-mini |
| `DEFAULT_LLM_TEMPERATURE` | LLM temperature | 0.2 |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key | - |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key | - |
| `LANGFUSE_HOST` | Langfuse host | https://cloud.langfuse.com |

### Configuration File Locations

```
.env.development     # Development environment
.env.staging         # Staging environment  
.env.production      # Production environment
.env.example         # Template file
```

### Environment-Specific Settings

| Setting | Development | Staging | Production |
|---------|-------------|---------|------------|
| Debug | true | false | false |
| Log Level | DEBUG | INFO | WARNING |
| Log Format | console | json | json |
| Rate Limits | Relaxed | Moderate | Strict |

### Secret Management
- Store secrets in environment-specific `.env` files
- Never commit `.env` files to version control
- Use environment variables in production
- Rotate JWT secrets regularly

---

## Development Workflow

### Git Workflow Recommendations

```bash
# Feature development
git checkout -b feature/feature-name
git add .
git commit -m "feat: add new feature"
git push origin feature/feature-name

# Create pull request to main branch
```

### Branch Naming Conventions

- `feature/` - New features
- `fix/` - Bug fixes  
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions/updates

### Commit Message Standards

Follow conventional commits:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation
- `style:` - Formatting changes
- `refactor:` - Code refactoring
- `test:` - Adding tests
- `chore:` - Maintenance tasks

### Testing Requirements Before Commits

```bash
# Run linting
make lint

# Format code
make format

# Run tests (when implemented)
pytest

# Check for security issues
# (Add security scanning tools as needed)
```

### Code Review Checklist
- [ ] Code follows project style guidelines
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] Security considerations addressed
- [ ] Performance impact assessed
- [ ] Error handling implemented

---

## Key Dependencies & Integrations

### Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | >=0.115.12 | Web framework |
| `uvicorn` | >=0.34.0 | ASGI server |
| `sqlmodel` | >=0.0.24 | Database ORM |
| `psycopg2-binary` | >=2.9.10 | PostgreSQL adapter |

### LangGraph Configuration

| Package | Version | Purpose |
|---------|---------|---------|
| `langgraph` | >=0.4.1 | Graph-based agent framework |
| `langchain` | >=0.3.25 | LLM framework |
| `langchain-openai` | >=0.3.16 | OpenAI integration |
| `langgraph-checkpoint-postgres` | >=2.0.19 | PostgreSQL checkpointing |

**Setup:**
```python
# Initialize LangGraph agent
from app.core.langgraph.graph import LangGraphAgent
agent = LangGraphAgent()

# Use with PostgreSQL checkpointer
from langgraph.checkpoint.postgres import PostgresSaver
pg_saver = PostgresSaver.from_conn_string(settings.POSTGRES_URL)
```

### Authentication & Security

| Package | Version | Purpose |
|---------|---------|---------|
| `python-jose[cryptography]` | >=3.4.0 | JWT handling |
| `passlib[bcrypt]` | >=1.7.4 | Password hashing |
| `slowapi` | >=0.1.9 | Rate limiting |

### Monitoring & Observability

| Package | Version | Purpose |
|---------|---------|---------|
| `langfuse` | ==3.0.3 | LLM observability |
| `prometheus-client` | >=0.19.0 | Metrics collection |
| `structlog` | >=25.2.0 | Structured logging |

**Langfuse Setup:**
```python
from langfuse import Langfuse
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
)
```

### External Services Integration

| Service | Purpose | Configuration |
|---------|---------|---------------|
| PostgreSQL | Primary database | `POSTGRES_URL` |
| OpenAI API | LLM provider | `LLM_API_KEY` |
| Langfuse | Observability | `LANGFUSE_*` keys |
| Prometheus | Metrics | Auto-configured |
| Grafana | Dashboards | Docker Compose |

---

## Troubleshooting Quick Reference

### Common Errors and Solutions

#### Database Connection Issues

**Error:** `connection to server failed`
```bash
# Check database URL
echo $POSTGRES_URL

# Test connection
psql $POSTGRES_URL -c "SELECT 1;"

# Verify environment file loaded
source scripts/set_env.sh development
```

#### Authentication Errors

**Error:** `Invalid authentication credentials`
```bash
# Check JWT secret is set
echo $JWT_SECRET_KEY

# Verify token format
# Tokens should be: eyJ...

# Check token expiry
# Default: 30 days from JWT_ACCESS_TOKEN_EXPIRE_DAYS
```

#### Rate Limiting Issues

**Error:** `Rate limit exceeded`
```bash
# Check current rate limits
echo $RATE_LIMIT_DEFAULT

# Environment-specific limits:
# Development: 1000/day, 200/hour
# Staging: 500/day, 100/hour  
# Production: 200/day, 50/hour
```

#### LangGraph Errors

**Error:** `PostgresSaver initialization failed`
```bash
# Verify checkpoint tables exist
psql $POSTGRES_URL -c "\dt checkpoint*"

# Check LangGraph permissions
# Ensure user can CREATE/DROP tables
```

### Debug Commands

```bash
# Check environment loading
make set-env ENV=development

# View application logs
tail -f logs/app.log

# Database connection test
python -c "from app.services.database import database_service; print(database_service.health_check())"

# LLM API test  
python -c "import openai; print(openai.api_key[:10] + '...')"

# Check all environment variables
env | grep -E "(POSTGRES|LLM|JWT|LANGFUSE)"
```

### Log File Locations

```
logs/
├── app.log              # Application logs
├── access.log           # HTTP access logs
└── error.log            # Error logs
```

### Health Check Endpoints

```bash
# Application health
curl http://localhost:8000/health

# API health  
curl http://localhost:8000/api/v1/health

# Database connectivity
curl http://localhost:8000/health | jq .components.database
```

### Performance Monitoring

```bash
# Prometheus metrics
curl http://localhost:9090

# Grafana dashboards
# http://localhost:3000
# Username: admin
# Password: admin

# Application metrics endpoint
curl http://localhost:8000/metrics
```

---

## Project Structure Overview

### Key Directories

```
boardroom-repo/
├── app/                          # Main application code
│   ├── api/v1/                   # API endpoints
│   │   ├── auth.py              # Authentication endpoints
│   │   ├── chatbot.py           # Chat functionality
│   │   └── endpoints/           # Additional endpoints
│   ├── core/                    # Core functionality
│   │   ├── config.py            # Configuration management
│   │   ├── logging.py           # Logging setup
│   │   ├── metrics.py           # Prometheus metrics
│   │   ├── middleware.py        # Custom middleware
│   │   └── langgraph/           # LangGraph integration
│   ├── models/                  # Database models
│   ├── schemas/                 # Pydantic schemas
│   ├── services/                # Business logic services
│   └── utils/                   # Utility functions
├── docs/                        # Documentation
├── evals/                       # Evaluation framework
├── grafana/                     # Grafana configuration
├── prometheus/                  # Prometheus configuration
├── scripts/                     # Helper scripts
└── tests/                       # Test files
```

### File Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| API Modules | `snake_case.py` | `auth.py`, `chatbot.py` |
| Models | `singular_noun.py` | `user.py`, `session.py` |
| Schemas | `resource_action.py` | `auth.py`, `chat.py` |
| Services | `resource_service.py` | `database_service.py` |
| Utils | `functionality.py` | `auth.py`, `sanitization.py` |
| Tests | `test_*.py` | `test_auth.py` |

### Module Organization

#### API Layer (`app/api/`)
- **Purpose**: HTTP request/response handling
- **Dependencies**: Schemas, services, core modules
- **Responsibility**: Input validation, authentication, rate limiting

#### Core Layer (`app/core/`)
- **Purpose**: Application infrastructure 
- **Dependencies**: External services, configuration
- **Responsibility**: Configuration, logging, metrics, middleware

#### Models Layer (`app/models/`)
- **Purpose**: Database entity definitions
- **Dependencies**: SQLModel, database
- **Responsibility**: Data persistence, relationships

#### Services Layer (`app/services/`)
- **Purpose**: Business logic implementation
- **Dependencies**: Models, external APIs
- **Responsibility**: Data processing, business rules

#### Schemas Layer (`app/schemas/`)
- **Purpose**: Data validation and serialization
- **Dependencies**: Pydantic
- **Responsibility**: Request/response validation, documentation

### Import Guidelines

```python
# Standard library imports
import os
from typing import List, Dict

# Third-party imports  
from fastapi import APIRouter, Depends
from sqlmodel import Session

# Local imports
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import UserCreate
```

### Configuration Management

```python
# Environment-based configuration
from app.core.config import settings

# Access configuration
database_url = settings.POSTGRES_URL
debug_mode = settings.DEBUG
api_prefix = settings.API_V1_STR
```

This developer reference provides quick access to all essential information needed for efficient development and maintenance of the FastAPI LangGraph Agent Template.