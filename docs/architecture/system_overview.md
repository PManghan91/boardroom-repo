# System Architecture Overview

**Document Version**: 1.0  
**Last Updated**: January 2025  
**Author**: Founder + Claude Code  
**Audience**: Technical Team / Developers  
**Next Review**: With major architectural changes  

## Overview

Boardroom AI is a modern web application built with a microservices-oriented architecture. It combines a FastAPI backend with LangGraph AI workflows and a Next.js frontend to deliver AI-powered meeting and decision management capabilities.

## High-Level Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   API Gateway   │────▶│   Backend       │
│   (Next.js)     │     │   (FastAPI)     │     │   Services      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                        │
         └───────────────────────┴────────────────────────┘
                                 │
                    ┌────────────┴─────────────┐
                    ▼                          ▼
            ┌─────────────┐           ┌─────────────┐
            │    Redis    │           │  PostgreSQL │
            │   (Cache)   │           │  (Database) │
            └─────────────┘           └─────────────┘
                    │                          │
                    └────────────┬─────────────┘
                                 ▼
                        ┌─────────────────┐
                        │   Monitoring    │
                        │  (Prometheus/   │
                        │    Grafana)     │
                        └─────────────────┘
```

## Technology Stack

### Backend
- **FastAPI**: High-performance async Python web framework
  - Automatic OpenAPI documentation
  - Type safety with Pydantic
  - Built-in async/await support
  
- **Python 3.13**: Latest Python with performance improvements
- **LangGraph**: Stateful AI workflow orchestration
- **LangChain**: LLM integration framework
- **PostgreSQL**: Primary data store and LangGraph checkpointing
- **Redis**: High-performance caching layer
- **SQLModel**: Type-safe ORM (SQLAlchemy + Pydantic)

### Frontend
- **Next.js 15**: React framework with App Router
- **TypeScript**: Type safety across frontend
- **TailwindCSS**: Utility-first styling
- **Zustand**: State management
- **React Query**: Server state synchronization
- **Radix UI**: Accessible component primitives

### Infrastructure
- **Docker & Docker Compose**: Containerization
- **Prometheus**: Metrics collection
- **Grafana**: Metrics visualization
- **GitHub Actions**: CI/CD automation

## Core Components

### 1. API Gateway (FastAPI)

The API gateway handles all incoming requests with:
- Request routing to appropriate services
- Authentication and authorization
- Rate limiting and throttling
- Request/response transformation
- API versioning (`/api/v1/`)

### 2. Authentication Service

JWT-based authentication system:
```
User Login → Validate Credentials → Generate JWT → Return Token
                                                    ↓
Request → Verify JWT → Load User/Session → Authorize Access
```

Features:
- 24-hour token expiration
- Session management with UUID tracking
- Password hashing with bcrypt
- Role-based access control (future)

### 3. AI Service (LangGraph)

Graph-based conversation flow:
```
Start → Chat Node → Should Continue? → Yes → Tool Call → Chat Node
                           ↓
                          No → End
