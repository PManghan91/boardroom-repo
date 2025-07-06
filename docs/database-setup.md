# Database Setup for Development

This guide explains how to set up and manage the development database for Boardroom AI.

## Overview

Boardroom AI uses:
- **PostgreSQL 16** as the primary database
- **Redis 7** for caching and session management
- **Docker Compose** for easy local development

## Quick Start

### 1. Start the Development Database

```bash
./scripts/start-dev-db.sh
```

This will:
- Start PostgreSQL on port 5432
- Start Redis on port 6379
- Initialize the database with required extensions
- Show connection information

### 2. Verify Connectivity

```bash
python scripts/test_db_connection.py
```

This will test both PostgreSQL and Redis connections.

### 3. Stop the Database

```bash
./scripts/stop-dev-db.sh
```

## Database Configuration

### Connection Details

**PostgreSQL:**
- Host: `localhost`
- Port: `5432`
- Database: `boardroom_dev`
- Username: `boardroom`
- Password: `boardroom123`
- URL: `postgresql://boardroom:boardroom123@localhost:5432/boardroom_dev`

**Redis:**
- Host: `localhost`
- Port: `6379`
- Database: `0`
- URL: `redis://localhost:6379/0`

### Environment Variables

The following environment variables are used (configured in `.env.development`):

```env
# PostgreSQL (for LangGraph checkpointing)
POSTGRES_URL="postgresql://boardroom:boardroom123@localhost:5432/boardroom_dev"

# PostgreSQL (for SQLModel/async operations)
DATABASE_URL="postgresql+asyncpg://boardroom:boardroom123@localhost:5432/boardroom_dev"

# Redis
REDIS_URL="redis://localhost:6379/0"
```

## Database Management

### PgAdmin (Optional)

Start PgAdmin for visual database management:

```bash
./scripts/start-dev-db.sh --with-pgadmin
```

Access PgAdmin at: http://localhost:5050
- Email: `admin@boardroom.local`
- Password: `admin123`

### Reset Database

To completely reset the database (delete all data):

```bash
./scripts/reset-dev-db.sh
```

**Warning:** This will delete all data in the development database!

### Database Migrations

The project uses Alembic for database migrations:

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Alternative Options

### Using External PostgreSQL

If you prefer to use an external PostgreSQL instance:

1. Update `.env.development` with your connection details:
   ```env
   DATABASE_URL="postgresql+asyncpg://user:password@host:port/database"
   POSTGRES_URL="postgresql://user:password@host:port/database"
   ```

2. Ensure your PostgreSQL has the required extensions:
   ```sql
   CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
   CREATE EXTENSION IF NOT EXISTS "pgcrypto";
   ```

### Using SQLite for Development

For lightweight development without Docker:

1. Update `.env.development`:
   ```env
   DATABASE_URL="sqlite+aiosqlite:///./boardroom_dev.db"
   ```

2. Note: Some features may not work with SQLite (e.g., advanced PostgreSQL features)

## Docker Compose Files

- `docker-compose.dev.yml` - Development-specific services
- `docker-compose.yml` - Main application services

### Development Services

The `docker-compose.dev.yml` includes:
- PostgreSQL 16 with health checks
- Redis 7 with persistence
- PgAdmin (optional, with --profile tools)

### Volumes

Data is persisted in Docker volumes:
- `postgres-data` - PostgreSQL data
- `redis-data` - Redis persistence
- `pgadmin-data` - PgAdmin configuration

## Troubleshooting

### Connection Refused

If you get "connection refused" errors:

1. Check if services are running:
   ```bash
   docker ps
   ```

2. Check logs:
   ```bash
   docker-compose -f docker-compose.dev.yml logs postgres
   docker-compose -f docker-compose.dev.yml logs redis
   ```

3. Ensure ports are not in use:
   ```bash
   lsof -i :5432  # PostgreSQL
   lsof -i :6379  # Redis
   ```

### Permission Issues

If you encounter permission issues:

```bash
# Fix script permissions
chmod +x scripts/*.sh

# Fix Python script permissions
chmod +x scripts/*.py
```

### Database Not Ready

If the database isn't ready immediately:

```bash
# Wait for PostgreSQL
docker-compose -f docker-compose.dev.yml exec postgres pg_isready

# Wait for Redis
docker-compose -f docker-compose.dev.yml exec redis redis-cli ping
```

## Best Practices

1. **Never commit `.env` files** with real credentials
2. **Use different credentials** for production
3. **Regular backups** in production environments
4. **Monitor performance** with PgAdmin or Grafana
5. **Keep Docker images updated** for security

## Additional Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/16/)
- [Redis Documentation](https://redis.io/documentation)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)