# Simple Deployment Guide

**Document Version**: 1.0  
**Last Updated**: January 2025  
**Author**: Founder + Claude Code  
**Audience**: Solo Developer / DevOps  
**Next Review**: With infrastructure changes  

## Overview

This guide provides step-by-step instructions for deploying Boardroom AI using Docker. The application consists of a FastAPI backend, Next.js frontend, PostgreSQL database, Redis cache, and optional monitoring stack.

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- Domain name (for production)
- SSL certificate (for production)
- PostgreSQL database (local or cloud-hosted)
- 2GB+ RAM, 10GB+ disk space

## Quick Start Deployment

### 1. Clone and Prepare

```bash
# Clone repository
git clone <repository-url>
cd boardroom-repo

# Create environment file
cp .env.example .env.production
```

### 2. Configure Environment

Edit `.env.production` with your production values:

```env
# Required Configuration
APP_ENV=production
PROJECT_NAME="Boardroom AI"
DEBUG=false

# Database (use your production database)
POSTGRES_URL="postgresql://user:password@host:5432/boardroom_prod"

# Security (generate new secrets!)
JWT_SECRET_KEY="generate-a-secure-random-string-here"
LLM_API_KEY="your-openai-api-key"

# Optional Monitoring
LANGFUSE_PUBLIC_KEY="your-langfuse-public-key"
LANGFUSE_SECRET_KEY="your-langfuse-secret-key"
```

**Important Security Notes:**
- Generate JWT secret: `openssl rand -hex 32`
- Never commit secrets to git
- Use environment variables or secrets management

### 3. Build and Deploy

```bash
# Build Docker images
make docker-build-env ENV=production

# Start all services
make docker-run-env ENV=production

# Or using docker-compose directly
docker-compose build
docker-compose up -d
```

### 4. Verify Deployment

```bash
# Check service health
curl http://localhost:8000/health

# View logs
docker-compose logs -f app

# Check all services
docker-compose ps
```

## Service Endpoints

After deployment, services are available at:

- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Frontend**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)

## Production Deployment Steps

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
```

### 2. SSL/TLS Configuration

For production, use a reverse proxy with SSL:

```nginx
# /etc/nginx/sites-available/boardroom
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Database Setup

#### Option A: Cloud Database (Recommended)
- Use Supabase, AWS RDS, or similar
- Update `POSTGRES_URL` in `.env.production`
- Ensure SSL connection is enabled

#### Option B: Local PostgreSQL
```bash
# Run database migrations
docker-compose exec app alembic upgrade head

# Create backup
pg_dump boardroom_prod > backup_$(date +%Y%m%d).sql
```

### 4. Environment-Specific Configuration

Create production overrides in `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  app:
    restart: always
    environment:
      - APP_ENV=production
      - DEBUG=false
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G

  redis:
    restart: always
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
```

Deploy with:
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Security Checklist

- [ ] Strong passwords for all services
- [ ] JWT secret key generated and secured
- [ ] Database using SSL connection
- [ ] Redis password configured
- [ ] Firewall configured (only expose 80/443)
- [ ] Regular security updates scheduled
- [ ] Backup strategy implemented
- [ ] Monitoring and alerting configured

## Monitoring Setup

### 1. Access Grafana
- URL: http://localhost:3001
- Default credentials: admin/admin
- Change password on first login

### 2. Available Dashboards
- API Performance Metrics
- Rate Limiting Statistics
- Database Performance
- System Resource Usage

### 3. Setting Up Alerts
```bash
# Example alert for high error rate
# Configure in Grafana UI under Alerting > Alert Rules
```

## Backup Procedures

### Database Backup
```bash
# Manual backup
docker-compose exec -T postgres pg_dump -U postgres boardroom_prod > backup_$(date +%Y%m%d).sql

# Automated daily backup (add to crontab)
0 2 * * * /path/to/backup-script.sh
```

### Application Backup
```bash
# Backup configuration and logs
tar -czf boardroom_backup_$(date +%Y%m%d).tar.gz \
  .env.production \
  logs/ \
  docker-compose.yml
```

## Rollback Procedures

### Quick Rollback
```bash
# Stop current deployment
docker-compose down

# Restore previous version
git checkout <previous-version-tag>

# Rebuild and restart
docker-compose build
docker-compose up -d
```

### Database Rollback
```bash
# Restore from backup
docker-compose exec -T postgres psql -U postgres boardroom_prod < backup_20250107.sql
```

## Performance Optimization

### 1. Resource Limits
Set appropriate limits in `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
```

### 2. Caching Configuration
Redis is configured with:
- Max memory: 256MB
- Eviction policy: allkeys-lru
- Persistence: AOF enabled

### 3. Application Tuning
- Worker processes: Auto-scaled based on CPU cores
- Connection pooling: Configured for PostgreSQL
- Rate limiting: Adjusted per endpoint

## Troubleshooting Deployment

### Service Won't Start
```bash
# Check logs
docker-compose logs app

# Common issues:
# - Missing environment variables
# - Database connection failed
# - Port already in use
```

### Database Connection Issues
```bash
# Test connection
docker-compose exec app python -c "from app.services.database import database_service; import asyncio; asyncio.run(database_service.initialize())"
```

### Memory Issues
```bash
# Check memory usage
docker stats

# Increase limits if needed
# Edit docker-compose.yml deploy section
```

## Maintenance Mode

To enable maintenance mode:
```bash
# Create maintenance page
echo "Under maintenance" > maintenance.html

# Update nginx to serve maintenance page
# Add to nginx config:
# location / {
#   try_files /maintenance.html @app;
# }
```

## Next Steps

1. Set up continuous deployment
2. Configure monitoring alerts
3. Implement automated backups
4. Review [Infrastructure Notes](./infrastructure.md)
5. Set up [Maintenance Procedures](../operations/maintenance.md)

## Quick Reference

### Common Commands
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f [service-name]

# Restart service
docker-compose restart [service-name]

# Update deployment
git pull
docker-compose build
docker-compose up -d
```

### Health Checks
```bash
# API health
curl http://localhost:8000/health

# Service status
docker-compose ps

# Resource usage
docker stats
```

---

**Need Help?** Review the [Troubleshooting Guide](../operations/troubleshooting.md) or check container logs with `docker-compose logs`.