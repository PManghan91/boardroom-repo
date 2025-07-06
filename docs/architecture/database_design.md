# Database Design Documentation

**Document Version**: 1.0  
**Last Updated**: January 2025  
**Author**: Founder + Claude Code  
**Audience**: Developers / Database Administrators  
**Next Review**: With schema changes  

## Overview

Boardroom AI uses PostgreSQL as its primary database with SQLModel (SQLAlchemy + Pydantic) for ORM functionality. The design supports multi-user collaboration, AI conversation persistence, and LangGraph checkpoint storage.

## Database Schema

### Entity Relationship Diagram

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│    User     │1───────*│  Boardroom  │1───────*│   Session   │
├─────────────┤         ├─────────────┤         ├─────────────┤
│ id (PK)     │         │ id (PK)     │         │ id (PK)     │
│ email       │         │ name        │         │ boardroom_id│
│ password    │         │ description │         │ user_id     │
│ full_name   │         │ owner_id(FK)│         │ title       │
│ is_active   │         │ is_active   │         │ status      │
│ is_verified │         │ max_users   │         │ started_at  │
└─────────────┘         └─────────────┘         │ ended_at    │
       │                                        └─────────────┘
       │                                                │
       └────────────────────┐                          │
                           │                          │
                           ▼                          ▼
                    ┌─────────────┐           ┌─────────────┐
                    │   Thread    │           │ LangGraph   │
                    ├─────────────┤           │ Checkpoints │
                    │ id (PK)     │           ├─────────────┤
                    │ session_id  │           │ thread_id   │
                    │ user_id     │           │ checkpoint  │
                    │ title       │           │ metadata    │
                    │ content     │           └─────────────┘
                    │ type        │
                    │ priority    │
                    └─────────────┘
```

## Core Tables

### 1. Users Table

Stores user account information and authentication data.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true NOT NULL,
    is_verified BOOLEAN DEFAULT false NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

**Indexes:**
- `idx_users_email`: For login queries
- `idx_users_active`: For filtering active users
- `idx_users_created_at`: For user analytics

**Constraints:**
- Email format validation with regex
- Unique email addresses

### 2. Boardrooms Table

Represents collaborative spaces for meetings and decisions.

```sql
CREATE TABLE boardrooms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT true NOT NULL,
    max_participants INTEGER DEFAULT 10,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

**Indexes:**
- `idx_boardrooms_owner`: Foreign key lookups
- `idx_boardrooms_active`: Active boardroom filtering
- `idx_boardrooms_name`: Name-based searches

**Constraints:**
- Name cannot be empty
- Max participants between 1-100

### 3. Sessions Table

Tracks individual meeting sessions within boardrooms.

```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    boardroom_id UUID NOT NULL REFERENCES boardrooms(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'active' NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE,
    ended_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

**Indexes:**
- `idx_sessions_boardroom`: Boardroom session lookups
- `idx_sessions_user`: User session history
- `idx_sessions_status`: Status filtering
- `idx_sessions_started_at`: Time-based queries

**Constraints:**
- Status in ('active', 'ended', 'paused')
- ended_at >= started_at

### 4. Threads Table

Stores conversation threads and discussion topics.

```sql
CREATE TABLE threads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    thread_type VARCHAR(50) DEFAULT 'discussion' NOT NULL,
    status VARCHAR(50) DEFAULT 'active' NOT NULL,
    priority INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

**Indexes:**
- `idx_threads_session`: Session thread lookups
- `idx_threads_user`: User thread history
- `idx_threads_type`: Type-based filtering
- `idx_threads_status`: Status filtering

**Constraints:**
- Type in ('discussion', 'decision', 'action_item', 'note')
- Priority between 1-5
- Status in ('active', 'resolved', 'archived')

## LangGraph Integration

### Checkpoint Tables

LangGraph uses PostgreSQL for conversation state persistence:

```sql
-- Managed by LangGraph
CREATE TABLE checkpoints (
    thread_id VARCHAR(255) NOT NULL,
    thread_ts VARCHAR(255) NOT NULL,
    parent_ts VARCHAR(255),
    checkpoint JSONB NOT NULL,
    metadata JSONB,
    PRIMARY KEY (thread_id, thread_ts)
);

CREATE TABLE checkpoint_writes (
    thread_id VARCHAR(255) NOT NULL,
    thread_ts VARCHAR(255) NOT NULL,
    task_id VARCHAR(255) NOT NULL,
    idx INTEGER NOT NULL,
    channel VARCHAR(255) NOT NULL,
    value JSONB,
    PRIMARY KEY (thread_id, thread_ts, task_id, idx)
);

CREATE TABLE checkpoint_blobs (
    thread_id VARCHAR(255) NOT NULL,
    thread_ts VARCHAR(255) NOT NULL,
    channel VARCHAR(255) NOT NULL,
    value BYTEA,
    PRIMARY KEY (thread_id, thread_ts, channel)
);
```

