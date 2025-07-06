# Deployment Guide - Boardroom Phase 3

## Overview

This guide provides comprehensive instructions for deploying the Boardroom Phase 3 application to production environments. It covers deployment strategies, infrastructure requirements, configuration management, and best practices for maintaining a reliable production system.

## Prerequisites

### System Requirements

#### Minimum Hardware Requirements
- **CPU**: 4 cores (8 cores recommended)
- **RAM**: 8GB (16GB recommended)
- **Storage**: 50GB SSD (100GB recommended)
- **Network**: 1Gbps connection

#### Software Requirements
- **Docker**: 20.10+ with Docker Compose 2.0+
- **Node.js**: 18.x or 20.x LTS
- **Python**: 3.11+
- **PostgreSQL**: 15+
- **Redis**: 7+
- **Nginx**: 1.24+ (for reverse proxy)

### Required Services
- PostgreSQL database
- Redis for caching and pub/sub
- S3-compatible storage (for backups)
- SMTP server (for emails)
- Monitoring infrastructure (Prometheus/Grafana)

## Architecture Overview

```mermaid
graph TB
    subgraph "Load Balancer"
        LB[Nginx/CloudFlare]
    end
    
    subgraph "Frontend Tier"
        FE1[Next.js App 1]
        FE2[Next.js App 2]
        FE3[Next.js App N]
    end
    
    subgraph "API Tier"
        API1[FastAPI Instance 1]
        API2[FastAPI Instance 2]
        API3[FastAPI Instance N]
    end
    
    subgraph "WebSocket Tier"
        WS1[WebSocket Server 1]
        WS2[WebSocket Server 2]
    end
    
    subgraph "Data Tier"
        PG[(PostgreSQL)]
        REDIS[(Redis)]
        S3[S3 Storage]
    end
    
    subgraph "Monitoring"
        PROM[Prometheus]
        GRAF[Grafana]
        SENTRY[Sentry]
    end
    
    LB --> FE1 & FE2 & FE3
    LB --> API1 & API2 & API3
    LB --> WS1 & WS2
    
    API1 & API2 & API3 --> PG
    API1 & API2 & API3 --> REDIS
    WS1 & WS2 --> REDIS
    
    API1 & API2 & API3 --> S3
    
    FE1 & FE2 & FE3 --> SENTRY
    API1 & API2 & API3 --> PROM
    PROM --> GRAF
```

## Deployment Strategies

### 1. Docker Compose (Development/Staging)

#### docker-compose.prod.yml

```yaml
version: '3.8'

services:
  # Frontend Service
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    environment:
      - NEXT_PUBLIC_API_URL=${API_URL}
      - NEXT_PUBLIC_WS_URL=${WS_URL}
      - NODE_ENV=production
    ports:
      - "3000:3000"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1.0'
          memory: 1G

  # Backend Service
  backend:
    build:
      context: ./
      dockerfile: Dockerfile.prod
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
      - ENVIRONMENT=production
    ports:
      - "8000:8000"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
    depends_on:
      - db
      - redis

  # Database
  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=${DB_NAME}
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - frontend
      - backend
    restart: unless-stopped

  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    restart: unless-stopped

  # Grafana
  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "3001:3000"
    depends_on:
      - prometheus
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:
```

### 2. Kubernetes Deployment

#### Frontend Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: boardroom-frontend
  namespace: boardroom
spec:
  replicas: 3
  selector:
    matchLabels:
      app: boardroom-frontend
  template:
    metadata:
      labels:
        app: boardroom-frontend
    spec:
      containers:
      - name: frontend
        image: boardroom/frontend:latest
        ports:
        - containerPort: 3000
        env:
        - name: NEXT_PUBLIC_API_URL
          valueFrom:
            configMapKeyRef:
              name: boardroom-config
              key: api.url
        - name: NODE_ENV
          value: "production"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: boardroom-frontend
  namespace: boardroom
spec:
  selector:
    app: boardroom-frontend
  ports:
  - port: 80
    targetPort: 3000
  type: ClusterIP