```

Components:
- **LangGraphAgent**: Orchestrates AI workflows
- **State Management**: PostgreSQL-backed checkpointing
- **Tool System**: Extensible tools for search, meeting management
- **Error Handling**: Retry logic with fallback models

### 4. Caching Layer (Redis)

Multi-tier caching strategy:
- **L1**: In-memory cache (1000 items, 5min TTL)
- **L2**: Redis cache (30min TTL)
- **L3**: Redis long-term (2hr TTL)

Cache categories:
- Database queries: 5 minutes
- AI operations: 30 minutes
- Auth tokens: 1 hour
- API responses: 10 minutes
- User sessions: 2 hours

### 5. Database Layer (PostgreSQL)

Primary data store with:
- User management and authentication
- Session and conversation history
- Boardroom and decision tracking
- LangGraph checkpoint storage
- Optimized indexing for performance

## API Design Patterns

### Standardized Response Format

Success response:
```json
{
    "success": true,
    "data": {...},
    "message": "Operation successful",
    "metadata": {
        "timestamp": "2025-01-07T10:30:00Z",
        "request_id": "550e8400-e29b-41d4-a716-446655440000",
        "version": "1.0.0"
    }
}
```

Error response:
```json
{
    "error": {
        "code": 400,
        "message": "Invalid request parameters",
        "type": "validation_error",
        "timestamp": "2025-01-07T10:30:00Z"
    }
}
```

### API Versioning
- URL-based: `/api/v1/`
- Header-based: `Accept: application/vnd.boardroom.v1+json`

### Rate Limiting
- Authentication endpoints: 5 req/min
- Chat endpoints: 30 req/min
- General endpoints: 60 req/min

## Security Architecture

### Defense in Depth
1. **Network Layer**: HTTPS, firewall rules
2. **Application Layer**: Input validation, sanitization
3. **Authentication**: JWT tokens, session management
4. **Authorization**: Role-based access (planned)
5. **Data Layer**: Encrypted at rest, secure connections

### Security Features
- Password strength validation
- SQL injection prevention
- XSS protection
- CORS configuration
- Environment-specific secrets

## Monitoring and Observability

### Metrics Collection
- HTTP request metrics (count, duration, status)
- AI operation metrics (inference time, tokens)
- Cache performance (hit rate, operations)
- Database connection pool metrics

### Logging Strategy
- Structured JSON logging
- Request correlation with UUIDs
- Environment-aware log levels
- Sensitive data masking

### Health Monitoring
```
/health → Basic health check
/api/v1/health/services → Detailed service status
/metrics → Prometheus metrics endpoint
```

## Scalability Considerations

### Horizontal Scaling
- Stateless API design
- Session storage in Redis
- Database connection pooling
- Load balancer ready

### Performance Optimizations
- Response caching
- Connection pooling
- JSON payload optimization
- Memory threshold monitoring
- Async request handling

## Deployment Architecture

### Development
```
Frontend (Next.js) → localhost:3000
Backend (FastAPI) → localhost:8000
PostgreSQL → localhost:5432
Redis → localhost:6379
```

### Production
```
Load Balancer
    ├── Frontend Containers (3000)
    └── Backend Containers (8000)
         ├── PostgreSQL (RDS/Supabase)
         └── Redis Cluster
```

## Key Design Decisions

### 1. Microservices Architecture
- **Why**: Scalability, maintainability, technology flexibility
- **Trade-off**: Increased complexity, network overhead

### 2. FastAPI over Django/Flask
- **Why**: Performance, automatic docs, type safety
- **Trade-off**: Smaller ecosystem, newer framework

### 3. PostgreSQL for LangGraph State
- **Why**: ACID compliance, checkpoint reliability
- **Trade-off**: Additional database load

### 4. Multi-tier Caching
- **Why**: Performance optimization, cost reduction
- **Trade-off**: Cache invalidation complexity

### 5. JWT Authentication
- **Why**: Stateless, scalable, standard
- **Trade-off**: Token revocation challenges

## Future Architecture Considerations

### Planned Enhancements
1. **Message Queue**: For async processing
2. **WebSocket Support**: Real-time collaboration
3. **Multi-tenancy**: Organization isolation
4. **Event Sourcing**: Audit trail
5. **GraphQL API**: Flexible data fetching

### Scaling Path
1. **Phase 1**: Single server deployment
2. **Phase 2**: Separate frontend/backend
3. **Phase 3**: Database read replicas
4. **Phase 4**: Microservices extraction
5. **Phase 5**: Kubernetes orchestration

## Architecture Principles

1. **Separation of Concerns**: Clear boundaries between components
2. **Fail Gracefully**: Degraded functionality over complete failure
3. **Configuration over Code**: Environment-based settings
4. **Security First**: Defense in depth approach
5. **Observable by Default**: Comprehensive monitoring

## Related Documentation

- [Database Design](./database_design.md)
- [API Design Patterns](./api_design.md)
- [LangGraph Integration](./langgraph_integration.md)
- [Deployment Guide](../deployment/deployment_guide.md)

---

**Questions?** Review the detailed component documentation or check the API documentation at `/docs`.