These tables store:
- Conversation state snapshots
- Tool execution history
- Message history
- AI decision points

## Key Design Decisions

### 1. UUID Primary Keys
- **Why**: Better for distributed systems, no sequence bottlenecks
- **Trade-off**: Slightly larger storage, non-sequential

### 2. Soft Deletes Not Used
- **Why**: Simplicity, GDPR compliance (true deletion)
- **Trade-off**: No recovery of deleted data

### 3. UTC Timestamps
- **Why**: Consistent time handling across timezones
- **Implementation**: All timestamps use `TIMESTAMP WITH TIME ZONE`

### 4. Cascade Deletes
- **Why**: Maintain referential integrity automatically
- **Risk**: Accidental data loss if not careful

### 5. JSON Storage for Flexibility
- **Used in**: LangGraph checkpoints, future metadata fields
- **Why**: Schema flexibility for evolving AI features

## Performance Optimizations

### Indexing Strategy
1. **Primary Keys**: Automatic B-tree indexes
2. **Foreign Keys**: Indexed for join performance
3. **Query Patterns**: Indexes on commonly filtered columns
4. **Composite Indexes**: For multi-column queries (future)

### Connection Pooling
```python
# Configuration
SQLALCHEMY_POOL_SIZE = 20
SQLALCHEMY_POOL_OVERFLOW = 10
SQLALCHEMY_POOL_TIMEOUT = 30
```

### Query Optimization Tips
1. Use `select()` with specific columns
2. Eager load relationships when needed
3. Batch operations where possible
4. Monitor slow queries with `pg_stat_statements`

## Migration Procedures

### Using Alembic

1. **Create Migration**:
   ```bash
   alembic revision --autogenerate -m "Description"
   ```

2. **Review Generated Migration**:
   ```bash
   # Check alembic/versions/[timestamp]_description.py
   ```

3. **Apply Migration**:
   ```bash
   alembic upgrade head
   ```

4. **Rollback if Needed**:
   ```bash
   alembic downgrade -1
   ```

### Manual Schema Updates
For development, use the migration script:
```bash
python scripts/migrate_schema.py
```

## Backup Strategy

### Daily Backups
```bash
# Automated backup script
pg_dump -h localhost -U postgres -d boardroom_prod \
  -f backup_$(date +%Y%m%d_%H%M%S).sql
```

### Point-in-Time Recovery
1. Enable WAL archiving in PostgreSQL
2. Regular base backups
3. Continuous WAL archiving

## Security Considerations

### Data Protection
1. **Passwords**: Bcrypt hashed, never stored in plain text
2. **PII**: Email addresses indexed but can be encrypted at rest
3. **Connections**: SSL required for production
4. **Permissions**: Least privilege principle

### SQL Injection Prevention
- SQLModel parameterized queries
- Input validation at API layer
- Stored procedures for complex operations (future)

## Monitoring

### Key Metrics
1. **Connection pool usage**
2. **Query execution time**
3. **Table sizes and growth**
4. **Index usage statistics**

### Health Checks
```python
# Database health check endpoint
GET /api/v1/health/services
```

## Future Enhancements

### Planned Features
1. **Audit Logging**: Track all data changes
2. **Multi-tenancy**: Organization-level isolation
3. **Full-text Search**: PostgreSQL FTS for content
4. **Time-series Data**: Meeting analytics
5. **Archival Strategy**: Move old data to cold storage

### Schema Evolution
1. **Version 1.1**: Add organization support
2. **Version 1.2**: Meeting analytics tables
3. **Version 1.3**: Integration tables
4. **Version 2.0**: Event sourcing (major refactor)

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check PostgreSQL is running
   - Verify connection string
   - Check firewall rules

2. **Migration Conflicts**
   - Ensure models match database
   - Check for pending migrations
   - Review alembic history

3. **Performance Issues**
   - Analyze slow queries
   - Check missing indexes
   - Review connection pool settings

## Related Documentation

- [System Architecture Overview](./system_overview.md)
- [API Design Patterns](./api_design.md)
- [Development Setup](../development/setup.md)
- [Troubleshooting Guide](../operations/troubleshooting.md)

---

**Need Help?** Check PostgreSQL logs or run `EXPLAIN ANALYZE` on slow queries.