```

#### Backend Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: boardroom-backend
  namespace: boardroom
spec:
  replicas: 3
  selector:
    matchLabels:
      app: boardroom-backend
  template:
    metadata:
      labels:
        app: boardroom-backend
    spec:
      containers:
      - name: backend
        image: boardroom/backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: boardroom-secrets
              key: database.url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: boardroom-secrets
              key: redis.url
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: boardroom-secrets
              key: secret.key
        resources:
          requests:
            memory: "1Gi"
            cpu: "1000m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: boardroom-backend
  namespace: boardroom
spec:
  selector:
    app: boardroom-backend
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

#### Ingress Configuration

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: boardroom-ingress
  namespace: boardroom
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/websocket-services: "boardroom-backend"
spec:
  tls:
  - hosts:
    - boardroom.com
    - api.boardroom.com
    secretName: boardroom-tls
  rules:
  - host: boardroom.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: boardroom-frontend
            port:
              number: 80
  - host: api.boardroom.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: boardroom-backend
            port:
              number: 80
```

## Environment Configuration

### Production Environment Variables

#### Frontend (.env.production)

```bash
# API Configuration
NEXT_PUBLIC_API_URL=https://api.boardroom.com
NEXT_PUBLIC_API_VERSION=/api/v1
NEXT_PUBLIC_WS_URL=wss://api.boardroom.com/ws

# Feature Flags
NEXT_PUBLIC_ENABLE_MFA=true
NEXT_PUBLIC_ENABLE_OFFLINE=true
NEXT_PUBLIC_ENABLE_ANALYTICS=true

# External Services
NEXT_PUBLIC_SENTRY_DSN=https://xxx@sentry.io/yyy
NEXT_PUBLIC_GA_TRACKING_ID=G-XXXXXXXXXX

# Security
NEXT_PUBLIC_ALLOWED_ORIGINS=https://boardroom.com,https://www.boardroom.com
```

#### Backend (.env.production)

```bash
# Database
DATABASE_URL=postgresql://user:password@db-host:5432/boardroom
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40

# Redis
REDIS_URL=redis://:password@redis-host:6379/0
REDIS_POOL_SIZE=10

# Security
SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_DELTA=3600
REFRESH_TOKEN_EXPIRATION_DELTA=604800

# Email
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key
DEFAULT_FROM_EMAIL=noreply@boardroom.com

# Storage
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET=boardroom-uploads
S3_REGION=us-west-2

# Monitoring
SENTRY_DSN=https://xxx@sentry.io/yyy
PROMETHEUS_ENABLED=true
LOG_LEVEL=INFO

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=100/hour
RATE_LIMIT_AUTH=5/15minutes
```

### Secrets Management

#### Using Kubernetes Secrets

```bash
# Create secrets
kubectl create secret generic boardroom-secrets \
  --from-literal=database.url="postgresql://user:password@db:5432/boardroom" \
  --from-literal=redis.url="redis://:password@redis:6379/0" \
  --from-literal=secret.key="your-secret-key" \
  --namespace=boardroom
```

#### Using AWS Secrets Manager

```python
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# In your application
secrets = get_secret('boardroom/production')
DATABASE_URL = secrets['database_url']
```

## Database Setup

### 1. Initial Setup

```bash
# Create database
createdb boardroom_production

# Run migrations
alembic upgrade head

# Create initial admin user
python scripts/create_admin.py
```

### 2. Database Optimization

```sql
-- Performance indexes
CREATE INDEX idx_meetings_date ON meetings(date);
CREATE INDEX idx_decisions_status ON decisions(status);
CREATE INDEX idx_users_email ON users(email);

-- Partitioning for large tables
CREATE TABLE audit_logs_2024 PARTITION OF audit_logs
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

-- Vacuum and analyze
VACUUM ANALYZE;
```

### 3. Backup Configuration

```bash
#!/bin/bash
# backup.sh

# Database backup
pg_dump $DATABASE_URL | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Upload to S3
aws s3 cp backup_*.sql.gz s3://boardroom-backups/db/

# Keep only last 30 days
find . -name "backup_*.sql.gz" -mtime +30 -delete
```

## SSL/TLS Configuration

### Nginx SSL Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name boardroom.com;

    ssl_certificate /etc/nginx/ssl/boardroom.crt;
    ssl_certificate_key /etc/nginx/ssl/boardroom.key;
    
    # Modern SSL configuration
    ssl_protocols TLSv1.3 TLSv1.2;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;
    
    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Content Security Policy
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://apis.google.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' wss://api.boardroom.com https://api.boardroom.com; frame-ancestors 'none';" always;
    
    location / {
        proxy_pass http://frontend:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Let's Encrypt Setup

```bash
# Install certbot
apt-get update
apt-get install certbot python3-certbot-nginx

# Obtain certificate
certbot --nginx -d boardroom.com -d www.boardroom.com -d api.boardroom.com

# Auto-renewal
echo "0 0,12 * * * root certbot renew --quiet" >> /etc/crontab
```

## Monitoring Setup

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'boardroom-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
      
  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['postgres-exporter:9187']
      
  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['redis-exporter:9121']
```

### Grafana Dashboards

```json
{
  "dashboard": {
    "title": "Boardroom Production Metrics",
    "panels": [
      {
        "title": "API Response Time",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, http_request_duration_seconds_bucket)"
          }
        ]
      },
      {
        "title": "Active WebSocket Connections",
        "targets": [
          {
            "expr": "websocket_connections_active"
          }
        ]
      },
      {
        "title": "Database Connections",
        "targets": [
          {
            "expr": "pg_stat_database_numbackends"
          }
        ]
      }
    ]
  }
}
```

### Alerting Rules

```yaml
# alerts.yml
groups:
  - name: boardroom
    rules:
      - alert: HighResponseTime
        expr: http_request_duration_seconds_p95 > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API response time"
          
      - alert: DatabaseConnectionsHigh
        expr: pg_stat_database_numbackends > 80
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool near limit"
          
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
```

## Deployment Process

### 1. Pre-deployment Checklist

```bash
#!/bin/bash
# pre-deploy.sh

echo "Running pre-deployment checks..."

# Run tests
npm test
pytest

# Check code quality
npm run lint
black --check .
mypy .

# Security scan
npm audit
safety check

# Build artifacts
npm run build
docker build -t boardroom/frontend:latest ./frontend
docker build -t boardroom/backend:latest .

echo "Pre-deployment checks complete!"
```

### 2. Database Migrations

```bash
#!/bin/bash
# migrate.sh

# Backup current database
pg_dump $DATABASE_URL > backup_pre_migration.sql

# Run migrations
alembic upgrade head

# Verify migration
alembic current
```

### 3. Zero-Downtime Deployment

```bash
#!/bin/bash
# deploy.sh

# Blue-Green Deployment
echo "Starting blue-green deployment..."

# Deploy to green environment
kubectl set image deployment/boardroom-backend backend=boardroom/backend:$VERSION -n boardroom-green

# Wait for green to be ready
kubectl wait --for=condition=available --timeout=300s deployment/boardroom-backend -n boardroom-green

# Run smoke tests
./scripts/smoke-tests.sh https://green.boardroom.com

# Switch traffic to green
kubectl patch ingress boardroom-ingress -p '{"spec":{"rules":[{"host":"api.boardroom.com","http":{"paths":[{"backend":{"service":{"name":"boardroom-backend-green"}}}]}}]}}'

# Monitor for errors
sleep 60
ERROR_RATE=$(kubectl exec -it prometheus -- promtool query instant 'rate(http_requests_total{status=~"5.."}[5m])' | grep -o '[0-9]*\.[0-9]*')

if (( $(echo "$ERROR_RATE > 0.01" | bc -l) )); then
  echo "High error rate detected, rolling back..."
  kubectl patch ingress boardroom-ingress -p '{"spec":{"rules":[{"host":"api.boardroom.com","http":{"paths":[{"backend":{"service":{"name":"boardroom-backend-blue"}}}]}}]}}'
  exit 1
fi

echo "Deployment successful!"
```

### 4. Post-deployment Verification

```bash
#!/bin/bash
# verify.sh

# Health checks
curl -f https://api.boardroom.com/api/v1/health || exit 1
curl -f https://boardroom.com/api/health || exit 1

# Functional tests
npm run test:e2e

# Performance tests
npm run test:performance

# Security scan
npm run security:scan

echo "Post-deployment verification complete!"
```

## Rollback Procedures

### Automatic Rollback

```yaml
# Kubernetes deployment with rollback
apiVersion: apps/v1
kind: Deployment
metadata:
  name: boardroom-backend
spec:
  progressDeadlineSeconds: 600
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
```

### Manual Rollback

```bash
# Rollback to previous version
kubectl rollout undo deployment/boardroom-backend

# Rollback database migration
alembic downgrade -1

# Restore from backup
pg_restore -d boardroom_production backup_pre_deployment.sql
```

## Performance Optimization

### Frontend Optimization

```nginx
# Static asset caching
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# Gzip compression
gzip on;
gzip_types text/plain text/css text/xml text/javascript application/javascript application/json application/xml+rss;
gzip_min_length 1000;
```

### Backend Optimization

```python
# Gunicorn configuration
bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
preload_app = True
```

## Security Hardening

### System Security

```bash
# Firewall rules
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp  # SSH
ufw allow 80/tcp  # HTTP
ufw allow 443/tcp # HTTPS
ufw enable

# Fail2ban configuration
cat > /etc/fail2ban/jail.local << EOF
[sshd]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
EOF
```

### Application Security

```python
# Security middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://boardroom.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["boardroom.com", "*.boardroom.com"]
)

app.add_middleware(
    RateLimitMiddleware,
    calls=100,
    period=3600
)
```

## Maintenance Tasks

### Regular Maintenance Schedule

```yaml
# cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: boardroom-maintenance
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: maintenance
            image: boardroom/maintenance:latest
            command:
            - /bin/sh
            - -c
            - |
              # Database maintenance
              psql $DATABASE_URL -c "VACUUM ANALYZE;"
              
              # Clear old sessions
              python manage.py clear_sessions
              
              # Clean up temp files
              find /tmp -name "boardroom_*" -mtime +1 -delete
              
              # Archive old logs
              python manage.py archive_logs
```

### Backup Strategy

```bash
#!/bin/bash
# backup-strategy.sh

# Daily backups
0 2 * * * /usr/local/bin/backup-database.sh

# Weekly full backup
0 3 * * 0 /usr/local/bin/backup-full.sh

# Monthly archive
0 4 1 * * /usr/local/bin/archive-backups.sh

# Backup retention: 7 daily, 4 weekly, 12 monthly
```

## Troubleshooting

### Common Issues

#### High Memory Usage
```bash
# Check memory usage
docker stats

# Analyze memory leaks
py-spy dump --pid $(pgrep -f gunicorn)

# Restart workers
kill -HUP $(pgrep -f gunicorn)
```

#### Database Connection Issues
```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity;

-- Kill idle connections
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle' 
AND state_change < now() - interval '1 hour';
```

#### WebSocket Connection Drops
```javascript
// Implement reconnection logic
class WebSocketManager {
  reconnect() {
    setTimeout(() => {
      this.connect()
    }, Math.min(10000, 1000 * Math.pow(2, this.reconnectAttempts++)))
  }
}
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export DJANGO_DEBUG=True

# Enable query logging
export DATABASE_LOG_QUERIES=True

# Enable performance profiling
export ENABLE_PROFILING=True
```

## Disaster Recovery

### Backup Restoration

```bash
#!/bin/bash
# restore.sh

# Stop services
docker-compose down

# Restore database
pg_restore -d boardroom_production backup_latest.sql

# Restore files
aws s3 sync s3://boardroom-backups/files/ /app/media/

# Start services
docker-compose up -d

# Verify restoration
./scripts/verify-restoration.sh
```

### Failover Procedures

```bash
# Primary to secondary failover
kubectl patch service boardroom-db -p '{"spec":{"selector":{"role":"secondary"}}}'

# Update connection strings
kubectl set env deployment/boardroom-backend DATABASE_URL=$SECONDARY_DB_URL

# Verify failover
./scripts/verify-failover.sh
```

---

For additional support, refer to the [Infrastructure Documentation](./infrastructure.md) or contact the DevOps team.